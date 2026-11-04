<script setup lang="ts">
import { computed } from 'vue'
import { useLabStore } from '~/stores/lab.store'
import { serviceLabelFor } from '~/utils/labServiceLabels'

const store = useLabStore()

function shortTime(iso: string): string {
  const parsed = new Date(iso)
  if (Number.isNaN(parsed.getTime())) return '—'
  return parsed.toLocaleTimeString('es-CO', { hour12: false })
}

interface GroupedDns {
  key: string
  query: string
  qtype: string
  count: number
  sourceIp: string
  capturedAt: string
}

const grouped = computed<GroupedDns[]>(() => {
  const map = new Map<string, GroupedDns>()
  for (const q of store.dnsQueries) {
    const key = `${q.qtype}|${q.query}`
    const existing = map.get(key)
    if (existing) {
      existing.count += 1
      if (Date.parse(q.capturedAt) > Date.parse(existing.capturedAt)) {
        existing.capturedAt = q.capturedAt
        existing.sourceIp = q.sourceIp
      }
    } else {
      map.set(key, {
        key,
        query: q.query,
        qtype: q.qtype,
        count: 1,
        sourceIp: q.sourceIp,
        capturedAt: q.capturedAt
      })
    }
  }
  return [...map.values()].sort(
    (a, b) => Date.parse(b.capturedAt) - Date.parse(a.capturedAt)
  )
})
</script>

<template>
  <section class="rounded-xl border border-border bg-card/60" aria-label="Consultas DNS">
    <header class="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
      <div class="flex items-center gap-2">
        <span class="h-2 w-2 rounded-full bg-amber-400" aria-hidden="true" />
        <h2 class="text-sm font-semibold text-foreground">Consultas DNS sin cifrar</h2>
      </div>
      <span class="font-mono text-[10px] text-muted-foreground">{{ store.totalDns }} · {{ grouped.length }} únicas</span>
    </header>

    <div class="max-h-[260px] overflow-y-auto">
      <p v-if="store.dnsQueries.length === 0" class="px-4 py-6 text-center text-xs text-muted-foreground">
        Sin consultas DNS. Con DNS sin cifrar, el proveedor ve cada dominio que visitas.
      </p>
      <ul v-else class="divide-y divide-border/70">
        <li
          v-for="g in grouped"
          :key="g.key"
          class="flex items-center justify-between gap-3 px-4 py-2 text-xs"
        >
          <div class="flex min-w-0 items-center gap-2">
            <span class="shrink-0 rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 font-mono text-[10px] text-amber-300">
              {{ g.qtype }}
            </span>
            <span class="truncate font-mono text-foreground/90">{{ g.query }}</span>
            <span
              v-if="serviceLabelFor(g.query)"
              class="shrink-0 rounded border px-1.5 py-0.5 font-mono text-[10px]"
              :class="serviceLabelFor(g.query)!.tone"
            >
              {{ serviceLabelFor(g.query)!.label }}
            </span>
          </div>
          <div class="flex shrink-0 items-center gap-2 font-mono text-[10px] text-muted-foreground">
            <span v-if="g.count > 1" class="rounded bg-muted px-1.5 py-0.5 text-foreground/80">×{{ g.count }}</span>
            <span>{{ g.sourceIp }}</span>
            <span>{{ shortTime(g.capturedAt) }}</span>
          </div>
        </li>
      </ul>
    </div>
  </section>
</template>
