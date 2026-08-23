import assert from 'node:assert/strict';
import {
  mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import test from 'node:test';

import { provisioningAuthorization } from '../editing-portfolio-publisher/scripts/lib/publisher-core.mjs';
import { doctor, provision } from '../editing-portfolio-publisher/scripts/remote_directus.mjs';

function profile(home) {
  return {
    profile_version: 1,
    id: 'test-site',
    provider: 'directus-over-ssh',
    cms_url: 'https://cms.test.example.com',
    site_url: 'https://portfolio.test.example.com',
    directus: {
      token_file: join(home, '.config', 'editing-portfolio-publisher', 'test-site', 'directus-token'),
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
    rebuild: { command: ['true'] },
    verification: { routes: ['/portfolio/{slug}/'] },
  };
}

function response(data, status = 200) {
  return new Response(JSON.stringify({ data }), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

function effectiveFromPermissions(permissions) {
  const effective = {};
  for (const item of permissions) {
    effective[item.collection] ??= {};
    effective[item.collection][item.action] = {
      access: item.permissions && Object.keys(item.permissions).length ? 'partial' : 'full',
      fields: [...item.fields],
    };
  }
  return effective;
}

function directusMock(siteProfile) {
  const state = {
    user: null,
    role: null,
    policy: null,
    access: [],
    permissions: [],
    serviceToken: null,
    tokenMeOverride: null,
    effectiveOverride: null,
    healthStatus: 'ok',
    missingPhotoField: null,
    mutations: [],
    loginHosts: [],
  };

  async function fetchMock(input, options = {}) {
    const url = new URL(input);
    const method = options.method || 'GET';
    const body = options.body && typeof options.body === 'string' ? JSON.parse(options.body) : null;
    const path = url.pathname;
    if (method !== 'GET' && path !== '/auth/login') state.mutations.push({ method, path, body });

    if (path === '/auth/login' && method === 'POST') {
      state.loginHosts.push(url.origin);
      return response({ access_token: 'admin-token' });
    }
    if (path === '/users/me' && method === 'GET') {
      if (options.headers?.Authorization !== `Bearer ${state.serviceToken}` || !state.serviceToken) {
        return response(null, 401);
      }
      if (state.tokenMeOverride) return response(state.tokenMeOverride);
      // Directus restituisce il solo id quando la policy dell'utente non
      // concede lettura su directus_users, ed e' il caso della matrice
      // approvata. Il mock deve comportarsi come il server vero: quando
      // restituiva anche ruolo, stato e marker, il provisioning passava nei
      // test e falliva contro ogni Directus reale.
      return state.user?.status === 'active'
        ? response({ id: state.user.id })
        : response(null, 401);
    }
    if (path === '/users/user-1' && method === 'GET') {
      return response(state.user);
    }
    if (path === '/permissions/me' && method === 'GET') {
      return response(state.effectiveOverride ?? effectiveFromPermissions(state.permissions));
    }
    if (path === '/server/health' && method === 'GET') {
      // Directus non incapsula questa risposta in `data`: il mock deve
      // rispondere come il server vero, altrimenti il client puo' sbagliare a
      // spacchettarla e i test non se ne accorgono.
      return new Response(JSON.stringify({ status: state.healthStatus }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      });
    }
    if (path === '/fields/photos' && method === 'GET') {
      const fields = ['id', ...Object.values(siteProfile.directus.fields.photo).filter(Boolean)];
      return response([...new Set(fields)]
        .filter((field) => field !== state.missingPhotoField)
        .map((field) => ({ field })));
    }
    if (path === '/fields/galleries' && method === 'GET') {
      const fields = ['id', ...Object.values(siteProfile.directus.fields.gallery).filter(Boolean)];
      return response([...new Set(fields)].map((field) => ({ field })));
    }
    if (path === '/users' && method === 'GET') {
      const email = url.searchParams.get('filter[email][_eq]');
      return response(state.user && state.user.email === email ? [state.user] : []);
    }
    if (path === '/users' && method === 'POST') {
      state.user = { id: 'user-1', role: null, ...body };
      return response(state.user);
    }
    if (path === '/users/user-1' && method === 'PATCH') {
      if (body.token) state.serviceToken = body.token;
      state.user = { ...state.user, ...body };
      return response(state.user);
    }
    if (path === '/roles' && method === 'GET') {
      const name = url.searchParams.get('filter[name][_eq]');
      return response(state.role && state.role.name === name ? [state.role] : []);
    }
    if (path === '/roles' && method === 'POST') {
      state.role = { id: 'role-1', ...body };
      return response(state.role);
    }
    if (path === '/policies' && method === 'GET') {
      const name = url.searchParams.get('filter[name][_eq]');
      return response(state.policy && state.policy.name === name ? [state.policy] : []);
    }
    if (path === '/policies' && method === 'POST') {
      state.policy = { id: 'policy-1', ...body };
      return response(state.policy);
    }
    if (path === '/access' && method === 'GET') {
      const role = url.searchParams.get('filter[role][_eq]');
      const policy = url.searchParams.get('filter[policy][_eq]');
      const user = url.searchParams.get('filter[user][_eq]');
      return response(state.access.filter((item) =>
        (!role || item.role === role) && (!policy || item.policy === policy) && (!user || item.user === user)
      ));
    }
    if (path === '/access' && method === 'POST') {
      const item = { id: `access-${state.access.length + 1}`, user: null, ...body };
      state.access.push(item);
      return response(item);
    }
    if (path === '/permissions' && method === 'GET') {
      const policy = url.searchParams.get('filter[policy][_eq]');
      return response(state.permissions.filter((item) => !policy || item.policy === policy));
    }
    if (path === '/permissions' && method === 'POST') {
      const item = { id: `permission-${state.permissions.length + 1}`, ...body };
      state.permissions.push(item);
      return response(item);
    }
    throw new Error(`Richiesta mock non gestita: ${method} ${url}`);
  }
  return { state, fetchMock };
}

function adminOptions(siteProfile, adminEnv) {
  const options = {
    admin_env_file: adminEnv,
    service_email: 'portfolio-publisher@test.example.com',
  };
  return { ...options, authorization_hash: provisioningAuthorization(siteProfile, options).hash };
}

test('provision è ordinato, field-minimal, idempotente e riparabile', async () => {
  const folder = mkdtempSync(join(tmpdir(), 'directus-provision.'));
  const originalHome = process.env.HOME;
  const originalFetch = globalThis.fetch;
  process.env.HOME = folder;
  const siteProfile = profile(folder);
  const adminEnv = join(folder, 'directus.env');
  writeFileSync(
    adminEnv,
    `PUBLIC_URL=${siteProfile.cms_url}\nADMIN_EMAIL=admin@test.example.com\nADMIN_PASSWORD=test-only\n`,
    { mode: 0o600 }
  );
  const mock = directusMock(siteProfile);
  globalThis.fetch = mock.fetchMock;
  try {
    const options = adminOptions(siteProfile, adminEnv);
    const first = await provision(siteProfile, options);
    assert.equal(first.ok, true);
    assert.equal(first.credential_rotated, true);
    assert.equal(first.doctor.ok, true);
    assert.equal(mock.state.loginHosts[0], siteProfile.cms_url);
    assert.equal(mock.state.mutations[0].path, '/users');
    assert.equal(mock.state.mutations[0].body.status, 'draft');
    assert.equal(Object.hasOwn(mock.state.mutations[0].body, 'role'), false);
    assert.equal(Object.hasOwn(mock.state.mutations[0].body, 'token'), false);
    const lastPermission = Math.max(...mock.state.mutations.map(
      (item, index) => item.path === '/permissions' ? index : -1
    ));
    assert.ok(lastPermission < mock.state.mutations.findIndex((item) => item.path === '/access'));
    assert.ok(mock.state.permissions.some(
      (item) => item.collection === 'directus_fields' && item.action === 'read'
    ));
    assert.equal(mock.state.permissions.some((item) => item.action === 'delete'), false);
    assert.equal(mock.state.permissions.some((item) => item.fields.includes('*')), false);
    assert.equal(statSync(siteProfile.directus.token_file).mode & 0o777, 0o600);
    assert.equal(statSync(dirname(siteProfile.directus.token_file)).mode & 0o777, 0o700);
    assert.equal(statSync(first.binding_file).mode & 0o777, 0o600);
    assert.equal(JSON.parse(readFileSync(first.journal_file, 'utf8')).status, 'complete');

    const tokenBefore = readFileSync(siteProfile.directus.token_file, 'utf8');
    const mutationsBefore = mock.state.mutations.length;
    const second = await provision(siteProfile, options);
    assert.equal(second.credential_rotated, false);
    assert.equal(mock.state.mutations.length, mutationsBefore);
    assert.equal(readFileSync(siteProfile.directus.token_file, 'utf8'), tokenBefore);

    mock.state.policy.admin_access = true;
    await assert.rejects(() => provision(siteProfile, options), /policy namespaced non è minima/);
    assert.equal(mock.state.mutations.length, mutationsBefore);
    mock.state.policy.admin_access = false;

    const originalFields = [...mock.state.permissions[0].fields];
    mock.state.permissions[0].fields = [...originalFields, '*'];
    await assert.rejects(() => provision(siteProfile, options), /Permesso non conforme/);
    assert.equal(mock.state.mutations.length, mutationsBefore);
    mock.state.permissions[0].fields = originalFields;

    const normalEffective = effectiveFromPermissions(mock.state.permissions);
    mock.state.effectiveOverride = structuredClone(normalEffective);
    mock.state.effectiveOverride.photos.create.access = 'partial';
    await assert.rejects(() => doctor(siteProfile), /access=partial, atteso=full/);
    mock.state.effectiveOverride = structuredClone(normalEffective);
    mock.state.effectiveOverride.private_notes = { delete: { access: 'full', fields: ['id'] } };
    await assert.rejects(() => doctor(siteProfile), /non deve concedere delete/);
    mock.state.effectiveOverride = null;
    mock.state.healthStatus = 'fail';
    await assert.rejects(() => doctor(siteProfile), /health non OK/);
    mock.state.healthStatus = 'ok';

    mock.state.permissions = mock.state.permissions.filter(
      (item) => !(item.collection === 'directus_fields' && item.action === 'read')
    );
    const repairStart = mock.state.mutations.length;
    const repaired = await provision(siteProfile, options);
    const repairMutations = mock.state.mutations.slice(repairStart);
    assert.equal(repaired.credential_rotated, false);
    assert.equal(repaired.permissions_created, 1);
    assert.equal(repairMutations.length, 1);
    assert.equal(repairMutations[0].path, '/permissions');
    assert.equal(repairMutations[0].body.collection, 'directus_fields');
    assert.equal(readFileSync(siteProfile.directus.token_file, 'utf8'), tokenBefore);
  } finally {
    globalThis.fetch = originalFetch;
    if (originalHome === undefined) delete process.env.HOME;
    else process.env.HOME = originalHome;
    rmSync(folder, { recursive: true, force: true });
  }
});

test('un postcheck fallito lascia un journal con gli ID creati', async () => {
  const folder = mkdtempSync(join(tmpdir(), 'directus-journal.'));
  const originalHome = process.env.HOME;
  const originalFetch = globalThis.fetch;
  process.env.HOME = folder;
  const siteProfile = profile(folder);
  const adminEnv = join(folder, 'directus.env');
  writeFileSync(
    adminEnv,
    `PUBLIC_URL=${siteProfile.cms_url}\nADMIN_EMAIL=admin@test.example.com\nADMIN_PASSWORD=test-only\n`,
    { mode: 0o600 }
  );
  const mock = directusMock(siteProfile);
  mock.state.missingPhotoField = 'image';
  globalThis.fetch = mock.fetchMock;
  try {
    let failure;
    try {
      await provision(siteProfile, adminOptions(siteProfile, adminEnv));
    } catch (error) {
      failure = error;
    }
    assert.ok(failure);
    assert.match(failure.message, /Campi mancanti in photos/);
    const journalPath = failure.message.match(/journal=(.+)$/)?.[1];
    assert.ok(journalPath);
    const journal = JSON.parse(readFileSync(journalPath, 'utf8'));
    assert.equal(journal.status, 'failed');
    assert.equal(journal.resources.user_id, 'user-1');
    assert.equal(journal.resources.role_id, 'role-1');
    assert.equal(journal.resources.policy_id, 'policy-1');
    assert.equal(journal.resources.access_id, 'access-1');
  } finally {
    globalThis.fetch = originalFetch;
    if (originalHome === undefined) delete process.env.HOME;
    else process.env.HOME = originalHome;
    rmSync(folder, { recursive: true, force: true });
  }
});

test('blocca endpoint admin non fidato e token fuori dalla root prima del login', async () => {
  const folder = mkdtempSync(join(tmpdir(), 'directus-trust.'));
  const originalHome = process.env.HOME;
  const originalFetch = globalThis.fetch;
  process.env.HOME = folder;
  try {
    const siteProfile = profile(folder);
    const adminEnv = join(folder, 'directus.env');
    writeFileSync(
      adminEnv,
      'PUBLIC_URL=https://collector.test.example.com\nADMIN_EMAIL=admin@test.example.com\nADMIN_PASSWORD=test-only\n',
      { mode: 0o600 }
    );
    let fetchCalls = 0;
    globalThis.fetch = async () => {
      fetchCalls += 1;
      throw new Error('fetch non atteso');
    };
    await assert.rejects(
      () => provision(siteProfile, adminOptions(siteProfile, adminEnv)),
      /PUBLIC_URL remoto non coincide/
    );
    assert.equal(fetchCalls, 0);
    const unsafe = profile(folder);
    unsafe.directus.token_file = '/directus-token';
    assert.throws(
      () => adminOptions(unsafe, adminEnv),
      /sotto .*editing-portfolio-publisher/
    );
    assert.equal(fetchCalls, 0);
  } finally {
    globalThis.fetch = originalFetch;
    if (originalHome === undefined) delete process.env.HOME;
    else process.env.HOME = originalHome;
    rmSync(folder, { recursive: true, force: true });
  }
});

test('non adotta utenti umani né sovrascrive token di un altro utente', async () => {
  const folder = mkdtempSync(join(tmpdir(), 'directus-collision.'));
  const originalHome = process.env.HOME;
  const originalFetch = globalThis.fetch;
  process.env.HOME = folder;
  const siteProfile = profile(folder);
  const adminEnv = join(folder, 'directus.env');
  writeFileSync(
    adminEnv,
    `PUBLIC_URL=${siteProfile.cms_url}\nADMIN_EMAIL=admin@test.example.com\nADMIN_PASSWORD=test-only\n`,
    { mode: 0o600 }
  );
  try {
    const human = directusMock(siteProfile);
    human.state.user = {
      id: 'user-1', email: 'portfolio-publisher@test.example.com',
      first_name: 'Ada', last_name: 'Lovelace', role: 'human-role',
      status: 'active', external_identifier: null,
    };
    globalThis.fetch = human.fetchMock;
    await assert.rejects(
      () => provision(siteProfile, adminOptions(siteProfile, adminEnv)),
      /utente non gestito/
    );
    assert.equal(human.state.mutations.length, 0);

    const other = directusMock(siteProfile);
    other.state.user = {
      id: 'user-1', email: 'portfolio-publisher@test.example.com',
      first_name: 'Portfolio', last_name: 'Publisher', role: null,
      status: 'active', external_identifier: null,
    };
    other.state.serviceToken = 'other-service-token';
    other.state.tokenMeOverride = {
      id: 'other-user', role: 'other-role', status: 'active', external_identifier: 'other',
    };
    mkdirSync(dirname(siteProfile.directus.token_file), { recursive: true, mode: 0o700 });
    writeFileSync(siteProfile.directus.token_file, 'other-service-token\n', { mode: 0o600 });
    globalThis.fetch = other.fetchMock;
    await assert.rejects(
      () => provision(siteProfile, adminOptions(siteProfile, adminEnv)),
      /Collisione token/
    );
    assert.equal(readFileSync(siteProfile.directus.token_file, 'utf8'), 'other-service-token\n');
    assert.equal(other.state.mutations.length, 0);
  } finally {
    globalThis.fetch = originalFetch;
    if (originalHome === undefined) delete process.env.HOME;
    else process.env.HOME = originalHome;
    rmSync(folder, { recursive: true, force: true });
  }
});

test('il token tecnico certifica solo il proprio id, e tanto basta', async () => {
  // Regressione dell'undicesimo rilievo, emerso contro un Directus 11 vero.
  // La matrice approvata non concede lettura su directus_users, quindi
  // /users/me restituisce il solo id: pretendere ruolo, stato e marker dal
  // token tecnico rendeva il provisioning impossibile da concludere, e
  // bloccava anche doctor, plan, stage e release, che passano tutti da
  // context(). Il mock ora risponde come il server vero.
  const originalFetch = globalThis.fetch;
  const originalHome = process.env.HOME;
  const folder = mkdtempSync(join(tmpdir(), 'directus-provision-id.'));
  try {
    process.env.HOME = folder;
    const siteProfile = profile(folder);
    const adminEnv = join(folder, 'directus.env');
    writeFileSync(
      adminEnv,
      `PUBLIC_URL=${siteProfile.cms_url}\nADMIN_EMAIL=admin@test.example.com\nADMIN_PASSWORD=test-only\n`,
      { mode: 0o600 }
    );
    const mock = directusMock(siteProfile);
    globalThis.fetch = mock.fetchMock;

    const preflight = await provision(siteProfile, adminOptions(siteProfile, adminEnv));
    const applied = await provision(
      siteProfile,
      adminOptions(siteProfile, adminEnv),
      true,
      preflight.authorization_hash
    );
    assert.equal(applied.ok, true);
    assert.equal(applied.user_id, 'user-1');

    // doctor passa da context(): deve reggere con lo stesso /users/me ridotto.
    const referto = await doctor(siteProfile);
    assert.equal(referto.ok, true);
    assert.equal(referto.cms_status, 'ok');
  } finally {
    globalThis.fetch = originalFetch;
    if (originalHome === undefined) delete process.env.HOME;
    else process.env.HOME = originalHome;
    rmSync(folder, { recursive: true, force: true });
  }
});
