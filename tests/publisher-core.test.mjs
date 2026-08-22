import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

import {
  assertNoEmbeddedSecrets,
  canonicalProfile,
  mapFields,
  planHash,
  provisioningAuthorization,
  provisioningPermissions,
  redact,
  resolvePhotoPath,
  shellQuote,
  validatePlan,
  validateProfile,
  validateProvisioningOptions,
  validateRemoteProfile,
  validateServiceEmail,
} from '../editing-portfolio-publisher/scripts/lib/publisher-core.mjs';

function profile() {
  return {
    profile_version: 1,
    id: 'test-site',
    provider: 'directus-over-ssh',
    cms_url: 'https://cms.giuseppelupo.net',
    site_url: 'https://portfolio.giuseppelupo.net',
    ssh: {
      host: 'example.com',
      port: 22,
      user: 'publisher',
      identity_file: '/Users/Test User/.ssh/id_ed25519',
      remote_workdir: '/home/publisher/.local/share/editing-portfolio-publisher',
      remote_helper: '/home/publisher/.local/share/editing-portfolio-publisher/remote_directus.mjs',
    },
    directus: {
      token_file: '/home/publisher/.config/editing-portfolio-publisher/directus-token',
      collections: { photos: 'photos', galleries: 'galleries' },
      fields: {
        photo: {
          image: 'image', title_it: 'title_it', title_en: 'title_en',
          alt_it: 'alt_it', alt_en: 'alt_en', lat: 'lat', lng: 'lng', place: 'place',
          sort: 'sort', published: 'published', gallery: 'gallery', source_hash: null,
        },
        gallery: {
          slug: 'slug', title_it: 'title_it', title_en: 'title_en',
          description_it: 'description_it', description_en: 'description_en',
          cover: 'cover', sort: 'sort', published: 'published', filter_flag: null,
        },
      },
    },
    rebuild: { command: ['bash', '/home/publisher/rebuild.sh'] },
    verification: { routes: ['/portfolio/{slug}/'], expected_text: '{title_it}' },
  };
}

function plan() {
  return {
    plan_version: 2,
    profile_id: 'test-site',
    source_dir: '/Users/Test User/Desktop/Napoli 2023',
    gallery: {
      action: 'create',
      existing_id: null,
      slug: 'napoli-sulla-soglia',
      title_it: 'Napoli, sulla soglia',
      title_en: 'Naples, on the Threshold',
      description_it: 'Una serie sulle soglie.',
      description_en: 'A series about thresholds.',
      cover_file: 'foto 01.jpg',
      sort: null,
      filter_flag: null,
    },
    photos: [{
      order: 1,
      file: 'foto 01.jpg',
      title_it: 'La soglia',
      title_en: 'The Threshold',
      alt_it: 'Una figura davanti a un ingresso.',
      alt_en: 'A figure in front of an entrance.',
      place: 'Napoli, Italia',
      lat: 40.8518,
      lng: 14.2681,
      location_source: 'explicit',
      location_precision: 'exact',
    }],
    approval: { approved: false, approved_at: null, approved_by: null },
  };
}

test('accetta un profilo a riferimenti e percorsi locali con spazi', () => {
  assert.equal(validateProfile(profile()).id, 'test-site');
  assert.equal(validatePlan(plan(), 'test-site').photos.length, 1);
});

test('il profilo remoto canonico omette SSH ma resta valido per l helper', () => {
  const remote = canonicalProfile(profile());
  assert.equal(Object.hasOwn(remote, 'ssh'), false);
  assert.equal(validateRemoteProfile(remote).id, 'test-site');
  assert.throws(() => validateProfile(remote), /ssh\.host mancante/);
});

test('rifiuta password, token e contenuto PEM incorporati', () => {
  assert.throws(() => assertNoEmbeddedSecrets({ password: 'vietata' }), /non è ammesso/);
  assert.throws(() => assertNoEmbeddedSecrets({ token: 'vietato' }), /non è ammesso/);
  assert.throws(
    () => assertNoEmbeddedSecrets({ identity_file: '-----BEGIN OPENSSH PRIVATE KEY-----' }),
    /chiave privata/
  );
  assert.throws(
    () => assertNoEmbeddedSecrets({ rebuild: { command: ['curl', 'Authorization: Bearer abcdefghijklmnop'] } }),
    /credenziale inline/
  );
});

