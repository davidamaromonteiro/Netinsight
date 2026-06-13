<script>
  import { onMount, onDestroy } from 'svelte';
  import { api } from '../lib/api/client';

  let { onNavigate } = $props();

  let stats = $state(null);
  let campaigns = $state([]);
  let recentVulns = $state([]);
  let loading = $state(true);
  let error = $state('');

  let severityCanvas = $state(null);
  let campaignCanvas = $state(null);
  let severityChart = null;
  let campaignChart = null;

  const COLORS = ['#ef4444', '#f97316', '#eab308', '#3b82f6', '#6b7280'];
  const GLOW_COLORS = ['rgba(239,68,68,0.4)', 'rgba(249,115,22,0.4)', 'rgba(234,179,8,0.4)', 'rgba(59,130,246,0.4)', 'rgba(107,114,128,0.4)'];

  onMount(async () => {
    try {
      const [s, c, v] = await Promise.all([api.getStats(), api.getCampaigns(), api.getVulnerabilities(null, null)]);
      stats = s; campaigns = c; recentVulns = v.slice(0, 8);
    } catch (err) { error = err.message; }
    finally { loading = false; }

    try {
      const { Chart, registerables } = await import('chart.js');
      Chart.register(...registerables);
      await renderCharts(Chart);
    } catch (e) { console.warn('Chart.js unavailable'); }
  });

  async function renderCharts(Chart) {
    if (severityCanvas && stats?.vulnerabilities_by_severity) {
      if (severityChart) severityChart.destroy();
      const sev = stats.vulnerabilities_by_severity;
      severityChart = new Chart(severityCanvas, {
        type: 'doughnut',
        data: {
          labels: ['Critique', 'Haute', 'Moyenne', 'Basse', 'Aucune'],
          datasets: [{ data: [sev.critical||0, sev.high||0, sev.medium||0, sev.low||0, sev.none||0], backgroundColor: COLORS, borderColor: '#0f172a', borderWidth: 3, hoverBorderColor: '#06b6d4' }]
        },
        options: {
          responsive: true, maintainAspectRatio: false, cutout: '65%',
          plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', padding: 16, font: { size: 11 } } } }
        }
      });
    }
    if (campaignCanvas && campaigns.length > 0) {
      if (campaignChart) campaignChart.destroy();
      const counts = {}; campaigns.forEach(c => { counts[c.status] = (counts[c.status]||0)+1; });
      const statusColors = { pending: '#eab308', running: '#3b82f6', completed: '#22c55e', failed: '#ef4444', cancelled: '#6b7280' };
      campaignChart = new Chart(campaignCanvas, {
        type: 'bar',
        data: {
          labels: Object.keys(counts),
          datasets: [{ data: Object.values(counts), backgroundColor: Object.keys(counts).map(s=>statusColors[s]||'#6b7280'), borderRadius: 6, borderSkipped: false }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { y: { ticks: { color: '#64748b', stepSize: 1 }, grid: { color: 'rgba(71,85,105,0.2)' } }, x: { ticks: { color: '#94a3b8' }, grid: { display: false } } }
        }
      });
    }
  }

  onDestroy(() => { if (severityChart) severityChart.destroy(); if (campaignChart) campaignChart.destroy(); });

  function sevBadge(s) {
    const m = { CRITICAL: 'bg-red-500/10 text-red-400 border-red-500/30', HIGH: 'bg-orange-500/10 text-orange-400 border-orange-500/30', MEDIUM: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30', LOW: 'bg-blue-500/10 text-blue-400 border-blue-500/30' };
    return `px-2 py-0.5 rounded-md text-[11px] font-medium border ${m[s] || 'bg-slate-500/10 text-slate-400 border-slate-500/30'}`;
  }
</script>

<div class="max-w-7xl mx-auto">
  <div class="flex items-center justify-between mb-8">
    <div>
      <h1 class="text-2xl font-bold text-white">Tableau de bord</h1>
      <p class="text-sm text-slate-400 mt-1">Vue d'ensemble de votre surface d'attaque</p>
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-20">
      <div class="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin"></div>
    </div>
  {:else if error}
    <div class="glass rounded-xl p-8 text-center">
      <p class="text-red-400 mb-3">⚠️ {error}</p>
      <button onclick={() => location.reload()} class="px-4 py-2 bg-cyan-500/20 text-cyan-400 rounded-lg hover:bg-cyan-500/30 transition-colors text-sm">Réessayer</button>
    </div>
  {:else if stats}
    <!-- Stats Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <div class="glass rounded-xl p-5 transition-all duration-300 hover:scale-[1.02] bg-gradient-to-br from-cyan-500/10 to-cyan-600/5 border border-cyan-500/20 shadow-cyan-500/10">
        <div class="flex items-start justify-between mb-3"><p class="text-xs text-slate-400 uppercase tracking-wider font-medium">Campagnes</p><span class="text-lg">🎯</span></div>
        <p class="text-3xl font-bold text-cyan-400 tracking-tight">{stats.total_campaigns}</p>
        <p class="text-xs text-slate-500 mt-1">{stats.active_campaigns} actives</p>
      </div>
      <div class="glass rounded-xl p-5 transition-all duration-300 hover:scale-[1.02] bg-gradient-to-br from-blue-500/10 to-blue-600/5 border border-blue-500/20 shadow-blue-500/10">
        <div class="flex items-start justify-between mb-3"><p class="text-xs text-slate-400 uppercase tracking-wider font-medium">Hôtes</p><span class="text-lg">🖥️</span></div>
        <p class="text-3xl font-bold text-blue-400 tracking-tight">{stats.total_hosts}</p>
        <p class="text-xs text-slate-500 mt-1">détectés</p>
      </div>
      <div class="glass rounded-xl p-5 transition-all duration-300 hover:scale-[1.02] bg-gradient-to-br from-amber-500/10 to-amber-600/5 border border-amber-500/20 shadow-amber-500/10">
        <div class="flex items-start justify-between mb-3"><p class="text-xs text-slate-400 uppercase tracking-wider font-medium">Services</p><span class="text-lg">🔌</span></div>
        <p class="text-3xl font-bold text-amber-400 tracking-tight">{stats.total_services}</p>
        <p class="text-xs text-slate-500 mt-1">exposés</p>
      </div>
      <div class="glass rounded-xl p-5 transition-all duration-300 hover:scale-[1.02] bg-gradient-to-br from-red-500/10 to-red-600/5 border border-red-500/20 shadow-red-500/10">
        <div class="flex items-start justify-between mb-3"><p class="text-xs text-slate-400 uppercase tracking-wider font-medium">Vulnérabilités</p><span class="text-lg">🛡️</span></div>
        <p class="text-3xl font-bold text-red-400 tracking-tight">{stats.total_vulnerabilities}</p>
        <p class="text-xs text-slate-500 mt-1">trouvées</p>
      </div>
    </div>

    <!-- Charts -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
      <div class="glass rounded-xl p-6 transition-all duration-300">
        <h3 class="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">Sévérité des vulnérabilités</h3>
        <div style="height: 240px;"><canvas bind:this={severityCanvas}></canvas></div>
      </div>
      <div class="glass rounded-xl p-6 transition-all duration-300">
        <h3 class="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">Statut des campagnes</h3>
        <div style="height: 240px;"><canvas bind:this={campaignCanvas}></canvas></div>
      </div>
    </div>

    <!-- Recent Vulns -->
    {#if recentVulns.length > 0}
      <div class="glass rounded-xl overflow-hidden">
        <div class="px-6 py-4 border-b border-slate-700/30 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-slate-300 uppercase tracking-wider">Dernières vulnérabilités</h3>
          <button onclick={() => onNavigate?.('vulns')} class="text-xs text-cyan-400 hover:text-cyan-300 transition-colors">Voir tout →</button>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead>
              <tr class="border-b border-slate-700/20 text-left">
                <th class="px-6 py-3 text-[11px] text-slate-500 uppercase tracking-wider">CVE</th>
                <th class="px-6 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Sévérité</th>
                <th class="px-6 py-3 text-[11px] text-slate-500 uppercase tracking-wider">CVSS</th>
                <th class="px-6 py-3 text-[11px] text-slate-500 uppercase tracking-wider hidden sm:table-cell">Description</th>
              </tr>
            </thead>
            <tbody>
              {#each recentVulns as vuln}
                <tr class="border-b border-slate-700/10 hover:bg-slate-800/30 transition-colors">
                  <td class="px-6 py-3 font-mono text-sm text-cyan-400">{vuln.cve_id}</td>
                  <td class="px-6 py-3"><span class={sevBadge(vuln.severity)}>{vuln.severity || 'NONE'}</span></td>
                  <td class="px-6 py-3"><span class="text-sm font-mono {vuln.cvss_score >= 9 ? 'text-red-400' : vuln.cvss_score >= 7 ? 'text-orange-400' : 'text-yellow-400'}">{vuln.cvss_score?.toFixed(1) || '—'}</span></td>
                  <td class="px-6 py-3 text-sm text-slate-400 truncate max-w-xs hidden sm:table-cell">{vuln.description?.slice(0, 80) || '—'}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    {/if}
  {/if}
</div>
