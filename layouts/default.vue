<script setup lang="ts">
const store = useSentinelStore()
const labStore = useLabStore()
const route = useRoute()

const isLab = computed(() => route.path.startsWith('/laboratorio'))

const tabs = [
  { label: 'Defensa', to: '/', description: 'IDS ARP y postura TLS' },
  { label: 'Laboratorio', to: '/laboratorio', description: 'Visual MITM con Scapy' }
]

const postureBadge = computed(() => {
  const collisions = store.metrics?.activeCollisions ?? 0
  if (collisions > 0 || store.metrics?.overallPosture === 'CRITICAL_ALERT') {
    return {
      label: 'ALERTA CRÍTICA MITM / ARP',
      classes: 'border-rose-500/40 bg-rose-500/10 text-rose-400',
      dot: 'bg-rose-400'
    }
  }
  return {
    label: 'ESCUDO ACTIVO · KERNEL EN VIVO',
    classes: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400',
    dot: 'bg-emerald-400'
  }
})

const labBadge = computed(() => {
  switch (labStore.connection) {
    case 'open':
      return {
        label: labStore.isSynthetic ? 'LAB CONECTADO · SIMULACIÓN' : 'LAB CONECTADO',
        classes: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400',
        dot: 'bg-emerald-400'
      }
    case 'connecting':
      return {
        label: 'CONECTANDO AL LAB',
        classes: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300',
        dot: 'bg-cyan-400'
      }
    case 'error':
      return {
        label: 'LAB CON ERROR',
        classes: 'border-rose-500/40 bg-rose-500/10 text-rose-400',
        dot: 'bg-rose-400'
      }
    default:
      return {
        label: 'LAB DESCONECTADO',
        classes: 'border-border bg-muted text-muted-foreground',
        dot: 'bg-slate-500'
      }
  }
})

const activeBadge = computed(() => (isLab.value ? labBadge.value : postureBadge.value))

const subtitle = computed(() =>
  isLab.value
    ? 'Laboratorio Visual MITM — captura pasiva HTTP/DNS con Scapy y WebSocket'
    : 'Defensa contra Hombre en el Medio (ARP) y Auditoría de Cifrado en Tiempo Real'
)
</script>

<template>
  <div class="min-h-screen bg-background text-foreground flex flex-col">
    <header class="sticky top-0 z-30 border-b border-border bg-background/85 backdrop-blur-md">
      <div class="mx-auto w-full max-w-[1860px] px-[clamp(1.25rem,3vw,3rem)] h-16 flex items-center justify-between gap-4">
        <div class="flex items-center gap-3 min-w-0">
          <div class="h-10 w-10 rounded-lg border border-primary/30 bg-primary/10 flex items-center justify-center text-primary shrink-0">
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 3l7 3v6c0 5-3.5 8.5-7 9-3.5-.5-7-4-7-9V6l7-3z" />
              <circle cx="12" cy="12" r="2.5" />
              <path stroke-linecap="round" d="M12 7v2.5M12 14.5V17M7 12h2.5M14.5 12H17" />
            </svg>
          </div>
          <div class="min-w-0">
            <div class="flex items-center gap-2.5 flex-wrap">
              <h1 class="text-base font-bold tracking-tight text-foreground">
                NetSentinel IDS
              </h1>
              <span
                v-if="isLab"
                class="inline-flex items-center rounded border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-amber-300 whitespace-nowrap"
              >
                Solo laboratorio
              </span>
              <span
                v-else
                class="hidden sm:inline-flex items-center rounded border border-border bg-muted px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground whitespace-nowrap"
              >
                Radar de red en vivo
              </span>
            </div>
            <p class="text-xs text-muted-foreground line-clamp-1">{{ subtitle }}</p>
          </div>
        </div>

        <div class="flex items-center gap-3 shrink-0">
          <div
            class="inline-flex items-center gap-2 rounded-full border px-3.5 py-1 text-xs font-semibold tracking-wide whitespace-nowrap"
            :class="activeBadge.classes"
          >
            <span class="h-2 w-2 rounded-full animate-pulse shrink-0" :class="activeBadge.dot" />
            <span>{{ activeBadge.label }}</span>
          </div>
        </div>
      </div>

      <nav
        class="mx-auto w-full max-w-[1860px] px-[clamp(1.25rem,3vw,3rem)] flex gap-1 border-t border-border/60"
        aria-label="Secciones de NetSentinel"
      >
        <NuxtLink
          v-for="tab in tabs"
          :key="tab.to"
          :to="tab.to"
          class="relative -mb-px border-b-2 px-3 py-2.5 text-xs font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          :class="
            (isLab ? tab.to === '/laboratorio' : tab.to === '/')
              ? 'border-primary text-foreground'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          "
          :aria-current="(isLab ? tab.to === '/laboratorio' : tab.to === '/') ? 'page' : undefined"
        >
          {{ tab.label }}
          <span class="ml-1.5 hidden font-normal text-[10px] text-muted-foreground sm:inline">
            {{ tab.description }}
          </span>
        </NuxtLink>
      </nav>
    </header>

    <main class="flex-1 mx-auto w-full max-w-[1860px] px-[clamp(1.25rem,3vw,3rem)] py-6">
      <slot />
    </main>

    <footer class="border-t border-border bg-card/40 py-4">
      <div class="mx-auto w-full max-w-[1860px] px-[clamp(1.25rem,3vw,3rem)] flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-muted-foreground">
        <span v-if="isLab">
          Captura pasiva de laboratorio · Sin inyección de paquetes · Credenciales solo en memoria
        </span>
        <span v-else>
          Telemetría Pasiva del Kernel Linux · Cero Inyección de Paquetes
        </span>
        <span class="font-mono">
          {{ isLab ? 'ws://127.0.0.1:8765' : (store.interfaceSource || '/proc/net/arp + /proc/net/tcp') }}
        </span>
      </div>
    </footer>
  </div>
</template>
