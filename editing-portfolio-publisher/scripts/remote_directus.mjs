#!/usr/bin/env node

import { spawnSync } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { lstat, mkdir, open, readFile, realpath, rename, unlink } from 'node:fs/promises';
import { homedir } from 'node:os';
import { basename, dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  canonicalRemoteProfile,
  DirectusClient,
  DirectusHttpError,
  directusQuery,
  mapFields,
  normalizeHttpsUrl,
  provisioningAuthorization,
  provisioningIdentity,
  provisioningPermissions,
  readJson,
  redact,
  sha256File,
  validatePlan,
  validateRemoteProfile,
  writeJsonAtomic,
} from './lib/publisher-core.mjs';

const MANAGER = 'editing-portfolio-publisher';
const TOKEN_BASENAME = 'directus-token';

async function stdinJson() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  if (chunks.length === 0) throw new Error('Input JSON mancante');
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}

function argument(args, name) {
  const index = args.indexOf(name);
  if (index === -1 || !args[index + 1]) throw new Error(`${name} mancante`);
  return args[index + 1];
}

function parseEnv(text) {
  const values = {};
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const index = trimmed.indexOf('=');
    if (index < 1) continue;
    const key = trimmed.slice(0, index).trim();
    let value = trimmed.slice(index + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    values[key] = value;
  }
  return values;
}

async function loginAdmin(cmsUrl, email, password) {
  const response = await fetch(`${cmsUrl}/auth/login`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ email, password, mode: 'json' }),
  });
  const text = await response.text();
  let payload = null;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    throw new Error(`Login Directus: risposta non JSON (${response.status})`);
  }
  if (!response.ok) {
    const message = payload?.errors?.[0]?.message || `HTTP ${response.status}`;
    throw new Error(`Login Directus: ${message}`);
  }
  const token = payload?.data?.access_token;
  if (!token) throw new Error('Login Directus: access token amministrativo non ricevuto');
  return token;
}

async function first(client, path, label = 'record') {
  const data = await client.request(path);
  if (Array.isArray(data) && data.length > 1) {
    throw new Error(`Collisione di provisioning: trovati più record per ${label}`);
  }
  return Array.isArray(data) ? data[0] ?? null : data;
}

function relationId(value) {
  return value && typeof value === 'object' ? value.id : value;
}

function isInside(base, target) {
  const rel = relative(base, target);
  return rel === '' || (rel !== '..' && !rel.startsWith(`..${sep}`));
}

async function assertOwned(info, label) {
  if (typeof process.getuid === 'function' && info.uid !== process.getuid()) {
    throw new Error(`${label} deve appartenere all’utente remoto`);
  }
}

async function privateRegularFile(path, label, { allowMissing = false } = {}) {
  let info;
  try {
    info = await lstat(path);
  } catch (error) {
    if (allowMissing && error.code === 'ENOENT') return null;
    throw error;
  }
  if (info.isSymbolicLink() || !info.isFile()) throw new Error(`${label} deve essere un file regolare, non un symlink`);
  await assertOwned(info, label);
  if ((info.mode & 0o777) !== 0o600) throw new Error(`${label} deve avere permessi esatti 600`);
  return info;
}

async function privateDirectory(path, label) {
  const info = await lstat(path);
  if (info.isSymbolicLink() || !info.isDirectory()) {
    throw new Error(`${label} deve essere una directory reale, non un symlink`);
  }
  await assertOwned(info, label);
  if ((info.mode & 0o777) !== 0o700) throw new Error(`${label} deve avere permessi esatti 700`);
  return info;
}

async function credentialPaths(profile) {
  const root = resolve(homedir(), '.config', MANAGER);
  const tokenFile = resolve(profile.directus.token_file);
  if (!isInside(root, tokenFile) || tokenFile === root || basename(tokenFile) !== TOKEN_BASENAME) {
    throw new Error(`directus.token_file deve terminare in ${TOKEN_BASENAME} sotto ${root}`);
  }
  await mkdir(root, { recursive: true, mode: 0o700 });
  await privateDirectory(root, 'directory credenziali');
  const tokenDirectory = dirname(tokenFile);
  await mkdir(tokenDirectory, { recursive: true, mode: 0o700 });
  const parts = relative(root, tokenDirectory).split(sep).filter(Boolean);
  let cursor = root;
  for (const part of parts) {
    cursor = join(cursor, part);
    await privateDirectory(cursor, 'directory token');
  }
  const [realHome, realRoot, realTokenDirectory] = await Promise.all([
    realpath(homedir()), realpath(root), realpath(tokenDirectory),
  ]);
  if (!isInside(realHome, realRoot) || !isInside(realRoot, realTokenDirectory)) {
    throw new Error('Il percorso token risolto esce dalla directory credenziali dedicata');
  }
  return {
    root,
    tokenFile,
    bindingFile: `${tokenFile}.binding.json`,
  };
}

