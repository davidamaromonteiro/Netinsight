<script>
  let { status } = $props();
  const styles = {
    pending: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
    running: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
    completed: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    failed: 'bg-red-500/10 text-red-400 border-red-500/30',
    cancelled: 'bg-slate-500/10 text-slate-400 border-slate-500/30',
    up: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    down: 'bg-red-500/10 text-red-400 border-red-500/30',
    open: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    filtered: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
    closed: 'bg-red-500/10 text-red-400 border-red-500/30',
  };
</script>
<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium border {styles[status] || styles.pending}">
  <span class="pulse-dot {status === 'up' || status === 'completed' || status === 'open' ? 'up' : status === 'down' || status === 'failed' || status === 'closed' ? 'down' : ''}" style={!['up','down','completed','failed','open','closed'].includes(status) ? 'display:none' : ''}></span>
  {status}
</span>
