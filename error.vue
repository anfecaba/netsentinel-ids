<script setup lang="ts">
import type { NuxtError } from '#app'

const props = defineProps<{ error: NuxtError }>()

const statusCode = computed(() => props.error?.statusCode ?? 500)
const message = computed(() =>
  statusCode.value === 404
    ? 'La ruta solicitada no existe en este panel.'
    : 'Algo interrumpió el panel de NetSentinel.'
)

function goHome(): void {
  clearError({ redirect: '/' })
}

function reload(): void {
  if (typeof window !== 'undefined') window.location.reload()
}
</script>

<template>
  <div class="min-h-screen bg-background text-foreground flex items-center justify-center px-6 py-16">
    <div class="w-full max-w-lg rounded-2xl border border-border bg-card/70 p-8 shadow-2xl">
      <div class="flex items-start gap-4">
        <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-rose-500/40 bg-rose-500/10 text-rose-400">
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v4m0 4h.01M10.3 3.9L2.6 17a2 2 0 001.7 3h15.4a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z" />
          </svg>
        </div>
        <div class="min-w-0">
          <p class="font-mono text-xs uppercase tracking-widest text-muted-foreground">
            Error {{ statusCode }}
          </p>
          <h1 class="mt-1 text-xl font-bold tracking-tight text-foreground">
            NetSentinel no pudo mostrar esta vista
          </h1>
          <p class="mt-2 text-sm leading-relaxed text-muted-foreground">
            {{ message }}
          </p>
          <p v-if="error?.message" class="mt-3 break-words rounded-lg border border-border bg-background/60 px-3 py-2 font-mono text-[11px] text-muted-foreground">
            {{ error.message }}
          </p>
        </div>
      </div>

      <div class="mt-6 flex flex-col gap-2 sm:flex-row">
        <button
          type="button"
          class="inline-flex flex-1 items-center justify-center rounded-lg border border-primary/40 bg-primary/10 px-4 py-2 text-sm font-semibold text-primary transition hover:bg-primary/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          @click="goHome"
        >
          Volver al panel de defensa
        </button>
        <button
          type="button"
          class="inline-flex flex-1 items-center justify-center rounded-lg border border-border px-4 py-2 text-sm font-semibold text-muted-foreground transition hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          @click="reload"
        >
          Recargar
        </button>
      </div>

      <p class="mt-6 text-center text-[11px] text-muted-foreground">
        Si el fallo persiste, revisa la consola del navegador y los logs de Nuxt.
      </p>
    </div>
  </div>
</template>