async function writePending(path, content) {
  const temporary = join(
    dirname(path),
    `.${basename(path)}.${process.pid}.${randomBytes(8).toString('hex')}.pending`
  );
  const handle = await open(temporary, 'wx', 0o600);
  try {
    await handle.writeFile(content, 'utf8');
    await handle.sync();
  } finally {
    await handle.close();
  }
  await privateRegularFile(temporary, 'file temporaneo');
  return temporary;
}

async function writePrivateAtomic(path, content) {
  await privateRegularFile(path, 'file privato', { allowMissing: true });
  const temporary = await writePending(path, content);
  try {
    await rename(temporary, path);
  } catch (error) {
    await unlink(temporary).catch(() => {});
    throw error;
  }
  await privateRegularFile(path, 'file privato');
}

async function readPrivateText(path, label, { allowMissing = false } = {}) {
  const info = await privateRegularFile(path, label, { allowMissing });
  if (!info) return null;
  return readFile(path, 'utf8');
}

async function readBinding(paths, profile, { allowMissing = false } = {}) {
  const text = await readPrivateText(paths.bindingFile, 'binding token', { allowMissing });
  if (text === null) return null;
  let binding;
  try {
    binding = JSON.parse(text);
  } catch {
    throw new Error('Il binding token non è JSON valido');
  }
  const cmsUrl = normalizeHttpsUrl(profile.cms_url, 'cms_url');
  if (binding.profile_id !== profile.id || binding.cms_url !== cmsUrl) {
    throw new Error('Il binding token appartiene a un altro profilo o CMS');
  }
  return binding;
}

async function readToken(path, { allowMissing = false } = {}) {
  const text = await readPrivateText(path, 'file token Directus', { allowMissing });
  if (text === null) return null;
  const token = text.trim();
  if (!token) throw new Error('Il file token Directus è vuoto');
  return token;
}

function stableValue(value) {
  if (Array.isArray(value)) return value.map(stableValue);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stableValue(value[key])]));
  }
  return value;
}

function emptyAsNull(value) {
  if (value === null || value === undefined) return null;
  if (typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === 0) return null;
  return stableValue(value);
}

function normalizePermission(permission) {
  return {
    collection: permission.collection,
    action: permission.action,
    fields: [...(permission.fields ?? [])].sort(),
    permissions: emptyAsNull(permission.permissions),
    validation: emptyAsNull(permission.validation),
    presets: emptyAsNull(permission.presets),
  };
}

function permissionKey(permission) {
  return `${permission.collection}/${permission.action}`;
}

function samePermission(left, right) {
  return JSON.stringify(normalizePermission(left)) === JSON.stringify(normalizePermission(right));
}

async function listPolicyPermissions(client, policyId) {
  return client.request(directusQuery('/permissions', {
    'filter[policy][_eq]': policyId,
    limit: -1,
    fields: 'id,collection,action,fields,permissions,validation,presets,policy',
  }));
}

function auditPolicyPermissions(existing, required) {
  const requiredByKey = new Map(required.map((item) => [permissionKey(item), item]));
  const existingByKey = new Map();
  for (const item of existing) {
    const key = permissionKey(item);
    if (existingByKey.has(key)) throw new Error(`Permesso duplicato nella policy: ${key}`);
    existingByKey.set(key, item);
    const expected = requiredByKey.get(key);
    if (!expected) throw new Error(`Permesso extra nella policy tecnica: ${key}`);
    if (!samePermission(item, expected)) throw new Error(`Permesso non conforme nella policy tecnica: ${key}`);
  }
  return required.filter((item) => !existingByKey.has(permissionKey(item)));
}

async function listAccess(client, filterName, value) {
  if (!value) return [];
  return client.request(directusQuery('/access', {
    [`filter[${filterName}][_eq]`]: value,
    limit: -1,
    fields: 'id,role,user,policy',
  }));
}

