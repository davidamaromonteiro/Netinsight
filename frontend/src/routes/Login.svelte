<script>
  import { auth } from '../lib/stores/auth';
  import Logo from '../lib/components/Logo.svelte';

  let email = $state('');
  let password = $state('');
  let error = $state('');
  let loading = $state(false);

  async function handleLogin(e) {
    e.preventDefault();
    error = '';
    loading = true;
    try { await auth.login(email, password); }
    catch (err) { error = err.message || 'Email ou mot de passe incorrect'; }
    finally { loading = false; }
  }
</script>

<div class="min-h-screen flex items-center justify-center p-4" style="background: radial-gradient(ellipse at top, #0f172a 0%, #0a0e17 60%, #060a10 100%);">
  <div class="w-full max-w-md animate-fade-in">
    <!-- Logo -->
    <div class="mb-10">
      <Logo mode="hero" />
    </div>

    <!-- Card -->
    <div class="glass rounded-2xl p-8">
      <h2 class="text-lg font-semibold text-white mb-6">Connexion</h2>

      {#if error}
        <div class="mb-4 px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm flex items-center gap-2">
          <span>⚠️</span> {error}
        </div>
      {/if}

      <form onsubmit={handleLogin} class="space-y-4">
        <div>
          <label for="email" class="block text-xs text-slate-400 mb-1.5 uppercase tracking-wider font-medium">Email</label>
          <input id="email" type="email" bind:value={email} required placeholder="admin@exemple.fr"
            class="w-full px-4 py-2.5 bg-slate-900/80 border border-slate-700/50 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/30 transition-all text-sm" />
        </div>
        <div>
          <label for="password" class="block text-xs text-slate-400 mb-1.5 uppercase tracking-wider font-medium">Mot de passe</label>
          <input id="password" type="password" bind:value={password} required placeholder="••••••••"
            class="w-full px-4 py-2.5 bg-slate-900/80 border border-slate-700/50 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/30 transition-all text-sm" />
        </div>
        <button type="submit" disabled={loading}
          class="w-full py-2.5 rounded-xl text-sm font-medium transition-all duration-300 disabled:opacity-50 relative overflow-hidden"
          style="background: linear-gradient(135deg, #06b6d4, #3b82f6); box-shadow: 0 0 20px rgba(6,182,212,0.2);">
          <span class="relative z-10 text-white">{loading ? 'Connexion...' : 'Se connecter'}</span>
        </button>
      </form>
    </div>

    <p class="text-center text-[10px] text-slate-700 mt-6 font-mono tracking-wider">NetInsight v0.3.0 — Sécurité réseau</p>
  </div>
</div>
