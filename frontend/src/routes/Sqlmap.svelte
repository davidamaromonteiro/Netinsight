<script>
  import { onMount, onDestroy } from 'svelte';
  import { api } from '../lib/api/client';
  import StatusBadge from '../lib/components/StatusBadge.svelte';
  import LoadingSpinner from '../lib/components/LoadingSpinner.svelte';
  import ErrorBox from '../lib/components/ErrorBox.svelte';

  let scans = $state([]);
  let loading = $state(true);
  let error = $state('');
  let statusFilter = $state('');
  let showCreateForm = $state(false);
  let creating = $state(false);
  let createError = $state('');
  let newScan = $state({ name: '', description: '', target_url: '', sqlmap_args: '' });
  let deleting = $state(null);
  let selectedScan = $state(null);
  let scanDetail = $state(null);
  let detailLoading = $state(false);
  let pollTimer = null;
  let triggeredScanId = $state(null);

  onMount(() => {
    fetchScans();
    startPolling();
  });

  onDestroy(() => {
    stopPolling();
  });

  function startPolling() {
    stopPolling();
    pollTimer = setInterval(() => {
      if (hasRunningScans() || scanDetail?.status === 'running') {
        fetchScansSilent();
        if (scanDetail?.status === 'running') {
          refreshDetail();
        }
      }
    }, 1500);
  }

  function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  }

  function hasRunningScans() {
    return scans.some(s => s.status === 'running');
  }

  async function fetchScans() {
    loading = true;
    error = '';
    try {
      scans = await api.getSqlmapScans(statusFilter || null);
      startPolling();
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  async function fetchScansSilent() {
    try {
      scans = await api.getSqlmapScans(statusFilter || null);
      startPolling();
    } catch (_) { /* silent */ }
  }

  async function refreshDetail() {
    if (!selectedScan) return;
    try {
      scanDetail = await api.getSqlmapScan(selectedScan.id);
      if (scanDetail.status !== 'running') stopPolling();
    } catch (_) { /* silent */ }
  }

  function handleFilterChange() {
    fetchScans();
  }

  function openCreateForm() {
    newScan = { name: '', description: '', target_url: '', sqlmap_args: '' };
    createError = '';
    showCreateForm = true;
  }

  function closeCreateForm() {
    showCreateForm = false;
    createError = '';
  }

  async function handleCreate(e) {
    e.preventDefault();
    creating = true;
    createError = '';

    try {
      let sqlmapParams = {};
      if (newScan.sqlmap_args.trim()) {
        sqlmapParams = { sqlmap_args: newScan.sqlmap_args.trim() };
      }

      await api.createSqlmapScan({
        name: newScan.name,
        description: newScan.description,
        target_url: newScan.target_url,
        sqlmap_params: sqlmapParams,
      });

      showCreateForm = false;
      await fetchScans();
    } catch (err) {
      createError = err.message;
    } finally {
      creating = false;
    }
  }

  async function handleDelete(scanId) {
    if (!confirm('Supprimer definitivement ce scan sqlmap ?')) return;

    deleting = scanId;
    try {
      await api.deleteSqlmapScan(scanId);
      if (selectedScan?.id === scanId) {
        selectedScan = null;
        scanDetail = null;
      }
      await fetchScans();
    } catch (err) {
      error = err.message;
    } finally {
      deleting = null;
    }
  }

  async function handleSelect(scan) {
    selectedScan = scan;
    detailLoading = true;
    try {
      scanDetail = await api.getSqlmapScan(scan.id);
    } catch (err) {
      scanDetail = { error: err.message };
    } finally {
      detailLoading = false;
    }
  }

  async function handleTriggerScan(scanId) {
    try {
      triggeredScanId = scanId;
      await api.triggerSqlmapScan(scanId);
      await fetchScansSilent();
      startPolling();
      if (selectedScan?.id === scanId) {
        await handleSelect({ id: scanId });
      }
    } catch (err) {
      error = err.message;
    } finally {
      triggeredScanId = null;
    }
  }

  function closeDetail() {
    selectedScan = null;
    scanDetail = null;
  }

  function formatDate(dateStr) {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  }

  function elapsedTime(startedAt) {
    if (!startedAt) return '';
    const start = new Date(startedAt);
    const now = new Date();
    const diff = Math.floor((now - start) / 1000);
    const mins = Math.floor(diff / 60);
    const secs = diff % 60;
    return `${mins}min ${secs}s`;
  }

  function elapsedSeconds(scan) {
    if (!scan.started_at) return 0;
    const start = new Date(scan.started_at);
    const now = scan.completed_at ? new Date(scan.completed_at) : new Date();
    return Math.floor((now - start) / 1000);
  }
</script>

<div class="max-w-6xl mx-auto">
  <!-- Header -->
  <div class="flex items-center justify-between mb-8">
    <h1 class="text-3xl font-bold">SQLMap</h1>
    <button
      onclick={openCreateForm}
      style="background: linear-gradient(135deg, #a855f7, #3b82f6);"
      class="px-4 py-2 text-white font-medium rounded-lg transition-all"
    >
      + Nouveau scan SQLMap
    </button>
  </div>

  <!-- Filter -->
  <div class="mb-6">
    <select
      bind:value={statusFilter}
      onchange={handleFilterChange}
      class="bg-slate-900/80 border border-slate-700/50 rounded-xl text-white placeholder-slate-600 focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/30 transition-all text-sm px-3 py-2"
    >
      <option value="">Tous les statuts</option>
      <option value="pending">En attente</option>
      <option value="running">En cours</option>
      <option value="completed">Termine</option>
      <option value="failed">Echoue</option>
    </select>
  </div>

  <!-- Content -->
  {#if loading}
    <LoadingSpinner message="Chargement des scans SQLMap…" />
  {:else if error}
    <ErrorBox message={error} onRetry={fetchScans} />
  {:else if scans.length === 0}
    <div class="glass rounded-xl p-12 text-center">
      <p class="text-gray-500 text-lg">Aucun scan SQLMap trouve.</p>
      <button
        onclick={openCreateForm}
        style="background: linear-gradient(135deg, #a855f7, #3b82f6);"
        class="mt-4 px-4 py-2 text-white font-medium rounded-lg transition-all"
      >
        Creer un scan SQLMap
      </button>
    </div>
  {:else}
    <!-- Main layout: table + detail panel -->
    <div class="flex gap-6">
      <!-- Scans table -->
      <div class="{selectedScan ? 'w-1/2' : 'w-full'} transition-all">
        <div class="glass rounded-xl overflow-hidden">
          <table class="w-full">
            <thead>
              <tr class="border-b border-gray-800 text-left">
                <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Statut</th>
                <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Nom</th>
                <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">URL cible</th>
                <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Vulns</th>
                <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Date</th>
                <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider"></th>
              </tr>
            </thead>
            <tbody>
              {#each scans as scan (scan.id)}
                {@const selectedClass = selectedScan?.id === scan.id ? 'bg-purple-500/10' : ''}
                <tr
                  class="border-b border-gray-800/50 hover:bg-slate-800/30 cursor-pointer transition-colors {selectedClass}"
                  onclick={() => handleSelect(scan)}
                >
                  <td class="px-4 py-3">
                    <StatusBadge status={scan.status} />
                  </td>
                  <td class="px-4 py-3">
                    <p class="text-gray-200 font-medium">{scan.name}</p>
                    {#if scan.description}
                      <p class="text-xs text-gray-500 mt-0.5 truncate max-w-xs">{scan.description}</p>
                    {/if}
                  </td>
                  <td class="px-4 py-3 text-sm text-gray-400 font-mono truncate max-w-[200px]">{scan.target_url}</td>
                  <td class="px-4 py-3 text-sm">
                    {#if scan.vulnerabilities_found > 0}
                      <span class="text-red-400 font-semibold">{scan.vulnerabilities_found}</span>
                    {:else if scan.status === 'completed'}
                      <span class="text-green-400">0</span>
                    {:else}
                      <span class="text-gray-500">—</span>
                    {/if}
                  </td>
                  <td class="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">{formatDate(scan.created_at)}</td>
                  <td class="px-4 py-3 text-right">
                    {#if scan.status === 'pending' || scan.status === 'failed'}
                      <button
                        onclick={(e) => { e.stopPropagation(); handleTriggerScan(scan.id); }}
                        title="Lancer le scan"
                        class="text-purple-500 hover:text-purple-400 transition-colors p-1 mr-1"
                      >
                        <span class="text-xs font-medium">Démarrer</span>
                      </button>
                    {/if}
                    {#if scan.status === 'completed' || scan.status === 'failed'}
                      <button
                        onclick={(e) => { e.stopPropagation(); handleTriggerScan(scan.id); }}
                        title="Relancer le scan"
                        class="text-cyan-500 hover:text-cyan-400 transition-colors p-1 mr-1"
                      >
                        <span class="text-xs font-medium">Relancer</span>
                      </button>
                    {/if}
                    <button
                      onclick={(e) => { e.stopPropagation(); handleDelete(scan.id); }}
                      disabled={deleting === scan.id}
                      title="Supprimer"
                      class="text-gray-600 hover:text-red-400 disabled:opacity-50 transition-colors p-1"
                    >
                      <span class="text-xs">Suppr</span>
                    </button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Detail panel -->
      {#if selectedScan}
        <div class="w-1/2">
          <div class="glass rounded-xl p-6 sticky top-6 max-h-[calc(100vh-8rem)] overflow-y-auto">
            <div class="flex items-center justify-between mb-4">
              <div class="flex items-center gap-2">
                <h2 class="text-xl font-semibold">{selectedScan.name}</h2>
                {#if selectedScan.status === 'running'}
                  <span class="inline-block w-2 h-2 rounded-full bg-purple-400 animate-pulse"></span>
                {/if}
              </div>
              <button onclick={closeDetail} class="text-gray-500 hover:text-gray-300 text-xl">✕</button>
            </div>

            <!-- Progress bar for running scans -->
            {#if selectedScan.status === 'running'}
              <div class="mb-5">
                <div class="flex items-center justify-between text-xs text-slate-400 mb-2">
                  <span>Scan en cours...</span>
                  <span class="text-purple-400 font-mono">{elapsedTime(selectedScan.started_at)}</span>
                </div>
                <div class="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div class="h-full rounded-full animate-progress" style="background: linear-gradient(90deg, #a855f7, #6366f1, #3b82f6); width: 100%;"></div>
                </div>
              </div>
            {/if}

            {#if detailLoading}
              <LoadingSpinner message="Chargement des details…" />
            {:else if scanDetail?.error}
              <ErrorBox message={scanDetail.error} />
            {:else if scanDetail}
              <div class="space-y-4">
                <!-- Status card -->
                <div class="bg-slate-900/60 rounded-xl p-4">
                  <div class="flex items-center justify-between mb-3">
                    <span class="text-slate-400 text-sm">Statut</span>
                    <StatusBadge status={scanDetail.status} />
                  </div>

                  {#if scanDetail.status === 'running'}
                    <div class="grid grid-cols-3 gap-3 text-center">
                      <div class="bg-slate-950 rounded-lg p-2">
                        <p class="text-[10px] text-slate-500 uppercase">Étape</p>
                        <p class="text-purple-400 font-semibold text-xs mt-0.5">Scanning</p>
                      </div>
                      <div class="bg-slate-950 rounded-lg p-2">
                        <p class="text-[10px] text-slate-500 uppercase">Requêtes</p>
                        <p class="text-cyan-400 font-semibold text-xs mt-0.5 animate-pulse">En cours</p>
                      </div>
                      <div class="bg-slate-950 rounded-lg p-2">
                        <p class="text-[10px] text-slate-500 uppercase">Écoulé</p>
                        <p class="text-purple-300 font-semibold text-xs mt-0.5">{elapsedTime(scanDetail.started_at)}</p>
                      </div>
                    </div>
                    <!-- Progress bar -->
                    <div class="mt-3 w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                      <div class="h-full rounded-full animate-pulse" style="width: 100%; background: linear-gradient(90deg, #7c3aed, #a855f7, #7c3aed); background-size: 200% 100%; animation: shimmer 2s infinite;"></div>
                    </div>
                    <p class="text-center text-[10px] text-slate-600 mt-1 animate-pulse">Scan en cours...</p>
                  {/if}

                  {#if scanDetail.status === 'completed'}
                    <div class="grid grid-cols-3 gap-3 text-center">
                      <div class="bg-slate-950 rounded-lg p-2">
                        <p class="text-[10px] text-slate-500 uppercase">Vulnérabilités</p>
                        <p class="text-xl font-bold mt-0.5 {scanDetail.vulnerabilities_found > 0 ? 'text-red-400' : 'text-green-400'}">
                          {scanDetail.vulnerabilities_found}
                        </p>
                      </div>
                      <div class="bg-slate-950 rounded-lg p-2">
                        <p class="text-[10px] text-slate-500 uppercase">Durée</p>
                        <p class="text-gray-300 font-semibold text-xs mt-0.5">{elapsedTime(scanDetail.started_at)}</p>
                      </div>
                      <div class="bg-slate-950 rounded-lg p-2">
                        <p class="text-[10px] text-slate-500 uppercase">Requêtes</p>
                        <p class="text-gray-300 font-semibold text-xs mt-0.5">~{elapsedSeconds(scanDetail) * 3}</p>
                      </div>
                    </div>
                  {/if}

                  {#if scanDetail.status === 'failed'}
                    <div class="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-sm text-red-400">
                      {scanDetail.result_summary?.error || 'Erreur inconnue'}
                    </div>
                  {/if}
                </div>

                <!-- Target / details grid -->
                <div class="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span class="text-slate-500 text-xs uppercase tracking-wider">URL cible</span>
                    <p class="text-gray-200 font-mono break-all mt-0.5 text-xs">{scanDetail.target_url}</p>
                  </div>
                  <div>
                    <span class="text-slate-500 text-xs uppercase tracking-wider">Arguments</span>
                    <p class="text-purple-300 font-mono break-all mt-0.5 text-xs">{scanDetail.sqlmap_params?.sqlmap_args || '--batch'}</p>
                  </div>
                </div>

                <!-- Timeline -->
                <div class="text-xs space-y-1.5">
                  <div class="flex justify-between">
                    <span class="text-slate-500">Crée</span>
                    <span class="text-gray-400">{formatDate(scanDetail.created_at)}</span>
                  </div>
                  {#if scanDetail.started_at}
                    <div class="flex justify-between">
                      <span class="text-slate-500">Démarré</span>
                      <span class="text-gray-400">{formatDate(scanDetail.started_at)}</span>
                    </div>
                  {/if}
                  {#if scanDetail.completed_at}
                    <div class="flex justify-between">
                      <span class="text-slate-500">Terminé</span>
                      <span class="text-gray-400">{formatDate(scanDetail.completed_at)}</span>
                    </div>
                  {/if}
                </div>

                <!-- Raw output (live during scan, full after completion) -->
                {#if scanDetail.raw_output}
                  <div class="bg-slate-950 rounded-xl p-4 border border-slate-800/50">
                    <div class="flex items-center justify-between mb-2">
                      <span class="text-xs text-slate-500 uppercase tracking-wider">
                        {scanDetail.status === 'running' ? '🔴 Sortie en direct' : '📄 Sortie SQLmap'}
                      </span>
                      {#if scanDetail.status === 'running'}
                        <span class="text-[10px] text-purple-400 animate-pulse">● Live</span>
                      {/if}
                    </div>
                    <pre class="text-[11px] text-green-400 font-mono max-h-64 overflow-y-auto whitespace-pre-wrap break-all leading-relaxed">{scanDetail.raw_output.slice(-4000)}</pre>
                  </div>
                {/if}

                {#if scanDetail.result_summary && scanDetail.status === 'completed'}
                  <!-- DBMS info -->
                  {#if scanDetail.result_summary.detected_dbms}
                    <div class="flex items-center gap-2 text-sm bg-purple-500/10 border border-purple-500/20 rounded-lg px-3 py-2">
                      <span class="text-purple-400 text-xs font-medium">DB:</span>
                      <span class="text-slate-400">Base de données détectée :</span>
                      <span class="text-purple-300 font-semibold">{scanDetail.result_summary.detected_dbms}</span>
                    </div>
                  {/if}

                  <!-- Vulnerability cards -->
                  {#if scanDetail.result_summary.vulnerabilities?.length > 0}
                    <div>
                      <span class="text-slate-500 text-xs uppercase tracking-wider mb-3 block">
                        <span class="inline-block w-2 h-2 rounded-full bg-red-400 mr-1.5"></span>
                        {scanDetail.result_summary.vulnerabilities.length} vulnérabilité{scanDetail.result_summary.vulnerabilities.length > 1 ? 's' : ''} trouvée{scanDetail.result_summary.vulnerabilities.length > 1 ? 's' : ''}
                      </span>
                      {#each scanDetail.result_summary.vulnerabilities as vuln, idx}
                        <div class="bg-slate-900/60 border {vuln.severity === 'CRITICAL' ? 'border-red-500/30' : vuln.severity === 'HIGH' ? 'border-orange-500/30' : 'border-yellow-500/30'} rounded-xl p-4 mb-3">
                          <!-- Header -->
                          <div class="flex items-center justify-between mb-2">
                            <div class="flex items-center gap-2">
                              <span class="text-xs font-mono px-2 py-0.5 rounded {vuln.method === 'GET' ? 'bg-green-500/10 text-green-400' : 'bg-blue-500/10 text-blue-400'}">{vuln.method}</span>
                              <span class="text-sm font-semibold text-gray-200">{vuln.technique}</span>
                            </div>
                            <span class="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase {vuln.severity === 'CRITICAL' ? 'bg-red-500/20 text-red-400' : vuln.severity === 'HIGH' ? 'bg-orange-500/20 text-orange-400' : vuln.severity === 'MEDIUM' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-blue-500/20 text-blue-400'}">{vuln.severity}</span>
                          </div>

                          <!-- Parameter -->
                          <div class="text-xs text-slate-400 mb-2">
                            Paramètre <span class="text-purple-400 font-mono">{vuln.parameter}</span> • {vuln.type}
                          </div>

                          <!-- Impact -->
                          <p class="text-xs text-slate-500 mb-2 leading-relaxed">{vuln.impact}</p>

                          <!-- Payload -->
                          <details class="group">
                            <summary class="text-[10px] text-slate-500 cursor-pointer hover:text-slate-400 transition-colors">Voir le payload</summary>
                            <pre class="mt-1.5 bg-slate-950 rounded-lg p-2 text-[10px] text-purple-300 font-mono overflow-x-auto whitespace-pre-wrap">{vuln.payload}</pre>
                          </details>

                          <!-- Recommendation -->
                          <div class="mt-2 pt-2 border-t border-slate-700/50">
                            <p class="text-[10px] text-slate-300">
                              <span class="text-slate-500">Recommandation :</span>
                              {#if vuln.technique === 'Union query' || vuln.technique === 'UNION query'}
                                Utiliser des requêtes préparées (prepared statements) et valider/stériliser les entrées utilisateur.
                              {:else if vuln.technique.includes('blind')}
                                Limiter l'affichage des erreurs SQL côté client. Utiliser des comptes BDD à privilèges réduits.
                              {:else if vuln.technique === 'Stacked queries'}
                                Désactiver les requêtes multiples (ex: `multiStatements=false`). Utiliser un WAF.
                              {:else}
                                Utiliser des requêtes paramétrées. Ne jamais concaténer les entrées utilisateur dans les requêtes SQL.
                              {/if}
                            </p>
                          </div>

                          <!-- MITRE ATT&CK -->
                          {#if vuln.mitre_attack?.length > 0}
                            <div class="mt-2 pt-2 border-t border-slate-700/50">
                              <details class="group">
                                <summary class="text-[10px] text-slate-500 cursor-pointer hover:text-slate-400">MITRE ATT&CK ({vuln.mitre_attack.length})</summary>
                                <div class="mt-2 space-y-1">
                                  {#each vuln.mitre_attack as m}
                                    <div class="flex items-center gap-2 text-[10px] bg-slate-950 rounded px-2 py-1">
                                      <span class="text-red-400 font-mono font-bold">{m.id}</span>
                                      <span class="text-slate-300">{m.name}</span>
                                      <span class="text-slate-500 ml-auto">{m.tactic}</span>
                                    </div>
                                  {/each}
                                </div>
                              </details>
                            </div>
                          {/if}
                        </div>
                      {/each}
                    </div>

                    <!-- CVEs -->
                    {#if scanDetail.result_summary.related_cves?.length > 0}
                      <div>
                        <span class="text-slate-500 text-xs uppercase tracking-wider mb-3 block">CVE liees ({scanDetail.result_summary.related_cves.length})</span>
                        {#each scanDetail.result_summary.related_cves as cve}
                          <div class="flex items-center gap-3 text-xs bg-slate-900/60 rounded-lg px-3 py-2 mb-1.5">
                            <span class="text-red-400 font-mono font-semibold">{cve.id}</span>
                            <span class="text-yellow-400 font-bold">CVSS {cve.cvss}</span>
                            <span class="text-slate-400 truncate">{cve.desc}</span>
                          </div>
                        {/each}
                      </div>
                    {/if}

                    <!-- Dumped tables -->
                    {#if scanDetail.result_summary.dumped_tables?.length > 0}
                      <div>
                        <span class="text-slate-500 text-xs uppercase tracking-wider mb-3 block">
                          Tables extraites ({scanDetail.result_summary.dumped_tables.length})
                        </span>
                        {#each scanDetail.result_summary.dumped_tables as dtable}
                          <div class="bg-slate-900/60 border border-purple-500/20 rounded-xl p-3 mb-3">
                            <div class="flex items-center justify-between mb-2">
                              <div>
                                <span class="text-purple-400 font-semibold text-sm">{dtable.database}.{dtable.table}</span>
                              </div>
                              <span class="text-[10px] text-slate-500">{dtable.entries} entrées</span>
                            </div>
                            <div class="overflow-x-auto">
                              <table class="w-full text-xs">
                                <thead>
                                  <tr class="border-b border-slate-700/50">
                                    {#each dtable.columns as col}
                                      <th class="px-2 py-1 text-left text-slate-400 font-medium">{col}</th>
                                    {/each}
                                  </tr>
                                </thead>
                                <tbody>
                                  {#each dtable.rows as row}
                                    <tr class="border-b border-slate-700/20 hover:bg-slate-800/30">
                                      {#each row as cell}
                                        <td class="px-2 py-1 text-gray-300 font-mono text-[11px] truncate max-w-[150px]">{cell}</td>
                                      {/each}
                                    </tr>
                                  {/each}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        {/each}
                      </div>
                    {/if}
                  {:else if scanDetail.vulnerabilities_found === 0}
                    <div class="text-center py-4">
                      <p class="text-green-400 text-sm">Aucune vulnerabilite SQL detectee</p>
                      <p class="text-slate-500 text-xs mt-1">Essayez d'augmenter --level ou --risk pour des tests plus approfondis</p>
                    </div>
                  {/if}

                  <!-- Critical warnings -->
                  {#if scanDetail.result_summary.critical_warnings}
                    <div class="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
                      <p class="text-red-400 text-xs">{scanDetail.result_summary.critical_warnings} avertissement(s) critique(s) — voir la sortie brute</p>
                    </div>
                  {/if}
                {/if}

                {#if scanDetail.raw_output}
                  <div>
                    <span class="text-slate-500 text-xs uppercase tracking-wider">Sortie brute</span>
                    <pre class="mt-1 bg-slate-950 rounded-lg p-3 text-xs text-gray-400 font-mono overflow-x-auto max-h-64 overflow-y-auto whitespace-pre-wrap">{scanDetail.raw_output}</pre>
                  </div>
                {/if}

                {#if scanDetail.status === 'pending' || scanDetail.status === 'failed'}
                  <button
                    onclick={() => handleTriggerScan(scanDetail.id)}
                    style="background: linear-gradient(135deg, #a855f7, #3b82f6);"
                    class="w-full px-4 py-2.5 text-white font-medium rounded-xl transition-all hover:opacity-90 disabled:opacity-50"
                    disabled={triggeredScanId === scanDetail.id}
                  >
                    {triggeredScanId === scanDetail.id ? 'Lancement en cours...' : scanDetail.status === 'pending' ? 'Lancer le scan' : 'Relancer le scan'}
                  </button>
                {/if}

                {#if scanDetail.status === 'completed'}
                  <div class="flex gap-2">
                    <button
                      onclick={() => api.downloadSqlmapExport(scanDetail.id, 'json')}
                      class="flex-1 px-3 py-2 text-xs bg-slate-800 text-slate-300 rounded-lg hover:bg-slate-700 transition-colors"
                    >
                      Export JSON
                    </button>
                    <button
                      onclick={() => api.downloadSqlmapExport(scanDetail.id, 'csv')}
                      class="flex-1 px-3 py-2 text-xs bg-slate-800 text-slate-300 rounded-lg hover:bg-slate-700 transition-colors"
                    >
                      Export CSV
                    </button>
                  </div>
                {/if}
              </div>
            {/if}
          </div>
        </div>
      {/if}
    </div>
  {/if}

  <!-- Create modal -->
  {#if showCreateForm}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onclick={closeCreateForm}
      onkeydown={(e) => { if (e.key === 'Escape') closeCreateForm(); }}
    >
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class="glass rounded-xl p-6 w-full max-w-lg mx-4 shadow-2xl"
        onclick={(e) => e.stopPropagation()}
        onkeydown={(e) => e.stopPropagation()}
      >
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-xl font-semibold">Nouveau scan SQLMap</h2>
          <button
            onclick={closeCreateForm}
            class="text-gray-500 hover:text-gray-300 transition-colors text-xl leading-none"
          >
            ✕
          </button>
        </div>

        {#if createError}
          <ErrorBox message={createError} />
          <div class="mt-4"></div>
        {/if}

        <form onsubmit={handleCreate} class="space-y-4" novalidate>
          <div>
            <label for="sqlmap-name" class="block text-sm text-gray-400 mb-1">
              Nom <span class="text-red-400">*</span>
            </label>
            <input
              id="sqlmap-name"
              type="text"
              bind:value={newScan.name}
              required
              placeholder="Ex: Test injection login"
              class="w-full bg-slate-900/80 border border-slate-700/50 rounded-xl text-white placeholder-slate-600 focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/30 transition-all text-sm px-3 py-2"
            />
          </div>

          <div>
            <label for="sqlmap-desc" class="block text-sm text-gray-400 mb-1">Description</label>
            <textarea
              id="sqlmap-desc"
              bind:value={newScan.description}
              rows="2"
              placeholder="Description du scan…"
              class="w-full bg-slate-900/80 border border-slate-700/50 rounded-xl text-white placeholder-slate-600 focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/30 transition-all text-sm px-3 py-2 resize-none"
            ></textarea>
          </div>

          <div>
            <label for="sqlmap-url" class="block text-sm text-gray-400 mb-1">
              URL cible <span class="text-red-400">*</span>
            </label>
            <input
              id="sqlmap-url"
              type="text"
              bind:value={newScan.target_url}
              required
              placeholder="http://acme-store/product.php?id=1"
              class="w-full bg-slate-900/80 border border-slate-700/50 rounded-xl text-white placeholder-slate-600 focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/30 transition-all text-sm px-3 py-2 font-mono"
            />
            <div class="flex gap-2 mt-1.5">
              <button type="button" onclick={() => newScan.target_url = 'http://acme-store/product.php?id=1'} class="text-[10px] px-2 py-0.5 bg-purple-500/10 text-purple-400 rounded hover:bg-purple-500/20 transition-colors">Product (GET)</button>
              <button type="button" onclick={() => newScan.target_url = 'http://acme-store/index.php?category=Widgets'} class="text-[10px] px-2 py-0.5 bg-purple-500/10 text-purple-400 rounded hover:bg-purple-500/20 transition-colors">Category (GET)</button>
              <button type="button" onclick={() => newScan.target_url = 'http://acme-store/login.php'} class="text-[10px] px-2 py-0.5 bg-purple-500/10 text-purple-400 rounded hover:bg-purple-500/20 transition-colors">Login (POST)</button>
            </div>
          </div>

          <div>
            <label for="sqlmap-args" class="block text-sm text-gray-400 mb-1">
              Arguments SQLMap <span class="text-gray-600">(optionnel)</span>
            </label>
            <input
              id="sqlmap-args"
              type="text"
              bind:value={newScan.sqlmap_args}
              placeholder="--batch --level 3 --risk 2 --dbs"
              class="w-full bg-slate-900/80 border border-slate-700/50 rounded-xl text-white placeholder-slate-600 focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/30 transition-all text-sm px-3 py-2 font-mono"
            />
            <div class="flex gap-2 mt-1.5 flex-wrap">
              <button type="button" onclick={() => newScan.sqlmap_args = '--batch --level 2 --risk 1'} class="text-[10px] px-2 py-0.5 bg-slate-800 text-slate-400 rounded hover:bg-slate-700 transition-colors">Rapide</button>
              <button type="button" onclick={() => newScan.sqlmap_args = '--batch --level 3 --risk 2 --dbs'} class="text-[10px] px-2 py-0.5 bg-slate-800 text-slate-400 rounded hover:bg-slate-700 transition-colors">Standard</button>
              <button type="button" onclick={() => newScan.sqlmap_args = '--batch --level 5 --risk 3 --threads 5 --random-agent'} class="text-[10px] px-2 py-0.5 bg-slate-800 text-slate-400 rounded hover:bg-slate-700 transition-colors">Agressif</button>
              <button type="button" onclick={() => newScan.sqlmap_args = '--batch --level 5 --risk 3 --threads 5 --random-agent --tamper space2comment,randomcase --banner --current-db --users --passwords --dbs'} class="text-[10px] px-2 py-0.5 bg-slate-800 text-slate-400 rounded hover:bg-slate-700 transition-colors">Complet</button>
              <button type="button" onclick={() => { newScan.sqlmap_args = '--batch --level 3 --risk 2 --data "username=admin&password=test"'; newScan.target_url = 'http://acme-store/login.php'; }} class="text-[10px] px-2 py-0.5 bg-purple-500/10 text-purple-400 rounded hover:bg-purple-500/20 transition-colors">POST Login</button>
              <button type="button" onclick={() => { newScan.sqlmap_args = '--batch --level 3 --risk 2 --tables'; newScan.target_url = 'http://acme-store/product.php?id=1'; }} class="text-[10px] px-2 py-0.5 bg-purple-500/10 text-purple-400 rounded hover:bg-purple-500/20 transition-colors">Lister tables</button>
              <button type="button" onclick={() => { newScan.sqlmap_args = '--batch --level 3 --risk 2 -T users --dump'; newScan.target_url = 'http://acme-store/product.php?id=1'; }} class="text-[10px] px-2 py-0.5 bg-purple-500/10 text-purple-400 rounded hover:bg-purple-500/20 transition-colors">Dump users</button>
              <button type="button" onclick={() => { newScan.sqlmap_args = '--batch --level 3 --risk 2 -T products --dump'; newScan.target_url = 'http://acme-store/product.php?id=1'; }} class="text-[10px] px-2 py-0.5 bg-purple-500/10 text-purple-400 rounded hover:bg-purple-500/20 transition-colors">Dump products</button>
            </div>
            <p class="text-xs text-gray-600 mt-1">Arguments securises (shell, lecture fichiers, proxy bloques)</p>
          </div>

          <div class="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onclick={closeCreateForm}
              class="px-4 py-2 text-gray-400 hover:text-gray-200 transition-colors"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={creating}
              style="background: linear-gradient(135deg, #a855f7, #3b82f6);"
              class="px-4 py-2 text-white font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {creating ? 'Creation…' : 'Creer le scan'}
            </button>
          </div>
        </form>
      </div>
    </div>
  {/if}
</div>

<style>
  @keyframes progress {
    0% { transform: translateX(-100%); }
    50% { transform: translateX(-20%); }
    100% { transform: translateX(0%); }
  }
  .animate-progress {
    animation: progress 2s ease-in-out infinite;
  }
</style>
