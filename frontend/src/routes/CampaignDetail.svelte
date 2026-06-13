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

  onMount(() => {
    fetchAll();
  });

  async function fetchAll() {
    loading = true;
    error = '';
    try {
      [campaign, hosts, report] = await Promise.all([
        api.getCampaign(campaignId),
        api.getHosts(campaignId),
        api.getCampaignReport(campaignId).catch(() => null),
      ]);
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  async function handleTriggerScan() {
    if (!confirm('Lancer le scan pour cette campagne ?')) return;
    actionLoading = true;
    actionMessage = '';
    try {
      await api.triggerScan(campaignId);
      actionMessage = 'Scan lancé avec succès.';
      await fetchAll();
    } catch (err) {
      actionMessage = `Erreur : ${err.message}`;
    } finally {
      actionLoading = false;
    }
  }

  async function handleTriggerReport() {
    actionLoading = true;
    actionMessage = '';
    try {
      const result = await api.triggerReport(campaignId);
      report = result;
      actionMessage = 'Rapport généré avec succès.';
    } catch (err) {
      actionMessage = `Erreur : ${err.message}`;
    } finally {
      actionLoading = false;
    }
  }

  function formatDate(dateStr) {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
</script>

<div class="max-w-6xl mx-auto">
  <!-- Back button -->
  <button
    onclick={onBack}
    class="mb-4 px-3 py-1.5 text-sm text-gray-400 hover:text-gray-200 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
  >
    ← Retour aux campagnes
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
          <h1 class="text-2xl font-bold text-gray-100">{campaign.name}</h1>
          {#if campaign.description}
            <p class="text-gray-400 mt-1">{campaign.description}</p>
          {/if}
        </div>
        <StatusBadge status={campaign.status} />
      </div>

      <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4 text-sm">
        <div>
          <p class="text-gray-500">Créée le</p>
          <p class="text-gray-300">{formatDate(campaign.created_at)}</p>
        </div>
        <div>
          <p class="text-gray-500">Mise à jour</p>
          <p class="text-gray-300">{formatDate(campaign.updated_at)}</p>
        </div>
        <div>
          <p class="text-gray-500">Cibles</p>
          <p class="text-gray-300">
            {#if campaign.targets}
              {Array.isArray(campaign.targets) ? campaign.targets.length : '—'}
            {:else}
              —
            {/if}
          </p>
        </div>
        <div>
          <p class="text-gray-500">Hôtes détectés</p>
          <p class="text-gray-300">{hosts.length}</p>
        </div>
      </div>

      <!-- Targets list -->
      {#if campaign.targets && Array.isArray(campaign.targets) && campaign.targets.length > 0}
        <div class="mt-4 pt-4 border-t border-gray-800">
          <p class="text-xs text-gray-500 mb-2">Cibles configurées</p>
          <div class="flex flex-wrap gap-1.5">
            {#each campaign.targets as target}
              <span class="px-2 py-0.5 text-xs bg-slate-800/80 text-slate-300 border border-slate-700/30 rounded-lg font-mono">
                {target}
              </span>
            {/each}
          </div>
        </div>
      {/if}

      <!-- Actions -->
      <div class="mt-6 pt-4 border-t border-gray-800 flex flex-wrap items-center gap-3">
        {#if campaign.status === 'pending' || campaign.status === 'failed'}
          <button
            onclick={handleTriggerScan}
            disabled={actionLoading}
            class="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-medium rounded-lg transition-colors text-sm"
          >
            {actionLoading ? 'Lancement…' : '🚀 Lancer le scan'}
          </button>
        {/if}

        {#if campaign.status === 'completed'}
          <button
            onclick={handleTriggerReport}
            disabled={actionLoading}
            class="px-4 py-2 bg-green-600 hover:bg-green-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-medium rounded-lg transition-colors text-sm"
          >
            {actionLoading ? 'Génération…' : '📄 Générer le rapport'}
          </button>
        {/if}

        {#if report && report.id}
          <button
            onclick={() => api.downloadReport(report.id, `rapport_${campaign.name}.pdf`)}
            class="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white font-medium rounded-lg transition-colors text-sm"
          >
            📥 Télécharger le rapport
          </button>
        {/if}

        {#if actionMessage}
          <span
            class={`text-sm ml-2 ${
              actionMessage.startsWith('Erreur') ? 'text-red-400' : 'text-green-400'
            }`}
          >
            {actionMessage}
          </span>
        {/if}
      </div>
    </div>

    <!-- Hosts list -->
    <div class="glass rounded-xl overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-800">
        <h2 class="text-lg font-semibold">Hôtes détectés ({hosts.length})</h2>
      </div>

      {#if hosts.length === 0}
        <div class="p-12 text-center">
          <p class="text-gray-500">Aucun hôte détecté pour cette campagne.</p>
        </div>
      {:else}
        <table class="w-full">
          <thead>
            <tr class="border-b border-gray-800 text-left">
              <th class="px-6 py-3 text-[11px] text-slate-500 uppercase tracking-wider">IP</th>
              <th class="px-6 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Hostname</th>
              <th class="px-6 py-3 text-[11px] text-slate-500 uppercase tracking-wider">OS</th>
              <th class="px-6 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Statut</th>
              <th class="px-6 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Ports ouverts</th>
            </tr>
          </thead>
          <tbody>
            {#each hosts as host (host.id)}
              <tr class="border-b border-gray-800/50 hover:bg-slate-800/30 transition-colors">
                <td class="px-6 py-3 font-mono text-sm text-cyan-400">{host.ip || '—'}</td>
                <td class="px-6 py-3 text-sm text-gray-300">{host.hostname || '—'}</td>
                <td class="px-6 py-3 text-sm text-gray-400">{host.os || '—'}</td>
                <td class="px-6 py-3">
                  <span
                    class={`px-2 py-0.5 rounded text-xs font-medium border ${
                      host.status === 'up' ? 'bg-green-900/50 text-green-400 border-green-800' :
                      host.status === 'down' ? 'bg-red-900/50 text-red-400 border-red-800' :
                      'bg-slate-800/80 text-slate-300 border-slate-700/30'
                    }`}
                  >
                    {host.status || 'inconnu'}
                  </span>
                </td>
                <td class="px-6 py-3 text-sm text-gray-400">{host.port_count ?? '—'}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>
  {/if}
</div>
