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
    <div>
      <h1 class="text-2xl font-bold text-slate-100">Campagnes</h1>
      <p class="text-sm text-slate-400 mt-1">Gérez vos campagnes de scan réseau</p>
    </div>
    <button onclick={openCreateForm} class="btn-cyber text-sm flex items-center gap-1.5">
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
      </svg>
      Nouvelle campagne
    </button>
  </div>

  <!-- Filter -->
  <div class="mb-6">
    <select bind:value={statusFilter} onchange={handleFilterChange} class="select-cyber">
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
      <p class="text-slate-500 text-lg">Aucune campagne trouvée.</p>
      <button onclick={openCreateForm} class="btn-cyber text-sm mt-4 inline-block">
        Créer une campagne
      </button>
    </div>
  {:else}
    <div class="glass rounded-xl overflow-hidden">
      <table class="table-cyber">
        <thead>
          <tr>
            <th>Statut</th>
            <th>Nom</th>
            <th>Cibles</th>
            <th>Hôtes</th>
            <th>Vuln.</th>
            <th>Date</th>
            <th class="w-12"></th>
          </tr>
        </thead>
        <tbody>
          {#each campaigns as campaign (campaign.id)}
            <tr class="border-b border-slate-800/50 hover:bg-slate-800/30 cursor-pointer transition-colors"
              onclick={() => onSelectCampaign(campaign.id)}>
              <td><StatusBadge status={campaign.status} /></td>
              <td>
                <p class="text-slate-200 font-medium">{campaign.name}</p>
                {#if campaign.description}
                  <p class="text-xs text-slate-500 mt-0.5 truncate max-w-xs">{campaign.description}</p>
                {/if}
              </td>
              <td class="text-sm text-slate-400">{campaign.target_count ?? '—'}</td>
              <td class="text-sm text-slate-400">{campaign.host_count ?? '—'}</td>
              <td class="text-sm text-slate-400">{campaign.vuln_count ?? '—'}</td>
              <td class="text-sm text-slate-500 whitespace-nowrap">{formatDate(campaign.created_at)}</td>
              <td class="text-right">
                <button onclick={(e) => { e.stopPropagation(); handleDelete(campaign.id); }}
                  disabled={deleting === campaign.id}
                  class="text-slate-600 hover:text-red-400 disabled:opacity-50 transition-colors p-1"
                  title="Supprimer">
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                  </svg>
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
    <div class="modal-backdrop" onclick={closeCreateForm} onkeydown={(e) => { if (e.key === 'Escape') closeCreateForm(); }}>
      <div class="glass rounded-xl p-6 w-full max-w-lg mx-4 shadow-2xl animate-fade-in"
        onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.stopPropagation()}>
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-xl font-semibold text-slate-100">Nouvelle campagne</h2>
          <button onclick={closeCreateForm}
            class="text-slate-500 hover:text-slate-300 transition-colors text-xl leading-none">✕</button>
        </div>

        {#if createError}
          <ErrorBox message={createError} />
          <div class="mt-4"></div>
        {/if}

        <form onsubmit={handleCreate} class="space-y-4">
          <div>
            <label for="cam-name" class="block text-xs text-slate-400 mb-1.5 uppercase tracking-wider font-medium">
              Nom <span class="text-red-400">*</span>
            </label>
            <input id="cam-name" type="text" bind:value={newCampaign.name} required
              placeholder="Ex: Scan réseau interne" class="input-cyber" />
          </div>

          <div>
            <label for="cam-desc" class="block text-xs text-slate-400 mb-1.5 uppercase tracking-wider font-medium">Description</label>
            <textarea id="cam-desc" bind:value={newCampaign.description} rows="2"
              placeholder="Description de la campagne…" class="input-cyber resize-none"></textarea>
          </div>

          <div>
            <label for="cam-targets" class="block text-xs text-slate-400 mb-1.5 uppercase tracking-wider font-medium">
              Cibles <span class="text-red-400">*</span>
            </label>
            <textarea id="cam-targets" bind:value={newCampaign.targets} rows="3" required
              placeholder="192.168.1.0/24&#10;10.0.0.1&#10;example.com"
              class="input-cyber resize-none font-mono"></textarea>
            <p class="text-xs text-slate-600 mt-1">Une cible par ligne ou séparées par des virgules</p>
          </div>

          <div>
            <label for="cam-params" class="block text-xs text-slate-400 mb-1.5 uppercase tracking-wider font-medium">
              Paramètres de scan <span class="text-slate-500 font-normal">(JSON optionnel)</span>
            </label>
            <textarea id="cam-params" bind:value={newCampaign.scan_params} rows="3"
              placeholder={JSON.stringify({ports: "1-1000", timing: 4}).replace(/"/g, "'")}
              class="input-cyber resize-none font-mono"></textarea>
          </div>

          <div class="flex justify-end gap-3 pt-2">
            <button type="button" onclick={closeCreateForm}
              class="px-4 py-2 text-slate-400 hover:text-slate-200 transition-colors text-sm">Annuler</button>
            <button type="submit" disabled={creating} class="btn-cyber text-sm">
              {creating ? 'Création…' : 'Créer la campagne'}
            </button>
          </div>
        </form>
      </div>
    </div>
  {/if}
</div>
