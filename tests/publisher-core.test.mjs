import assert from 'node:assert/strict';
import test from 'node:test';

import {
  assertNoEmbeddedSecrets,
  mapFields,
  planHash,
  redact,
  resolvePhotoPath,
  shellQuote,
  validatePlan,
  validateProfile,
} from '../editing-portfolio-publisher/scripts/lib/publisher-core.mjs';

function profile() {
  return {
    profile_version: 1,
    id: 'test-site',
    provider: 'directus-over-ssh',
    cms_url: 'https://cms.example.com',
    site_url: 'https://portfolio.example.com',
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
      fields: { photo: { image: 'image' }, gallery: { slug: 'slug' } },
    },
    rebuild: { command: ['bash', '/home/publisher/rebuild.sh'] },
    verification: { routes: ['/portfolio/{slug}/'], expected_text: '{title_it}' },
  };
}

function plan() {
  return {
    plan_version: 1,
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
      lat: 40.8518,
      lng: 14.2681,
    }],
    approval: { approved: false, approved_at: null, approved_by: null },
  };
}

test('accetta un profilo a riferimenti e percorsi locali con spazi', () => {
  assert.equal(validateProfile(profile()).id, 'test-site');
  assert.equal(validatePlan(plan(), 'test-site').photos.length, 1);
});

test('rifiuta password, token e contenuto PEM incorporati', () => {
  assert.throws(() => assertNoEmbeddedSecrets({ password: 'vietata' }), /non è ammesso/);
  assert.throws(() => assertNoEmbeddedSecrets({ token: 'vietato' }), /non è ammesso/);
  assert.throws(
    () => assertNoEmbeddedSecrets({ identity_file: '-----BEGIN OPENSSH PRIVATE KEY-----' }),
    /chiave privata/
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
});
