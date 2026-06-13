<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api/client';
  import StatusBadge from '../lib/components/StatusBadge.svelte';
  import LoadingSpinner from '../lib/components/LoadingSpinner.svelte';
  import ErrorBox from '../lib/components/ErrorBox.svelte';

  let { campaignId, onBack } = $props();

  let campaign = $state(null);
  let hosts = $state([]);
  let report = $state(null);
  let loading = $state(true);
  let error = $state('');
  let actionLoading = $state(false);
  let actionMessage = $state('');

  onMount(() => { fetchAll(); });

  async function fetchAll() {
    loading = true; error = '';
    try {
      [campaign, hosts, report] = await Promise.all([
        api.getCampaign(campaignId),
        api.getHosts(campaignId),
        api.getCampaignReport(campaignId).catch(() => null),
      ]);
    } catch (err) { error = err.message; }
    finally { loading = false; }
  }

  async function handleTriggerScan() {
    if (!confirm('Lancer le scan pour cette campagne ?')) return;
    actionLoading = true; actionMessage = '';
    try { await api.triggerScan(campaignId); actionMessage = 'Scan lancé avec succès.'; await fetchAll(); }
    catch (err) { actionMessage = `Erreur : ${err.message}`; }
    finally { actionLoading = false; }
  }

  async function handleTriggerReport() {
    actionLoading = true; actionMessage = '';
    try { report = await api.triggerReport(campaignId); actionMessage = 'Rapport généré avec succès.'; }
    catch (err) { actionMessage = `Erreur : ${err.message}`; }
    finally { actionLoading = false; }
  }

  function formatDate(dateStr) {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('fr-FR', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' });
  }
</script>

<div class="max-w-6xl mx-auto page-fade">
  <!-- Back button -->
  <button onclick={onBack}
    class="mb-4 px-3 py-1.5 text-sm text-slate-400 hover:text-slate-200 bg-slate-800/80 hover:bg-slate-700/80 rounded-lg transition-all duration-200 flex items-center gap-1.5 w-fit">
    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/></svg>
    Retour aux campagnes
  </button>

  {#if loading}
    <LoadingSpinner message="Chargement de la campagne…" />
  {:else if error}
    <ErrorBox message={error} onRetry={fetchAll} />
  {:else if campaign}
    <!-- Campaign info card -->
    <div class="glass rounded-xl p-6 mb-8">
      <div class="flex items-start justify-between mb-4">
        <div>
          <h1 class="text-2xl font-bold text-slate-100">{campaign.name}</h1>
          {#if campaign.description}
            <p class="text-slate-400 mt-1 text-sm">{campaign.description}</p>
          {/if}
        </div>
        <StatusBadge status={campaign.status} />
      </div>

      <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4 text-sm">
        <div>
          <p class="text-slate-500 text-xs uppercase tracking-wider">Créée le</p>
          <p class="text-slate-300">{formatDate(campaign.created_at)}</p>
        </div>
        <div>
          <p class="text-slate-500 text-xs uppercase tracking-wider">Mise à jour</p>
          <p class="text-slate-300">{formatDate(campaign.updated_at)}</p>
        </div>
        <div>
          <p class="text-slate-500 text-xs uppercase tracking-wider">Cibles</p>
          <p class="text-slate-300">{Array.isArray(campaign.targets) ? campaign.targets.length : '—'}</p>
        </div>
        <div>
          <p class="text-slate-500 text-xs uppercase tracking-wider">Hôtes</p>
          <p class="text-slate-300">{hosts.length}</p>
        </div>
      </div>

      {#if campaign.targets && Array.isArray(campaign.targets) && campaign.targets.length > 0}
        <div class="mt-4 pt-4 border-t border-slate-800">
          <p class="text-xs text-slate-500 mb-2 uppercase tracking-wider">Cibles configurées</p>
          <div class="flex flex-wrap gap-1.5">
            {#each campaign.targets as target}
              <span class="px-2 py-0.5 text-xs bg-slate-800/80 text-slate-300 border border-slate-700/30 rounded-lg font-mono">{target}</span>
            {/each}
          </div>
        </div>
      {/if}

      <!-- Actions -->
      <div class="mt-6 pt-4 border-t border-slate-800 flex flex-wrap items-center gap-3">
        {#if campaign.status === 'pending' || campaign.status === 'failed'}
          <button onclick={handleTriggerScan} disabled={actionLoading}
            class="btn-cyber text-sm" class:opacity-50={actionLoading}>
            {actionLoading ? 'Lancement…' : '🚀 Lancer le scan'}
          </button>
        {/if}
        {#if campaign.status === 'completed'}
          <button onclick={handleTriggerReport} disabled={actionLoading}
            class="btn-cyber green text-sm">
            {actionLoading ? 'Génération…' : '📄 Générer le rapport'}
          </button>
        {/if}
        {#if report && report.id}
          <button onclick={() => api.downloadReport(report.id, `rapport_${campaign.name}.pdf`)}
            class="btn-cyber text-sm">
            📥 Télécharger le rapport
          </button>
        {/if}
        {#if actionMessage}
          <span class="text-sm ml-2" class:text-green-400={!actionMessage.startsWith('Erreur')} class:text-red-400={actionMessage.startsWith('Erreur')}>
            {actionMessage}
          </span>
        {/if}
      </div>
    </div>

    <!-- Hosts list -->
    <div class="glass rounded-xl overflow-hidden">
      <div class="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
        <h2 class="text-base font-semibold text-slate-200">Hôtes détectés <span class="text-slate-500 font-normal">({hosts.length})</span></h2>
      </div>
      {#if hosts.length === 0}
        <div class="p-12 text-center">
          <p class="text-slate-500">Aucun hôte détecté pour cette campagne.</p>
        </div>
      {:else}
        <table class="table-cyber">
          <thead>
            <tr>
              <th>IP</th>
              <th>Hostname</th>
              <th>OS</th>
              <th>Statut</th>
              <th>Ports ouverts</th>
            </tr>
          </thead>
          <tbody>
            {#each hosts as host (host.id)}
              <tr class="cursor-pointer hover:bg-slate-800/30 transition-colors">
                <td class="font-mono text-sm text-cyan-400">{host.ip || '—'}</td>
                <td class="text-sm text-slate-300">{host.hostname || '—'}</td>
                <td class="text-sm text-slate-400">{host.os || '—'}</td>
                <td>
                  <span class="badge {host.status === 'up' ? 'badge-up' : host.status === 'down' ? 'badge-down' : 'badge-none'}">
                    {host.status || 'inconnu'}
                  </span>
                </td>
                <td class="text-sm text-slate-400">{host.port_count ?? '—'}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>
  {/if}
</div>