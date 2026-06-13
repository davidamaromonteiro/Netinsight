<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api/client';
  import LoadingSpinner from '../lib/components/LoadingSpinner.svelte';
  import ErrorBox from '../lib/components/ErrorBox.svelte';

  let users = $state([]);
  let loading = $state(true);
  let error = $state('');
  let roleFilter = $state('');
  let showCreateForm = $state(false);
  let creating = $state(false);
  let createError = $state('');
  let newUser = $state({ email: '', password: '', full_name: '', role: 'analyst' });

  onMount(() => { fetchUsers(); });

  async function fetchUsers() {
    loading = true; error = '';
    try { users = await api.getUsers(roleFilter || null); }
    catch (err) { error = err.message; }
    finally { loading = false; }
  }

  async function handleCreate(e) {
    e.preventDefault(); creating = true; createError = '';
    try {
      await api.createUser(newUser.email, newUser.password, newUser.full_name, newUser.role);
      showCreateForm = false;
      newUser = { email: '', password: '', full_name: '', role: 'analyst' };
      await fetchUsers();
    } catch (err) { createError = err.message; }
    finally { creating = false; }
  }

  async function handleRoleChange(userId, newRole) {
    try { await api.updateUserRole(userId, newRole); await fetchUsers(); }
    catch (err) { error = err.message; }
  }

  async function handleToggleActive(userId) {
    try { await api.toggleUserActive(userId); await fetchUsers(); }
    catch (err) { error = err.message; }
  }

  async function handleDelete(userId, email) {
    if (!confirm(`Supprimer l'utilisateur ${email} ?`)) return;
    try { await api.deleteUser(userId); await fetchUsers(); }
    catch (err) { error = err.message; }
  }

  function formatDate(dateStr) {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  }
</script>

<div class="max-w-6xl mx-auto">
  <div class="flex items-center justify-between mb-8">
    <h1 class="text-3xl font-bold">Utilisateurs</h1>
    <button onclick={() => { showCreateForm = true; }}
      style="background: linear-gradient(135deg, #06b6d4, #3b82f6);"
      class="px-4 py-2 text-white font-medium rounded-lg transition-all">
      + Nouvel utilisateur
    </button>
  </div>

  <div class="mb-6">
    <select bind:value={roleFilter} onchange={fetchUsers}
      class="bg-slate-900/80 border border-slate-700/50 rounded-xl text-white text-sm px-3 py-2">
      <option value="">Tous les roles</option>
      <option value="admin">Admin</option>
      <option value="analyst">Analyst</option>
      <option value="viewer">Viewer</option>
    </select>
  </div>

  {#if loading}
    <LoadingSpinner message="Chargement des utilisateurs..." />
  {:else if error}
    <ErrorBox message={error} onRetry={fetchUsers} />
  {:else if users.length === 0}
    <div class="glass rounded-xl p-12 text-center">
      <p class="text-gray-500">Aucun utilisateur trouve.</p>
    </div>
  {:else}
    <div class="glass rounded-xl overflow-hidden">
      <table class="w-full">
        <thead>
          <tr class="border-b border-gray-800 text-left">
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Email</th>
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Nom</th>
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Role</th>
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Actif</th>
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider">Cree le</th>
            <th class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider"></th>
          </tr>
        </thead>
        <tbody>
          {#each users as user (user.id)}
            <tr class="border-b border-gray-800/50 hover:bg-slate-800/30 transition-colors">
              <td class="px-4 py-3 text-sm text-gray-200 font-mono">{user.email}</td>
              <td class="px-4 py-3 text-sm text-gray-400">{user.full_name || '—'}</td>
              <td class="px-4 py-3">
                <select value={user.role} onchange={(e) => handleRoleChange(user.id, e.target.value)}
                  class="bg-slate-900 border border-slate-700/50 rounded-lg text-xs px-2 py-1
                    {user.role === 'admin' ? 'text-cyan-400' : user.role === 'analyst' ? 'text-purple-400' : 'text-slate-400'}">
                  <option value="admin">Admin</option>
                  <option value="analyst">Analyst</option>
                  <option value="viewer">Viewer</option>
                </select>
              </td>
              <td class="px-4 py-3">
                <button onclick={() => handleToggleActive(user.id)}
                  class="px-2 py-0.5 rounded text-[11px] font-medium transition-colors
                    {user.is_active ? 'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20' : 'bg-red-500/10 text-red-400 hover:bg-red-500/20'}">
                  {user.is_active ? 'Actif' : 'Inactif'}
                </button>
              </td>
              <td class="px-4 py-3 text-xs text-gray-500">{formatDate(user.created_at)}</td>
              <td class="px-4 py-3 text-right">
                <button onclick={() => handleDelete(user.id, user.email)}
                  class="text-gray-600 hover:text-red-400 transition-colors text-xs">Suppr</button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}

  <!-- Create modal -->
  {#if showCreateForm}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onclick={() => showCreateForm = false}
      onkeydown={(e) => { if (e.key === 'Escape') showCreateForm = false; }}>
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="glass rounded-xl p-6 w-full max-w-md mx-4 shadow-2xl"
        onclick={(e) => e.stopPropagation()}
        onkeydown={(e) => e.stopPropagation()}>
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-xl font-semibold">Nouvel utilisateur</h2>
          <button onclick={() => showCreateForm = false} class="text-gray-500 hover:text-gray-300 text-xl">x</button>
        </div>
        {#if createError}<ErrorBox message={createError} /><div class="mt-4"></div>{/if}
        <form onsubmit={handleCreate} class="space-y-4">
          <div>
            <label class="block text-sm text-gray-400 mb-1">Email <span class="text-red-400">*</span></label>
            <input type="email" bind:value={newUser.email} required placeholder="user@example.com"
              class="w-full bg-slate-900/80 border border-slate-700/50 rounded-xl text-white placeholder-slate-600 text-sm px-3 py-2" />
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-1">Mot de passe <span class="text-red-400">*</span></label>
            <input type="password" bind:value={newUser.password} required minlength="8" placeholder="8 caracteres minimum"
              class="w-full bg-slate-900/80 border border-slate-700/50 rounded-xl text-white placeholder-slate-600 text-sm px-3 py-2" />
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-1">Nom complet</label>
            <input type="text" bind:value={newUser.full_name} placeholder="Jean Dupont"
              class="w-full bg-slate-900/80 border border-slate-700/50 rounded-xl text-white placeholder-slate-600 text-sm px-3 py-2" />
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-1">Role</label>
            <select bind:value={newUser.role}
              class="w-full bg-slate-900/80 border border-slate-700/50 rounded-xl text-white text-sm px-3 py-2">
              <option value="admin">Admin — tous les droits</option>
              <option value="analyst">Analyst — creer/lancer des scans</option>
              <option value="viewer">Viewer — lecture seule</option>
            </select>
          </div>
          <div class="flex justify-end gap-3 pt-2">
            <button type="button" onclick={() => showCreateForm = false} class="px-4 py-2 text-gray-400 hover:text-gray-200">Annuler</button>
            <button type="submit" disabled={creating}
              style="background: linear-gradient(135deg, #06b6d4, #3b82f6);"
              class="px-4 py-2 text-white font-medium rounded-lg disabled:opacity-50">
              {creating ? 'Creation...' : 'Creer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  {/if}
</div>
