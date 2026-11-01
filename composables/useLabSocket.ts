import { onUnmounted, ref } from 'vue'
import { LabEventSchema } from '../types/lab'
import type { LabEvent } from '../types/lab'
import { useLabStore } from '../stores/lab.store'
import type { LabConnection } from '../stores/lab.store'

const DEFAULT_URL = 'ws://127.0.0.1:8765'
const BASE_RETRY_MS = 500
const MAX_RETRY_MS = 10_000
// Ingesta por lotes: sin esto, 30 eventos/s saturan el hilo principal y la
// cola del navegador crece hasta que la latencia se dispara.
const FLUSH_MS = 100
const MAX_PENDING = 600

export interface LabSocketOptions {
  url?: string
}

export function useLabSocket(options: LabSocketOptions = {}) {
  const store = useLabStore()
  const status = ref<LabConnection>('idle')

  let socket: WebSocket | null = null
  let retryTimer: ReturnType<typeof setTimeout> | null = null
  let flushTimer: ReturnType<typeof setTimeout> | null = null
  let retryCount = 0
  let manualClose = false
  let droppedEvents = 0
  let nextDropWarning = 100
  const pending: LabEvent[] = []

  function resolveUrl(): string {
    if (options.url) return options.url
    try {
      const config = useRuntimeConfig()
      const configured = (config.public as Record<string, unknown> | undefined)?.labWsUrl
      if (typeof configured === 'string' && configured.length > 0) return configured
    } catch {
      // Fuera de Nuxt (tests) se usa el valor por defecto.
    }
    return DEFAULT_URL
  }

  function clearRetry(): void {
    if (retryTimer) {
      clearTimeout(retryTimer)
      retryTimer = null
    }
  }

  function setStatus(next: LabConnection): void {
    status.value = next
    store.setConnection(next)
  }

  function scheduleRetry(): void {
    if (manualClose) return
    clearRetry()
    const delay = Math.min(MAX_RETRY_MS, BASE_RETRY_MS * 2 ** retryCount)
    retryCount += 1
    retryTimer = setTimeout(() => {
      retryTimer = null
      connect()
    }, delay)
  }

  function trimPending(): void {
    if (pending.length <= MAX_PENDING) return

    const overflow = pending.length - MAX_PENDING
    const dropped = pending.splice(0, overflow)
    const rescued = dropped.filter((event) => event.type === 'credential')
    if (rescued.length > 0) pending.unshift(...rescued)
    droppedEvents += overflow - rescued.length
    if (droppedEvents >= nextDropWarning) {
      nextDropWarning += 100
      console.warn(`[lab] cola saturada: ${droppedEvents} eventos descartados`)
    }
  }

  function flush(): void {
    flushTimer = null
    if (pending.length === 0) return

    const batch = pending.splice(0, pending.length)
    store.ingestBatch(batch)
  }

  function enqueue(event: LabEvent): void {
    pending.push(event)
    trimPending()
    if (flushTimer) return
    flushTimer = setTimeout(flush, FLUSH_MS)
  }

  function clearPending(): void {
    pending.length = 0
    if (flushTimer) {
      clearTimeout(flushTimer)
      flushTimer = null
    }
  }

  function connect(): void {
    if (typeof window === 'undefined' || typeof WebSocket === 'undefined') return

    manualClose = false
    clearRetry()

    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
      return
    }

    setStatus('connecting')

    try {
      socket = new WebSocket(resolveUrl())
    } catch (error) {
      store.setError(error instanceof Error ? error.message : 'No se pudo abrir el WebSocket')
      setStatus('error')
      scheduleRetry()
      return
    }

    socket.onopen = () => {
      retryCount = 0
      store.setError(null)
      setStatus('open')
    }

    socket.onmessage = (message: MessageEvent) => {
      let payload: unknown
      try {
        payload = JSON.parse(String(message.data))
      } catch {
        console.warn('[lab] mensaje no JSON descartado')
        return
      }

      const parsed = LabEventSchema.safeParse(payload)
      if (!parsed.success) {
        console.warn('[lab] evento fuera del contrato descartado', parsed.error.issues)
        return
      }

      enqueue(parsed.data)
    }
    socket.onerror = () => {
      // `onclose` se encarga de la reconexión.
      setStatus('error')
    }

    socket.onclose = () => {
      socket = null
      setStatus('closed')
      if (!manualClose) scheduleRetry()
    }
  }

  function disconnect(): void {
    manualClose = true
    clearRetry()
    clearPending()
    if (socket) {
      socket.onclose = null
      socket.onerror = null
      socket.onmessage = null
      try {
        socket.close(1000, 'cliente desconectado')
      } catch {
        // El socket ya estaba cerrado.
      }
      socket = null
    }
    setStatus('closed')
  }

  onUnmounted(() => {
    disconnect()
  })

  return { connect, disconnect, status }
}
