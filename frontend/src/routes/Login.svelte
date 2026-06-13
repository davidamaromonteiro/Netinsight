<script>
  import { auth } from '../lib/stores/auth';

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
    <div class="text-center mb-10">
      <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4" style="background: linear-gradient(135deg, #06b6d4, #3b82f6); box-shadow: 0 0 40px rgba(6,182,212,0.3);">
        <span class="text-2xl font-bold text-white">N</span>
      </div>
      <h1 class="text-3xl font-bold text-gradient">NetInsight</h1>
      <p class="text-slate-500 mt-2 text-sm">Plateforme d'analyse de sécurité réseau</p>
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

    <p class="text-center text-xs text-slate-600 mt-6">NetInsight v0.2.0 — Sécurité réseau</p>
  </div>
</div>
