<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api/client';
  import StatusBadge from '../lib/components/StatusBadge.svelte';
  import LoadingSpinner from '../lib/components/LoadingSpinner.svelte';
  import ErrorBox from '../lib/components/ErrorBox.svelte';

  let { onSelectCampaign } = $props();

  let campaigns = $state([]);
  let loading = $state(true);
  let error = $state('');
  let statusFilter = $state('');
  let showCreateForm = $state(false);
  let creating = $state(false);
  let createError = $state('');
  let newCampaign = $state({ name: '', description: '', targets: '', scan_params: '' });
  let deleting = $state(null);

  onMount(() => {
    fetchCampaigns();
  });

  async function fetchCampaigns() {
    loading = true;
    error = '';
    try {
      campaigns = await api.getCampaigns(statusFilter || null);
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  function handleFilterChange() {
    fetchCampaigns();
  }

  function openCreateForm() {
    newCampaign = { name: '', description: '', targets: '', scan_params: '' };
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
      const targets = newCampaign.targets
        .split(/[\n,]+/)
        .map((t) => t.trim())
        .filter(Boolean);

      if (targets.length === 0) {
        createError = 'Au moins une cible est requise.';
        creating = false;
        return;
      }

      let scanParams = {};
      if (newCampaign.scan_params.trim()) {
        try {
          scanParams = JSON.parse(newCampaign.scan_params);
        } catch {
          createError = 'Le JSON des paramètres de scan est invalide.';
          creating = false;
          return;
        }
      }

      await api.createCampaign({
        name: newCampaign.name,
        description: newCampaign.description,
        targets,
        scan_params: scanParams,
      });

      showCreateForm = false;
      await fetchCampaigns();
    } catch (err) {
      createError = err.message;
    } finally {
      creating = false;
    }
  }

  async function handleDelete(campaignId) {
    if (!confirm('Supprimer définitivement cette campagne ?')) return;

    deleting = campaignId;
    try {
      await api.deleteCampaign(campaignId);
      await fetchCampaigns();
    } catch (err) {
      error = err.message;
    } finally {
      deleting = null;
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
  <!-- Header -->
  <div class="flex items-center justify-between mb-8">
    <h1 class="text-3xl font-bold">Campagnes</h1>
    <button
      onclick={openCreateForm}
      style="background: linear-gradient(135deg, #06b6d4, #3b82f6);"
      class="px-4 py-2 text-white font-medium rounded-lg transition-all"
    >
      + Nouvelle campagne
    </button>
  </div>

  <!-- Filter -->
  <div class="mb-6">
    <select
      bind:value={statusFilter}
      onchange={handleFilterChange}
      class="bg-slate-900/80 border border-slate-700/50 rounded-xl text-white placeholder-slate-600 focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/30 transition-all text-sm px-3 py-2"
    >
      <option value="">Tous les statuts</option>
      <option value="pending">En attente</option>
      <option value="running">En cours</option>
      <option value="completed">Terminée</option>
      <option value="failed">Échouée</option>
    </select>
  </div>

  <!-- Content -->
  {#if loading}
    <LoadingSpinner message="Chargement des campagnes…" />
  {:else if error}
    <ErrorBox message={error} onRetry={fetchCampaigns} />
  {:else if campaigns.length === 0}
    <div class="glass rounded-xl p-12 text-center">
      <p class="text-gray-500 text-lg">Aucune campagne trouvée.</p>
      <button
        onclick={openCreateForm}
        style="background: linear-gradient(135deg, #06b6d4, #3b82f6);"
        class="mt-4 px-4 py-2 text-white font-medium rounded-lg transition-all"
      >
        Créer une campagne
      </button>
    </div>
  {:else}
    <!-- Campaigns table -->
    <div class="glass rounded-xl overflow-hidden">
      <table class="w-full">
        <thead>
          <tr class="border-b border-gray-800 text-left">
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Statut</th>
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Nom</th>
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Cibles</th>
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Hôtes</th>
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Vuln.</th>
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Date</th>
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider"></th>
          </tr>
        </thead>
        <tbody>
          {#each campaigns as campaign (campaign.id)}
            <tr
              class="border-b border-gray-800/50 hover:bg-slate-800/30 cursor-pointer transition-colors"
              onclick={() => onSelectCampaign(campaign.id)}
            >
              <td class="px-4 py-3">
                <StatusBadge status={campaign.status} />
              </td>
              <td class="px-4 py-3">
                <p class="text-gray-200 font-medium">{campaign.name}</p>
                {#if campaign.description}
                  <p class="text-xs text-gray-500 mt-0.5 truncate max-w-xs">{campaign.description}</p>
                {/if}
              </td>
              <td class="px-4 py-3 text-sm text-gray-400">{campaign.target_count ?? '—'}</td>
              <td class="px-4 py-3 text-sm text-gray-400">{campaign.host_count ?? '—'}</td>
              <td class="px-4 py-3 text-sm text-gray-400">{campaign.vuln_count ?? '—'}</td>
              <td class="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">{formatDate(campaign.created_at)}</td>
              <td class="px-4 py-3 text-right">
                <button
                  onclick={(e) => { e.stopPropagation(); handleDelete(campaign.id); }}
                  disabled={deleting === campaign.id}
                  title="Supprimer"
                  class="text-gray-600 hover:text-red-400 disabled:opacity-50 transition-colors p-1"
                >
                  🗑️
                </button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}

  <!-- Create campaign modal -->
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
          <h2 class="text-xl font-semibold">Nouvelle campagne</h2>
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

        <form onsubmit={handleCreate} class="space-y-4">
          <div>
            <label for="cam-name" class="block text-sm text-gray-400 mb-1">
              Nom <span class="text-red-400">*</span>
            </label>
            <input
              id="cam-name"
              type="text"
              bind:value={newCampaign.name}
              required
              placeholder="Ex: Scan réseau interne"
              class="w-full bg-slate-900/80 border border-slate-700/50 rounded-xl text-white placeholder-slate-600 focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/30 transition-all text-sm px-3 py-2"
            />
          </div>

          <div>
            <label for="cam-desc" class="block text-sm text-gray-400 mb-1">Description</label>
            <textarea
              id="cam-desc"
              bind:value={newCampaign.description}
              rows="2"
              placeholder="Description de la campagne…"
              class="w-full bg-slate-900/80 border border-slate-700/50 rounded-xl text-white placeholder-slate-600 focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/30 transition-all text-sm px-3 py-2 resize-none"
            ></textarea>
          </div>

          <div>
            <label for="cam-targets" class="block text-sm text-gray-400 mb-1">
              Cibles <span class="text-red-400">*</span>
            </label>
            <textarea
              id="cam-targets"
              bind:value={newCampaign.targets}
              rows="3"
              required
              placeholder="192.168.1.0/24&#10;10.0.0.1&#10;example.com"
              class="w-full bg-slate-900/80 border border-slate-700/50 rounded-xl text-white placeholder-slate-600 focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/30 transition-all text-sm px-3 py-2 font-mono"
            ></textarea>
            <p class="text-xs text-gray-600 mt-1">Une cible par ligne ou séparées par des virgules (IP, CIDR, nom de domaine)</p>
          </div>

          <div>
            <label for="cam-params" class="block text-sm text-gray-400 mb-1">
              Paramètres de scan <span class="text-gray-600">(JSON optionnel)</span>
            </label>
            <textarea
              id="cam-params"
              bind:value={newCampaign.scan_params}
              rows="3"
              placeholder={JSON.stringify({ports: "1-1000", timing: 4}).replace(/"/g, "'")}
              class="w-full bg-slate-900/80 border border-slate-700/50 rounded-xl text-white placeholder-slate-600 focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/30 transition-all text-sm px-3 py-2 font-mono"
            ></textarea>
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
              style="background: linear-gradient(135deg, #06b6d4, #3b82f6);"
              class="px-4 py-2 text-white font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {creating ? 'Création…' : 'Créer la campagne'}
            </button>
          </div>
        </form>
      </div>
    </div>
  {/if}
</div>
