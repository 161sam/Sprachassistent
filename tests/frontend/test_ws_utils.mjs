import assert from 'node:assert';
import { getAuthToken } from '../../voice-assistant-apps/shared/core/ws-utils.js';

global.localStorage = {
  store: { voice_auth_token: 'abc' },
  getItem(key) { return this.store[key] || null; },
  setItem(key, value) { this.store[key] = value; }
};

const token = await getAuthToken();
assert.strictEqual(token, 'abc');
assert.strictEqual(global.localStorage.store.wsToken, 'abc');

delete global.localStorage.store.voice_auth_token;
delete global.localStorage.store.wsToken;
const token2 = await getAuthToken();
assert.strictEqual(token2, 'devsecret');
assert.strictEqual(global.localStorage.store.wsToken, 'devsecret');

console.log('ws-utils tests passed');
