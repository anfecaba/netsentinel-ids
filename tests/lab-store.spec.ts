import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useLabStore } from '../stores/lab.store'
import type { LabCredential, LabDns, LabFlow } from '../types/lab'

const NOW = '2026-10-29T12:00:00.000Z'

function makeFlow(index: number, capturedAt = NOW): LabFlow {
  return {
    type: 'flow',
    id: `flow-${index}`,
    capturedAt,
    sourceIp: `10.0.0.${index % 200}`,
    sourcePort: 40000 + index,
    destinationIp: '10.0.1.1',
    destinationPort: 80,
    protocol: 'HTTP',
    encrypted: false,
    bytes: 100,
    riskLevel: 'warning',
    synthetic: false
  }
}

function makeCredential(index = 0): LabCredential {
  return {
    type: 'credential',
    id: `cred-${index}`,
    capturedAt: NOW,
    sourceIp: '10.0.0.1',
    destinationIp: '10.0.1.1',
    host: 'lab.local',
    method: 'POST',
    path: '/login',
    fields: [
      { name: 'username', value: 'alice', category: 'user', confidence: 0.99 },
      { name: 'password', value: 'SuperSecret123', category: 'password', confidence: 1 }
    ],
    synthetic: false
  }
}

function makeDns(index: number): LabDns {
  return {
    type: 'dns',
    id: `dns-${index}`,
    capturedAt: NOW,
    sourceIp: '10.0.0.1',
    destinationIp: '10.0.1.53',
    query: `host-${index}.lab.local`,
    qtype: 'A',
    encrypted: false,
    synthetic: false
  }
}

describe('useLabStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('ingresa un flujo y actualiza el grafo', () => {
    const store = useLabStore()
    store.ingest(makeFlow(1))

    expect(store.totalFlows).toBe(1)
    expect(store.graph.nodes.length).toBe(2)
    expect(store.graph.edges.length).toBe(1)
  })

  it('no duplica flujos con el mismo id', () => {
    const store = useLabStore()
    store.ingest(makeFlow(1))
    store.ingest(makeFlow(1))

    expect(store.totalFlows).toBe(1)
  })

  it('conserva como máximo 500 flujos', () => {
    const store = useLabStore()
    for (let index = 0; index < 620; index += 1) {
      store.ingest(makeFlow(index))
    }

    expect(store.totalFlows).toBe(500)
  })

  it('marca el grafo al ingerir una credencial', () => {
    const store = useLabStore()
    store.ingest(makeFlow(1))
    store.ingest(makeCredential())

    expect(store.totalCredentials).toBe(1)
    expect(store.graph.edges.some((edge) => edge.hasCredential)).toBe(true)
    expect(store.graph.nodes.some((node) => node.hasCredential)).toBe(true)
  })

  it('ingresa credenciales aunque la vista esté pausada', () => {
    const store = useLabStore()
    store.togglePause()

    store.ingest(makeFlow(1))
    store.ingest(makeCredential())

    expect(store.totalFlows).toBe(0)
    expect(store.totalCredentials).toBe(1)
  })

  it('ignora DNS duplicado y respeta el límite', () => {
    const store = useLabStore()
    for (let index = 0; index < 260; index += 1) {
      store.ingest(makeDns(index))
    }
    store.ingest(makeDns(0))

    expect(store.totalDns).toBe(200)
  })

  it('calcula la latencia con capturedAt', () => {
    const store = useLabStore()
    store.setConnection('open')
    store.ingest(makeFlow(1))

    expect(store.latencyMs).toBeGreaterThanOrEqual(0)
  })

  it('clear vacía flujos, credenciales, DNS y selección', () => {
    const store = useLabStore()
    store.ingest(makeFlow(1))
    store.ingest(makeCredential())
    store.ingest(makeDns(1))
    store.selectNode('10.0.0.1')

    store.clear()

    expect(store.totalFlows).toBe(0)
    expect(store.totalCredentials).toBe(0)
    expect(store.totalDns).toBe(0)
    expect(store.selectedNodeId).toBeNull()
    expect(store.latencyMs).toBe(-1)
  })

  it('ingesta por lotes deduplica en una sola pasada', () => {
    const store = useLabStore()
    store.ingestBatch([
      makeFlow(1),
      makeFlow(2),
      makeCredential(1),
      makeCredential(1),
      makeDns(1),
      makeDns(1)
    ])

    expect(store.totalFlows).toBe(2)
    expect(store.totalCredentials).toBe(1)
    expect(store.totalDns).toBe(1)
  })

  it('alterna la selección de nodo y el estado de pausa', () => {
    const store = useLabStore()
    store.selectNode('10.0.0.1')
    expect(store.selectedNodeId).toBe('10.0.0.1')
    store.selectNode('10.0.0.1')
    expect(store.selectedNodeId).toBeNull()

    expect(store.isPaused).toBe(false)
    store.togglePause()
    expect(store.isPaused).toBe(true)
  })

  it('normaliza el FPS y expone el modo sintético', () => {
    const store = useLabStore()
    store.setFps(29.6)
    expect(store.fps).toBe(30)
    store.setFps(-5)
    expect(store.fps).toBe(0)

    store.ingest({
      type: 'hello',
      serverId: 'lab-demo',
      version: '0.1.0',
      startedAt: NOW,
      iface: 'demo',
      mode: 'demo',
      capabilities: ['http', 'dns'],
      synthetic: true
    })
    expect(store.isSynthetic).toBe(true)
  })
})
