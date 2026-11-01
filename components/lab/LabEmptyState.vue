<script setup lang="ts">
const store = useLabStore()
const copied = ref<string | null>(null)

const emit = defineEmits<{ retry: [] }>()

const isDemo = computed(() => store.serverInfo?.mode === 'demo')

const commands = computed(() => [
  {
    id: 'demo',
    title: '1. Validar la interfaz sin tocar la red',
    code: 'cd capture && uv run python -m lab_capture.main --demo --nodes 100 --rate 30'
  },
  {
    id: 'live',
    title: '2. Captura real en tu laboratorio (requiere autorización)',
    code: 'cd capture && uv run python -m lab_capture.main --iface "<interfaz>" --i-have-authorization'
  }
])

async function copy(id: string, code: string) {
  try {
    await navigator.clipboard.writeText(code)
    copied.value = id
    setTimeout(() => {
      if (copied.value === id) copied.value = null
    }, 1800)
  } catch {
    copied.value = null
  }
}
</script>

<template>
  <section class="rounded-xl border border-dashed border-border bg-card/40 px-5 py-6">
    <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div class="max-w-xl space-y-1">
        <h2 class="text-sm font-semibold text-foreground">El laboratorio está escuchando, pero no hay eventos</h2>
        <p class="text-xs leading-relaxed text-muted-foreground">
          <template v-if="store.connection === 'open'">
            La conexión WebSocket está abierta. Inicia el backend de captura para ver tráfico.
          </template>
          <template v-else-if="store.connection === 'connecting'">
            Conectando al WebSocket del laboratorio…
          </template>
          <template v-else>
            Abre el backend en una terminal y vuelve a intentar la conexión. Sin backend, esta
            vista no recibe eventos.
          </template>
        </p>
        <p v-if="isDemo" class="text-xs text-amber-300">
          Modo SIMULACIÓN activo: los eventos son sintéticos.
        </p>
      </div>

      <button
        type="button"
        class="inline-flex shrink-0 items-center gap-2 rounded-lg border border-primary/40 bg-primary/10 px-3 py-2 text-xs font-semibold text-primary transition hover:bg-primary/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        @click="emit('retry')"
      >
        Reintentar conexión
      </button>
    </div>

    <ol class="mt-5 grid gap-3 lg:grid-cols-2">
      <li v-for="command in commands" :key="command.id" class="rounded-lg border border-border bg-background/60 p-3">
        <p class="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">{{ command.title }}</p>
        <div class="mt-2 flex items-start gap-2">
          <code class="min-w-0 flex-1 break-all rounded bg-muted px-2 py-1.5 font-mono text-[11px] leading-relaxed text-foreground/90">
            {{ command.code }}
          </code>
          <button
            type="button"
            class="shrink-0 rounded border border-border px-2 py-1 text-[11px] text-muted-foreground transition hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
            @click="copy(command.id, command.code)"
          >
            {{ copied === command.id ? 'Copiado' : 'Copiar' }}
          </button>
        </div>
      </li>
    </ol>
  </section>
</template>
