import { createHash } from 'node:crypto';
import { readFile, rename, writeFile } from 'node:fs/promises';
import { basename, dirname, resolve } from 'node:path';

const SECRET_KEY = /(^authorization$|authorization_header|password|secret|token|private.?key)/i;
const FORBIDDEN_PROFILE_KEY = /^(authorization|password|secret|token|private_key|private_key_content|passphrase)$/i;
const PRIVATE_KEY_PEM = /-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----/;
const INLINE_SECRET = /(authorization\s*:\s*bearer\s+\S+|\bbearer\s+[A-Za-z0-9._~+/=-]{16,}|--?(?:token|password|secret)(?:=|\s+)\S+)/ig;
const DIRECTUS_IDENTIFIER = /^[A-Za-z_][A-Za-z0-9_]*$/;
const PROFILE_ID = /^[a-z0-9][a-z0-9-]*$/;
const REQUIRED_FIELD_MAPPINGS = Object.freeze({
  photo: Object.freeze([
    'image', 'title_it', 'title_en', 'alt_it', 'alt_en', 'lat', 'lng', 'place',
    'sort', 'published', 'gallery',
  ]),
  gallery: Object.freeze([
    'slug', 'title_it', 'title_en', 'description_it', 'description_en', 'cover',
    'sort', 'published',
  ]),
});

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

