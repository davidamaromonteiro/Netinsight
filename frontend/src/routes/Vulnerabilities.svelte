<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api/client';
  import LoadingSpinner from '../lib/components/LoadingSpinner.svelte';
  import ErrorBox from '../lib/components/ErrorBox.svelte';

  let vulnerabilities = $state([]);
  let hosts = $state([]);
  let loading = $state(true);
  let error = $state('');
  let hostFilter = $state('');
  let severityFilter = $state('');
  let expandedVuln = $state(null);

  onMount(() => {
    fetchAll();
  });

  async function fetchAll() {
    loading = true;
    error = '';
    try {
      [vulnerabilities, hosts] = await Promise.all([
        api.getVulnerabilities(hostFilter || null, severityFilter || null),
        api.getHosts(),
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

  function getHostIp(hostId) {
    const h = hosts.find((host) => host.id === hostId);
    return h ? h.ip : hostId || '—';
  }

  function truncate(text, maxLen = 120) {
    if (!text) return '—';
    return text.length > maxLen ? text.slice(0, maxLen) + '…' : text;
  }

  function severityClass(severity) {
    const map = {
      CRITICAL: 'bg-red-900/50 text-red-400 border-red-800',
      HIGH: 'bg-orange-900/50 text-orange-400 border-orange-800',
      MEDIUM: 'bg-yellow-900/50 text-yellow-400 border-yellow-800',
      LOW: 'bg-blue-900/50 text-blue-400 border-blue-800',
    };
    return map[severity] || 'badge-none';
  }

  function cvssColor(score) {
    const s = parseFloat(score);
    if (isNaN(s)) return 'text-slate-400';
    if (s >= 9.0) return 'text-red-400';
    if (s >= 7.0) return 'text-orange-400';
    if (s >= 4.0) return 'text-yellow-400';
    return 'text-blue-400';
  }

  function formatCvss(score) {
    const s = parseFloat(score);
    return isNaN(s) ? '—' : s.toFixed(1);
  }

  let sortedVulns = $derived(
    [...vulnerabilities].sort((a, b) => {
      const scoreA = parseFloat(a.cvss_score) || 0;
      const scoreB = parseFloat(b.cvss_score) || 0;
      return scoreB - scoreA;
    }),
  );

  function toggleExpand(cveId) {
    expandedVuln = expandedVuln === cveId ? null : cveId;
  }
</script>

<div class="max-w-6xl mx-auto">
  <!-- Header -->
  <div class="flex items-center justify-between mb-8">
    <h1 class="text-3xl font-bold">Vulnérabilités</h1>
  </div>

  <!-- Filters -->
  <div class="flex flex-wrap items-center gap-4 mb-6">
    <select
      bind:value={hostFilter}
      onchange={handleFilterChange}
      class="select-cyber"
    >
      <option value="">Tous les hôtes</option>
      {#each hosts as host (host.id)}
        <option value={host.id}>{host.ip}{host.hostname ? ' (' + host.hostname + ')' : ''}</option>
      {/each}
    </select>

    <select
      bind:value={severityFilter}
      onchange={handleFilterChange}
      class="select-cyber"
    >
      <option value="">Toutes les sévérités</option>
      <option value="CRITICAL">Critique</option>
      <option value="HIGH">Haute</option>
      <option value="MEDIUM">Moyenne</option>
      <option value="LOW">Basse</option>
      <option value="NONE">Aucune</option>
    </select>
  </div>

  <!-- Content -->
  {#if loading}
    <LoadingSpinner message="Chargement des vulnérabilités…" />
  {:else if error}
    <ErrorBox message={error} onRetry={fetchAll} />
  {:else if sortedVulns.length === 0}
    <div class="glass rounded-xl p-12 text-center">
      {#if hostFilter || severityFilter}
        <p class="text-slate-500 text-lg">Aucune vulnérabilité ne correspond aux filtres.</p>
        <button onclick={() => { hostFilter = ''; severityFilter = ''; fetchAll(); }}
          class="btn-cyber text-sm mt-4 inline-block">
          Réinitialiser les filtres
        </button>
      {:else}
        <p class="text-slate-500 text-lg">Aucune vulnérabilité détectée.</p>
      {/if}
    </div>
  {:else}
    <div class="glass rounded-xl overflow-hidden">
      <table class="table-cyber">
        <thead>
          <tr>
            <th>CVE ID</th>
            <th>Sévérité</th>
            <th>CVSS</th>
            <th>Hôte</th>
            <th>Description</th>
            <th class="w-8"></th>
          </tr>
        </thead>
        <tbody>
          {#each sortedVulns as vuln (vuln.id)}
            <tr class="border-b border-slate-800/50 hover:bg-slate-800/30 cursor-pointer transition-colors"
              onclick={() => toggleExpand(vuln.cve_id || vuln.id)}>
              <td class="font-mono text-sm text-cyan-400">{vuln.cve_id || vuln.id}</td>
              <td><span class="badge {severityClass(vuln.severity)}">{vuln.severity || 'NONE'}</span></td>
              <td class="font-mono text-sm font-medium {cvssColor(vuln.cvss_score)}">{formatCvss(vuln.cvss_score)}</td>
              <td class="text-sm text-slate-400 font-mono">{getHostIp(vuln.host_id)}</td>
              <td class="text-sm text-slate-400 max-w-md">{truncate(vuln.description)}</td>
              <td class="text-right text-slate-500 text-xs">{expandedVuln === (vuln.cve_id || vuln.id) ? '▲' : '▼'}</td>
            </tr>
            {#if expandedVuln === (vuln.cve_id || vuln.id)}
              <tr class="border-b border-slate-800/50 bg-slate-800/30">
                <td colspan="6" class="px-6 py-4">
                  <p class="text-sm text-slate-300 whitespace-pre-wrap">{vuln.description || '—'}</p>
                  {#if vuln.references && Array.isArray(vuln.references) && vuln.references.length > 0}
                    <div class="mt-3">
                      <p class="text-xs text-slate-500 mb-1 uppercase tracking-wider">Références</p>
                      <ul class="space-y-1">
                        {#each vuln.references as ref}
                          <li><a href={ref} target="_blank" rel="noopener"
                            class="text-xs text-cyan-400 hover:text-cyan-300 underline break-all">{ref}</a></li>
                        {/each}
                      </ul>
                    </div>
                  {/if}
                </td>
              </tr>
            {/if}
          {/each}
        </tbody>
      </table>
    </div>

    <!-- Count -->
    <p class="text-xs text-slate-600 mt-3">
      {sortedVulns.length} vulnérabilité{sortedVulns.length !== 1 ? 's' : ''}
      {#if hostFilter || severityFilter} (filtrée{sortedVulns.length !== 1 ? 's' : ''}){/if}
      — triées par score CVSS décroissant
    </p>
  {/if}
</div>
