<script setup lang="ts">
const store = useLabStore()

function shortTime(iso: string): string {
  const parsed = new Date(iso)
  if (Number.isNaN(parsed.getTime())) return '—'
  return parsed.toLocaleTimeString('es-CO', { hour12: false })
}
</script>

<template>
  <section class="rounded-xl border border-border bg-card/60" aria-label="Consultas DNS">
    <header class="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
      <div class="flex items-center gap-2">
        <span class="h-2 w-2 rounded-full bg-amber-400" aria-hidden="true" />
        <h2 class="text-sm font-semibold text-foreground">Consultas DNS sin cifrar</h2>
      </div>
      <span class="font-mono text-[10px] text-muted-foreground">{{ store.totalDns }}</span>
    </header>

    <div class="max-h-[260px] overflow-y-auto">
      <p v-if="store.dnsQueries.length === 0" class="px-4 py-6 text-center text-xs text-muted-foreground">
        Sin consultas DNS. Con DNS sin cifrar, el proveedor ve cada dominio que visitas.
      </p>
      <ul v-else class="divide-y divide-border/70">
        <li
          v-for="query in store.dnsQueries"
          :key="query.id"
          class="flex items-center justify-between gap-3 px-4 py-2 text-xs"
        >
          <div class="flex min-w-0 items-center gap-2">
            <span class="shrink-0 rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 font-mono text-[10px] text-amber-300">
              {{ query.qtype }}
            </span>
            <span class="truncate font-mono text-foreground/90">{{ query.query }}</span>
          </div>
          <div class="flex shrink-0 items-center gap-2 font-mono text-[10px] text-muted-foreground">
            <span>{{ query.sourceIp }}</span>
            <span>{{ shortTime(query.capturedAt) }}</span>
          </div>
        </li>
      </ul>
    </div>
  </section>
</template>
