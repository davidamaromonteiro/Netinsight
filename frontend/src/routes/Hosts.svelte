<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api/client';
  import StatusBadge from '../lib/components/StatusBadge.svelte';
  import LoadingSpinner from '../lib/components/LoadingSpinner.svelte';
  import ErrorBox from '../lib/components/ErrorBox.svelte';

  let { onSelectHost } = $props();

  let hosts = $state([]);
  let campaigns = $state([]);
  let loading = $state(true);
  let error = $state('');
  let campaignFilter = $state('');
  let searchIp = $state('');

  onMount(() => {
    fetchAll();
  });

  async function fetchAll() {
    loading = true;
    error = '';
    try {
      [hosts, campaigns] = await Promise.all([
        api.getHosts(campaignFilter || null),
        api.getCampaigns(),
      ]);
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  function handleFilterChange() {
    fetchAll();
  }

  function getCampaignName(campaignId) {
    const campaign = campaigns.find((c) => c.id === campaignId);
    return campaign ? campaign.name : '—';
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

  let filteredHosts = $derived(
    hosts.filter((host) => {
      if (searchIp.trim() && !host.ip.toLowerCase().includes(searchIp.trim().toLowerCase())) {
        return false;
      }
      return true;
    }),
  );
</script>

<div class="max-w-6xl mx-auto">
  <!-- Header -->
  <div class="flex items-center justify-between mb-8">
    <h1 class="text-3xl font-bold">Hôtes détectés</h1>
  </div>

  <!-- Filters -->
  <div class="flex flex-wrap items-center gap-4 mb-6">
    <select
      bind:value={campaignFilter}
      onchange={handleFilterChange}
      class="bg-slate-900/80 border border-slate-700/50 rounded-xl text-white placeholder-slate-600 focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/30 transition-all text-sm px-3 py-2"
    >
      <option value="">Toutes les campagnes</option>
      {#each campaigns as campaign (campaign.id)}
        <option value={campaign.id}>{campaign.name}</option>
      {/each}
    </select>

    <div class="relative">
      <input
        type="text"
        bind:value={searchIp}
        placeholder="Rechercher par IP…"
        class="pl-8 bg-slate-900/80 border border-slate-700/50 rounded-xl text-white placeholder-slate-600 focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/30 transition-all text-sm px-3 py-2 w-56"
      />
      <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500 text-xs">🔍</span>
    </div>
  </div>

  <!-- Content -->
  {#if loading}
    <LoadingSpinner message="Chargement des hôtes…" />
  {:else if error}
    <ErrorBox message={error} onRetry={fetchAll} />
  {:else if filteredHosts.length === 0}
    <div class="glass rounded-xl p-12 text-center">
      {#if searchIp || campaignFilter}
        <p class="text-gray-500 text-lg">Aucun hôte ne correspond aux filtres.</p>
        <button
          onclick={() => { searchIp = ''; campaignFilter = ''; fetchAll(); }}
          class="mt-4 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 font-medium rounded-lg transition-colors"
        >
          Réinitialiser les filtres
        </button>
      {:else}
        <p class="text-gray-500 text-lg">Aucun hôte détecté.</p>
      {/if}
    </div>
  {:else}
    <!-- Hosts table -->
    <div class="glass rounded-xl overflow-hidden">
      <table class="w-full">
        <thead>
          <tr class="border-b border-gray-800 text-left">
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">IP</th>
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Hostname</th>
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">OS</th>
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Statut</th>
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Ports ouverts</th>
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Campagne</th>
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Dernière vue</th>
          </tr>
        </thead>
        <tbody>
          {#each filteredHosts as host (host.id)}
            <tr
              class="border-b border-gray-800/50 hover:bg-slate-800/30 cursor-pointer transition-colors"
              onclick={() => onSelectHost(host.id)}
            >
              <td class="px-4 py-3 font-mono text-sm text-cyan-400">{host.ip || '—'}</td>
              <td class="px-4 py-3 text-sm text-gray-300">{host.hostname || '—'}</td>
              <td class="px-4 py-3 text-sm text-gray-400">{host.os || '—'}</td>
              <td class="px-4 py-3">
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
              <td class="px-4 py-3 text-sm text-gray-400">{host.port_count ?? '—'}</td>
              <td class="px-4 py-3 text-sm text-gray-400">{getCampaignName(host.campaign_id)}</td>
              <td class="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">{formatDate(host.last_seen)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <!-- Count -->
    <p class="text-xs text-gray-600 mt-3">
      {filteredHosts.length} hôte{filteredHosts.length !== 1 ? 's' : ''} affiché{filteredHosts.length !== 1 ? 's' : ''}
      {#if searchIp || campaignFilter} (filtré{filteredHosts.length !== 1 ? 's' : ''}){/if}
    </p>
  {/if}
</div>