function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map(
      (key) => `${JSON.stringify(key)}:${stableJson(value[key])}`
    ).join(',')}}`;
  }
  return JSON.stringify(value);
}

export async function sha256File(path) {
  return sha256(await readFile(path));
}

export function redact(value) {
  if (Array.isArray(value)) return value.map(redact);
  if (typeof value === 'string') return value.replace(INLINE_SECRET, '[REDACTED]');
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

export function normalizeHttpsUrl(value, label = 'URL') {
  const raw = requireString(value, label).trim();
  let parsed;
  try {
    parsed = new URL(raw);
  } catch {
    throw new Error(`${label} non è un URL valido`);
  }
  if (parsed.protocol !== 'https:') throw new Error(`${label} deve usare HTTPS`);
  if (!parsed.hostname) throw new Error(`${label} deve contenere un hostname`);
  if (parsed.username || parsed.password) throw new Error(`${label} non può contenere credenziali`);
  if (parsed.search) throw new Error(`${label} non può contenere query string`);
  if (parsed.hash) throw new Error(`${label} non può contenere fragment`);
  parsed.pathname = parsed.pathname.replace(/\/+$/, '') || '/';
  return `${parsed.origin}${parsed.pathname === '/' ? '' : parsed.pathname}`;
}

function requireDirectusIdentifier(value, label, { applicationCollection = false } = {}) {
  const identifier = requireString(value, label);
  if (!DIRECTUS_IDENTIFIER.test(identifier) || identifier.length > 64) {
    throw new Error(`${label} non è un identifier Directus valido`);
  }
  if (identifier === '*') throw new Error(`${label} non può essere wildcard`);
  if (applicationCollection && identifier.toLowerCase().startsWith('directus_')) {
    throw new Error(`${label} non può usare il namespace directus_`);
  }
  return identifier;
}

function validateFieldMapping(mapping, section) {
  if (!mapping || typeof mapping !== 'object' || Array.isArray(mapping)) {
    throw new Error(`directus.fields.${section} mancante`);
  }
  for (const canonical of REQUIRED_FIELD_MAPPINGS[section]) {
    if (mapping[canonical] === null || mapping[canonical] === undefined || mapping[canonical] === '') {
      throw new Error(`directus.fields.${section}.${canonical} è obbligatorio e non può essere null`);
    }
  }
  const seen = new Map();
  for (const [canonical, directus] of Object.entries(mapping)) {
    if (directus === null) continue;
    const identifier = requireDirectusIdentifier(directus, `directus.fields.${section}.${canonical}`);
    if (seen.has(identifier)) {
      throw new Error(
        `directus.fields.${section}: mapping duplicato ${identifier} per ${seen.get(identifier)} e ${canonical}`
      );
    }
    seen.set(identifier, canonical);
  }
}

export function validateServiceEmail(value) {
  const email = requireString(value, 'service_email').trim();
  if (email.length > 254 || !/^[^\s@]+@[^\s@]+$/.test(email)) {
    throw new Error('service_email non è un indirizzo email valido');
  }
  const domain = email.slice(email.lastIndexOf('@') + 1).toLowerCase();
  if (!/^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/.test(domain)) {
    throw new Error('service_email deve usare un dominio DNS valido');
  }
  const suffix = domain.slice(domain.lastIndexOf('.') + 1);
  if (['example', 'invalid', 'localhost', 'test'].includes(suffix)) {
    throw new Error(`service_email usa il dominio riservato .${suffix}`);
  }
  if (['example.com', 'example.net', 'example.org', 'example.edu'].includes(domain)) {
    throw new Error(`service_email usa il dominio documentale riservato ${domain}`);
  }
  return email.toLowerCase();
}

export function validateProvisioningOptions(options = {}, profile) {
  requireRemoteAbsolute(options.admin_env_file, 'admin_env_file');
  const serviceEmail = validateServiceEmail(options.service_email);
  if (!profile) throw new Error('profilo richiesto per validare il provisioning');
  const cmsHost = new URL(normalizeHttpsUrl(profile.cms_url, 'cms_url')).hostname.toLowerCase();
  const emailDomain = serviceEmail.slice(serviceEmail.lastIndexOf('@') + 1);
  if (cmsHost !== emailDomain && !cmsHost.endsWith(`.${emailDomain}`)) {
    throw new Error('Il dominio di service_email deve coincidere con cms_url o esserne il dominio padre');
  }
  return {
    admin_env_file: options.admin_env_file,
    service_email: serviceEmail,
  };
}

export function provisioningPermissions(profile) {
  validateRemoteProfile(profile);
  const photos = profile.directus.collections.photos;
  const galleries = profile.directus.collections.galleries;
  const photo = profile.directus.fields.photo;
  const gallery = profile.directus.fields.gallery;
  const photoAll = [...new Set(['id', ...Object.values(photo).filter(Boolean)])].sort();
  const galleryAll = [...new Set(['id', ...Object.values(gallery).filter(Boolean)])].sort();
  // Directus applica i field permissions anche durante l'upload multipart. La
  // whitelist esplicita copre i metadati file gestiti dal core senza ricorrere
  // a ['*']; campi custom vanno aggiunti deliberatamente a questa specifica.
  const directusFileCreateFields = [
    'charset', 'created_on', 'description', 'duration', 'embed', 'filename_disk',
    'filename_download', 'filesize', 'focal_point_divider', 'focal_point_x',
    'focal_point_y', 'folder', 'height', 'id', 'location', 'metadata', 'modified_by',
    'modified_on', 'storage', 'storage_divider', 'tags', 'title', 'tus_data',
    'tus_id', 'type', 'uploaded_by', 'uploaded_on', 'width',
  ];
  return [
    { collection: photos, action: 'read', fields: photoAll, permissions: {}, validation: {}, presets: null },
    {
      collection: photos, action: 'create', fields: photoAll.filter((field) => field !== 'id'),
      permissions: {}, validation: { [photo.published]: { _eq: false } },
      presets: { [photo.published]: false },
    },
    {
      collection: photos, action: 'update', fields: [photo.published],
      permissions: {}, validation: {}, presets: null,
    },
    { collection: galleries, action: 'read', fields: galleryAll, permissions: {}, validation: {}, presets: null },
    {
      collection: galleries, action: 'create', fields: galleryAll.filter((field) => field !== 'id'),
      permissions: {}, validation: { [gallery.published]: { _eq: false } },
      presets: { [gallery.published]: false },
    },
    {
      collection: galleries, action: 'update', fields: [gallery.cover, gallery.published].sort(),
      permissions: {}, validation: {}, presets: null,
    },
    {
      collection: 'directus_files', action: 'read', fields: ['filename_download', 'filesize', 'id'],
      permissions: {}, validation: {}, presets: null,
    },
    {
      collection: 'directus_files', action: 'create', fields: directusFileCreateFields,
      permissions: {}, validation: {}, presets: null,
    },
    {
      collection: 'directus_fields', action: 'read', fields: ['collection', 'field'],
      permissions: { collection: { _in: [photos, galleries] } }, validation: {}, presets: null,
    },
  ];
}

export function provisioningIdentity(profile) {
  validateRemoteProfile(profile);
  const cmsUrl = normalizeHttpsUrl(profile.cms_url, 'cms_url');
  const scope = sha256(`${profile.id}\0${cmsUrl}`).slice(0, 12);
  const label = profile.id.slice(0, 48);
  const marker = `editing-portfolio-publisher:${scope}`;
  const description = `Managed by editing-portfolio-publisher; profile=${profile.id}; scope=${scope}`;
  return {
    scope,
    marker,
    description,
    role_name: `Portfolio Publisher [${label}:${scope}]`,
    policy_name: `Portfolio Publisher Policy [${label}:${scope}]`,
  };
}

export function provisioningAuthorization(profile, rawOptions) {
  const options = validateProvisioningOptions(rawOptions, profile);
  const canonical = canonicalRemoteProfile(profile);
  const permissionSpec = provisioningPermissions(canonical);
  const identity = provisioningIdentity(canonical);
  const document = {
    authorization_version: 1,
    profile: canonical,
    options,
    identity,
    permission_spec: permissionSpec,
  };
  return {
    hash: sha256(stableJson(document)),
    options,
    identity,
    permission_spec: permissionSpec,
    profile_id: canonical.id,
    cms_url: canonical.cms_url,
  };
}

export function assertNoEmbeddedSecrets(value, path = 'profile') {
  if (typeof value === 'string') {
    if (PRIVATE_KEY_PEM.test(value)) throw new Error(`${path} contiene una chiave privata`);
    INLINE_SECRET.lastIndex = 0;
    if (INLINE_SECRET.test(value)) throw new Error(`${path} contiene una credenziale inline`);
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

export function validateRemoteProfile(profile) {
  assertNoEmbeddedSecrets(profile);
  if (profile?.profile_version !== 1) throw new Error('profile_version deve essere 1');
  if (profile?.provider !== 'directus-over-ssh') throw new Error('provider deve essere directus-over-ssh');
  const profileId = requireString(profile.id, 'id');
  if (!PROFILE_ID.test(profileId) || profileId.length > 64) throw new Error('id profilo non valido');
  for (const key of ['cms_url', 'site_url']) {
    normalizeHttpsUrl(profile[key], key);
  }
  const tokenFile = profile.directus?.token_file;
  requireRemoteAbsolute(tokenFile, 'directus.token_file');
  if (basename(tokenFile) !== 'directus-token' ||
      !tokenFile.includes('/.config/editing-portfolio-publisher/')) {
    throw new Error('directus.token_file deve stare sotto .config/editing-portfolio-publisher e terminare in directus-token');
  }
  const collections = profile.directus?.collections ?? {};
  for (const key of ['photos', 'galleries']) {
    requireDirectusIdentifier(collections[key], `directus.collections.${key}`, { applicationCollection: true });
  }
  if (collections.photos === collections.galleries) throw new Error('Le collection photos e galleries devono essere distinte');
  for (const section of ['photo', 'gallery']) {
    validateFieldMapping(profile.directus?.fields?.[section], section);
  }
  if (!Array.isArray(profile.rebuild?.command) || profile.rebuild.command.length === 0) {
    throw new Error('rebuild.command deve essere una lista non vuota');
  }
  if (!Array.isArray(profile.verification?.routes) || profile.verification.routes.length === 0) {
    throw new Error('verification.routes deve essere una lista non vuota');
  }
  return profile;
}

export function validateProfile(profile) {
  validateRemoteProfile(profile);
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
  return profile;
}

export function validatePlan(plan, profileId) {
  if (plan?.plan_version !== 2) throw new Error('plan_version deve essere 2');
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
    for (const key of ['file', 'title_it', 'title_en', 'alt_it', 'alt_en', 'place', 'location_source']) {
      requireString(photo[key], `photo.${key}`);
    }
    if (files.has(photo.file)) throw new Error(`File duplicato nel piano: ${photo.file}`);
    files.add(photo.file);
    if (typeof photo.lat !== 'number' || photo.lat < -90 || photo.lat > 90) {
      throw new Error(`Latitudine non valida: ${photo.file}`);
    }
    if (typeof photo.lng !== 'number' || photo.lng < -180 || photo.lng > 180) {
      throw new Error(`Longitudine non valida: ${photo.file}`);
    }
    if (!['exact', 'approximate'].includes(photo.location_precision)) {
      throw new Error(`Precisione geografica non valida: ${photo.file}`);
    }
    if (!['explicit', 'analysis', 'exif', 'reverse-geocoded', 'project-default', 'mixed'].includes(photo.location_source)) {
      throw new Error(`Origine geografica non valida: ${photo.file}`);
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

export function canonicalRemoteProfile(profile) {
  validateRemoteProfile(profile);
  return {
    profile_version: profile.profile_version,
    id: profile.id,
    provider: profile.provider,
    cms_url: normalizeHttpsUrl(profile.cms_url, 'cms_url'),
    site_url: normalizeHttpsUrl(profile.site_url, 'site_url'),
    directus: profile.directus,
    rebuild: profile.rebuild,
    verification: profile.verification,
  };
}

export function canonicalProfile(profile) {
  validateProfile(profile);
  return canonicalRemoteProfile(profile);
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

export class DirectusHttpError extends Error {
  constructor(message, { status, method, path, payload } = {}) {
    super(message);
    this.name = 'DirectusHttpError';
    this.status = status;
    this.method = method;
    this.path = path;
    this.payload = payload;
  }
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
      throw new DirectusHttpError(
        `${method} ${path}: HTTP ${response.status} ${JSON.stringify(safe)}`,
        { status: response.status, method, path, payload: safe }
      );
    }
    // Quasi tutta l'API di Directus incapsula la risposta in `data`, ma non
    // /server/health, che segue il formato degli health check e risponde
    // {"status":"ok"} al primo livello. Restituire json.data alla cieca faceva
    // leggere "stato mancante" da un server che aveva appena detto di stare
    // bene, e fermava la postcondizione del provisioning e ogni doctor.
    return 'data' in json ? json.data : json;
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
