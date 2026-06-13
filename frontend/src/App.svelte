<script>
  import { onMount } from 'svelte';
  import { auth } from './lib/stores/auth';
  import Login from './routes/Login.svelte';
  import Dashboard from './routes/Dashboard.svelte';
  import Campaigns from './routes/Campaigns.svelte';
  import CampaignDetail from './routes/CampaignDetail.svelte';
  import Hosts from './routes/Hosts.svelte';
  import HostDetail from './routes/HostDetail.svelte';
  import Vulnerabilities from './routes/Vulnerabilities.svelte';
  import Sqlmap from './routes/Sqlmap.svelte';
  import Nikto from './routes/Nikto.svelte';
  import AdminUsers from './routes/AdminUsers.svelte';
  import MitreAttack from './routes/MitreAttack.svelte';
  import AuditLog from './routes/AuditLog.svelte';

  let route = $state('login');
  let isAuth = $state(false);
  let userRole = $state(null);
  let userEmail = $state(null);
  let campaignId = $state(null);
  let hostId = $state(null);

  onMount(() => {
    auth.init();
    return auth.subscribe((val) => {
      isAuth = val.isAuthenticated;
      userRole = val.user?.role || null;
      userEmail = val.user?.email || null;
      if (val.isAuthenticated && route === 'login') route = 'dashboard';
    });
  });

  function go(r) { route = r; if (r !== 'campaign_detail') campaignId = null; if (r !== 'host_detail') hostId = null; }
  function goCampaign(id) { campaignId = id; route = 'campaign_detail'; }
  function goHost(id) { hostId = id; route = 'host_detail'; }
  function doLogout() { auth.logout(); route = 'login'; }
</script>

