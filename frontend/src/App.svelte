<script>
  import { onMount } from 'svelte';
  import { auth } from './lib/stores/auth';
  import Logo from './lib/components/Logo.svelte';
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

  const navItems = [
    { id: 'dashboard',      label: 'Tableau de bord',  color: 'cyan',   icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
    { id: 'campaigns',      label: 'Campagnes',        color: 'emerald', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01' },
    { id: 'hosts',          label: 'Hôtes',            color: 'blue',    icon: 'M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01' },
    { id: 'vulns',          label: 'Vulnérabilités',   color: 'red',     icon: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z' },
    { id: 'mitre',          label: 'MITRE ATT&CK',     color: 'orange',  icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z' },
    { id: 'sqlmap',         label: 'SQLMap',            color: 'purple',  icon: 'M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z' },
    { id: 'nikto',          label: 'Nikto',             color: 'amber',   icon: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z' },
    { id: 'history',        label: 'Historique',        color: 'slate',   icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' },
  ];

  function navColor(id) {
    const found = navItems.find(n => n.id === id);
    return found?.color || 'slate';
  }

  function navColorClass(id) {
    const colors = {
      cyan:    { dot: 'bg-cyan-400',     bg: 'rgba(6,182,212,0.12)',  border: 'rgba(6,182,212,0.2)' },
      emerald: { dot: 'bg-emerald-400',  bg: 'rgba(52,211,153,0.12)', border: 'rgba(52,211,153,0.2)' },
      blue:    { dot: 'bg-blue-400',     bg: 'rgba(96,165,250,0.12)', border: 'rgba(96,165,250,0.2)' },
      red:     { dot: 'bg-red-400',      bg: 'rgba(248,113,113,0.12)', border: 'rgba(248,113,113,0.2)' },
      orange:  { dot: 'bg-orange-400',   bg: 'rgba(251,146,60,0.12)', border: 'rgba(251,146,60,0.2)' },
      purple:  { dot: 'bg-purple-400',   bg: 'rgba(192,132,252,0.12)', border: 'rgba(192,132,252,0.2)' },
      amber:   { dot: 'bg-amber-400',    bg: 'rgba(251,191,36,0.12)', border: 'rgba(251,191,36,0.2)' },
      slate:   { dot: 'bg-slate-400',    bg: 'rgba(148,163,184,0.08)', border: 'rgba(148,163,184,0.15)' },
    };
    return colors[navColor(id)] || colors.slate;
  }

  function isActive(item) {
    if (item.id === 'campaigns') return route === 'campaigns' || route === 'campaign_detail';
    if (item.id === 'hosts') return route === 'hosts' || route === 'host_detail';
    return route === item.id;
  }
</script>

{#if isAuth}
  <div class="flex h-screen overflow-hidden">
    <!-- Sidebar -->
    <aside class="w-64 flex flex-col border-r border-slate-800/50 flex-shrink-0" style="background: linear-gradient(180deg, #0f172a 0%, #0a0f1e 100%);">
      <div class="p-4 border-b border-slate-800/30">
        <Logo mode="full" size="md" />
      </div>

      <nav class="flex-1 p-3 space-y-0.5 overflow-y-auto">
        {#each navItems as item}
          {@const active = isActive(item)}
          {@const c = navColorClass(item.id)}
          <button
            onclick={() => go(item.id)}
            class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-sm"
            class:text-white={active}
            class:text-slate-400={!active}
            class:hover:text-slate-200={!active}
            style={[active ? `background: linear-gradient(135deg, ${c.bg}, transparent); border: 1px solid ${c.border};` : '', !active ? 'background: transparent;' : ''].join('')}
            onmouseenter={(e) => { if (!active) e.currentTarget.style.background = 'rgba(30,41,59,0.5)'; }}
            onmouseleave={(e) => { if (!active) e.currentTarget.style.background = ''; }}
          >
            <!-- Nav icon -->
            <svg class="w-4 h-4 flex-shrink-0" class:text-slate-400={!active} fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"
              style={active ? `color: ${c.dot.replace('bg-', '').replace('-400', '')};` : ''}>
              <path stroke-linecap="round" stroke-linejoin="round" d={item.icon} />
            </svg>
            <span class="font-medium">{item.label}</span>
          </button>
        {/each}
      </nav>

      <!-- User info & admin -->
      <div class="p-3 border-t border-slate-800/30 space-y-1">
        {#if userEmail}
          <div class="px-3 py-2 rounded-lg bg-slate-900/50">
            <div class="flex items-center gap-2 text-xs">
              <span class="w-2 h-2 rounded-full inline-block flex-shrink-0"
                class:bg-cyan-400={userRole === 'admin'}
                class:bg-purple-400={userRole === 'analyst'}
                class:bg-slate-400={userRole !== 'admin' && userRole !== 'analyst'}>
              </span>
              <span class="truncate text-slate-400">{userEmail}</span>
            </div>
            <div class="mt-1 ml-4">
              {#if userRole === 'admin'}
                <span class="px-1.5 py-0.5 rounded text-[10px] font-medium uppercase inline-block bg-cyan-500/10 text-cyan-400">{userRole}</span>
              {:else if userRole === 'analyst'}
                <span class="px-1.5 py-0.5 rounded text-[10px] font-medium uppercase inline-block bg-purple-500/10 text-purple-400">{userRole}</span>
              {:else}
                <span class="px-1.5 py-0.5 rounded text-[10px] font-medium uppercase inline-block bg-slate-500/10 text-slate-400">{userRole}</span>
              {/if}
            </div>
          </div>
        {/if}
        {#if userRole === 'admin'}
          <button onclick={() => go('users')}
            class="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-slate-500 hover:text-cyan-400 hover:bg-slate-800/30 transition-all duration-200 text-xs">
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
            </svg>
            Gérer les utilisateurs
          </button>
        {/if}
        <button onclick={doLogout}
          class="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-500/10 transition-all duration-200 text-sm">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          Déconnexion
        </button>
      </div>
    </aside>

    <!-- Main content -->
    <main class="flex-1 overflow-y-auto p-6 lg:p-8">
      <div class="page-fade" style="animation: fadeIn 0.35s ease-out;">
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
      </div>
    </main>
  </div>
{:else}
  <Login />
{/if}