async function auditAccess(client, { roleId, policyId, userId, requireLink = false }) {
  const [roleAccess, policyAccess, userAccess] = await Promise.all([
    listAccess(client, 'role', roleId),
    listAccess(client, 'policy', policyId),
    listAccess(client, 'user', userId),
  ]);
  if (userAccess.length) throw new Error('L’utente tecnico non deve avere policy assegnate direttamente');
  const roleUnexpected = roleAccess.filter((item) => relationId(item.policy) !== policyId || relationId(item.user));
  const policyUnexpected = policyAccess.filter((item) => relationId(item.role) !== roleId || relationId(item.user));
  if (roleUnexpected.length || policyUnexpected.length) {
    throw new Error('Ruolo o policy tecnica hanno relazioni di accesso extra');
  }
  const links = roleAccess.filter((item) => relationId(item.policy) === policyId);
  if (links.length > 1) throw new Error('Collegamento ruolo-policy duplicato');
  if (requireLink && links.length !== 1) throw new Error('Collegamento ruolo-policy mancante');
  return links[0] ?? null;
}

async function inspectToken(paths, cmsUrl, expectedUserId) {
  const token = await readToken(paths.tokenFile, { allowMissing: true });
  if (!token) return { token: null, state: 'missing', me: null };
  const tokenClient = new DirectusClient(cmsUrl, token);
  let me;
  try {
    me = await tokenClient.request('/users/me?fields=id,role,status,external_identifier');
  } catch (error) {
    if (error instanceof DirectusHttpError && error.status === 401) {
      return { token: null, state: 'unauthorized', me: null };
    }
    throw error;
  }
  if (!expectedUserId || me?.id !== expectedUserId) {
    throw new Error('Collisione token: il file appartiene a un altro utente Directus');
  }
  return { token, state: 'valid', me };
}

async function persistJournal(path, journal) {
  journal.updated_at = new Date().toISOString();
  await writePrivateAtomic(path, `${JSON.stringify(journal, null, 2)}\n`);
}