test('l hash del job non cambia con i metadati di approvazione', () => {
  const first = plan();
  const second = structuredClone(first);
  second.approval = { approved: true, approved_at: '2026-08-22T12:00:00Z', approved_by: 'owner' };
  assert.equal(planHash(profile(), first), planHash(profile(), second));
});

test('impedisce traversal, slug e coordinate non validi', () => {
  assert.throws(() => resolvePhotoPath(plan(), { file: '../secret.jpg' }), /fuori source_dir/);
  const badSlug = plan();
  badSlug.gallery.slug = 'Napoli Soglia';
  assert.throws(() => validatePlan(badSlug, 'test-site'), /slug/);
  const badLat = plan();
  badLat.photos[0].lat = 91;
  assert.throws(() => validatePlan(badLat, 'test-site'), /Latitudine/);
});

test('mappa solo i campi configurati e quota argomenti shell', () => {
  assert.deepEqual(mapFields({ title_it: 'Titolo', ignored: true }, { title_it: 'title', ignored: null }), {
    title: 'Titolo',
  });
  assert.equal(shellQuote("l'arte"), "'l'\\''arte'");
  assert.throws(() => shellQuote('riga\nnuova'), /non valido/);
});

test('redige ricorsivamente i valori sensibili', () => {
  assert.deepEqual(redact({ token_file: '/secret/path', nested: { password: 'x', ok: 1 } }), {
    token_file: '[REDACTED]',
    nested: { password: '[REDACTED]', ok: 1 },
  });
  assert.equal(redact('Authorization: Bearer abcdefghijklmnop'), '[REDACTED]');
});

test('valida email e opzioni di provisioning prima delle mutazioni', () => {
  assert.equal(
    validateServiceEmail('portfolio-publisher@giuseppelupo.net'),
    'portfolio-publisher@giuseppelupo.net'
  );
  assert.throws(
    () => validateServiceEmail('portfolio-publisher@local.invalid'),
    /dominio riservato \.invalid/
  );
  assert.throws(
    () => validateProvisioningOptions({
      admin_env_file: 'directus/.env',
      service_email: 'portfolio-publisher@giuseppelupo.net',
    }, profile()),
    /percorso assoluto/
  );
  assert.deepEqual(validateProvisioningOptions({
    admin_env_file: '/opt/stack/directus/.env',
    service_email: 'portfolio-publisher@giuseppelupo.net',
  }, profile()), {
    admin_env_file: '/opt/stack/directus/.env',
    service_email: 'portfolio-publisher@giuseppelupo.net',
  });
});

test('il provisioning include la lettura schema e non concede delete o wildcard', () => {
  const permissions = provisioningPermissions(profile());
  assert.ok(permissions.some(
    (item) => item.collection === 'directus_fields' && item.action === 'read'
  ));
  assert.ok(permissions.some(
    (item) => item.collection === 'photos' && item.action === 'create'
  ));
  assert.ok(permissions.some(
    (item) => item.collection === 'galleries' && item.action === 'update'
  ));
  assert.equal(permissions.some((item) => item.action === 'delete'), false);
  assert.equal(permissions.some((item) => item.collection === '*'), false);
  assert.equal(permissions.some((item) => item.fields.includes('*')), false);
  assert.deepEqual(
    permissions.find((item) => item.collection === 'directus_fields').fields,
    ['collection', 'field']
  );
});

test('rifiuta collection di sistema, mapping essenziali null e URL con credenziali', () => {
  const wildcard = profile();
  wildcard.directus.collections.photos = '*';
  assert.throws(() => validateProfile(wildcard), /identifier Directus|wildcard/);
  const system = profile();
  system.directus.collections.photos = 'directus_users';
  assert.throws(() => validateProfile(system), /namespace directus_/);
  const duplicate = profile();
  duplicate.directus.collections.galleries = 'photos';
  assert.throws(() => validateProfile(duplicate), /devono essere distinte/);
  const missing = profile();
  missing.directus.fields.photo.published = null;
  assert.throws(() => validateProfile(missing), /published.*obbligatorio/);
  const credentialUrl = profile();
  credentialUrl.cms_url = 'https://user:password@cms.giuseppelupo.net';
  assert.throws(() => validateProfile(credentialUrl), /credenziali/);
});

