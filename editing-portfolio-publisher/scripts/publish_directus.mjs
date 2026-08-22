#!/usr/bin/env node

import { spawnSync } from 'node:child_process';
import { mkdtemp, readFile, rm, stat, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  canonicalProfile,
  fillTemplate,
  localManifestPath,
  planHash,
  provisioningAuthorization,
  readJson,
  redact,
  resolvePhotoPath,
  sha256File,
  shellQuote,
  validatePlan,
  validateProfile,
  writeJsonAtomic,
} from './lib/publisher-core.mjs';

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const REMOTE_HELPER = join(SCRIPT_DIR, 'remote_directus.mjs');
const CORE_HELPER = join(SCRIPT_DIR, 'lib', 'publisher-core.mjs');

function option(args, name, required = false) {
  const index = args.indexOf(name);
  const value = index === -1 ? undefined : args[index + 1];
  if (required && (!value || value.startsWith('--'))) throw new Error(`${name} mancante`);
  return value;
}

function has(args, name) {
  return args.includes(name);
}

function run(program, args, { input, timeout = 180_000, quiet = false } = {}) {
  const result = spawnSync(program, args, {
    input,
    encoding: 'utf8',
    timeout,
    maxBuffer: 20 * 1024 * 1024,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    const stderr = (result.stderr || '').trim().slice(-2000);
    throw new Error(`${program} fallito (${result.status}): ${stderr}`);
  }
  if (!quiet && result.stderr) process.stderr.write(result.stderr);
  return result.stdout ?? '';
}

function target(profile) {
  return `${profile.ssh.user}@${profile.ssh.host}`;
}

function sshBase(profile) {
  return [
    '-i', profile.ssh.identity_file,
    '-p', String(profile.ssh.port),
    '-o', 'BatchMode=yes',
    '-o', 'IdentitiesOnly=yes',
    target(profile),
  ];
}

function scpBase(profile) {
  return [
    '-i', profile.ssh.identity_file,
    '-P', String(profile.ssh.port),
    '-o', 'BatchMode=yes',
    '-o', 'IdentitiesOnly=yes',
  ];
}

function remoteExec(profile, command, { input, timeout } = {}) {
  return run('ssh', [...sshBase(profile), command], { input, timeout, quiet: true });
}

function remoteJson(profile, command, envelope, { timeout } = {}) {
  const output = remoteExec(profile, command, {
    input: JSON.stringify(envelope),
    timeout,
  });
  return JSON.parse(output);
}

function remoteHelperCommand(profile, command, extra = []) {
  return ['node', profile.ssh.remote_helper, command, ...extra].map(shellQuote).join(' ');
}

function remoteSpec(profile, path) {
  if (/\s/.test(path)) throw new Error('I percorsi remoti non possono contenere spazi');
  return `${target(profile)}:${path}`;
}

async function checkLocalProfile(profile) {
  validateProfile(profile);
  const info = await stat(profile.ssh.identity_file);
  if (!info.isFile()) throw new Error('ssh.identity_file non è un file');
  if ((info.mode & 0o077) !== 0) throw new Error('La chiave SSH deve avere permessi 600 o 400');
}

async function preparePlan(planPath, profile) {
  const plan = structuredClone(await readJson(planPath));
  validatePlan(plan, profile.id);
  const basenames = new Set();
  for (const photo of plan.photos) {
    const path = resolvePhotoPath(plan, photo);
    const info = await stat(path);
    if (!info.isFile()) throw new Error(`Non è un file: ${path}`);
    const name = basename(photo.file);
    if (basenames.has(name)) throw new Error(`Due sorgenti hanno lo stesso nome base: ${name}`);
    basenames.add(name);
    photo.source_hash = await sha256File(path);
  }
  return plan;
}

async function installRemote(profile, confirmed) {
  if (!confirmed) throw new Error('install-remote richiede --confirm');
  const libDir = join(profile.ssh.remote_workdir, 'lib');
  const jobsDir = join(profile.ssh.remote_workdir, 'jobs');
  remoteExec(profile, `mkdir -p -- ${shellQuote(libDir)} ${shellQuote(jobsDir)}`);
  run('scp', [...scpBase(profile), REMOTE_HELPER, remoteSpec(profile, profile.ssh.remote_helper)], { quiet: true });
  run('scp', [...scpBase(profile), CORE_HELPER, remoteSpec(profile, join(libDir, 'publisher-core.mjs'))], { quiet: true });
  remoteExec(profile, `chmod 700 -- ${shellQuote(profile.ssh.remote_helper)}`);
  return { ok: true, installed: profile.ssh.remote_helper };
}

async function doctor(profile) {
  await checkLocalProfile(profile);
  const command = remoteHelperCommand(profile, 'doctor');
  return remoteJson(profile, command, { profile: canonicalProfile(profile) });
}

async function provision(profile, rawOptions, confirmed, confirmationHash) {
  const authorization = provisioningAuthorization(profile, rawOptions);
  if (!confirmed) {
    return {
      ok: true,
      mode: 'local-preflight',
      profile_id: authorization.profile_id,
      cms_url: authorization.cms_url,
      service_email: authorization.options.service_email,
      admin_env_file: authorization.options.admin_env_file,
      credential_path: profile.directus.token_file,
      identity: authorization.identity,
      permission_spec: authorization.permission_spec,
      authorization_hash: authorization.hash,
      apply: `ripetere il comando con --confirm --authorization-hash ${authorization.hash}`,
      ssh_opened: false,
    };
  }
  if (!confirmationHash || confirmationHash !== authorization.hash) {
    throw new Error(
      `Hash di autorizzazione non valido: eseguire di nuovo il preflight e usare --confirm --authorization-hash ${authorization.hash}`
    );
  }
  await checkLocalProfile(profile);
  const command = remoteHelperCommand(profile, 'provision', [
    '--admin-env', authorization.options.admin_env_file,
    '--service-email', authorization.options.service_email,
    '--authorization-hash', authorization.hash,
  ]);
  return remoteJson(profile, command, { profile: canonicalProfile(profile) });
}

async function inspect(profile, planPath) {
  await checkLocalProfile(profile);
  const plan = await preparePlan(planPath, profile);
  const command = remoteHelperCommand(profile, 'plan');
  return remoteJson(profile, command, { profile: canonicalProfile(profile), plan });
}

async function uploadJob(profile, plan, planPath) {
  const id = planHash(profile, plan);
  const remoteJob = join(profile.ssh.remote_workdir, 'jobs', id);
  const remoteFiles = join(remoteJob, 'files');
  remoteExec(profile, `mkdir -p -- ${shellQuote(remoteFiles)}`);
  const temporary = await mkdtemp(join(tmpdir(), 'editing-portfolio-publisher.'));
  try {
    const envelopePath = join(temporary, 'envelope.json');
    await writeFile(
      envelopePath,
      `${JSON.stringify({ profile: canonicalProfile(profile), plan }, null, 2)}\n`,
      { mode: 0o600 }
    );
    run('scp', [...scpBase(profile), envelopePath, remoteSpec(profile, join(remoteJob, 'envelope.json'))], { quiet: true });
    for (const photo of plan.photos) {
      const source = resolvePhotoPath(plan, photo);
      const destination = join(remoteFiles, basename(photo.file));
      run('scp', [...scpBase(profile), source, remoteSpec(profile, destination)], { quiet: true, timeout: 300_000 });
    }
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
  return { id, remoteJob, planPath };
}

function downloadManifest(profile, remoteJob, destination) {
  run('scp', [...scpBase(profile), remoteSpec(profile, join(remoteJob, 'manifest.json')), destination], { quiet: true });
}

async function stage(profile, planPath, confirmed, manifestOption) {
  if (!confirmed) throw new Error('stage richiede --confirm');
  await checkLocalProfile(profile);
  const plan = await preparePlan(planPath, profile);
  if (plan.approval?.approved !== true) throw new Error('Il piano deve avere approval.approved=true');
  const inspection = remoteJson(
    profile,
    remoteHelperCommand(profile, 'plan'),
    { profile: canonicalProfile(profile), plan }
  );
  const job = await uploadJob(profile, plan, planPath);
  const command = remoteHelperCommand(profile, 'stage', ['--job', job.remoteJob]);
  try {
    remoteExec(profile, command, { timeout: 900_000 });
  } catch (error) {
    if (!inspection.safe_to_stage) {
      throw new Error(`Piano bloccato: ${JSON.stringify(inspection.duplicates)}. ${error.message}`);
    }
    throw error;
  }
  const destination = resolve(manifestOption ?? localManifestPath(planPath));
  downloadManifest(profile, job.remoteJob, destination);
  const manifest = await readJson(destination);
  manifest.local_plan_path = resolve(planPath);
  await writeJsonAtomic(destination, manifest);
  return redact(manifest);
}

async function verifyLive(profile, plan) {
  const results = [];
  for (const route of profile.verification.routes) {
    const path = fillTemplate(route, { ...plan.gallery });
    const url = new URL(path, profile.site_url).toString();
    const response = await fetch(url, { redirect: 'follow' });
    const html = await response.text();
    const expected = profile.verification.expected_text
      ? fillTemplate(profile.verification.expected_text, plan.gallery)
      : null;
    const ok = response.ok && (!expected || html.includes(expected));
    results.push({ url, status: response.status, expected, ok });
  }
  return results;
}

async function release(profile, manifestPath, confirmed) {
  if (!confirmed) throw new Error('release richiede --confirm');
  await checkLocalProfile(profile);
  const manifest = await readJson(manifestPath);
  if (!manifest.remote_job) throw new Error('remote_job mancante nel manifest');
  const planPath = manifest.local_plan_path ?? join(dirname(manifestPath), 'publication-plan.json');
  const envelope = await readJson(planPath).catch(() => null);
  const command = remoteHelperCommand(profile, 'release', ['--job', manifest.remote_job]);
  remoteExec(profile, command, { timeout: 900_000 });
  downloadManifest(profile, manifest.remote_job, manifestPath);
  const updated = await readJson(manifestPath);
  updated.local_plan_path = planPath;
  await writeJsonAtomic(manifestPath, updated);
  let verification = [];
  if (envelope) verification = await verifyLive(profile, envelope);
  return { manifest: redact(updated), verification };
}

function usage() {
  return [
    'Uso:',
    '  publish_directus.mjs install-remote --profile FILE --confirm',
    '  publish_directus.mjs provision --profile FILE --admin-env FILE --service-email EMAIL [--confirm --authorization-hash HASH]',
    '  publish_directus.mjs doctor --profile FILE',
    '  publish_directus.mjs plan --profile FILE --plan FILE',
    '  publish_directus.mjs stage --profile FILE --plan FILE --confirm [--manifest FILE]',
    '  publish_directus.mjs release --profile FILE --manifest FILE --confirm',
  ].join('\n');
}

async function main() {
  const [command, ...args] = process.argv.slice(2);
  if (!command || command === '--help' || has(args, '--help')) {
    process.stdout.write(`${usage()}\n`);
    return;
  }
  const profilePath = resolve(option(args, '--profile', true));
  const profile = await readJson(profilePath);
  validateProfile(profile);
  let result;
  if (command === 'install-remote') {
    result = await installRemote(profile, has(args, '--confirm'));
  } else if (command === 'provision') {
    result = await provision(profile, {
      admin_env_file: option(args, '--admin-env', true),
      service_email: option(args, '--service-email', true),
    }, has(args, '--confirm'), option(args, '--authorization-hash'));
  } else if (command === 'doctor') {
    result = await doctor(profile);
  } else if (command === 'plan') {
    result = await inspect(profile, resolve(option(args, '--plan', true)));
  } else if (command === 'stage') {
    result = await stage(
      profile,
      resolve(option(args, '--plan', true)),
      has(args, '--confirm'),
      option(args, '--manifest')
    );
  } else if (command === 'release') {
    result = await release(profile, resolve(option(args, '--manifest', true)), has(args, '--confirm'));
  } else {
    throw new Error(`Comando sconosciuto: ${command}\n${usage()}`);
  }
  process.stdout.write(`${JSON.stringify(redact(result), null, 2)}\n`);
}

main().catch((error) => {
  process.stderr.write(`Errore: ${error.message}\n`);
  process.exitCode = 1;
});
