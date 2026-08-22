#!/usr/bin/env node

import { spawnSync } from 'node:child_process';
import { readFile, stat } from 'node:fs/promises';
import { basename, join, resolve } from 'node:path';
import {
  DirectusClient,
  directusQuery,
  mapFields,
  readJson,
  redact,
  reverseFieldMap,
  sha256File,
  validatePlan,
  validateProfile,
  writeJsonAtomic,
} from './lib/publisher-core.mjs';

async function stdinJson() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  if (chunks.length === 0) throw new Error('Input JSON mancante');
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}

async function readToken(path) {
  const info = await stat(path);
  if ((info.mode & 0o077) !== 0) throw new Error('Il file token Directus deve avere permessi 600');
  if (typeof process.getuid === 'function' && info.uid !== process.getuid()) {
    throw new Error('Il file token Directus deve appartenere all’utente remoto');
  }
  const token = (await readFile(path, 'utf8')).trim();
  if (!token) throw new Error('Il file token Directus è vuoto');
  return token;
}

async function context(profile) {
  validateProfile(profile);
  const token = await readToken(profile.directus.token_file);
  return { profile, client: new DirectusClient(profile.cms_url, token) };
}

function mappedFields(mapping, required) {
  return required.map((name) => mapping[name]).filter(Boolean);
}

async function checkSchema(profile, client) {
  const checks = [
    {
      collection: profile.directus.collections.photos,
      mapping: profile.directus.fields.photo,
      required: ['image', 'title_it', 'title_en', 'alt_it', 'alt_en', 'sort', 'published', 'gallery'],
    },
    {
      collection: profile.directus.collections.galleries,
      mapping: profile.directus.fields.gallery,
      required: ['slug', 'title_it', 'title_en', 'cover', 'sort', 'published'],
    },
  ];
  const report = {};
  for (const check of checks) {
    const fields = await client.request(`/fields/${encodeURIComponent(check.collection)}`);
    const present = new Set(fields.map((item) => item.field));
    const expected = mappedFields(check.mapping, check.required);
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

async function doctor(profile) {
  const { client } = await context(profile);
  const health = await client.request('/server/health');
  const schema = await checkSchema(profile, client);
  return {
    ok: true,
    profile_id: profile.id,
    cms_status: health?.status ?? 'ok',
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
  validateProfile(profile);
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
    const body = mapFields(
      { ...plan.gallery, sort: gallerySort, cover: cover.directus_file_id, published: false },
      galleryMap
    );
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
  validateProfile(profile);
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
  if (command === 'doctor') {
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
    throw new Error('Uso: remote_directus.mjs doctor|plan|stage|release');
  }
  process.stdout.write(`${JSON.stringify(redact(result), null, 2)}\n`);
}

main().catch((error) => {
  process.stderr.write(`Errore: ${error.message}\n`);
  process.exitCode = 1;
});
