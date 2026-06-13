<script>
  import { onMount, onDestroy } from 'svelte';
  import { api } from '../lib/api/client';
  import StatusBadge from '../lib/components/StatusBadge.svelte';
  import LoadingSpinner from '../lib/components/LoadingSpinner.svelte';
  import ErrorBox from '../lib/components/ErrorBox.svelte';

  let scans = $state([]);
  let loading = $state(true);
  let error = $state('');
  let showCreateForm = $state(false);
  let creating = $state(false);
  let createError = $state('');
  let newScan = $state({ name: '', description: '', target_url: '', target_host: '', target_port: 80, use_ssl: false, nikto_params: '{}' });
  let selectedScan = $state(null);
  let scanDetail = $state(null);
  let pollTimer = null;

  onMount(() => { fetchScans(); startPolling(); });
  onDestroy(() => { stopPolling(); });

  function startPolling() {
    stopPolling();
    pollTimer = setInterval(() => {
      if (scans.some(s => s.status === 'running') || scanDetail?.status === 'running') {
        fetchScansSilent();
        if (scanDetail?.status === 'running') refreshDetail();
      }
    }, 2000);
  }
  function stopPolling() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null; } }

  async function fetchScans() { loading = true; error = ''; try { scans = await api.getNiktoScans(); } catch(e) { error = e.message; } finally { loading = false; } }
  async function fetchScansSilent() { try { scans = await api.getNiktoScans(); } catch(_) {} }

  async function handleSelect(scan) {
    selectedScan = scan;
    try { scanDetail = await api.getNiktoScan(scan.id); startPolling(); } catch(_) {}
  }

  async function refreshDetail() {
    if (!selectedScan) return;
    try { scanDetail = await api.getNiktoScan(selectedScan.id); } catch(_) {}
  }

  async function handleTrigger(id) {
    try { await api.triggerNiktoScan(id); startPolling(); await refreshDetail(); } catch(e) { error = e.message; }
  }

  async function handleCreate(e) {
    e.preventDefault(); creating = true; createError = '';
    try {
      await api.createNiktoScan({
        name: newScan.name, description: newScan.description,
        target_url: newScan.target_url, target_host: newScan.target_host,
        target_port: newScan.target_port, use_ssl: newScan.use_ssl,
        nikto_params: JSON.parse(newScan.nikto_params || '{}'),
      });
      showCreateForm = false; await fetchScans();
    } catch(e) { createError = e.message; } finally { creating = false; }
  }

  function formatDate(d) { return d ? new Date(d).toLocaleDateString('fr-FR', { day:'2-digit', month:'2-digit', hour:'2-digit', minute:'2-digit' }) : '—'; }
  function elapsedTime(startedAt) { if (!startedAt) return ''; const diff = Math.floor((Date.now() - new Date(startedAt)) / 1000); if (diff < 60) return diff + 's'; return Math.floor(diff/60) + 'm ' + (diff%60) + 's'; }
</script>