export async function provision(profile, rawOptions) {
  const canonical = canonicalRemoteProfile(profile);
  const authorization = provisioningAuthorization(canonical, rawOptions);
  if (!rawOptions.authorization_hash || rawOptions.authorization_hash !== authorization.hash) {
    throw new Error('authorization_hash remoto non coincide con il preflight approvato');
  }

  const identity = provisioningIdentity(canonical);
  const paths = await credentialPaths(canonical);
  const journalFile = join(paths.root, `provision-${identity.scope}.json`);
  const journal = {
    journal_version: 1,
    status: 'preflight',
    authorization_hash: authorization.hash,
    profile_id: canonical.id,
    cms_url: canonical.cms_url,
    service_email: authorization.options.service_email,
    identity: {
      marker: identity.marker,
      role_name: identity.role_name,
      policy_name: identity.policy_name,
    },
    resources: {},
    mutations: [],
    created_at: new Date().toISOString(),
  };
  await persistJournal(journalFile, journal);

  try {
    await privateRegularFile(authorization.options.admin_env_file, 'file amministrativo Directus');
    const env = parseEnv(await readFile(authorization.options.admin_env_file, 'utf8'));
    if (!env.ADMIN_EMAIL || !env.ADMIN_PASSWORD || !env.PUBLIC_URL) {
      throw new Error('ADMIN_EMAIL, ADMIN_PASSWORD o PUBLIC_URL mancanti nel file amministrativo remoto');
    }
    const trustedCmsUrl = normalizeHttpsUrl(env.PUBLIC_URL, 'PUBLIC_URL');
    if (trustedCmsUrl !== canonical.cms_url) {
      throw new Error('PUBLIC_URL remoto non coincide esattamente con cms_url approvato');
    }
    const adminToken = await loginAdmin(trustedCmsUrl, env.ADMIN_EMAIL, env.ADMIN_PASSWORD);
    const client = new DirectusClient(trustedCmsUrl, adminToken);
    const requiredPermissions = provisioningPermissions(canonical);
    const existingBinding = await readBinding(paths, canonical, { allowMissing: true });

    // Preflight Directus completamente read-only. Collisioni omonime o stato
    // sovrapermissivo vengono rifiutati prima di creare qualunque record.
    let [user, role, policy] = await Promise.all([
      first(client, directusQuery('/users', {
        'filter[email][_eq]': authorization.options.service_email,
        limit: 2,
        fields: 'id,email,role,status,first_name,last_name,external_identifier',
      }), `utente ${authorization.options.service_email}`),
      first(client, directusQuery('/roles', {
        'filter[name][_eq]': identity.role_name,
        limit: 2,
        fields: 'id,name,description',
      }), `ruolo ${identity.role_name}`),
      first(client, directusQuery('/policies', {
        'filter[name][_eq]': identity.policy_name,
        limit: 2,
        fields: 'id,name,description,admin_access,app_access',
      }), `policy ${identity.policy_name}`),
    ]);

    if (role && role.description !== identity.description) {
      throw new Error('Collisione: il ruolo namespaced esistente non è gestito da questa skill');
    }
    if (policy && (policy.description !== identity.description || policy.admin_access || policy.app_access)) {
      throw new Error('Collisione: la policy namespaced non è minima o non è gestita da questa skill');
    }

    const tokenState = await inspectToken(paths, trustedCmsUrl, user?.id ?? null);
    let legacyAdoption = false;
    if (user) {
      if (user.external_identifier !== identity.marker) {
        legacyAdoption = !user.external_identifier &&
          user.first_name === 'Portfolio' && user.last_name === 'Publisher' &&
          tokenState.state === 'valid';
        if (!legacyAdoption) {
          throw new Error('Collisione: l’email appartiene a un utente non gestito dalla skill');
        }
      }
      const currentRole = relationId(user.role);
      if (!legacyAdoption && currentRole && role && currentRole !== role.id) {
        throw new Error('L’utente tecnico gestito appartiene a un ruolo inatteso');
      }
    }

    if (existingBinding) {
      if (!user || !role || !policy || existingBinding.user_id !== user.id ||
          existingBinding.role_id !== role.id || existingBinding.policy_id !== policy.id ||
          existingBinding.marker !== identity.marker) {
        throw new Error('Il binding token non coincide con le identità Directus esistenti');
      }
    }

    if (policy) auditPolicyPermissions(await listPolicyPermissions(client, policy.id), requiredPermissions);
    await auditAccess(client, {
      roleId: role?.id,
      policyId: policy?.id,
      userId: user?.id,
      requireLink: false,
    });

    journal.status = 'applying';
    await persistJournal(journalFile, journal);

    // Se l’utente non esiste, questa resta la prima mutazione Directus: Directus
    // valida l’email su un account draft privo di ruolo e token.
    let userCreated = false;
    if (!user) {
      user = await client.request('/users', {
        method: 'POST',
        body: {
          email: authorization.options.service_email,
          first_name: 'Portfolio',
          last_name: 'Publisher',
          external_identifier: identity.marker,
          status: 'draft',
        },
      });
      userCreated = true;
      journal.resources.user_id = user.id;
      journal.mutations.push('create-user-draft');
      await persistJournal(journalFile, journal);
    } else {
      journal.resources.user_id = user.id;
    }

    if (!role) {
      role = await client.request('/roles', {
        method: 'POST',
        body: {
          name: identity.role_name,
          icon: 'photo_library',
          description: identity.description,
        },
      });
      journal.mutations.push('create-role');
    }
    journal.resources.role_id = role.id;
    await persistJournal(journalFile, journal);

    if (!policy) {
      policy = await client.request('/policies', {
        method: 'POST',
        body: {
          name: identity.policy_name,
          icon: 'photo_library',
          description: identity.description,
          admin_access: false,
          app_access: false,
          enforce_tfa: false,
        },
      });
      journal.mutations.push('create-policy');
    }
    journal.resources.policy_id = policy.id;
    await persistJournal(journalFile, journal);

    let permissionsCreated = 0;
    const missingPermissions = auditPolicyPermissions(
      await listPolicyPermissions(client, policy.id),
      requiredPermissions
    );
    for (const permission of missingPermissions) {
      await client.request('/permissions', {
        method: 'POST',
        body: { policy: policy.id, ...permission },
      });
      permissionsCreated += 1;
      journal.mutations.push(`create-permission:${permissionKey(permission)}`);
      await persistJournal(journalFile, journal);
    }
    auditPolicyPermissions(await listPolicyPermissions(client, policy.id), requiredPermissions);

    // Il ruolo diventa efficace soltanto dopo che l’intera matrice è presente.
    let access = await auditAccess(client, {
      roleId: role.id,
      policyId: policy.id,
      userId: user.id,
      requireLink: false,
    });
    if (!access) {
      access = await client.request('/access', {
        method: 'POST',
        body: { role: role.id, policy: policy.id },
      });
      journal.mutations.push('create-role-policy-access');
    }
    journal.resources.access_id = access.id;
    await auditAccess(client, {
      roleId: role.id,
      policyId: policy.id,
      userId: user.id,
      requireLink: true,
    });
    await persistJournal(journalFile, journal);

    let staticToken = tokenState.token;
    const credentialRotated = !staticToken;
    if (credentialRotated) staticToken = randomBytes(32).toString('hex');
    let tokenPending = null;
    if (credentialRotated) tokenPending = await writePending(paths.tokenFile, `${staticToken}\n`);

    const currentRole = relationId(user.role);
    const userPatch = {
      role: role.id,
      status: 'active',
      external_identifier: identity.marker,
    };
    if (credentialRotated) userPatch.token = staticToken;
    const needsPatch = userCreated || legacyAdoption || currentRole !== role.id ||
      user.status !== 'active' || user.external_identifier !== identity.marker || credentialRotated;
    if (needsPatch) {
      try {
        user = await client.request(`/users/${encodeURIComponent(user.id)}`, {
          method: 'PATCH',
          body: userPatch,
        });
      } catch (error) {
        if (tokenPending) await unlink(tokenPending).catch(() => {});
        throw error;
      }
      journal.mutations.push('activate-service-user');
      await persistJournal(journalFile, journal);
    }

    const candidateClient = new DirectusClient(trustedCmsUrl, staticToken);
    let candidateMe;
    try {
      candidateMe = await candidateClient.request('/users/me?fields=id,role,status,external_identifier');
    } catch (error) {
      if (tokenPending) journal.token_pending_file = tokenPending;
      throw error;
    }
    if (candidateMe?.id !== user.id || relationId(candidateMe.role) !== role.id ||
        candidateMe.status !== 'active' || candidateMe.external_identifier !== identity.marker) {
      if (tokenPending) journal.token_pending_file = tokenPending;
      throw new Error('Il token candidato non certifica l’identità tecnica attesa');
    }
    if (tokenPending) {
      await privateRegularFile(paths.tokenFile, 'file token Directus', { allowMissing: true });
      await rename(tokenPending, paths.tokenFile);
      await privateRegularFile(paths.tokenFile, 'file token Directus');
    }

    const binding = {
      binding_version: 1,
      profile_id: canonical.id,
      cms_url: trustedCmsUrl,
      user_id: user.id,
      role_id: role.id,
      policy_id: policy.id,
      marker: identity.marker,
      authorization_hash: authorization.hash,
    };
    await writePrivateAtomic(paths.bindingFile, `${JSON.stringify(binding, null, 2)}\n`);
    journal.binding_written = true;
    await persistJournal(journalFile, journal);

    const postcondition = await doctor(canonical);
    journal.status = 'complete';
    journal.postcondition = { ok: true };
    delete journal.token_pending_file;
    await persistJournal(journalFile, journal);

    return {
      ok: true,
      role_id: role.id,
      policy_id: policy.id,
      user_id: user.id,
      access_id: access.id,
      service_email: authorization.options.service_email,
      permissions_created: permissionsCreated,
      credential_rotated: credentialRotated,
      token_file: paths.tokenFile,
      binding_file: paths.bindingFile,
      journal_file: journalFile,
      doctor: postcondition,
    };
  } catch (error) {
    journal.status = 'failed';
    journal.error = String(error.message || error).slice(0, 2000);
    await persistJournal(journalFile, journal).catch(() => {});
    throw new Error(`${error.message}; journal=${journalFile}`);
  }
}