test('lega email e autorizzazione al CMS e alla matrice esatta', () => {
  assert.throws(() => validateServiceEmail('publisher@example.com'), /documentale riservato/);
  assert.throws(() => validateProvisioningOptions({
    admin_env_file: '/opt/stack/directus/.env',
    service_email: 'publisher@altrodominio.it',
  }, profile()), /dominio.*cms_url/);
  const first = provisioningAuthorization(profile(), {
    admin_env_file: '/opt/stack/directus/.env',
    service_email: 'publisher@giuseppelupo.net',
  });
  const changed = profile();
  changed.directus.fields.photo.image = 'hero_image';
  const second = provisioningAuthorization(changed, {
    admin_env_file: '/opt/stack/directus/.env',
    service_email: 'publisher@giuseppelupo.net',
  });
  assert.notEqual(first.hash, second.hash);
});

test('la CLI rifiuta il dominio riservato prima di aprire SSH', () => {
  const folder = mkdtempSync(join(tmpdir(), 'publisher-provision-test.'));
  try {
    const profilePath = join(folder, 'profile.json');
    writeFileSync(profilePath, JSON.stringify(profile()));
    const script = new URL(
      '../editing-portfolio-publisher/scripts/publish_directus.mjs',
      import.meta.url
    );
    const result = spawnSync(process.execPath, [
      script.pathname,
      'provision',
      '--profile', profilePath,
      '--admin-env', '/opt/stack/directus/.env',
      '--service-email', 'portfolio-publisher@local.invalid',
      '--confirm',
    ], { encoding: 'utf8' });
    assert.equal(result.status, 1);
    assert.match(result.stderr, /dominio riservato \.invalid/);
    assert.doesNotMatch(result.stderr, /ssh\.identity_file non è un file/);
  } finally {
    rmSync(folder, { recursive: true, force: true });
  }
});

test('la CLI esegue il preflight senza SSH e vincola apply all hash', () => {
  const folder = mkdtempSync(join(tmpdir(), 'publisher-confirm-test.'));
  try {
    const profilePath = join(folder, 'profile.json');
    writeFileSync(profilePath, JSON.stringify(profile()));
    const script = new URL(
      '../editing-portfolio-publisher/scripts/publish_directus.mjs',
      import.meta.url
    );
    const result = spawnSync(process.execPath, [
      script.pathname,
      'provision',
      '--profile', profilePath,
      '--admin-env', '/opt/stack/directus/.env',
      '--service-email', 'portfolio-publisher@giuseppelupo.net',
    ], { encoding: 'utf8' });
    assert.equal(result.status, 0);
    const output = JSON.parse(result.stdout);
    assert.equal(output.mode, 'local-preflight');
    assert.equal(output.ssh_opened, false);
    assert.match(output.authorization_hash, /^[a-f0-9]{64}$/);
    assert.equal(result.stderr, '');

    const wrongHash = spawnSync(process.execPath, [
      script.pathname,
      'provision',
      '--profile', profilePath,
      '--admin-env', '/opt/stack/directus/.env',
      '--service-email', 'portfolio-publisher@giuseppelupo.net',
      '--confirm',
      '--authorization-hash', '0'.repeat(64),
    ], { encoding: 'utf8' });
    assert.equal(wrongHash.status, 1);
    assert.match(wrongHash.stderr, /Hash di autorizzazione non valido/);
    assert.doesNotMatch(wrongHash.stderr, /ssh\.identity_file non è un file/);
  } finally {
    rmSync(folder, { recursive: true, force: true });
  }
});

test('la guida CLI espone il comando provision senza richiedere un profilo', () => {
  const script = new URL(
    '../editing-portfolio-publisher/scripts/publish_directus.mjs',
    import.meta.url
  );
  const result = spawnSync(process.execPath, [script.pathname, '--help'], { encoding: 'utf8' });
  assert.equal(result.status, 0);
  assert.match(result.stdout, /publish_directus\.mjs provision/);
  assert.equal(result.stderr, '');
});