<div class="max-w-6xl mx-auto">
  <div class="flex items-center justify-between mb-8">
    <div>
      <h1 class="text-3xl font-bold">Nikto Scanner</h1>
      <p class="text-sm text-slate-400 mt-1">Scan de vulnérabilités serveurs web</p>
    </div>
    <button onclick={() => showCreateForm = true} style="background: linear-gradient(135deg, #f59e0b, #d97706);" class="px-4 py-2 text-white font-medium rounded-lg">
      + Nouveau scan Nikto
    </button>
  </div>

  {#if loading}
    <LoadingSpinner message="Chargement..." />
  {:else if error}
    <ErrorBox message={error} onRetry={fetchScans} />
  {:else}
    <div class="flex gap-4">
      <!-- Scan list -->
      <div class="flex-1 glass rounded-xl overflow-hidden">
        <table class="w-full">
          <thead><tr class="border-b border-gray-800"><th class="px-4 py-3 text-[11px] text-slate-500 uppercase">Statut</th><th class="px-4 py-3 text-[11px] text-slate-500 uppercase">Nom</th><th class="px-4 py-3 text-[11px] text-slate-500 uppercase">Cible</th><th class="px-4 py-3 text-[11px] text-slate-500 uppercase">Findings</th><th class="px-4 py-3 text-[11px] text-slate-500 uppercase"></th></tr></thead>
          <tbody>
            {#each scans as scan (scan.id)}
              <tr class="border-b border-gray-800/50 hover:bg-slate-800/30 cursor-pointer {selectedScan?.id === scan.id ? 'bg-amber-500/10' : ''}" onclick={() => handleSelect(scan)}>
                <td class="px-4 py-3"><StatusBadge status={scan.status} /></td>
                <td class="px-4 py-3"><p class="text-gray-200 font-medium text-sm">{scan.name}</p></td>
                <td class="px-4 py-3 text-sm text-gray-400 font-mono truncate max-w-[180px]">{scan.target_host}:{scan.target_port}</td>
                <td class="px-4 py-3 text-sm">{scan.vulnerabilities_found > 0 ? scan.vulnerabilities_found : '—'}</td>
                <td class="px-4 py-3 text-right">
                  {#if scan.status === 'pending'}
                    <button onclick={(e) => { e.stopPropagation(); handleTrigger(scan.id); }} class="text-xs px-2 py-1 bg-amber-500/20 text-amber-400 rounded hover:bg-amber-500/30">Démarrer</button>
                  {/if}
                </td>
              </tr>
            {/each}
            {#if scans.length === 0}
              <tr><td colspan="5" class="px-4 py-12 text-center text-gray-500">Aucun scan Nikto. Créez-en un !</td></tr>
            {/if}
          </tbody>
        </table>
      </div>

      <!-- Detail panel -->
      {#if scanDetail}
        <div class="w-96 glass rounded-xl p-4 space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-semibold">{scanDetail.name}</h3>
            <StatusBadge status={scanDetail.status} />
          </div>

          {#if scanDetail.status === 'running'}
            <div class="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
              <div class="h-full rounded-full animate-pulse" style="width:100%; background: linear-gradient(90deg, #f59e0b, #fbbf24, #f59e0b); background-size: 200% 100%;"></div>
            </div>
            <p class="text-center text-[10px] text-amber-400 animate-pulse">{elapsedTime(scanDetail.started_at)}</p>
          {/if}

          <div class="text-xs space-y-1.5">
            <div><span class="text-slate-500">Cible:</span> <span class="text-gray-300 font-mono">{scanDetail.target_url}</span></div>
            <div><span class="text-slate-500">Host:</span> <span class="text-gray-300">{scanDetail.target_host}:{scanDetail.target_port} {scanDetail.use_ssl ? '(SSL)' : ''}</span></div>
          </div>

          {#if scanDetail.status === 'completed' && scanDetail.result_summary}
            {@const s = scanDetail.result_summary}
            <div class="grid grid-cols-3 gap-2 text-center text-xs">
              <div class="bg-red-500/10 rounded-lg p-2"><p class="text-red-400 font-bold">{s.high_findings || 0}</p><p class="text-slate-500">HIGH</p></div>
              <div class="bg-yellow-500/10 rounded-lg p-2"><p class="text-yellow-400 font-bold">{s.medium_findings || 0}</p><p class="text-slate-500">MEDIUM</p></div>
              <div class="bg-blue-500/10 rounded-lg p-2"><p class="text-blue-400 font-bold">{s.low_findings || 0}</p><p class="text-slate-500">LOW</p></div>
            </div>
            {#if s.server}<p class="text-xs text-slate-500">Server: <span class="text-gray-300">{s.server}</span></p>{/if}
            {#if s.vulnerabilities?.length > 0}
              <div class="max-h-48 overflow-y-auto space-y-1">
                {#each s.vulnerabilities as v}
                  <div class="bg-slate-900/60 rounded p-2 text-xs">
                    <span class="px-1 py-0.5 rounded text-[10px] font-medium {v.severity === 'CRITICAL' ? 'bg-red-500/20 text-red-400' : v.severity === 'HIGH' ? 'bg-orange-500/20 text-orange-400' : v.severity === 'MEDIUM' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-blue-500/20 text-blue-400'}">{v.severity}</span>
                    <span class="ml-1 text-gray-400">{v.finding?.slice(0, 100)}</span>
                  </div>
                {/each}
              </div>
            {/if}
          {/if}

          {#if scanDetail.raw_output}
            <div class="bg-slate-950 rounded p-2 max-h-40 overflow-y-auto">
              <pre class="text-[10px] text-green-400 font-mono whitespace-pre-wrap">{scanDetail.raw_output.slice(-2000)}</pre>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  {/if}

  <!-- Create modal -->
  {#if showCreateForm}
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onclick={() => showCreateForm = false} onkeydown={(e) => { if (e.key === 'Escape') showCreateForm = false; }}>
      <div class="glass rounded-xl p-6 w-full max-w-lg mx-4" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.stopPropagation()}>
        <h2 class="text-xl font-semibold mb-4">Nouveau scan Nikto</h2>
        {#if createError}<ErrorBox message={createError} />{/if}
        <form onsubmit={handleCreate} class="space-y-4" novalidate>
          <div><label class="block text-sm text-gray-400">Nom *</label><input type="text" bind:value={newScan.name} required class="w-full bg-slate-900/80 border border-slate-700/50 rounded-xl text-white text-sm px-3 py-2" placeholder="Scan web app prod"></div>
          <div><label class="block text-sm text-gray-400">Host *</label><input type="text" bind:value={newScan.target_host} required class="w-full bg-slate-900/80 border border-slate-700/50 rounded-xl text-white text-sm px-3 py-2 font-mono" placeholder="acme-store"></div>
          <div class="flex gap-3">
            <div class="flex-1"><label class="block text-sm text-gray-400">Port</label><input type="number" bind:value={newScan.target_port} class="w-full bg-slate-900/80 border border-slate-700/50 rounded-xl text-white text-sm px-3 py-2" placeholder="80"></div>
            <div class="flex items-end pb-2"><label class="flex items-center gap-2 text-sm text-gray-400"><input type="checkbox" bind:checked={newScan.use_ssl} class="accent-amber-500"> SSL</label></div>
          </div>
          <div class="flex gap-2">
            <button type="button" onclick={() => { newScan.target_host = 'acme-store'; newScan.target_port = 80; newScan.target_url = 'http://acme-store/'; }} class="text-[10px] px-2 py-0.5 bg-amber-500/10 text-amber-400 rounded">ACME HTTP</button>
            <button type="button" onclick={() => { newScan.target_host = 'localhost'; newScan.target_port = 8080; newScan.target_url = 'http://localhost:8080/'; }} class="text-[10px] px-2 py-0.5 bg-amber-500/10 text-amber-400 rounded">ACME localhost</button>
          </div>
          <div class="flex justify-end gap-3">
            <button type="button" onclick={() => showCreateForm = false} class="px-4 py-2 text-gray-400">Annuler</button>
            <button type="submit" disabled={creating} style="background: linear-gradient(135deg, #f59e0b, #d97706);" class="px-4 py-2 text-white rounded-lg">{creating ? 'Création...' : 'Créer'}</button>
          </div>
        </form>
      </div>
    </div>
  {/if}
</div>
