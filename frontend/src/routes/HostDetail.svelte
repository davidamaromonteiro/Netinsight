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
    return new Date(dateStr).toLocaleDateString('fr-FR', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' });
  }

  function truncate(text, maxLen = 120) {
    if (!text) return '—';
    return text.length > maxLen ? text.slice(0, maxLen) + '…' : text;
  }

  function severityClass(severity) {
    const map = {
      CRITICAL: 'badge-critical',
      HIGH: 'badge-high',
      MEDIUM: 'badge-medium',
      LOW: 'badge-low',
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

  function toggleExpand(cveId) {
    expandedVuln = expandedVuln === cveId ? null : cveId;
  }
</script>

<div class="max-w-6xl mx-auto page-fade">
  <!-- Back button -->
  <button onclick={onBack}
    class="mb-4 px-3 py-1.5 text-sm text-slate-400 hover:text-slate-200 bg-slate-800/80 hover:bg-slate-700/80 rounded-lg transition-all duration-200 flex items-center gap-1.5 w-fit">
    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/></svg>
    Retour aux hôtes
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
          <h1 class="text-2xl font-bold text-slate-100 font-mono">{host.ip || '—'}</h1>
          {#if host.hostname}
            <p class="text-slate-400 mt-0.5 text-sm">{host.hostname}</p>
          {/if}
        </div>
        <span class="badge {host.status === 'up' ? 'badge-up' : host.status === 'down' ? 'badge-down' : 'badge-none'}">
          {host.status || 'inconnu'}
        </span>
      </div>

      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 text-sm">
        <div>
          <p class="text-slate-500 text-xs uppercase tracking-wider">MAC</p>
          <p class="text-slate-300 font-mono">{host.mac || '—'}</p>
        </div>
        <div>
          <p class="text-slate-500 text-xs uppercase tracking-wider">OS</p>
          <p class="text-slate-300">{host.os || '—'}</p>
        </div>
        <div>
          <p class="text-slate-500 text-xs uppercase tracking-wider">Précision OS</p>
          <p class="text-slate-300">{host.os_accuracy != null ? host.os_accuracy + '%' : '—'}</p>
        </div>
        <div>
          <p class="text-slate-500 text-xs uppercase tracking-wider">Première vue</p>
          <p class="text-slate-300">{formatDate(host.first_seen)}</p>
        </div>
        <div>
          <p class="text-slate-500 text-xs uppercase tracking-wider">Dernière vue</p>
          <p class="text-slate-300">{formatDate(host.last_seen)}</p>
        </div>
        {#if host.campaign_id}
          <div>
            <p class="text-slate-500 text-xs uppercase tracking-wider">Campagne</p>
            {#if onSelectCampaign}
              <button onclick={() => onSelectCampaign(host.campaign_id)}
                class="text-cyan-400 hover:text-cyan-300 underline text-sm transition-colors">
                Voir la campagne →
              </button>
            {:else}
              <p class="text-slate-300">ID: {host.campaign_id}</p>
            {/if}
          </div>
        {/if}
      </div>
    </div>

    <!-- Ports et services -->
    <div class="glass rounded-xl overflow-hidden mb-6">
      <div class="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
        <h2 class="text-base font-semibold text-slate-200">Ports et services <span class="text-slate-500 font-normal">({ports.length})</span></h2>
      </div>
      {#if ports.length === 0}
        <div class="p-12 text-center"><p class="text-slate-500">Aucun port détecté</p></div>
      {:else}
        <table class="table-cyber">
          <thead><tr><th>Port</th><th>Protocole</th><th>État</th><th>Service</th><th>Version</th></tr></thead>
          <tbody>
            {#each ports as port (port.id)}
              <tr class="border-b border-slate-800/50">
                <td class="font-mono text-sm text-cyan-400">{port.port}</td>
                <td class="text-sm text-slate-400 uppercase">{port.protocol || '—'}</td>
                <td>
                  <span class="badge {port.state === 'open' ? 'badge-up' : port.state === 'filtered' ? 'badge-medium' : port.state === 'closed' ? 'badge-down' : 'badge-none'}">
                    {port.state || '—'}
                  </span>
                </td>
                <td class="text-sm text-slate-300">{port.service || '—'}</td>
                <td class="text-sm text-slate-400 font-mono">{port.version || '—'}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>

    <!-- Vulnérabilités -->
    <div class="glass rounded-xl overflow-hidden">
      <div class="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
        <h2 class="text-base font-semibold text-slate-200">Vulnérabilités <span class="text-slate-500 font-normal">({vulnerabilities.length})</span></h2>
        <div class="flex gap-2">
          <button onclick={handleGrabBanners} disabled={grabbingBanners}
            class="btn-cyber text-xs px-3 py-1.5 rounded-lg">
            {grabbingBanners ? 'Grab...' : '🖥️ Banners'}
          </button>
          <button onclick={handleEnrich} disabled={enriching}
            class="btn-cyber purple text-xs px-3 py-1.5 rounded-lg">
            {enriching ? 'Enrichissement...' : '🔍 Enrichir (CVE + MITRE)'}
          </button>
        </div>
      </div>
      {#if enrichResult}
        <div class="px-6 py-2 bg-slate-800/50 border-b border-slate-800 text-xs">
          {#if enrichResult.error}
            <span class="text-red-400">Erreur: {enrichResult.error}</span>
          {:else}
            <span class="text-green-400">✅ MITRE: {enrichResult.mitre?.techniques_new ?? '?'} techniques | NVD: {enrichResult.nvd?.vulns_new ?? '?'} CVEs</span>
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
        <div class="p-12 text-center"><p class="text-slate-500">Aucune vulnérabilité détectée</p></div>
      {:else}
        <table class="table-cyber">
          <thead><tr><th>CVE ID</th><th>Sévérité</th><th>CVSS</th><th>Description</th><th class="w-8"></th></tr></thead>
          <tbody>
            {#each vulnerabilities as vuln (vuln.id)}
              <tr class="border-b border-slate-800/50 hover:bg-slate-800/30 cursor-pointer transition-colors"
                onclick={() => toggleExpand(vuln.cve_id || vuln.id)}>
                <td class="font-mono text-sm text-cyan-400">{vuln.cve_id || vuln.id}</td>
                <td><span class="badge {severityClass(vuln.severity)}">{vuln.severity || 'NONE'}</span></td>
                <td class="font-mono text-sm font-medium {cvssColor(vuln.cvss_score)}">{formatCvss(vuln.cvss_score)}</td>
                <td class="text-sm text-slate-400 max-w-md">{truncate(vuln.description)}</td>
                <td class="text-right text-slate-500 text-xs">{expandedVuln === (vuln.cve_id || vuln.id) ? '▲' : '▼'}</td>
              </tr>
              {#if expandedVuln === (vuln.cve_id || vuln.id)}
                <tr class="border-b border-slate-800/50 bg-slate-800/20">
                  <td colspan="5" class="px-6 py-4">
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
      {/if}
    </div>
  {/if}
</div>
