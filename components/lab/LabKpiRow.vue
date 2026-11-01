<script setup lang="ts">
const store = useLabStore()

const latencyLabel = computed(() => {
  if (store.latencyMs < 0) return '—'
  return `${store.latencyMs} ms`
})

const latencyClass = computed(() => {
  if (store.latencyMs < 0) return 'text-muted-foreground'
  return store.latencyMs < 1500 ? 'text-emerald-400' : 'text-rose-400'
})

const fpsClass = computed(() =>
  store.fps >= 28 ? 'text-emerald-400' : store.fps > 0 ? 'text-amber-300' : 'text-muted-foreground'
)

const cards = computed(() => [
  { label: 'Flujos', value: String(store.totalFlows), tone: 'text-foreground' },
  { label: 'Credenciales', value: String(store.totalCredentials), tone: store.totalCredentials > 0 ? 'text-rose-400' : 'text-foreground' },
  { label: 'Consultas DNS', value: String(store.totalDns), tone: 'text-amber-300' },
  { label: 'Latencia WS', value: latencyLabel.value, tone: latencyClass.value },
  { label: 'Render', value: store.fps > 0 ? `${store.fps} FPS` : '—', tone: fpsClass.value },
  { label: 'Nodos', value: `${store.graph.nodes.length}/100`, tone: 'text-cyan-300' }
])
</script>

<template>
  <section aria-label="Indicadores del laboratorio" class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
    <div
      v-for="card in cards"
      :key="card.label"
      class="rounded-xl border border-border bg-card/60 px-4 py-3"
    >
      <p class="text-[11px] uppercase tracking-wider text-muted-foreground">{{ card.label }}</p>
      <p class="mt-1 font-mono text-lg font-semibold" :class="card.tone">{{ card.value }}</p>
    </div>
  </section>
</template>