{#if isAuth}
  <div class="flex h-screen overflow-hidden">
    <aside class="w-64 flex flex-col border-r border-slate-800/50" style="background: linear-gradient(180deg, #0f172a 0%, #0a0f1e 100%);">
      <div class="p-5 border-b border-slate-800/30">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg flex items-center justify-center" style="background: linear-gradient(135deg, #06b6d4, #3b82f6);">
            <span class="text-white font-bold text-sm">N</span>
          </div>
          <div>
            <h1 class="text-lg font-bold text-gradient">NetInsight</h1>
            <p class="text-[10px] text-slate-500 tracking-wider uppercase">v0.2.0</p>
          </div>
        </div>
      </div>

      <nav class="flex-1 p-3 space-y-1 overflow-y-auto">
        <button onclick={() => go('dashboard')} class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-sm {route === 'dashboard' ? 'text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}" style={route === 'dashboard' ? 'background: linear-gradient(135deg, rgba(6,182,212,0.15), rgba(59,130,246,0.1)); border: 1px solid rgba(6,182,212,0.2);' : ''}><span class="w-2 h-2 rounded-full bg-cyan-400 inline-block"></span><span class="font-medium">Tableau de bord</span></button>
        <button onclick={() => go('campaigns')} class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-sm {route === 'campaigns' || route === 'campaign_detail' ? 'text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}" style={route === 'campaigns' || route === 'campaign_detail' ? 'background: linear-gradient(135deg, rgba(6,182,212,0.15), rgba(59,130,246,0.1)); border: 1px solid rgba(6,182,212,0.2);' : ''}><span class="w-2 h-2 rounded-full bg-emerald-400 inline-block"></span><span class="font-medium">Campagnes</span></button>
        <button onclick={() => go('hosts')} class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-sm {route === 'hosts' || route === 'host_detail' ? 'text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}" style={route === 'hosts' || route === 'host_detail' ? 'background: linear-gradient(135deg, rgba(6,182,212,0.15), rgba(59,130,246,0.1)); border: 1px solid rgba(6,182,212,0.2);' : ''}><span class="w-2 h-2 rounded-full bg-blue-400 inline-block"></span><span class="font-medium">Hôtes</span></button>
        <button onclick={() => go('vulns')} class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-sm {route === 'vulns' ? 'text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}" style={route === 'vulns' ? 'background: linear-gradient(135deg, rgba(6,182,212,0.15), rgba(59,130,246,0.1)); border: 1px solid rgba(6,182,212,0.2);' : ''}><span class="w-2 h-2 rounded-full bg-red-400 inline-block"></span><span class="font-medium">Vulnérabilités</span></button>
        <button onclick={() => go('mitre')} class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-sm {route === 'mitre' ? 'text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}" style={route === 'mitre' ? 'background: linear-gradient(135deg, rgba(239,68,68,0.1), rgba(249,115,22,0.05)); border: 1px solid rgba(239,68,68,0.2);' : ''}><span class="w-2 h-2 rounded-full bg-orange-400 inline-block"></span><span class="font-medium">MITRE ATT&CK</span></button>
        <button onclick={() => go('sqlmap')} class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-sm {route === 'sqlmap' ? 'text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}" style={route === 'sqlmap' ? 'background: linear-gradient(135deg, rgba(168,85,247,0.15), rgba(59,130,246,0.1)); border: 1px solid rgba(168,85,247,0.2);' : ''}><span class="w-2 h-2 rounded-full bg-purple-400 inline-block"></span><span class="font-medium">SQLMap</span></button>
        <button onclick={() => go('nikto')} class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-sm {route === 'nikto' ? 'text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}" style={route === 'nikto' ? 'background: linear-gradient(135deg, rgba(245,158,11,0.15), rgba(217,119,6,0.1)); border: 1px solid rgba(245,158,11,0.2);' : ''}><span class="w-2 h-2 rounded-full bg-amber-400 inline-block"></span><span class="font-medium">Nikto</span></button>
        <button onclick={() => go('history')} class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-sm {route === 'history' ? 'text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}" style={route === 'history' ? 'background: linear-gradient(135deg, rgba(100,116,139,0.1), rgba(71,85,105,0.05)); border: 1px solid rgba(100,116,139,0.2);' : ''}><span class="w-2 h-2 rounded-full bg-slate-400 inline-block"></span><span class="font-medium">Historique</span></button>
      </nav>

      <div class="p-3 border-t border-slate-800/30 space-y-2">
        {#if userEmail}
          <div class="px-3 py-1.5 text-xs">
            <div class="flex items-center gap-2 text-slate-400">
              <span class="w-1.5 h-1.5 rounded-full {userRole === 'admin' ? 'bg-cyan-400' : userRole === 'analyst' ? 'bg-purple-400' : 'bg-slate-400'}"></span>
              <span class="truncate">{userEmail}</span>
            </div>
            <div class="mt-0.5 ml-4">
              <span class="px-1.5 py-0.5 rounded text-[10px] font-medium uppercase {userRole === 'admin' ? 'bg-cyan-500/10 text-cyan-400' : userRole === 'analyst' ? 'bg-purple-500/10 text-purple-400' : 'bg-slate-500/10 text-slate-400'}">
                {userRole}
              </span>
            </div>
          </div>
        {/if}
        {#if userRole === 'admin'}
          <button onclick={() => go('users')} class="w-full flex items-center gap-2 px-3 py-1.5 rounded-lg text-slate-400 hover:text-cyan-400 hover:bg-slate-800/50 transition-all duration-200 text-xs">
            <span class="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
            Gérer les utilisateurs
          </button>
        {/if}
        <button onclick={doLogout} class="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-all duration-200 text-sm">Déconnexion</button>
      </div>
    </aside>

    <main class="flex-1 overflow-y-auto p-6 lg:p-8">
      {#if route === 'dashboard'}<Dashboard onNavigate={go} />
      {:else if route === 'campaigns'}<Campaigns onSelectCampaign={goCampaign} />
      {:else if route === 'campaign_detail'}<CampaignDetail campaignId={campaignId} onBack={() => go('campaigns')} />
      {:else if route === 'hosts'}<Hosts onSelectHost={goHost} />
      {:else if route === 'host_detail'}<HostDetail hostId={hostId} onBack={() => go('hosts')} onSelectCampaign={goCampaign} />
      {:else if route === 'vulns'}<Vulnerabilities />
      {:else if route === 'sqlmap'}<Sqlmap />
      {:else if route === 'nikto'}<Nikto />
      {:else if route === 'mitre'}<MitreAttack />
      {:else if route === 'history'}<AuditLog />
      {:else if route === 'users' && userRole === 'admin'}<AdminUsers />
      {/if}
    </main>
  </div>
{:else}
  <Login />
{/if}
