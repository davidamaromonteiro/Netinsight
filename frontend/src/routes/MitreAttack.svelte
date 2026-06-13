<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api/client';

  let ready = $state(false);
  let tactics = $state([]);
  let techniques = $state([]);
  let mappings = $state([]);
  let stats = $state(null);
  let selectedTactic = $state('');
  let searchQuery = $state('');
  let selected = $state(null);

  onMount(async () => {
    try { tactics = await api.getMitreTactics(); } catch(_) {}
    try { techniques = await api.getMitreTechniques(); } catch(_) {}
    try { mappings = await api.getMitreMappings(); } catch(_) {}
    try { stats = await api.getMitreStats(); } catch(_) {}
    ready = true;
  });

  async function filter() {
    try {
      techniques = await api.getMitreTechniques(selectedTactic || null, searchQuery || null);
    } catch(_) {}
  }

  function count(tid) { return mappings.filter(m => m.technique_id === tid).length; }

  function tc(tactic) {
    const m = {
      'Initial Access': 'border-red-500/30 text-red-400 bg-red-500/10',
      'Execution': 'border-orange-500/30 text-orange-400 bg-orange-500/10',
      'Persistence': 'border-amber-500/30 text-amber-400 bg-amber-500/10',
      'Privilege Escalation': 'border-yellow-500/30 text-yellow-400 bg-yellow-500/10',
      'Credential Access': 'border-pink-500/30 text-pink-400 bg-pink-500/10',
      'Discovery': 'border-blue-500/30 text-blue-400 bg-blue-500/10',
      'Lateral Movement': 'border-cyan-500/30 text-cyan-400 bg-cyan-500/10',
      'Collection': 'border-purple-500/30 text-purple-400 bg-purple-500/10',
      'Command and Control': 'border-indigo-500/30 text-indigo-400 bg-indigo-500/10',
      'Exfiltration': 'border-violet-500/30 text-violet-400 bg-violet-500/10',
      'Impact': 'border-rose-500/30 text-rose-400 bg-rose-500/10',
    };
    return m[tactic] || 'border-slate-500/30 text-slate-400 bg-slate-500/10';
  }
</script>

<div class="max-w-7xl mx-auto">
  <h1 class="text-3xl font-bold mb-2">MITRE ATT&CK</h1>
  <p class="text-sm text-slate-400 mb-8">Base de connaissances des techniques d'attaque</p>

  {#if !ready}
    <div class="text-center py-20"><div class="w-8 h-8 border-2 border-red-400 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div><p class="text-slate-400">Chargement...</p></div>
  {:else}
    {#if stats}
      <div class="grid grid-cols-3 gap-4 mb-6">
        <div class="glass rounded-xl p-4 text-center"><p class="text-2xl font-bold text-red-400">{stats.unique_techniques}</p><p class="text-xs text-slate-500 mt-1">Techniques</p></div>
        <div class="glass rounded-xl p-4 text-center"><p class="text-2xl font-bold text-cyan-400">{stats.unique_tactics}</p><p class="text-xs text-slate-500 mt-1">Tactiques</p></div>
        <div class="glass rounded-xl p-4 text-center"><p class="text-2xl font-bold text-purple-400">{stats.total_mappings}</p><p class="text-xs text-slate-500 mt-1">Correspondances</p></div>
      </div>
    {/if}

    <div class="flex gap-3 mb-6">
      <select bind:value={selectedTactic} onchange={filter} class="bg-slate-900/80 border border-slate-700/50 rounded-xl text-white text-sm px-3 py-2">
        <option value="">Toutes les tactiques</option>
        {#each tactics as t}<option value={t.id}>{t.name}</option>{/each}
      </select>
      <input type="text" bind:value={searchQuery} oninput={filter} placeholder="Rechercher..." class="flex-1 bg-slate-900/80 border border-slate-700/50 rounded-xl text-white placeholder-slate-600 text-sm px-3 py-2" />
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
      {#each techniques as t (t.id)}
        <button onclick={() => selected = t} class="glass rounded-xl p-4 text-left hover:bg-slate-800/30 transition-colors cursor-pointer">
          <div class="flex items-start justify-between mb-2">
            <span class="font-mono text-sm font-bold text-red-400">{t.id}</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-medium border {tc(t.tactic)}">{t.tactic}</span>
          </div>
          <p class="text-sm text-gray-200 font-medium">{t.name}</p>
          {#if count(t.id) > 0}<p class="text-[10px] text-purple-400 mt-1">{count(t.id)} correspondance(s)</p>{/if}
        </button>
      {/each}
    </div>

    {#if techniques.length === 0}
      <div class="glass rounded-xl p-12 text-center mt-4"><p class="text-gray-500">Aucune technique</p></div>
    {/if}

    {#if selected}
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onclick={() => selected = null} onkeydown={e => { if (e.key === 'Escape') selected = null; }}>
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="glass rounded-xl p-6 w-full max-w-lg mx-4 shadow-2xl" onclick={e => e.stopPropagation()} onkeydown={e => e.stopPropagation()}>
          <div class="flex items-center justify-between mb-4"><h2 class="text-xl font-semibold">{selected.id}</h2><button onclick={() => selected = null} class="text-gray-500 hover:text-gray-300 text-xl">x</button></div>
          <div class="space-y-4">
            <p class="text-lg text-gray-200">{selected.name}</p>
            <span class="px-2 py-0.5 rounded text-xs font-medium border {tc(selected.tactic)}">{selected.tactic}</span>
            {#if selected.url}
              <a href={selected.url} target="_blank" rel="noopener" class="block text-xs text-cyan-400 hover:text-cyan-300 underline">Documentation MITRE</a>
            {/if}
            <div><span class="text-xs text-slate-500">Correspondances</span><p class="text-2xl font-bold text-purple-400 mt-1">{count(selected.id)}</p></div>
          </div>
        </div>
      </div>
    {/if}
  {/if}
</div>
