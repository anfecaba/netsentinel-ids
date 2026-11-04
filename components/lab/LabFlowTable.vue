<script setup lang="ts">
import { serviceLabelFor } from '~/utils/labServiceLabels'

const store = useLabStore()

const rows = computed(() =>
  [...store.flowList]
    .sort((a, b) => Date.parse(b.capturedAt) - Date.parse(a.capturedAt))
    .slice(0, 12)
)

const protocolClass: Record<string, string> = {
  HTTP: 'border-rose-500/40 bg-rose-500/10 text-rose-300',
  HTTPS: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
  TLS: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
  DNS: 'border-amber-500/40 bg-amber-500/10 text-amber-300'
}

function serviceFor(flow: { host?: string; destinationIp: string }): { label: string; tone: string } | null {
  return serviceLabelFor(flow.host ?? null)
}

function shortTime(iso: string): string {
  const parsed = new Date(iso)
  if (Number.isNaN(parsed.getTime())) return '—'
  return parsed.toLocaleTimeString('es-CO', { hour12: false })
}
</script>

<template>
  <section class="rounded-xl border border-border bg-card/60" aria-label="Flujos recientes">
    <header class="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
      <div class="flex items-center gap-2">
        <span class="h-2 w-2 rounded-full bg-cyan-400" aria-hidden="true" />
        <h2 class="text-sm font-semibold text-foreground">Flujos recientes</h2>
      </div>
      <span class="font-mono text-[10px] text-muted-foreground">{{ store.totalFlows }}</span>
    </header>

    <p v-if="rows.length === 0" class="px-4 py-6 text-center text-xs text-muted-foreground">
      Sin flujos registrados.
    </p>

    <div v-else class="max-h-[260px] overflow-y-auto">
      <table class="w-full text-left text-xs">
        <thead class="sticky top-0 bg-card text-[10px] uppercase tracking-wider text-muted-foreground">
          <tr>
            <th scope="col" class="px-4 py-2 font-medium">Hora</th>
            <th scope="col" class="px-2 py-2 font-medium">Origen → destino</th>
            <th scope="col" class="px-2 py-2 font-medium">Protocolo</th>
            <th scope="col" class="px-2 py-2 font-medium">Servicio</th>
            <th scope="col" class="px-4 py-2 text-right font-medium">Cifrado</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border/70">
          <tr v-for="flow in rows" :key="flow.id">
            <td class="whitespace-nowrap px-4 py-2 font-mono text-[10px] text-muted-foreground">
              {{ shortTime(flow.capturedAt) }}
            </td>
            <td class="px-2 py-2 font-mono text-[10px] text-foreground/80">
              <span class="break-all">{{ flow.sourceIp }}:{{ flow.sourcePort }}</span>
              <span class="text-muted-foreground"> → </span>
              <span class="break-all">{{ flow.destinationIp }}:{{ flow.destinationPort }}</span>
            </td>
            <td class="px-2 py-2">
              <span
                class="rounded border px-1.5 py-0.5 font-mono text-[10px]"
                :class="protocolClass[flow.protocol] ?? 'border-border bg-muted text-muted-foreground'"
              >
                {{ flow.protocol }}
              </span>
            </td>
            <td class="px-2 py-2">
              <span
                v-if="serviceFor(flow)"
                class="rounded border px-1.5 py-0.5 font-mono text-[10px]"
                :class="serviceFor(flow)!.tone"
              >
                {{ serviceFor(flow)!.label }}
              </span>
              <span v-else-if="flow.host" class="truncate font-mono text-[10px] text-muted-foreground">
                {{ flow.host }}
              </span>
              <span v-else class="font-mono text-[10px] text-muted-foreground">—</span>
            </td>
            <td class="px-4 py-2 text-right">
              <span v-if="flow.encrypted" class="text-emerald-400" title="Cifrado">TLS</span>
              <span v-else class="text-rose-400" title="Sin cifrar">plano</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
