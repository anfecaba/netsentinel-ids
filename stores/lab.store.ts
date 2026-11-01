import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type {
  LabCredential,
  LabDns,
  LabEvent,
  LabFlow,
  LabGraph,
  LabHello,
  LabStats
} from '../types/lab'
import { buildLabGraph } from '../utils/labGraphModel'
import { calculateLatencyMs } from '../utils/labMetrics'

export type LabConnection = 'idle' | 'connecting' | 'open' | 'closed' | 'error'

const MAX_FLOWS = 500
const MAX_CREDENTIALS = 100
const MAX_DNS = 200
const MAX_NODES = 100

function timeOf(iso: string | undefined): number {
  if (!iso) return 0
  const parsed = Date.parse(iso)
  return Number.isNaN(parsed) ? 0 : parsed
}

function trimFlows(flows: Record<string, LabFlow>): Record<string, LabFlow> {
  const entries = Object.entries(flows)
  if (entries.length <= MAX_FLOWS) return flows

  entries.sort((a, b) => timeOf(b[1].capturedAt) - timeOf(a[1].capturedAt))
  const kept: Record<string, LabFlow> = {}
  for (const [id, flow] of entries.slice(0, MAX_FLOWS)) {
    kept[id] = flow
  }
  return kept
}

export const useLabStore = defineStore('lab', () => {
  const connection = ref<LabConnection>('idle')
  const serverInfo = ref<LabHello | null>(null)
  const flowsById = ref<Record<string, LabFlow>>({})
  const credentials = ref<LabCredential[]>([])
  const dnsQueries = ref<LabDns[]>([])
  const stats = ref<LabStats | null>(null)
  const lastError = ref<string | null>(null)
  const isPaused = ref(false)
  const selectedNodeId = ref<string | null>(null)
  const fps = ref(0)
  const latencyMs = ref(-1)
  const lastEventAt = ref<number | null>(null)

  const flowList = computed<LabFlow[]>(() => Object.values(flowsById.value))
  const totalFlows = computed<number>(() => flowList.value.length)
  const totalCredentials = computed<number>(() => credentials.value.length)
  const totalDns = computed<number>(() => dnsQueries.value.length)
  const isSynthetic = computed<boolean>(() => serverInfo.value?.mode === 'demo')
  const isConnected = computed<boolean>(() => connection.value === 'open')
  const hasData = computed<boolean>(
    () => totalFlows.value > 0 || totalCredentials.value > 0 || totalDns.value > 0
  )

  const graph = computed<LabGraph>(() =>
    buildLabGraph(flowList.value, credentials.value, MAX_NODES)
  )

  function ingestBatch(events: LabEvent[]): void {
    if (events.length === 0) return

    const freshFlows: LabFlow[] = []
    const freshDns: LabDns[] = []
    let nextCredentials = credentials.value
    let credentialsChanged = false
    let latestCapturedAt: string | null = null

    for (const event of events) {
      switch (event.type) {
        case 'hello':
          serverInfo.value = event
          continue

        case 'stats':
          stats.value = event
          continue

        case 'error':
          lastError.value = event.message
          connection.value = 'error'
          continue

        case 'credential': {
          // Una credencial no se pierde por pausar la vista.
          if (nextCredentials.some((item) => item.id === event.id)) continue
          nextCredentials = [event, ...nextCredentials]
          credentialsChanged = true
          latestCapturedAt = event.capturedAt
          continue
        }

        case 'flow': {
          if (isPaused.value) continue
          if (flowsById.value[event.id]) continue
          if (freshFlows.some((item) => item.id === event.id)) continue
          freshFlows.push(event)
          latestCapturedAt = event.capturedAt
          continue
        }

        case 'dns': {
          if (isPaused.value) continue
          if (dnsQueries.value.some((item) => item.id === event.id)) continue
          if (freshDns.some((item) => item.id === event.id)) continue
          freshDns.push(event)
          latestCapturedAt = event.capturedAt
          continue
        }
      }
    }

    if (freshFlows.length > 0) {
      const merged: Record<string, LabFlow> = { ...flowsById.value }
      for (const flow of freshFlows) {
        merged[flow.id] = flow
      }
      // Una sola poda y una sola ordenación por lote.
      flowsById.value = trimFlows(merged)
    }

    if (credentialsChanged) {
      credentials.value = nextCredentials.slice(0, MAX_CREDENTIALS)
    }

    if (freshDns.length > 0) {
      const merged = [...freshDns.reverse(), ...dnsQueries.value]
      const seen = new Set<string>()
      dnsQueries.value = merged.filter((item) => {
        if (seen.has(item.id)) return false
        seen.add(item.id)
        return true
      }).slice(0, MAX_DNS)
    }

    if (latestCapturedAt) {
      lastEventAt.value = Date.now()
      latencyMs.value = calculateLatencyMs(latestCapturedAt)
    }
  }

  function ingest(event: LabEvent): void {
    ingestBatch([event])
  }

  function clear(): void {
    flowsById.value = {}
    credentials.value = []
    dnsQueries.value = []
    stats.value = null
    selectedNodeId.value = null
    latencyMs.value = -1
    lastEventAt.value = null
  }

  function clearCredentials(): void {
    credentials.value = []
  }

  function setFps(value: number): void {
    fps.value = Number.isFinite(value) && value >= 0 ? Math.round(value) : 0
  }

  function selectNode(ip: string | null): void {
    selectedNodeId.value = selectedNodeId.value === ip ? null : ip
  }

  function setConnection(status: LabConnection): void {
    connection.value = status
  }

  function setError(message: string | null): void {
    lastError.value = message
  }

  function togglePause(): void {
    isPaused.value = !isPaused.value
  }

  return {
    connection,
    serverInfo,
    flowsById,
    credentials,
    dnsQueries,
    stats,
    lastError,
    isPaused,
    selectedNodeId,
    fps,
    latencyMs,
    lastEventAt,
    flowList,
    totalFlows,
    totalCredentials,
    totalDns,
    isSynthetic,
    isConnected,
    hasData,
    graph,
    ingest,
    ingestBatch,
    clear,
    clearCredentials,
    setFps,
    selectNode,
    setConnection,
    setError,
    togglePause
  }
})
