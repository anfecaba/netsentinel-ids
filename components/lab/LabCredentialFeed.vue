<script setup lang="ts">
const store = useLabStore()

function shortTime(iso: string): string {
  const parsed = new Date(iso)
  if (Number.isNaN(parsed.getTime())) return '—'
  return parsed.toLocaleTimeString('es-CO', { hour12: false })
}

const categoryLabel: Record<string, string> = {
  user: 'usuario',
  password: 'contraseña',
  email: 'correo',
  token: 'token',
  other: 'otro'
}
</script>

<template>
  <section class="flex h-full flex-col rounded-xl border border-rose-500/25 bg-card/60" aria-label="Credenciales capturadas">
    <header class="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
      <div class="flex min-w-0 items-center gap-2">
        <span class="h-2 w-2 shrink-0 rounded-full bg-rose-400" aria-hidden="true" />
        <h2 class="truncate text-sm font-semibold text-foreground">Credenciales en claro</h2>
        <span class="rounded border border-rose-500/40 bg-rose-500/10 px-1.5 py-0.5 font-mono text-[10px] text-rose-300">
          {{ store.totalCredentials }}
        </span>
      </div>
      <button
        type="button"
        class="shrink-0 rounded border border-border px-2 py-1 text-[11px] text-muted-foreground transition hover:border-rose-500/40 hover:text-rose-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-400"
        @click="store.clearCredentials()"
      >
        Limpiar
      </button>
    </header>

    <div class="max-h-[520px] flex-1 space-y-2 overflow-y-auto px-3 py-3">
      <p v-if="store.credentials.length === 0" class="px-1 py-8 text-center text-xs leading-relaxed text-muted-foreground">
        Sin credenciales todavía.<br />
        Envía el formulario por <strong class="text-foreground/80">HTTP</strong> y aparecerán aquí;
        por HTTPS solo verás metadatos TLS.
      </p>

      <article
        v-for="credential in store.credentials"
        :key="credential.id"
        class="rounded-lg border border-rose-500/30 bg-rose-500/[0.05] p-3"
      >
        <div class="flex flex-wrap items-baseline justify-between gap-x-2 gap-y-1">
          <p class="min-w-0 break-all font-mono text-xs font-semibold text-rose-200">
            {{ credential.host }}
          </p>
          <p class="font-mono text-[10px] text-muted-foreground">{{ shortTime(credential.capturedAt) }}</p>
        </div>
        <p class="mt-0.5 font-mono text-[11px] text-muted-foreground">
          <span class="text-amber-300">{{ credential.method }}</span> {{ credential.path }}
        </p>

        <dl class="mt-2 space-y-1">
          <div
            v-for="field in credential.fields"
            :key="`${credential.id}-${field.name}`"
            class="grid grid-cols-[minmax(0,7rem)_minmax(0,1fr)] items-baseline gap-2"
          >
            <dt class="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
              {{ field.name }}
              <span class="sr-only">({{ categoryLabel[field.category] ?? field.category }})</span>
            </dt>
            <dd class="break-all rounded bg-background/70 px-1.5 py-0.5 font-mono text-[11px] text-foreground">
              {{ field.value }}
            </dd>
          </div>
        </dl>

        <div class="mt-2 flex flex-wrap items-center gap-2 text-[10px] text-muted-foreground">
          <span class="font-mono">{{ credential.sourceIp }} → {{ credential.destinationIp }}</span>
          <span
            v-if="credential.synthetic"
            class="rounded border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 font-mono uppercase tracking-wide text-amber-300"
          >
            simulación
          </span>
        </div>
      </article>
    </div>

    <footer class="border-t border-border px-4 py-2 text-[10px] leading-relaxed text-muted-foreground">
      Los valores se muestran completos a propósito para la demo académica. No se guardan en disco.
    </footer>
  </section>
</template>
