<script>let { message = 'Chargement...' } = $props();</script>
<div class="flex flex-col items-center justify-center py-16 gap-3 animate-fade-in">
  <div class="w-8 h-8 border-2 border-cyan-400/30 border-t-cyan-400 rounded-full animate-spin"></div>
  <p class="text-sm text-slate-400">{message}</p>
</div>
