import { createHash } from 'node:crypto';
import { readFile, rename, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';

const SECRET_KEY = /(authorization|password|secret|token|private.?key)/i;
const FORBIDDEN_PROFILE_KEY = /^(authorization|password|secret|token|private_key|private_key_content|passphrase)$/i;
const PRIVATE_KEY_PEM = /-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----/;

export async function readJson(path) {
  return JSON.parse(await readFile(path, 'utf8'));
}

export async function writeJsonAtomic(path, value) {
  const temporary = `${path}.tmp`;
  await writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`, { encoding: 'utf8', mode: 0o600 });
  await rename(temporary, path);
}

export function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

export async function sha256File(path) {
  return sha256(await readFile(path));
}

export function redact(value) {
  if (Array.isArray(value)) return value.map(redact);
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [key, SECRET_KEY.test(key) ? '[REDACTED]' : redact(item)])
  );
}

function requireString(value, label) {
  if (typeof value !== 'string' || value.trim() === '') throw new Error(`${label} mancante`);
  return value;
}

function requireAbsolute(value, label) {
  requireString(value, label);
  if (!value.startsWith('/')) throw new Error(`${label} deve essere un percorso assoluto`);
  if (/[\r\n\0]/.test(value)) throw new Error(`${label} contiene caratteri non validi`);
}

function requireRemoteAbsolute(value, label) {
  requireAbsolute(value, label);
  if (/\s/.test(value)) throw new Error(`${label} remoto non può contenere spazi`);
}

export function assertNoEmbeddedSecrets(value, path = 'profile') {
  if (typeof value === 'string') {
    if (PRIVATE_KEY_PEM.test(value)) throw new Error(`${path} contiene una chiave privata`);
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((item, index) => assertNoEmbeddedSecrets(item, `${path}[${index}]`));
    return;
  }
  if (!value || typeof value !== 'object') return;
  for (const [key, item] of Object.entries(value)) {
    if (FORBIDDEN_PROFILE_KEY.test(key)) {
      throw new Error(`${path}.${key} non è ammesso: usare solo riferimenti a file locali`);
    }
    assertNoEmbeddedSecrets(item, `${path}.${key}`);
  }
}

export function validateProfile(profile) {
  assertNoEmbeddedSecrets(profile);
  if (profile?.profile_version !== 1) throw new Error('profile_version deve essere 1');
  if (profile?.provider !== 'directus-over-ssh') throw new Error('provider deve essere directus-over-ssh');
  requireString(profile.id, 'id');
  for (const key of ['cms_url', 'site_url']) {
    const value = requireString(profile[key], key);
    if (!value.startsWith('https://')) throw new Error(`${key} deve usare HTTPS`);
  }
  const ssh = profile.ssh ?? {};
  for (const key of ['host', 'user']) requireString(ssh[key], `ssh.${key}`);
  if (ssh.host.startsWith('-') || ssh.user.startsWith('-')) throw new Error('host e user SSH non validi');
  if (!Number.isInteger(ssh.port) || ssh.port < 1 || ssh.port > 65535) {
    throw new Error('ssh.port non valida');
  }
  requireAbsolute(ssh.identity_file, 'ssh.identity_file');
  for (const key of ['remote_workdir', 'remote_helper']) {
    requireRemoteAbsolute(ssh[key], `ssh.${key}`);
  }
  requireRemoteAbsolute(profile.directus?.token_file, 'directus.token_file');
  for (const key of ['photos', 'galleries']) {
    requireString(profile.directus?.collections?.[key], `directus.collections.${key}`);
  }
  for (const section of ['photo', 'gallery']) {
    const fields = profile.directus?.fields?.[section];
    if (!fields || typeof fields !== 'object') throw new Error(`directus.fields.${section} mancante`);
  }
  if (!Array.isArray(profile.rebuild?.command) || profile.rebuild.command.length === 0) {
    throw new Error('rebuild.command deve essere una lista non vuota');
  }
  if (!Array.isArray(profile.verification?.routes) || profile.verification.routes.length === 0) {
    throw new Error('verification.routes deve essere una lista non vuota');
  }
  return profile;
}

export function validatePlan(plan, profileId) {
  if (plan?.plan_version !== 1) throw new Error('plan_version deve essere 1');
  if (plan.profile_id !== profileId) throw new Error('profile_id del piano non coincide con il profilo');
  requireAbsolute(plan.source_dir, 'source_dir');
  const gallery = plan.gallery ?? {};
  if (!['create', 'existing'].includes(gallery.action)) throw new Error('gallery.action non valida');
  if (gallery.action === 'existing') requireString(gallery.existing_id, 'gallery.existing_id');
  for (const key of ['slug', 'title_it', 'title_en', 'description_it', 'description_en', 'cover_file']) {
    requireString(gallery[key], `gallery.${key}`);
  }
  if (!/^[a-z0-9][a-z0-9-]*$/.test(gallery.slug)) throw new Error('gallery.slug non valido');
  if (!Array.isArray(plan.photos) || plan.photos.length === 0) throw new Error('photos deve essere non vuoto');
  const files = new Set();
  const orders = new Set();
  for (const photo of plan.photos) {
    if (!Number.isInteger(photo.order) || photo.order < 1 || orders.has(photo.order)) {
      throw new Error(`Ordine non valido o duplicato: ${photo.order}`);
    }
    orders.add(photo.order);
    for (const key of ['file', 'title_it', 'title_en', 'alt_it', 'alt_en']) {
      requireString(photo[key], `photo.${key}`);
    }
    if (files.has(photo.file)) throw new Error(`File duplicato nel piano: ${photo.file}`);
    files.add(photo.file);
    if (photo.lat != null && (typeof photo.lat !== 'number' || photo.lat < -90 || photo.lat > 90)) {
      throw new Error(`Latitudine non valida: ${photo.file}`);
    }
    if (photo.lng != null && (typeof photo.lng !== 'number' || photo.lng < -180 || photo.lng > 180)) {
      throw new Error(`Longitudine non valida: ${photo.file}`);
    }
  }
  if (!files.has(gallery.cover_file)) throw new Error('La cover non appartiene alla selezione');
  return plan;
}

export function resolvePhotoPath(plan, photo) {
  const path = resolve(plan.source_dir, photo.file);
  const source = resolve(plan.source_dir);
  if (path !== source && !path.startsWith(`${source}/`)) throw new Error(`Percorso fuori source_dir: ${photo.file}`);
  return path;
}

export function canonicalProfile(profile) {
  validateProfile(profile);
  return {
    profile_version: profile.profile_version,
    id: profile.id,
    provider: profile.provider,
    cms_url: profile.cms_url,
    site_url: profile.site_url,
    directus: profile.directus,
    rebuild: profile.rebuild,
    verification: profile.verification,
  };
}

export function mapFields(source, mapping) {
  const result = {};
  for (const [canonical, directus] of Object.entries(mapping)) {
    if (directus && source[canonical] !== undefined) result[directus] = source[canonical];
  }
  return result;
}

export function reverseFieldMap(mapping) {
  return Object.fromEntries(Object.entries(mapping).filter(([, value]) => value).map(([key, value]) => [value, key]));
}

export function fillTemplate(template, values) {
  return template.replace(/\{([a-z_]+)\}/g, (_, key) => String(values[key] ?? `{${key}}`));
}

export function shellQuote(value) {
  if (typeof value !== 'string' || /[\r\n\0]/.test(value)) throw new Error('Argomento shell non valido');
  return `'${value.replaceAll("'", "'\\''")}'`;
}

export function directusQuery(path, params = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) query.set(key, String(value));
  }
  const suffix = query.toString();
  return `${path}${suffix ? `?${suffix}` : ''}`;
}

export class DirectusClient {
  constructor(baseUrl, token, fetchImpl = fetch) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.token = token;
    this.fetch = fetchImpl;
  }

  async request(path, { method = 'GET', body, form } = {}) {
    const headers = { Authorization: `Bearer ${this.token}` };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    const response = await this.fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: form ?? (body === undefined ? undefined : JSON.stringify(body)),
    });
    const text = await response.text();
    let json = {};
    try {
      json = text ? JSON.parse(text) : {};
    } catch {
      json = { raw: text.slice(0, 500) };
    }
    if (!response.ok) {
      const safe = redact(json);
      throw new Error(`${method} ${path}: HTTP ${response.status} ${JSON.stringify(safe)}`);
    }
    return json.data;
  }
}

export function planHash(profile, plan) {
  const stablePlan = structuredClone(plan);
  delete stablePlan.approval;
  return sha256(JSON.stringify({ profile_id: profile.id, plan: stablePlan })).slice(0, 16);
}

export function localManifestPath(planPath) {
  return resolve(dirname(planPath), 'publication-manifest.json');
}
