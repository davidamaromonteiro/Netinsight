<script>let { message = 'Une erreur est survenue', onRetry = null } = $props();</script>
<div class="glass rounded-xl p-8 text-center animate-fade-in">
  <p class="text-red-400 mb-3">⚠️ {message}</p>
  {#if onRetry}
    <button onclick={onRetry} class="px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200" style="background: rgba(6,182,212,0.15); color: #22d3ee; border: 1px solid rgba(6,182,212,0.2);">
      Réessayer
    </button>
  {/if}
</div>