async function context(profile) {
  const canonical = canonicalRemoteProfile(profile);
  const paths = await credentialPaths(canonical);
  const binding = await readBinding(paths, canonical);
  const token = await readToken(paths.tokenFile);
  const client = new DirectusClient(binding.cms_url, token);
  const me = await client.request('/users/me?fields=id,role,status,external_identifier');
  if (me?.id !== binding.user_id || relationId(me.role) !== binding.role_id ||
      me.status !== 'active' || me.external_identifier !== binding.marker) {
    throw new Error('Identità tecnica non coerente con il binding token');
  }
  return { profile: canonical, client, binding, me };
}

function mappedFields(mapping, required) {
  return required.map((name) => mapping[name]).filter(Boolean);
}

async function checkEffectivePermissions(profile, client) {
  const effective = await client.request('/permissions/me');
  const required = provisioningPermissions(profile);
  const problems = [];
  const requiredKeys = new Set();
  for (const permission of required) {
    const key = permissionKey(permission);
    requiredKeys.add(key);
    const actual = effective?.[permission.collection]?.[permission.action];
    const expectedAccess = emptyAsNull(permission.permissions) ? 'partial' : 'full';
    if (actual?.access !== expectedAccess) {
      problems.push(`${key}: access=${actual?.access ?? 'none'}, atteso=${expectedAccess}`);
      continue;
    }
    const actualFields = [...(actual.fields ?? [])].sort();
    const expectedFields = [...permission.fields].sort();
    if (JSON.stringify(actualFields) !== JSON.stringify(expectedFields)) {
      problems.push(`${key}: campi effettivi non conformi`);
    }
  }
  if (problems.length) throw new Error(`Permessi tecnici non conformi: ${problems.join('; ')}`);

  const withDelete = [];
  const extras = [];
  for (const [collection, actions] of Object.entries(effective ?? {})) {
    for (const [action, detail] of Object.entries(actions ?? {})) {
      if (!detail?.access || detail.access === 'none') continue;
      const key = `${collection}/${action}`;
      if (action === 'delete') withDelete.push(collection);
      if (!requiredKeys.has(key)) extras.push({ collection, action, access: detail.access });
    }
  }
  if (withDelete.length) {
    throw new Error(`L’identità tecnica non deve concedere delete: ${[...new Set(withDelete)].join(', ')}`);
  }
  return {
    required: [...requiredKeys],
    no_delete: true,
    extra_access: extras,
  };
}

