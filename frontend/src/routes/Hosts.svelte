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
      class="select-cyber"
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
        class="input-cyber pl-8 w-56"
      />
      <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500 text-xs">🔍</span>
    </div>
  </div>

  {#if loading}
    <LoadingSpinner message="Chargement des hôtes…" />
  {:else if error}
    <ErrorBox message={error} onRetry={fetchAll} />
  {:else if filteredHosts.length === 0}
    <div class="glass rounded-xl p-12 text-center">
      {#if searchIp || campaignFilter}
        <p class="text-slate-500 text-lg">Aucun hôte ne correspond aux filtres.</p>
        <button onclick={() => { searchIp = ''; campaignFilter = ''; fetchAll(); }}
          class="btn-cyber text-sm mt-4 inline-block">
          Réinitialiser les filtres
        </button>
      {:else}
        <p class="text-slate-500 text-lg">Aucun hôte détecté.</p>
      {/if}
    </div>
  {:else}
    <div class="glass rounded-xl overflow-hidden">
      <table class="table-cyber">
        <thead>
          <tr>
            <th>IP</th>
            <th>Hostname</th>
            <th>OS</th>
            <th>Statut</th>
            <th>Ports ouverts</th>
            <th>Campagne</th>
            <th>Dernière vue</th>
          </tr>
        </thead>
        <tbody>
          {#each filteredHosts as host (host.id)}
            <tr class="border-b border-slate-800/50 hover:bg-slate-800/30 cursor-pointer transition-colors"
              onclick={() => onSelectHost(host.id)}>
              <td class="font-mono text-sm text-cyan-400">{host.ip || '—'}</td>
              <td class="text-sm text-slate-300">{host.hostname || '—'}</td>
              <td class="text-sm text-slate-400">{host.os || '—'}</td>
              <td>
                <span class="badge {host.status === 'up' ? 'badge-up' : host.status === 'down' ? 'badge-down' : 'badge-none'}">
                  {host.status || 'inconnu'}
                </span>
              </td>
              <td class="text-sm text-slate-400">{host.port_count ?? '—'}</td>
              <td class="text-sm text-slate-400">{getCampaignName(host.campaign_id)}</td>
              <td class="text-sm text-slate-500 whitespace-nowrap">{formatDate(host.last_seen)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <p class="text-xs text-slate-600 mt-3">
      {filteredHosts.length} hôte{filteredHosts.length !== 1 ? 's' : ''} affiché{filteredHosts.length !== 1 ? 's' : ''}
      {#if searchIp || campaignFilter} (filtré{filteredHosts.length !== 1 ? 's' : ''}){/if}
    </p>
  {/if}
</div>
