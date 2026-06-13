<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api/client';
  import StatusBadge from '../lib/components/StatusBadge.svelte';
  import LoadingSpinner from '../lib/components/LoadingSpinner.svelte';
  import ErrorBox from '../lib/components/ErrorBox.svelte';

  let { hostId, onBack, onSelectCampaign = null } = $props();

  let host = $state(null);
  let ports = $state([]);
  let vulnerabilities = $state([]);
  let loading = $state(true);
  let error = $state('');
  let enriching = $state(false);
  let enrichResult = $state(null);
  let grabbingBanners = $state(false);
  let banners = $state([]);
  let expandedVuln = $state(null);
  let vulnLoading = $state(false);

  onMount(() => {
    fetchAll();
  });

  async function fetchAll() {
    loading = true;
    error = '';
    try {
      [host, ports, vulnerabilities] = await Promise.all([
        api.getHost(hostId),
        api.getHostPorts(hostId).catch(() => []),
        api.getHostVulnerabilities(hostId).catch(() => []),
      ]);
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  async function refreshVulnerabilities() {
    vulnLoading = true;
    try {
      vulnerabilities = await api.getHostVulnerabilities(hostId);
    } catch (err) {
      error = err.message;
    } finally {
      vulnLoading = false;
    }
  }

  async function handleEnrich() {
    enriching = true;
    enrichResult = null;
    try {
      enrichResult = await api.enrichHost(hostId);
      await refreshVulnerabilities();
    } catch (err) {
      enrichResult = { error: err.message };
    } finally {
      enriching = false;
    }
  }

  async function handleGrabBanners() {
    grabbingBanners = true;
    try { await api.grabBanners(hostId); banners = await api.getHostBanners(hostId); }
    catch (err) { error = err.message; }
    finally { grabbingBanners = false; }
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
    return map[severity] || 'bg-gray-700/50 text-gray-400 border-gray-600';
  }

  function cvssColor(score) {
    const s = parseFloat(score);
    if (isNaN(s)) return 'text-gray-400';
    if (s >= 9.0) return 'text-red-400';
    if (s >= 7.0) return 'text-orange-400';
    if (s >= 4.0) return 'text-yellow-400';
    return 'text-blue-400';
  }

  function formatCvss(score) {
    const s = parseFloat(score);
    return isNaN(s) ? '—' : s.toFixed(1);
  }

  function toggleExpand(cveId) {
    expandedVuln = expandedVuln === cveId ? null : cveId;
  }
</script>

<div class="max-w-6xl mx-auto">
  <!-- Back button -->
  <button
    onclick={onBack}
    class="mb-4 px-3 py-1.5 text-sm text-gray-400 hover:text-gray-200 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
  >
    ← Retour aux hôtes
  </button>

  {#if loading}
    <LoadingSpinner message="Chargement de l'hôte…" />
  {:else if error}
    <ErrorBox message={error} onRetry={fetchAll} />
  {:else if host}
    <!-- ============ Section 1 — Infos hôte ============ -->
    <div class="glass rounded-xl p-6 mb-6">
      <div class="flex items-start justify-between mb-4">
        <div>
          <h1 class="text-2xl font-bold text-gray-100 font-mono">{host.ip || '—'}</h1>
          {#if host.hostname}
            <p class="text-gray-400 mt-0.5">{host.hostname}</p>
          {/if}
        </div>
        <span
          class={`px-2 py-0.5 rounded text-xs font-medium border ${
            host.status === 'up' ? 'bg-green-900/50 text-green-400 border-green-800' :
            host.status === 'down' ? 'bg-red-900/50 text-red-400 border-red-800' :
            'bg-gray-800 text-gray-400 border-gray-700'
          }`}
        >
          {host.status || 'inconnu'}
        </span>
      </div>

      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 text-sm">
        <div>
          <p class="text-gray-500">MAC</p>
          <p class="text-gray-300 font-mono">{host.mac || '—'}</p>
        </div>
        <div>
          <p class="text-gray-500">OS</p>
          <p class="text-gray-300">{host.os || '—'}</p>
        </div>
        <div>
          <p class="text-gray-500">Précision OS</p>
          <p class="text-gray-300">{host.os_accuracy != null ? host.os_accuracy + '%' : '—'}</p>
        </div>
        <div>
          <p class="text-gray-500">Première vue</p>
          <p class="text-gray-300">{formatDate(host.first_seen)}</p>
        </div>
        <div>
          <p class="text-gray-500">Dernière vue</p>
          <p class="text-gray-300">{formatDate(host.last_seen)}</p>
        </div>
        {#if host.campaign_id}
          <div>
            <p class="text-gray-500">Campagne</p>
            {#if onSelectCampaign}
              <button
                onclick={() => onSelectCampaign(host.campaign_id)}
                class="text-cyan-400 hover:text-cyan-300 underline text-sm transition-colors"
              >
                Voir la campagne
              </button>
            {:else}
              <p class="text-gray-300">ID: {host.campaign_id}</p>
            {/if}
          </div>
        {/if}
      </div>
    </div>

    <!-- ============ Section 2 — Ports et services ============ -->
    <div class="glass rounded-xl overflow-hidden mb-6">
      <div class="px-6 py-4 border-b border-gray-800">
        <h2 class="text-lg font-semibold">Ports et services ({ports.length})</h2>
      </div>

      {#if ports.length === 0}
        <div class="p-12 text-center">
          <p class="text-gray-500">Aucun port détecté</p>
        </div>
      {:else}
        <table class="w-full">
          <thead>
            <tr class="border-b border-gray-800 text-left">
              <th class="px-6 py-3 text-xs text-gray-500 font-medium uppercase">Port</th>
              <th class="px-6 py-3 text-xs text-gray-500 font-medium uppercase">Protocole</th>
              <th class="px-6 py-3 text-xs text-gray-500 font-medium uppercase">État</th>
              <th class="px-6 py-3 text-xs text-gray-500 font-medium uppercase">Service</th>
              <th class="px-6 py-3 text-xs text-gray-500 font-medium uppercase">Version</th>
            </tr>
          </thead>
          <tbody>
            {#each ports as port (port.id)}
              <tr class="border-b border-gray-800/50">
                <td class="px-6 py-3 font-mono text-sm text-cyan-400">{port.port}</td>
                <td class="px-6 py-3 text-sm text-gray-400 uppercase">{port.protocol || '—'}</td>
                <td class="px-6 py-3 text-sm">
                  <span
                    class={`px-2 py-0.5 rounded text-xs font-medium border ${
                      port.state === 'open' ? 'bg-green-900/50 text-green-400 border-green-800' :
                      port.state === 'filtered' ? 'bg-yellow-900/50 text-yellow-400 border-yellow-800' :
                      port.state === 'closed' ? 'bg-red-900/50 text-red-400 border-red-800' :
                      'bg-gray-800 text-gray-400 border-gray-700'
                    }`}
                  >
                    {port.state || '—'}
                  </span>
                </td>
                <td class="px-6 py-3 text-sm text-gray-300">{port.service || '—'}</td>
                <td class="px-6 py-3 text-sm text-gray-400 font-mono">{port.version || '—'}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>

    <!-- ============ Section 3 — Vulnérabilités ============ -->
    <div class="glass rounded-xl overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
        <h2 class="text-lg font-semibold">Vulnérabilités ({vulnerabilities.length})</h2>
        <div class="flex gap-2">
          <button
            onclick={handleGrabBanners}
            disabled={grabbingBanners}
            class="px-3 py-1.5 text-sm bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg transition-colors"
          >
            {grabbingBanners ? 'Grab...' : '🖥️ Banners'}
          </button>
          <button
            onclick={handleEnrich}
            disabled={enriching}
            class="px-3 py-1.5 text-sm bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg transition-colors"
          >
            {enriching ? 'Enrichissement...' : '🔍 Enrichir (CVE + MITRE)'}
          </button>
        </div>
      </div>
      {#if enrichResult}
        <div class="px-6 py-2 bg-gray-800/50 border-b border-gray-800 text-xs">
          {#if enrichResult.error}
            <span class="text-red-400">Erreur: {enrichResult.error}</span>
          {:else}
            <span class="text-green-400">
              ✅ MITRE: {enrichResult.mitre?.techniques_new ?? '?'} techniques |
              NVD: {enrichResult.nvd?.vulns_new ?? '?'} CVEs
            </span>
          {/if}
        </div>
      {/if}

      {#if banners.length > 0}
        <div class="px-6 py-3 bg-cyan-500/5 border-b border-cyan-500/10">
          <p class="text-xs text-cyan-400 font-medium mb-2">🖥️ Bannières ({banners.length})</p>
          {#each banners as b}
            <div class="bg-slate-950 rounded p-2 mb-1.5 text-xs">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-cyan-400 font-mono">{b.service_name}</span>
                <span class="text-slate-600">—</span>
                <span class="text-slate-500">{new Date(b.grabbed_at).toLocaleTimeString()}</span>
              </div>
              <pre class="text-green-400/70 font-mono whitespace-pre-wrap break-all">{b.raw_banner?.slice(0, 500)}</pre>
            </div>
          {/each}
        </div>
      {/if}

      {#if vulnerabilities.length === 0}
        <div class="p-12 text-center">
          <p class="text-gray-500">Aucune vulnérabilité détectée</p>
        </div>
      {:else}
        <table class="w-full">
          <thead>
            <tr class="border-b border-gray-800 text-left">
              <th class="px-6 py-3 text-xs text-gray-500 font-medium uppercase">CVE ID</th>
              <th class="px-6 py-3 text-xs text-gray-500 font-medium uppercase">Sévérité</th>
              <th class="px-6 py-3 text-xs text-gray-500 font-medium uppercase">CVSS</th>
              <th class="px-6 py-3 text-xs text-gray-500 font-medium uppercase">Description</th>
            </tr>
          </thead>
          <tbody>
            {#each vulnerabilities as vuln (vuln.id)}
              <tr
                class="border-b border-gray-800/50 hover:bg-gray-800/30 cursor-pointer transition-colors"
                onclick={() => toggleExpand(vuln.cve_id || vuln.id)}
              >
                <td class="px-6 py-3 font-mono text-sm text-cyan-400">{vuln.cve_id || vuln.id}</td>
                <td class="px-6 py-3">
                  <span class="px-2 py-0.5 rounded text-xs font-medium border {severityClass(vuln.severity)}">
                    {vuln.severity || 'NONE'}
                  </span>
                </td>
                <td class="px-6 py-3 font-mono text-sm font-medium {cvssColor(vuln.cvss_score)}">
                  {formatCvss(vuln.cvss_score)}
                </td>
                <td class="px-6 py-3 text-sm text-gray-400 max-w-md">
                  {truncate(vuln.description)}
                </td>
                <td class="px-6 py-3 text-right text-gray-500 text-xs">
                  {expandedVuln === (vuln.cve_id || vuln.id) ? '▲' : '▼'}
                </td>
              </tr>
              {#if expandedVuln === (vuln.cve_id || vuln.id)}
                <tr class="border-b border-gray-800/50 bg-gray-800/20">
                  <td colspan="5" class="px-6 py-4">
                    <p class="text-sm text-gray-300 whitespace-pre-wrap">{vuln.description || '—'}</p>
                    {#if vuln.references && Array.isArray(vuln.references) && vuln.references.length > 0}
                      <div class="mt-3">
                        <p class="text-xs text-gray-500 mb-1">Références :</p>
                        <ul class="space-y-1">
                          {#each vuln.references as ref}
                            <li>
                              <a
                                href={ref}
                                target="_blank"
                                rel="noopener"
                                class="text-xs text-cyan-400 hover:text-cyan-300 underline break-all"
                              >
                                {ref}
                              </a>
                            </li>
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
      {/if}
    </div>
  {/if}
</div>