async function checkSchema(profile, client) {
  const checks = [
    {
      collection: profile.directus.collections.photos,
      mapping: profile.directus.fields.photo,
    },
    {
      collection: profile.directus.collections.galleries,
      mapping: profile.directus.fields.gallery,
    },
  ];
  const report = {};
  for (const check of checks) {
    let fields;
    try {
      fields = await client.request(`/fields/${encodeURIComponent(check.collection)}`);
    } catch (error) {
      if (/HTTP 403/.test(error.message)) {
        throw new Error(
          `Schema ${check.collection} non leggibile: assegna directus_fields/read alla policy tecnica`
        );
      }
      throw error;
    }
    const present = new Set(fields.map((item) => item.field));
    const expected = Object.values(check.mapping).filter(Boolean);
    const missing = expected.filter((field) => !present.has(field));
    if (missing.length) throw new Error(`Campi mancanti in ${check.collection}: ${missing.join(', ')}`);
    report[check.collection] = { fields: present.size, required: expected };
  }
  return report;
}

async function listState(profile, client) {
  const photoMap = profile.directus.fields.photo;
  const galleryMap = profile.directus.fields.gallery;
  const photosCollection = profile.directus.collections.photos;
  const galleriesCollection = profile.directus.collections.galleries;
  const galleryFields = ['id', ...new Set(mappedFields(galleryMap, ['slug', 'title_it', 'sort', 'published', 'cover']))];
  const photoFields = ['id', ...new Set(mappedFields(photoMap, ['image', 'title_it', 'title_en', 'sort', 'published', 'gallery', 'source_hash']))];
  const [galleries, photos, files] = await Promise.all([
    client.request(directusQuery(`/items/${encodeURIComponent(galleriesCollection)}`, { limit: -1, fields: galleryFields.join(',') })),
    client.request(directusQuery(`/items/${encodeURIComponent(photosCollection)}`, { limit: -1, fields: photoFields.join(',') })),
    client.request(directusQuery('/files', { limit: -1, fields: 'id,filename_download,filesize' })),
  ]);
  return { galleries, photos, files };
}

function getMapped(item, mapping, canonical) {
  const field = mapping[canonical];
  return field ? item[field] : undefined;
}

async function inspectPlan(profile, plan, client) {
  validatePlan(plan, profile.id);
  const state = await listState(profile, client);
  const photoMap = profile.directus.fields.photo;
  const galleryMap = profile.directus.fields.gallery;
  const fileNames = new Set(state.files.map((item) => item.filename_download));
  const titles = new Set(
    state.photos.flatMap((item) => [getMapped(item, photoMap, 'title_it'), getMapped(item, photoMap, 'title_en')])
      .filter(Boolean)
      .map((value) => String(value).toLowerCase())
  );
  const hashes = new Set(
    state.photos.map((item) => getMapped(item, photoMap, 'source_hash')).filter(Boolean)
  );
  const galleryBySlug = state.galleries.find(
    (item) => getMapped(item, galleryMap, 'slug') === plan.gallery.slug
  );
  const duplicateFiles = plan.photos.filter((photo) => fileNames.has(photo.file)).map((photo) => photo.file);
  const duplicateTitles = plan.photos
    .filter((photo) => titles.has(photo.title_it.toLowerCase()) || titles.has(photo.title_en.toLowerCase()))
    .map((photo) => photo.title_it);
  const duplicateHashes = plan.photos.filter((photo) => photo.source_hash && hashes.has(photo.source_hash)).map((photo) => photo.file);

  return {
    counts: {
      galleries: state.galleries.length,
      photos: state.photos.length,
      files: state.files.length,
    },
    gallery: {
      action: plan.gallery.action,
      slug: plan.gallery.slug,
      existing_id: plan.gallery.existing_id ?? null,
      slug_already_exists: galleryBySlug?.id ?? null,
    },
    duplicates: {
      files: duplicateFiles,
      titles: duplicateTitles,
      hashes: duplicateHashes,
    },
    safe_to_stage:
      duplicateFiles.length === 0 &&
      duplicateTitles.length === 0 &&
      duplicateHashes.length === 0 &&
      (plan.gallery.action === 'existing' || !galleryBySlug),
    state,
  };
}

