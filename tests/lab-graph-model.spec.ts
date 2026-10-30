import { describe, it, expect } from 'vitest'
import { buildLabGraph } from '../utils/labGraphModel'
import type { LabCredential, LabFlow } from '../types/lab'

const NOW = new Date().toISOString()

function makeFlow(index: number): LabFlow {
  return {
    type: 'flow',
    id: `flow-${index}`,
    capturedAt: NOW,
    sourceIp: `10.0.0.${index % 120}`,
    sourcePort: 5000 + index,
    destinationIp: `10.0.1.${index % 120}`,
    destinationPort: 80,
    protocol: 'HTTP',
    encrypted: false,
    bytes: 100 + index,
    riskLevel: 'danger',
    synthetic: false
  }
}

function makeCredential(): LabCredential {
  return {
    type: 'credential',
    id: 'cred-1',
    capturedAt: NOW,
    sourceIp: '10.0.0.1',
    destinationIp: '10.0.1.1',
    host: 'lab.local',
    method: 'POST',
    path: '/login',
    fields: [
      {
        name: 'password',
        value: 'SuperSecret123',
        category: 'password',
        confidence: 0.99
      }
    ],
    synthetic: false
  }
}

describe('buildLabGraph', () => {
  it('limita el grafo a 100 nodos', () => {
    const flows = Array.from({ length: 120 }, (_, index) => makeFlow(index))
    const graph = buildLabGraph(flows, [], 100)

    expect(graph.nodes.length).toBeLessThanOrEqual(100)
    expect(graph.nodes.length).toBeGreaterThan(0)
  })

  it('marca arista y nodos con credencial', () => {
    const flows = Array.from({ length: 10 }, (_, index) => makeFlow(index))
    const graph = buildLabGraph(flows, [makeCredential()], 100)
    const credentialEdge = graph.edges.find(
      (edge) => edge.source === '10.0.0.1' && edge.target === '10.0.1.1'
    )

    expect(credentialEdge).toBeDefined()
    expect(credentialEdge?.hasCredential).toBe(true)
    expect(credentialEdge?.risk).toBe('danger')
    expect(graph.nodes.find((node) => node.id === '10.0.0.1')?.hasCredential).toBe(true)
    expect(graph.nodes.find((node) => node.id === '10.0.1.1')?.hasCredential).toBe(true)
  })

  it('agrega flujos repetidos en una sola arista', () => {
    const flow = makeFlow(1)
    const graph = buildLabGraph([flow, { ...flow, id: 'flow-2' }], [], 100)
    const edge = graph.edges.find(
      (item) => item.source === flow.sourceIp && item.target === flow.destinationIp
    )

    expect(graph.edges).toHaveLength(1)
    expect(edge?.count).toBe(2)
    expect(edge?.bytes).toBe(flow.bytes * 2)
  })

  it('no muta los flujos de entrada', () => {
    const flows = [makeFlow(1)]
    const snapshot = JSON.parse(JSON.stringify(flows))
    buildLabGraph(flows, [makeCredential()], 100)

    expect(flows).toEqual(snapshot)
  })
})
