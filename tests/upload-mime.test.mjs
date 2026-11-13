import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

import { mimeType, uploadFile } from '../editing-portfolio-publisher/scripts/remote_directus.mjs';

test('il tipo MIME segue l\'estensione, maiuscole comprese', () => {
  assert.equal(mimeType('_R003621.jpg'), 'image/jpeg');
  assert.equal(mimeType('SCATTO.JPEG'), 'image/jpeg');
  assert.equal(mimeType('ritratto.png'), 'image/png');
  assert.equal(mimeType('foto.webp'), 'image/webp');
  assert.equal(mimeType('stampa.TIF'), 'image/tiff');
  assert.equal(mimeType('scan.bmp'), 'image/bmp');
  assert.equal(mimeType('iphone.HEIC'), 'image/heic');
});

test('un\'estensione sconosciuta ferma l\'upload invece di caricare un octet-stream', () => {
  assert.throws(() => mimeType('appunti.txt'), /Estensione non gestita/);
  assert.throws(() => mimeType('senza-estensione'), /Estensione non gestita/);
});

test('uploadFile manda a Directus il file con il tipo immagine, non application/octet-stream', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'upload-mime-'));
  try {
    const path = join(dir, '_R003621.jpg');
    await writeFile(path, Buffer.from([0xff, 0xd8, 0xff, 0xd9]));
    let chiamata = null;
    const client = { request: async (url, options) => { chiamata = { url, options }; return { id: 'x' }; } };

    await uploadFile(client, path, '_R003621.jpg');

    assert.equal(chiamata.url, '/files');
    assert.equal(chiamata.options.method, 'POST');
    const file = chiamata.options.form.get('file');
    assert.equal(file.type, 'image/jpeg');
    assert.equal(file.name, '_R003621.jpg');
    assert.equal(file.size, 4);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});
