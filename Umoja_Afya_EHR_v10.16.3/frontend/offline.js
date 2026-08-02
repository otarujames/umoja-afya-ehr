(() => {
  'use strict';

  const DB_NAME = 'umoja-afya-secure-offline';
  const DB_VERSION = 1;
  const RELEASE = '10.16.3';
  const API = '/api/v1';
  const PBKDF2_ITERATIONS = 310000;
  const DEFAULT_LEASE_HOURS = 24;
  const MAX_OUTBOX = 1000;
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();
  const listeners = new Set();

  let database = null;
  let enrollment = null;
  let dataKey = null;
  let syncing = false;
  let installPrompt = null;

  function emit() {
    stats().then(value => listeners.forEach(listener => {
      try { listener(value); } catch (_) { /* UI listeners are isolated. */ }
    }));
  }

  function requestResult(request) {
    return new Promise((resolve, reject) => {
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error('Offline database request failed'));
    });
  }

  function transactionDone(transaction) {
    return new Promise((resolve, reject) => {
      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error || new Error('Offline database transaction failed'));
      transaction.onabort = () => reject(transaction.error || new Error('Offline database transaction was aborted'));
    });
  }

  async function getValue(storeName, key) {
    const tx = database.transaction(storeName, 'readonly');
    return requestResult(tx.objectStore(storeName).get(key));
  }

  async function putValue(storeName, value) {
    const tx = database.transaction(storeName, 'readwrite');
    tx.objectStore(storeName).put(value);
    await transactionDone(tx);
    return value;
  }

  async function deleteValue(storeName, key) {
    const tx = database.transaction(storeName, 'readwrite');
    tx.objectStore(storeName).delete(key);
    await transactionDone(tx);
  }

  async function allValues(storeName) {
    const tx = database.transaction(storeName, 'readonly');
    return requestResult(tx.objectStore(storeName).getAll());
  }

  function bytesToBase64(bytes) {
    let binary = '';
    for (let offset = 0; offset < bytes.length; offset += 0x8000) {
      binary += String.fromCharCode(...bytes.subarray(offset, Math.min(offset + 0x8000, bytes.length)));
    }
    return btoa(binary);
  }

  function base64ToBytes(value) {
    const binary = atob(value);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    return bytes;
  }

  async function derivePinKey(pin, salt) {
    const material = await crypto.subtle.importKey('raw', encoder.encode(pin), 'PBKDF2', false, ['deriveKey']);
    return crypto.subtle.deriveKey(
      { name: 'PBKDF2', salt, iterations: PBKDF2_ITERATIONS, hash: 'SHA-256' },
      material,
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt', 'decrypt'],
    );
  }

  async function encrypt(value) {
    if (!dataKey) throw new Error('Unlock offline mode before saving protected data.');
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const plaintext = encoder.encode(JSON.stringify(value));
    const ciphertext = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, dataKey, plaintext);
    return { version: 1, iv: bytesToBase64(iv), ciphertext: bytesToBase64(new Uint8Array(ciphertext)) };
  }

  async function decrypt(envelope) {
    if (!dataKey) throw new Error('Unlock offline mode to access protected data.');
    const plaintext = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: base64ToBytes(envelope.iv) },
      dataKey,
      base64ToBytes(envelope.ciphertext),
    );
    return JSON.parse(decoder.decode(plaintext));
  }

  function secureContextRequired() {
    if (!window.isSecureContext || !window.crypto?.subtle || !window.indexedDB) {
      throw new Error('Offline installation requires HTTPS and a browser with Web Crypto and IndexedDB support.');
    }
  }

  function leaseValid() {
    return Boolean(enrollment && Date.now() <= new Date(enrollment.expires_at).getTime());
  }

  async function init() {
    secureContextRequired();
    database = await new Promise((resolve, reject) => {
      const open = indexedDB.open(DB_NAME, DB_VERSION);
      open.onupgradeneeded = () => {
        const db = open.result;
        if (!db.objectStoreNames.contains('meta')) db.createObjectStore('meta', { keyPath: 'id' });
        if (!db.objectStoreNames.contains('cache')) db.createObjectStore('cache', { keyPath: 'id' });
        if (!db.objectStoreNames.contains('outbox')) {
          const store = db.createObjectStore('outbox', { keyPath: 'id' });
          store.createIndex('status', 'status', { unique: false });
          store.createIndex('created_at', 'created_at', { unique: false });
        }
      };
      open.onsuccess = () => resolve(open.result);
      open.onerror = () => reject(open.error || new Error('Could not open the offline database'));
    });
    enrollment = await getValue('meta', 'enrollment') || null;
    window.addEventListener('beforeinstallprompt', event => {
      event.preventDefault();
      installPrompt = event;
      emit();
    });
    window.addEventListener('appinstalled', () => {
      installPrompt = null;
      emit();
    });
    navigator.serviceWorker?.addEventListener('message', event => {
      if (event.data?.type === 'UMOJA_SYNC_REQUEST') window.dispatchEvent(new CustomEvent('umoja-offline-sync-request'));
    });
    emit();
    return state();
  }

  function validatePin(pin) {
    if (!/^\d{6,12}$/.test(String(pin || ''))) throw new Error('Choose a 6–12 digit offline PIN.');
    if (/^(\d)\1+$/.test(pin) || ['123456', '654321', '000000'].includes(pin)) throw new Error('Choose a less predictable offline PIN.');
  }

  async function enroll(pin, profile, policy = {}) {
    secureContextRequired();
    validatePin(pin);
    if (!profile?.account?.user_id) throw new Error('Sign in online before enabling offline mode.');
    const rawDataKey = crypto.getRandomValues(new Uint8Array(32));
    const salt = crypto.getRandomValues(new Uint8Array(16));
    const wrapIv = crypto.getRandomValues(new Uint8Array(12));
    const pinKey = await derivePinKey(pin, salt);
    const wrapped = await crypto.subtle.encrypt({ name: 'AES-GCM', iv: wrapIv }, pinKey, rawDataKey);
    dataKey = await crypto.subtle.importKey('raw', rawDataKey, { name: 'AES-GCM' }, false, ['encrypt', 'decrypt']);
    rawDataKey.fill(0);
    const leaseHours = Math.max(1, Math.min(72, Number(policy.lease_hours) || DEFAULT_LEASE_HOURS));
    enrollment = {
      id: 'enrollment',
      version: 1,
      user_id: profile.account.user_id,
      username: profile.account.username,
      country_code: profile.countryCode,
      device_id: profile.deviceId,
      salt: bytesToBase64(salt),
      wrap_iv: bytesToBase64(wrapIv),
      wrapped_key: bytesToBase64(new Uint8Array(wrapped)),
      enrolled_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + leaseHours * 3600000).toISOString(),
      lease_hours: leaseHours,
      maximum_pending_operations: Math.max(1, Math.min(MAX_OUTBOX, Number(policy.maximum_pending_operations) || MAX_OUTBOX)),
      release: RELEASE,
    };
    await putValue('meta', enrollment);
    await cachePut('offline-profile', profile, leaseHours * 3600000);
    await navigator.storage?.persist?.().catch(() => false);
    emit();
    return state();
  }

  async function unlock(pin) {
    secureContextRequired();
    enrollment = enrollment || await getValue('meta', 'enrollment');
    if (!enrollment) throw new Error('Offline mode has not been enabled on this device.');
    if (Date.now() > new Date(enrollment.expires_at).getTime()) throw new Error('The offline access lease expired. Reconnect and sign in to renew it.');
    try {
      const pinKey = await derivePinKey(pin, base64ToBytes(enrollment.salt));
      const raw = await crypto.subtle.decrypt(
        { name: 'AES-GCM', iv: base64ToBytes(enrollment.wrap_iv) },
        pinKey,
        base64ToBytes(enrollment.wrapped_key),
      );
      dataKey = await crypto.subtle.importKey('raw', raw, { name: 'AES-GCM' }, false, ['encrypt', 'decrypt']);
    } catch (_) {
      dataKey = null;
      throw new Error('Incorrect offline PIN or damaged offline vault.');
    }
    const profile = await cacheGet('offline-profile');
    if (!profile || profile.account?.user_id !== enrollment.user_id) {
      dataKey = null;
      throw new Error('The protected offline profile could not be verified.');
    }
    emit();
    return profile;
  }

  async function renew(pin, profile, policy = {}) {
    secureContextRequired();
    enrollment = enrollment || await getValue('meta', 'enrollment');
    if (!enrollment) throw new Error('Offline mode has not been enabled on this device.');
    if (!profile?.account?.user_id || profile.account.user_id !== enrollment.user_id) throw new Error('Online sign-in does not match the enrolled offline user.');
    try {
      const pinKey = await derivePinKey(pin, base64ToBytes(enrollment.salt));
      const raw = await crypto.subtle.decrypt(
        { name: 'AES-GCM', iv: base64ToBytes(enrollment.wrap_iv) },
        pinKey,
        base64ToBytes(enrollment.wrapped_key),
      );
      dataKey = await crypto.subtle.importKey('raw', raw, { name: 'AES-GCM' }, false, ['encrypt', 'decrypt']);
    } catch (_) {
      dataKey = null;
      throw new Error('Incorrect offline PIN or damaged offline vault.');
    }
    const protectedProfile = await cacheGet('offline-profile', true);
    if (!protectedProfile || protectedProfile.account?.user_id !== enrollment.user_id) {
      dataKey = null;
      throw new Error('The protected offline profile could not be verified.');
    }
    await refreshProfile(profile, policy);
    emit();
    return profile;
  }

  async function refreshProfile(profile, policy = {}) {
    if (!dataKey || !enrollment || profile?.account?.user_id !== enrollment.user_id) return false;
    const leaseHours = Math.max(1, Math.min(72, Number(policy.lease_hours) || enrollment.lease_hours || DEFAULT_LEASE_HOURS));
    enrollment.expires_at = new Date(Date.now() + leaseHours * 3600000).toISOString();
    enrollment.lease_hours = leaseHours;
    enrollment.country_code = profile.countryCode;
    enrollment.release = RELEASE;
    await putValue('meta', enrollment);
    await cachePut('offline-profile', profile, leaseHours * 3600000);
    emit();
    return true;
  }

  function lock() {
    dataKey = null;
    emit();
  }

  async function wipe() {
    dataKey = null;
    const tx = database.transaction(['meta', 'cache', 'outbox'], 'readwrite');
    tx.objectStore('meta').clear();
    tx.objectStore('cache').clear();
    tx.objectStore('outbox').clear();
    await transactionDone(tx);
    enrollment = null;
    emit();
  }

  async function cachePut(id, value, ttlMs = 24 * 3600000) {
    if (!dataKey || !leaseValid()) return false;
    const envelope = await encrypt({
      user_id: enrollment.user_id,
      value,
      stored_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + ttlMs).toISOString(),
    });
    await putValue('cache', { id, envelope, updated_at: new Date().toISOString() });
    return true;
  }

  async function cacheGet(id, allowExpired = false) {
    if (!dataKey || !enrollment) return null;
    if (!allowExpired && !leaseValid()) return null;
    const record = await getValue('cache', id);
    if (!record) return null;
    try {
      const protectedValue = await decrypt(record.envelope);
      if (protectedValue.user_id !== enrollment.user_id) return null;
      if (!allowExpired && Date.now() > new Date(protectedValue.expires_at).getTime()) return null;
      return protectedValue.value;
    } catch (_) {
      return null;
    }
  }

  function cacheable(path) {
    if (!path || /\/(auth|offline|audit|admin|messages|audio)/.test(path)) return false;
    return [
      '/facilities', '/modules', '/patients', '/encounters', '/module-activities', '/appointments',
      '/walk-ins', '/notes', '/flowsheets', '/charges', '/claims', '/payments', '/service-points',
      '/duty-rosters', '/workqueues', '/workqueue-items', '/medications', '/results', '/orders',
    ].some(prefix => path.startsWith(prefix));
  }

  function responseCacheId(path) {
    return `response:${enrollment?.user_id || 'unknown'}:${path}`;
  }

  async function cacheResponse(path, value) {
    if (!cacheable(path)) return false;
    return cachePut(responseCacheId(path), value);
  }

  async function cachedResponse(path) {
    if (!cacheable(path)) return null;
    return cacheGet(responseCacheId(path));
  }

  function queueable(path, options = {}) {
    const method = String(options.method || 'GET').toUpperCase();
    if (!['POST', 'PUT', 'PATCH'].includes(method) || options.body instanceof FormData) return false;
    const blocked = [
      /^\/auth\//, /^\/offline\//, /^\/notes\/audio/, /^\/notes\/[^/]+\/(sign|addendum)\/?$/,
      /^\/orders/, /^\/results/, /^\/medications/, /^\/admin/, /^\/break-glass/,
      /^\/patients\/[^/]+\/death/, /^\/encounters\/[^/]+\/discharge/,
      /^\/claims\/[^/]+/, /^\/registration\/search$/,
    ];
    if (blocked.some(pattern => pattern.test(path))) return false;
    const permitted = [
      method === 'POST' && path === '/registration',
      /^\/walk-ins(?:\/[^/]+)?$/.test(path),
      method === 'PATCH' && /^\/appointments\/[^/]+$/.test(path),
      method === 'PATCH' && /^\/encounters\/[^/]+\/status$/.test(path),
      /^\/module-activities(?:\/[^/]+)?$/.test(path),
      (method === 'POST' && path === '/notes') || (method === 'PATCH' && /^\/notes\/[^/]+$/.test(path)),
      /^\/flowsheets(?:\/[^/]+\/(?:actions|observations))?$/.test(path),
      method === 'POST' && ['/payments', '/charges', '/claims'].includes(path),
      /^\/workqueue-items(?:\/[^/]+)?$/.test(path),
    ];
    return permitted.some(Boolean) && typeof options.body === 'string' && options.body.length <= 512000;
  }

  function operationId() {
    return `off-${crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`}`;
  }

  function patientContext(value) {
    if (!value || typeof value !== 'object') return null;
    for (const key of ['patient_mpi_id', 'mpi_id', 'patient_id']) if (typeof value[key] === 'string') return value[key];
    for (const child of Object.values(value)) {
      const found = patientContext(child);
      if (found) return found;
    }
    return null;
  }

  async function enqueue(path, options = {}, context = {}) {
    if (!dataKey || !enrollment) throw new Error('Enable and unlock encrypted offline mode before recording data without a connection.');
    if (!leaseValid()) throw new Error('The offline access lease expired. Reconnect and sign in to renew it.');
    if (!queueable(path, options)) throw new Error('This safety-critical workflow requires an online connection.');
    const current = await stats();
    if (current.pending >= Number(enrollment.maximum_pending_operations || MAX_OUTBOX)) throw new Error('The offline outbox is full. Reconnect and synchronize before recording more work.');
    let parsedBody;
    try { parsedBody = JSON.parse(options.body); } catch (_) { throw new Error('Only structured clinical transactions can be saved offline.'); }
    const id = context.operationId || operationId();
    const createdAt = context.createdAt || new Date().toISOString();
    const envelope = await encrypt({
      user_id: enrollment.user_id,
      method: String(options.method || 'POST').toUpperCase(),
      path,
      body: parsedBody,
      country_code: context.countryCode || enrollment.country_code,
      facility_code: context.facilityCode || null,
      patient_mpi_id: patientContext(parsedBody),
    });
    await putValue('outbox', {
      id,
      status: 'PENDING',
      created_at: createdAt,
      updated_at: createdAt,
      attempts: 0,
      next_attempt_at: createdAt,
      envelope,
      last_error: null,
    });
    try {
      const registration = await navigator.serviceWorker?.ready;
      await registration?.sync?.register('umoja-afya-sync');
    } catch (_) { /* Online event and app startup also trigger sync. */ }
    emit();
    return {
      offline_queued: true,
      operation_id: id,
      status: 'PENDING_SYNC',
      notification: { message_en: 'Saved securely on this device. It will synchronize when the app is online and unlocked.' },
    };
  }

  async function operations() {
    if (!dataKey) return [];
    const rows = (await allValues('outbox')).sort((a, b) => a.created_at.localeCompare(b.created_at));
    const output = [];
    for (const row of rows) {
      let protectedValue = null;
      let errorMessage = null;
      try { protectedValue = await decrypt(row.envelope); } catch (_) { /* Marked unreadable in UI. */ }
      try { if (row.error) errorMessage = (await decrypt(row.error)).value; } catch (_) { /* Protected error remains hidden. */ }
      output.push({ ...row, protected: protectedValue, error_message: errorMessage });
    }
    return output;
  }

  async function markOperation(row, status, lastError = null, result = null) {
    const updated = {
      ...row,
      status,
      last_error: null,
      updated_at: new Date().toISOString(),
      attempts: Number(row.attempts || 0) + 1,
    };
    updated.error = lastError ? await encrypt({ user_id: enrollment.user_id, value: String(lastError) }) : null;
    if (result !== null) updated.result = await encrypt({ user_id: enrollment.user_id, value: result });
    await putValue('outbox', updated);
    return updated;
  }

  async function sync({ token, countryCode } = {}) {
    if (syncing) return stats();
    if (!navigator.onLine) throw new Error('No network connection is available.');
    if (!dataKey || !enrollment) throw new Error('Unlock offline mode before synchronizing.');
    if (!leaseValid()) throw new Error('Renew the offline access lease before synchronizing.');
    if (!token) throw new Error('Sign in online again before synchronizing protected transactions.');
    syncing = true;
    emit();
    let needsReview = false;
    try {
      const rows = (await allValues('outbox'))
        .filter(row => ['PENDING', 'RETRY', 'BLOCKED_AUTH'].includes(row.status))
        .sort((a, b) => a.created_at.localeCompare(b.created_at));
      for (const row of rows) {
        if (row.next_attempt_at && Date.now() < new Date(row.next_attempt_at).getTime()) continue;
        let item;
        try { item = await decrypt(row.envelope); } catch (_) {
          await markOperation(row, 'NEEDS_REVIEW', 'Protected transaction could not be decrypted.');
          needsReview = true;
          break;
        }
        if (item.user_id !== enrollment.user_id) {
          await markOperation(row, 'NEEDS_REVIEW', 'Transaction belongs to a different user.');
          needsReview = true;
          break;
        }
        let response;
        try {
          response = await fetch(`${API}${item.path}`, {
            method: item.method,
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`,
              'X-Country-Code': item.country_code || countryCode || '',
              'X-Idempotency-Key': row.id,
              'X-Offline-Created-At': row.created_at,
              'X-Offline-Device-ID': enrollment.device_id,
            },
            body: JSON.stringify(item.body),
          });
        } catch (error) {
          row.next_attempt_at = new Date(Date.now() + Math.min(300000, 5000 * (Number(row.attempts || 0) + 1))).toISOString();
          await markOperation(row, 'RETRY', error.message || 'Network interruption during sync.');
          break;
        }
        const contentType = response.headers.get('content-type') || '';
        const result = contentType.includes('application/json') ? await response.json() : await response.text();
        const detail = typeof result === 'object' ? (result.detail?.message || result.detail || result.message) : result;
        if (response.status === 401) {
          await markOperation(row, 'BLOCKED_AUTH', String(detail || 'Online sign-in is required.'));
          break;
        }
        if (response.status === 409 && response.headers.get('retry-after')) {
          row.next_attempt_at = new Date(Date.now() + Number(response.headers.get('retry-after') || 10) * 1000).toISOString();
          await markOperation(row, 'RETRY', String(detail || 'Server reconciliation is still processing.'));
          break;
        }
        if (response.status === 429 || response.status >= 500) {
          row.next_attempt_at = new Date(Date.now() + Number(response.headers.get('retry-after') || 30) * 1000).toISOString();
          await markOperation(row, 'RETRY', String(detail || `Server returned ${response.status}.`));
          break;
        }
        if (!response.ok) {
          await markOperation(row, 'NEEDS_REVIEW', String(detail || `Transaction was rejected (${response.status}).`), result);
          needsReview = true;
          break;
        }
        await markOperation(row, 'SYNCED', null, result);
      }

      const currentStats = await stats();
      try {
        await fetch(`${API}/offline/devices/${encodeURIComponent(enrollment.device_id)}/heartbeat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({
            outcome: needsReview || currentStats.needs_review ? 'NEEDS_REVIEW' : (currentStats.pending ? 'NO_CHANGES' : 'SYNCED'),
            pending_count: currentStats.pending,
          }),
        });
      } catch (_) { /* The outbox receipts remain authoritative. */ }
      const retentionCutoff = Date.now() - 7 * 24 * 3600000;
      for (const row of await allValues('outbox')) {
        if (row.status === 'SYNCED' && new Date(row.updated_at).getTime() < retentionCutoff) await deleteValue('outbox', row.id);
      }
      return currentStats;
    } finally {
      syncing = false;
      emit();
    }
  }

  async function retry(operationIdValue) {
    const row = await getValue('outbox', operationIdValue);
    if (!row) throw new Error('Offline transaction not found.');
    row.status = 'PENDING';
    row.last_error = null;
    row.error = null;
    row.next_attempt_at = new Date().toISOString();
    row.updated_at = new Date().toISOString();
    await putValue('outbox', row);
    emit();
  }

  async function discard(operationIdValue, confirmation) {
    const row = await getValue('outbox', operationIdValue);
    if (!row) return;
    if (!['NEEDS_REVIEW', 'BLOCKED_AUTH'].includes(row.status) || confirmation !== operationIdValue) {
      throw new Error('Only a reviewed rejected transaction can be discarded, using its full operation ID.');
    }
    await deleteValue('outbox', operationIdValue);
    emit();
  }

  async function stats() {
    const rows = database ? await allValues('outbox').catch(() => []) : [];
    return {
      enrolled: Boolean(enrollment),
      unlocked: Boolean(dataKey) && leaseValid(),
      expired: Boolean(enrollment && Date.now() > new Date(enrollment.expires_at).getTime()),
      expires_at: enrollment?.expires_at || null,
      device_id: enrollment?.device_id || null,
      user_id: enrollment?.user_id || null,
      pending: rows.filter(row => ['PENDING', 'RETRY', 'BLOCKED_AUTH'].includes(row.status)).length,
      needs_review: rows.filter(row => row.status === 'NEEDS_REVIEW').length,
      synced: rows.filter(row => row.status === 'SYNCED').length,
      syncing,
      online: navigator.onLine,
      install_available: Boolean(installPrompt),
      installed: window.matchMedia('(display-mode: standalone)').matches || Boolean(navigator.standalone),
    };
  }

  function state() {
    return {
      enrolled: Boolean(enrollment),
      unlocked: Boolean(dataKey) && leaseValid(),
      expired: Boolean(enrollment && Date.now() > new Date(enrollment.expires_at).getTime()),
      expires_at: enrollment?.expires_at || null,
      device_id: enrollment?.device_id || null,
      user_id: enrollment?.user_id || null,
    };
  }

  async function install() {
    if (!installPrompt) throw new Error('Use your browser menu and choose “Install app” or “Add to Home Screen”.');
    const prompt = installPrompt;
    installPrompt = null;
    await prompt.prompt();
    const choice = await prompt.userChoice;
    emit();
    return choice;
  }

  window.UmojaOffline = {
    init,
    enroll,
    unlock,
    renew,
    refreshProfile,
    lock,
    wipe,
    state,
    stats,
    operations,
    queueable,
    enqueue,
    cacheResponse,
    cachedResponse,
    sync,
    retry,
    discard,
    install,
    createOperationId: operationId,
    subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener); },
  };
})();
