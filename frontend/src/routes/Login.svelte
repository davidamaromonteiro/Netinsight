<script>
  import { auth } from '../lib/stores/auth';
  import Logo from '../lib/components/Logo.svelte';

  let email = $state('');
  let password = $state('');
  let error = $state('');
  let loading = $state(false);
  let showPassword = $state(false);

  async function handleLogin(e) {
    e.preventDefault();
    error = '';
    loading = true;
    try { await auth.login(email, password); }
    catch (err) { error = err.message || 'Email ou mot de passe incorrect'; }
    finally { loading = false; }
  }
</script>

<div class="min-h-screen flex items-center justify-center p-4 relative overflow-hidden"
  style="background: radial-gradient(ellipse at top, #0f172a 0%, #0a0e17 60%, #060a10 100%);">
  <!-- Decorative background glow -->
  <div class="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-cyan-500/5 rounded-full blur-3xl pointer-events-none"></div>
  <div class="absolute bottom-0 left-1/3 w-[400px] h-[400px] bg-blue-500/5 rounded-full blur-3xl pointer-events-none"></div>

  <div class="w-full max-w-md animate-fade-in relative z-10">
    <!-- Logo -->
    <div class="mb-8">
      <Logo mode="hero" />
    </div>

    <!-- Card -->
    <div class="glass rounded-2xl p-8">
      <h2 class="text-base font-semibold text-slate-200 mb-6">Connexion</h2>

      {#if error}
        <div class="mb-4 px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm flex items-center gap-2">
          <svg class="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <span>{error}</span>
        </div>
      {/if}

      <form onsubmit={handleLogin} class="space-y-4">
        <div>
          <label for="email" class="block text-xs text-slate-400 mb-1.5 uppercase tracking-wider font-medium">Email</label>
          <input id="email" type="email" bind:value={email} required placeholder="admin@netinsight.io"
            class="input-cyber" />
        </div>
        <div>
          <label for="password" class="block text-xs text-slate-400 mb-1.5 uppercase tracking-wider font-medium">Mot de passe</label>
          <div class="relative">
            <input id="password" type={showPassword ? 'text' : 'password'} bind:value={password} required placeholder="••••••••"
              class="input-cyber pr-10" />
            <button type="button" onclick={() => showPassword = !showPassword}
              class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors text-sm">
              {showPassword ? '🙈' : '👁️'}
            </button>
          </div>
        </div>
        <button type="submit" disabled={loading}
          class="btn-cyber w-full py-2.5 text-sm flex items-center justify-center gap-2">
          {#if loading}
            <span class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            <span>Connexion...</span>
          {:else}
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"/>
            </svg>
            <span>Se connecter</span>
          {/if}
        </button>
      </form>
    </div>

    <p class="text-center text-[10px] text-slate-700 mt-6 font-mono tracking-wider">NetInsight v0.3.0 — Sécurité réseau</p>
  </div>
</div>
