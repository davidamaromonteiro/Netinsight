<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api/client';
  import LoadingSpinner from '../lib/components/LoadingSpinner.svelte';
  import ErrorBox from '../lib/components/ErrorBox.svelte';

  let logs = $state([]);
  let ready = $state(false);
  let error = $state('');
  let actionFilter = $state('');
  let userFilter = $state('');

  onMount(async () => {
    try { logs = await api.getAuditLogs(); } catch (e) { error = e.message; }
    ready = true;
  });

  async function filter() {
    ready = false;
    try { logs = await api.getAuditLogs(actionFilter || null, userFilter || null); } catch(_) {}
    ready = true;
  }

  function actionLabel(a) {
    const m = {
      user_login: 'Connexion', user_created: 'Utilisateur cree', user_deleted: 'Utilisateur supprime',
      user_role_changed: 'Role modifie', user_toggled: 'Compte active/desactive',
      sqlmap_scan_created: 'Scan SQLMap cree', sqlmap_scan_triggered: 'Scan SQLMap lance',
      sqlmap_scan_deleted: 'Scan SQLMap supprime',
    };
    return m[a] || a;
  }

  function actionColor(a) {
    if (a.startsWith('user_')) return 'text-cyan-400';
    if (a.startsWith('sqlmap')) return 'text-purple-400';
    return 'text-slate-400';
  }

  function formatDate(d) {
    if (!d) return '—';
    return new Date(d).toLocaleString('fr-FR');
  }
</script>

<div class="max-w-6xl mx-auto">
  <h1 class="text-3xl font-bold mb-2">Historique</h1>
  <p class="text-sm text-slate-400 mb-8">Journal des actions realisees sur la plateforme</p>

  <div class="flex gap-3 mb-6">
    <select bind:value={actionFilter} onchange={filter} class="bg-slate-900/80 border border-slate-700/50 rounded-xl text-white text-sm px-3 py-2">
      <option value="">Toutes les actions</option>
      <option value="user_login">Connexion</option>
      <option value="user_created">Utilisateur cree</option>
      <option value="user_deleted">Utilisateur supprime</option>
      <option value="user_role_changed">Role modifie</option>
      <option value="sqlmap_scan_created">Scan cree</option>
      <option value="sqlmap_scan_triggered">Scan lance</option>
      <option value="sqlmap_scan_deleted">Scan supprime</option>
    </select>
    <input type="text" bind:value={userFilter} oninput={filter} placeholder="Filtrer par email..."
      class="flex-1 bg-slate-900/80 border border-slate-700/50 rounded-xl text-white placeholder-slate-600 text-sm px-3 py-2" />
  </div>

  {#if !ready}
    <LoadingSpinner message="Chargement..." />
  {:else if error}
    <ErrorBox message={error} />
  {:else if logs.length === 0}
    <div class="glass rounded-xl p-12 text-center"><p class="text-gray-500">Aucun log</p></div>
  {:else}
    <div class="glass rounded-xl overflow-hidden">
      <table class="w-full">
        <thead>
          <tr class="border-b border-gray-800 text-left">
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Date</th>
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Utilisateur</th>
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Action</th>
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider hidden sm:table-cell">Details</th>
          </tr>
        </thead>
        <tbody>
          {#each logs as log (log.id)}
            <tr class="border-b border-gray-800/50 hover:bg-slate-800/30 transition-colors">
              <td class="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">{formatDate(log.created_at)}</td>
              <td class="px-4 py-3 text-sm text-gray-300 font-mono">{log.user_email}</td>
              <td class="px-4 py-3">
                <span class="text-xs font-medium {actionColor(log.action)}">{actionLabel(log.action)}</span>
              </td>
              <td class="px-4 py-3 text-xs text-slate-500 hidden sm:table-cell">
                {#if log.details?.name}{log.details.name}{/if}
                {#if log.details?.target}{log.details.target}{/if}
                {#if log.details?.role} → {log.details.role}{/if}
                {#if log.details?.active !== undefined}{log.details.active ? 'active' : 'desactive'}{/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>