export async function doctor(profile) {
  const { profile: canonical, client } = await context(profile);
  const health = await client.request('/server/health');
  if (health?.status !== 'ok') throw new Error(`Directus health non OK: ${health?.status ?? 'mancante'}`);
  const permissions = await checkEffectivePermissions(canonical, client);
  const schema = await checkSchema(canonical, client);
  return {
    ok: true,
    profile_id: canonical.id,
    cms_status: health.status,
    permissions,
    schema,
  };
}

function maxSort(items, mapping) {
  return Math.max(0, ...items.map((item) => Number(getMapped(item, mapping, 'sort')) || 0));
}

async function uploadFile(client, path, fileName) {
  const form = new FormData();
  form.append('file', new Blob([await readFile(path)]), fileName);
  return client.request('/files', { method: 'POST', form });
}

async function stage(jobPath) {
  const envelope = await readJson(join(jobPath, 'envelope.json'));
  const { profile, plan } = envelope;
  validateRemoteProfile(profile);
  validatePlan(plan, profile.id);
  if (plan.approval?.approved !== true) throw new Error('Il piano non risulta approvato');
  const { client } = await context(profile);
  await checkSchema(profile, client);
  const manifestPath = join(jobPath, 'manifest.json');
  let manifest;
  try {
    manifest = await readJson(manifestPath);
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    manifest = {
      manifest_version: 1,
      profile_id: profile.id,
      status: 'staging',
      remote_job: jobPath,
      gallery: null,
      photos: [],
      created_at: new Date().toISOString(),
    };
  }

  const inspection = await inspectPlan(profile, plan, client);
  if (!manifest.gallery && !inspection.safe_to_stage) {
    throw new Error(`Possibili duplicati: ${JSON.stringify(inspection.duplicates)}`);
  }

  const photoMap = profile.directus.fields.photo;
  const galleryMap = profile.directus.fields.gallery;
  const photosCollection = profile.directus.collections.photos;
  const galleriesCollection = profile.directus.collections.galleries;
  const gallerySort = plan.gallery.sort ?? maxSort(inspection.state.galleries, galleryMap) + 1;
  const photoSortStart = maxSort(inspection.state.photos, photoMap) + 1;

  if (!manifest.gallery) {
    if (plan.gallery.action === 'existing') {
      manifest.gallery = { id: plan.gallery.existing_id, created: false, slug: plan.gallery.slug };
    } else {
      const body = mapFields(
        { ...plan.gallery, sort: gallerySort, published: false, cover: null },
        galleryMap
      );
      const gallery = await client.request(`/items/${encodeURIComponent(galleriesCollection)}`, {
        method: 'POST',
        body,
      });
      manifest.gallery = { id: gallery.id, created: true, slug: plan.gallery.slug };
    }
    await writeJsonAtomic(manifestPath, manifest);
  }

  for (let index = 0; index < plan.photos.length; index += 1) {
    const planned = plan.photos[index];
    let entry = manifest.photos.find((item) => item.file === planned.file);
    if (!entry) {
      entry = {
        file: planned.file,
        order: planned.order,
        sha256: planned.source_hash ?? await sha256File(join(jobPath, 'files', basename(planned.file))),
        directus_file_id: null,
        directus_photo_id: null,
      };
      manifest.photos.push(entry);
      await writeJsonAtomic(manifestPath, manifest);
    }
    if (!entry.directus_file_id) {
      const file = await uploadFile(client, join(jobPath, 'files', basename(planned.file)), basename(planned.file));
      entry.directus_file_id = file.id;
      await writeJsonAtomic(manifestPath, manifest);
    }
    if (!entry.directus_photo_id) {
      const canonical = {
        ...planned,
        image: entry.directus_file_id,
        source_hash: entry.sha256,
        sort: photoSortStart + index,
        published: false,
        gallery: manifest.gallery.id,
      };
      const body = mapFields(canonical, photoMap);
      const photo = await client.request(`/items/${encodeURIComponent(photosCollection)}`, {
        method: 'POST',
        body,
      });
      entry.directus_photo_id = photo.id;
      await writeJsonAtomic(manifestPath, manifest);
    }
  }

  if (manifest.gallery.created) {
    const cover = manifest.photos.find((item) => item.file === plan.gallery.cover_file);
    const body = mapFields({ cover: cover.directus_file_id }, galleryMap);
    await client.request(`/items/${encodeURIComponent(galleriesCollection)}/${manifest.gallery.id}`, {
      method: 'PATCH',
      body,
    });
  }
  manifest.status = 'staged';
  manifest.staged_at = new Date().toISOString();
  await writeJsonAtomic(manifestPath, manifest);
  return manifest;
}

