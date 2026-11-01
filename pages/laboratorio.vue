<script setup lang="ts">
const store = useLabStore()
const socket = useLabSocket()

const selectedNode = computed(
  () => store.graph.nodes.find((node) => node.id === store.selectedNodeId) ?? null
)

const showConnectionAlert = computed(
  () => store.connection === 'error' || store.connection === 'closed' || store.connection === 'idle'
)

const modeBadge = computed(() => {
  if (!store.serverInfo) return null
  return store.serverInfo.mode === 'demo'
    ? { label: 'SIMULACIÓN', classes: 'border-amber-500/40 bg-amber-500/10 text-amber-300' }
    : { label: 'CAPTURA REAL AUTORIZADA', classes: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300' }
})

onMounted(() => {
  socket.connect()
})

onUnmounted(() => {
  socket.disconnect()
})
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h2 class="text-lg font-bold tracking-tight text-foreground">Laboratorio Visual MITM</h2>
        <p class="mt-1 max-w-2xl text-xs leading-relaxed text-muted-foreground">
          Captura pasiva de HTTP y DNS con Scapy, publicada por WebSocket y dibujada a 30 FPS.
          Compara el mismo formulario por HTTP y por HTTPS para ver qué cambia cuando el tráfico
          viaja cifrado.
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <span
          v-if="modeBadge"
          class="rounded border px-2 py-1 font-mono text-[10px] uppercase tracking-wider"
          :class="modeBadge.classes"
        >
          {{ modeBadge.label }}
        </span>
        <button
          type="button"
          class="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          @click="store.togglePause()"
        >
          {{ store.isPaused ? 'Reanudar vista' : 'Pausar vista' }}
        </button>
        <button
          type="button"
          class="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition hover:border-rose-500/40 hover:text-rose-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-400"
          @click="store.clear()"
        >
          Limpiar todo
        </button>
      </div>
    </div>

    <LabWarningBanner />

    <div
      v-if="showConnectionAlert"
      class="flex flex-col gap-2 rounded-xl border border-rose-500/30 bg-rose-500/[0.06] px-4 py-3 text-xs sm:flex-row sm:items-center sm:justify-between"
      role="status"
    >
      <p class="text-rose-200/90">
        <template v-if="store.connection === 'error'">
          La conexión con el laboratorio falló.
          <span v-if="store.lastError" class="text-rose-200/70">({{ store.lastError }})</span>
        </template>
        <template v-else-if="store.connection === 'closed'">
          El WebSocket se cerró. Se reintentará automáticamente.
        </template>
        <template v-else>
          Aún no hay conexión con el backend de captura.
        </template>
      </p>
      <button
        type="button"
        class="shrink-0 rounded border border-rose-500/40 px-2.5 py-1 font-semibold text-rose-200 transition hover:bg-rose-500/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-400"
        @click="socket.connect"
      >
        Reintentar ahora
      </button>
    </div>

    <LabKpiRow />

    <LabEmptyState v-if="!store.hasData" @retry="socket.connect" />

    <div class="grid grid-cols-1 gap-5 xl:grid-cols-12 xl:items-start">
      <section class="rounded-xl border border-border bg-card/60 xl:col-span-8">
        <header class="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
          <div class="flex items-center gap-2">
            <h3 class="text-sm font-semibold text-foreground">Topología observada</h3>
            <span class="font-mono text-[10px] text-muted-foreground">
              {{ store.graph.nodes.length }} nodos · {{ store.graph.edges.length }} aristas
            </span>
          </div>
          <ul class="flex flex-wrap items-center gap-3 text-[10px] text-muted-foreground">
            <li class="flex items-center gap-1.5">
              <span class="h-2 w-2 rounded-full bg-emerald-400" aria-hidden="true" /> local
            </li>
            <li class="flex items-center gap-1.5">
              <span class="h-2 w-2 rounded-full bg-cyan-400" aria-hidden="true" /> gateway
            </li>
            <li class="flex items-center gap-1.5">
              <span class="h-2 w-2 rounded-full bg-amber-400" aria-hidden="true" /> DNS
            </li>
            <li class="flex items-center gap-1.5">
              <span class="h-2 w-2 rounded-full bg-violet-400" aria-hidden="true" /> remoto
            </li>
            <li class="flex items-center gap-1.5">
              <span class="h-2 w-2 rounded-full bg-rose-400" aria-hidden="true" /> credencial
            </li>
          </ul>
        </header>

        <LabGraphCanvas
          :graph="store.graph"
          :selected-node-id="store.selectedNodeId"
          @select-node="store.selectNode"
          @fps="store.setFps"
        />

        <footer class="flex flex-col gap-1 border-t border-border px-4 py-3 text-[11px] text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <p v-if="selectedNode" class="font-mono">
            {{ selectedNode.id }} · rol {{ selectedNode.role }} · grado {{ selectedNode.degree }}
            <span v-if="selectedNode.hasCredential" class="text-rose-300">· credencial vista</span>
          </p>
          <p v-else>Haz clic en un nodo para fijar su detalle.</p>
          <p class="font-mono">{{ store.fps }} FPS · {{ store.latencyMs >= 0 ? `${store.latencyMs} ms` : 'sin latencia' }}</p>
        </footer>
      </section>

      <div class="xl:col-span-4">
        <LabCredentialFeed />
      </div>
    </div>

    <div class="grid grid-cols-1 gap-5 lg:grid-cols-2">
      <LabDnsFeed />
      <LabFlowTable />
    </div>

    <p class="text-[11px] leading-relaxed text-muted-foreground">
      Límite honesto: en redes conmutadas o WPA2 el modo promiscuo no ve tráfico de otros equipos
      sin puerto espejo o un AP de laboratorio. Esta demo usa tráfico propio, loopback o una VM.
      Por HTTPS solo se muestran metadatos: el contenido no se descifra.
    </p>
  </div>
</template>
