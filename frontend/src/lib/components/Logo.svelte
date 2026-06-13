<script>
  /**
   * NetInsight Logo Component
   * Modes:
   *   - 'full'  : icon + wordmark + tagline (sidebar)
   *   - 'icon'  : just the hexagon shield icon (small spaces)
   *   - 'hero'  : large centré pour page de login
   *
   * Sizes (for full/icon modes): 'sm', 'md', 'lg', 'xl'
   */
  let { mode = 'full', size = 'md' } = $props();

  const sizeMap = {
    sm: 28,
    md: 36,
    lg: 48,
    xl: 64,
  };
  const iconPx = $derived(sizeMap[size] || sizeMap.md);
</script>

{#if mode === 'icon'}
  <!-- Icon only -->
  <img src="/logo-icon.svg" alt="NetInsight" style="height:{iconPx}px;width:auto;" class="block flex-shrink-0">
{:else if mode === 'hero'}
  <!-- Hero (login) -->
  <div class="flex flex-col items-center gap-4">
    <div class="relative">
      <img src="/logo-icon.svg" alt="NetInsight" style="height:80px;width:auto;" class="block">
    </div>
    <div class="text-center">
      <h1 class="text-4xl font-bold tracking-tight">
        <span class="text-white">Net</span
        ><span class="text-slate-400 font-light">Insight</span>
      </h1>
      <p class="text-slate-500 mt-2 text-xs tracking-[0.25em] uppercase font-mono">
        Analyse de sécurité réseau
      </p>
      <div class="mt-3 flex items-center justify-center gap-2">
        <span class="h-px w-8 bg-slate-800"></span>
        <span class="text-[10px] text-slate-600 font-mono tracking-widest">v0.3.0</span>
        <span class="h-px w-8 bg-slate-800"></span>
      </div>
    </div>
  </div>
{:else}
  <!-- Full: icon + wordmark -->
  <div class="flex items-center gap-3">
    <img src="/logo-icon.svg" alt="NetInsight" style="height:{iconPx}px;width:auto;" class="block flex-shrink-0">
    <div>
      <div class="flex items-baseline gap-0.5 leading-tight">
        <span class="text-lg font-extrabold text-white" style="font-size:{iconPx > 40 ? '1.25rem' : '1rem'}">Net</span>
        <span class="text-slate-400 font-light" style="font-size:{iconPx > 40 ? '1.25rem' : '1rem'}">Insight</span>
      </div>
      {#if size !== 'sm'}
        <p class="text-[9px] text-slate-600 tracking-[0.2em] uppercase font-mono mt-0.5">
          Analyse de sécurité réseau
        </p>
      {/if}
    </div>
  </div>
{/if}