async function release(jobPath) {
  const envelope = await readJson(join(jobPath, 'envelope.json'));
  const { profile, plan } = envelope;
  validateRemoteProfile(profile);
  validatePlan(plan, profile.id);
  const manifestPath = join(jobPath, 'manifest.json');
  const manifest = await readJson(manifestPath);
  if (!['staged', 'release_partial'].includes(manifest.status)) {
    throw new Error(`Manifest non rilasciabile: ${manifest.status}`);
  }
  const { client } = await context(profile);
  const photoMap = profile.directus.fields.photo;
  const galleryMap = profile.directus.fields.gallery;
  const photosCollection = profile.directus.collections.photos;
  const galleriesCollection = profile.directus.collections.galleries;
  manifest.status = 'release_partial';
  await writeJsonAtomic(manifestPath, manifest);

  for (const photo of manifest.photos) {
    await client.request(`/items/${encodeURIComponent(photosCollection)}/${photo.directus_photo_id}`, {
      method: 'PATCH',
      body: mapFields({ published: true }, photoMap),
    });
  }
  if (manifest.gallery.created) {
    await client.request(`/items/${encodeURIComponent(galleriesCollection)}/${manifest.gallery.id}`, {
      method: 'PATCH',
      body: mapFields({ published: true }, galleryMap),
    });
  }

  const [command, ...args] = profile.rebuild.command;
  const rebuild = spawnSync(command, args, { encoding: 'utf8', timeout: 180_000 });
  if (rebuild.error) throw rebuild.error;
  if (rebuild.status !== 0) {
    throw new Error(`Rebuild fallito con codice ${rebuild.status}: ${(rebuild.stderr || '').slice(-1000)}`);
  }
  manifest.status = 'released';
  manifest.released_at = new Date().toISOString();
  manifest.rebuild = { command: basename(command), exit_code: rebuild.status };
  await writeJsonAtomic(manifestPath, manifest);
  return manifest;
}

function jobArgument(args) {
  const index = args.indexOf('--job');
  if (index === -1 || !args[index + 1]) throw new Error('--job mancante');
  const path = resolve(args[index + 1]);
  if (/\s/.test(path)) throw new Error('Il percorso del job non può contenere spazi');
  return path;
}

async function main() {
  const [command, ...args] = process.argv.slice(2);
  let result;
  if (command === 'provision') {
    const { profile } = await stdinJson();
    result = await provision(profile, {
      admin_env_file: argument(args, '--admin-env'),
      service_email: argument(args, '--service-email'),
      authorization_hash: argument(args, '--authorization-hash'),
    });
  } else if (command === 'doctor') {
    const { profile } = await stdinJson();
    result = await doctor(profile);
  } else if (command === 'plan') {
    const { profile, plan } = await stdinJson();
    const { client } = await context(profile);
    await checkSchema(profile, client);
    const inspection = await inspectPlan(profile, plan, client);
    result = { ...inspection, state: undefined };
  } else if (command === 'stage') {
    result = await stage(jobArgument(args));
  } else if (command === 'release') {
    result = await release(jobArgument(args));
  } else {
    throw new Error('Uso: remote_directus.mjs provision|doctor|plan|stage|release');
  }
  process.stdout.write(`${JSON.stringify(redact(result), null, 2)}\n`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    process.stderr.write(`Errore: ${error.message}\n`);
    process.exitCode = 1;
  });
}
