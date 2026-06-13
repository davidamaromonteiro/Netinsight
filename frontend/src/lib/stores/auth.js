/**
 * Svelte store for authentication state.
 *
 * TODO: Move JWT to httpOnly cookie (security).
 *       The token should be set by the backend via Set-Cookie
 *       and read from document.cookie on the client.
 */
import { writable } from 'svelte/store';
import { api } from '../api/client';

function parseJwt(token) {
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(base64));
  } catch { return {}; }
}

function createAuthStore() {
  const { subscribe, set } = writable({
    isAuthenticated: false,
    token: null,
    user: null,
  });

  return {
    subscribe,

    init() {
      const token = api.loadToken();
      if (token) {
        const claims = parseJwt(token);
        set({
          isAuthenticated: true,
          token,
          user: { email: claims.sub || null, role: claims.role || 'analyst' },
        });
      }
    },

    async login(email, password) {
      const data = await api.login(email, password);
      api.setToken(data.access_token);
      const claims = parseJwt(data.access_token);

      set({
        isAuthenticated: true,
        token: data.access_token,
        user: { email, role: claims.role || 'analyst' },
      });
    },

    loginWithToken(token) {
      api.setToken(token);
      const claims = parseJwt(token);
      set({
        isAuthenticated: true,
        token,
        user: { email: claims.sub || null, role: claims.role || 'analyst' },
      });
    },

    logout() {
      api.clearToken();
      set({
        isAuthenticated: false,
        token: null,
        user: null,
      });
    },
  };
}

export const auth = createAuthStore();
