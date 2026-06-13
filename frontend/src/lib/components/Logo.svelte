<script>
  /**
   * NetInsight Logo Component
   * Modes:
   *   - 'full'  : icon + wordmark + tagline (sidebar)
   *   - 'icon'  : just the hexagon shield icon (small spaces)
   *   - 'hero'  : large centré pour page de login
   */
  let { mode = 'full', size = 'md' } = $props();

  const sizeMap = {
    sm: { icon: 28, name: '0.9rem' },
    md: { icon: 36, name: '1rem' },
    lg: { icon: 48, name: '1.15rem' },
    xl: { icon: 64, name: '1.35rem' },
  };
  const s = $derived(sizeMap[size] || sizeMap.md);
  const iconW = $derived(Math.round(s.icon * 140 / 100));
</script>

{#if mode === 'icon'}
  <img src="/logo-icon.svg" alt="NetInsight"
    style="height:{s.icon}px;width:{iconW}px;"
    class="block flex-shrink-0">
{:else if mode === 'hero'}
  <!-- Hero: centré avec halo lumineux -->
  <div class="flex flex-col items-center gap-5">
    <div class="relative flex items-center justify-center">
      <div class="absolute w-24 h-24 rounded-full bg-cyan-500/10 blur-2xl"></div>
      <div class="absolute w-16 h-16 rounded-full bg-blue-500/10 blur-xl"></div>
      <img src="/logo-icon.svg" alt="NetInsight"
        style="height:80px;width:112px;"
        class="block relative z-10 drop-shadow-[0_0_20px_rgba(6,182,212,0.3)]">
    </div>
    <div class="text-center space-y-1.5">
      <h1 class="text-4xl font-bold tracking-tight">
        <span class="text-white">Net</span><span class="text-slate-400 font-light">Insight</span>
      </h1>
      <p class="text-slate-500 text-xs tracking-[0.25em] uppercase font-mono">
        Analyse de sécurité réseau
      </p>
      <div class="flex items-center justify-center gap-3 pt-0.5">
        <span class="h-px w-6 bg-gradient-to-r from-transparent to-slate-700"></span>
        <span class="text-[10px] text-slate-600 font-mono tracking-widest">v0.3.0</span>
        <span class="h-px w-6 bg-gradient-to-l from-transparent to-slate-700"></span>
      </div>
    </div>
  </div>
{:else}
  <!-- Full: icon + wordmark -->
  <div class="flex items-center gap-3">
    <img src="/logo-icon.svg" alt="NetInsight"
      style="height:{s.icon}px;width:{iconW}px;"
      class="block flex-shrink-0">
    <div>
      <div class="flex items-baseline gap-0.5 leading-tight">
        <span class="font-extrabold text-white" style="font-size:{s.name}">Net</span>
        <span class="font-light text-slate-400" style="font-size:{s.name}">Insight</span>
      </div>
      <p class="text-[9px] text-slate-600 tracking-[0.2em] uppercase font-mono mt-0.5">
        Sécurité réseau
      </p>
    </div>
  </div>
{/if}
