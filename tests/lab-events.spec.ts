import { describe, it, expect } from 'vitest'
import { LabEventSchema } from '../types/lab'

describe('LabEventSchema', () => {
  it('acepta un evento credential válido', () => {
    const result = LabEventSchema.safeParse({
      type: 'credential',
      id: 'cred-1',
      capturedAt: new Date().toISOString(),
      sourceIp: '192.168.1.23',
      destinationIp: '192.168.1.7',
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
    })

    expect(result.success).toBe(true)
  })

  it('rechaza un evento credential sin campos', () => {
    const result = LabEventSchema.safeParse({
      type: 'credential',
      id: 'cred-1',
      capturedAt: new Date().toISOString(),
      sourceIp: '192.168.1.23',
      destinationIp: '192.168.1.7',
      host: 'lab.local',
      method: 'POST',
      path: '/login',
      fields: []
    })

    expect(result.success).toBe(false)
  })

  it('rechaza fechas inválidas y tipos desconocidos', () => {
    const invalidDate = LabEventSchema.safeParse({
      type: 'flow',
      id: 'flow-1',
      capturedAt: 'ayer',
      sourceIp: '10.0.0.1',
      sourcePort: 1234,
      destinationIp: '10.0.0.2',
      destinationPort: 80,
      protocol: 'HTTP',
      encrypted: false,
      bytes: 10,
      riskLevel: 'danger',
      synthetic: false
    })
    expect(invalidDate.success).toBe(false)

    expect(LabEventSchema.safeParse({ type: 'packet', id: 'x' }).success).toBe(false)
  })

  it('acepta hello y stats', () => {
    const hello = LabEventSchema.safeParse({
      type: 'hello',
      serverId: 'lab-1',
      version: '0.1.0',
      startedAt: new Date().toISOString(),
      iface: 'Wi-Fi',
      mode: 'demo',
      capabilities: ['http', 'dns'],
      synthetic: false
    })
    expect(hello.success).toBe(true)

    const stats = LabEventSchema.safeParse({
      type: 'stats',
      timestamp: new Date().toISOString(),
      packets: 1,
      flows: 1,
      credentials: 0,
      dnsQueries: 0,
      pps: 1.5,
      clients: 1,
      queue: 0,
      synthetic: false
    })
    expect(stats.success).toBe(true)
  })
})
