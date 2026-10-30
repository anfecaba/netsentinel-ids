import { z } from 'zod'

const IsoDateSchema = z.string().datetime({ offset: true })

export const LabProtocolSchema = z.enum([
  'HTTP',
  'HTTPS',
  'TLS',
  'DNS',
  'TCP',
  'UDP',
  'ARP'
])

export const LabRiskSchema = z.enum(['safe', 'warning', 'danger'])

export const LabCredentialCategorySchema = z.enum([
  'user',
  'password',
  'email',
  'token',
  'other'
])

export const LabCredentialFieldSchema = z.object({
  name: z.string().min(1),
  value: z.string(),
  category: LabCredentialCategorySchema,
  confidence: z.number().min(0).max(1)
})

export const LabHelloSchema = z.object({
  type: z.literal('hello'),
  serverId: z.string().min(1),
  version: z.string().min(1),
  startedAt: IsoDateSchema,
  iface: z.string().min(1),
  mode: z.enum(['live', 'demo']),
  capabilities: z.array(z.string()),
  synthetic: z.boolean().default(false)
})

export const LabFlowSchema = z.object({
  type: z.literal('flow'),
  id: z.string().min(1),
  capturedAt: IsoDateSchema,
  sourceIp: z.string().min(1),
  sourcePort: z.number().int().min(0).max(65535),
  destinationIp: z.string().min(1),
  destinationPort: z.number().int().min(0).max(65535),
  protocol: LabProtocolSchema,
  encrypted: z.boolean(),
  bytes: z.number().int().min(0),
  host: z.string().optional(),
  method: z.string().optional(),
  path: z.string().optional(),
  riskLevel: LabRiskSchema,
  note: z.string().optional(),
  synthetic: z.boolean().default(false)
})

export const LabCredentialSchema = z.object({
  type: z.literal('credential'),
  id: z.string().min(1),
  capturedAt: IsoDateSchema,
  flowId: z.string().optional(),
  sourceIp: z.string().min(1),
  destinationIp: z.string().min(1),
  host: z.string().min(1),
  method: z.string().min(1),
  path: z.string().min(1),
  fields: z.array(LabCredentialFieldSchema).min(1),
  synthetic: z.boolean().default(false)
})

export const LabDnsSchema = z.object({
  type: z.literal('dns'),
  id: z.string().min(1),
  capturedAt: IsoDateSchema,
  sourceIp: z.string().min(1),
  destinationIp: z.string().min(1),
  query: z.string().min(1),
  qtype: z.string().min(1),
  encrypted: z.boolean().default(false),
  synthetic: z.boolean().default(false)
})

export const LabStatsSchema = z.object({
  type: z.literal('stats'),
  timestamp: IsoDateSchema,
  packets: z.number().int().min(0),
  flows: z.number().int().min(0),
  credentials: z.number().int().min(0),
  dnsQueries: z.number().int().min(0),
  pps: z.number().min(0),
  clients: z.number().int().min(0),
  queue: z.number().int().min(0),
  synthetic: z.boolean().default(false)
})

export const LabErrorSchema = z.object({
  type: z.literal('error'),
  code: z.string().min(1),
  message: z.string().min(1),
  timestamp: IsoDateSchema,
  synthetic: z.boolean().default(false)
})

export const LabEventSchema = z.discriminatedUnion('type', [
  LabHelloSchema,
  LabFlowSchema,
  LabCredentialSchema,
  LabDnsSchema,
  LabStatsSchema,
  LabErrorSchema
])

export type LabProtocol = z.infer<typeof LabProtocolSchema>
export type LabRisk = z.infer<typeof LabRiskSchema>
export type LabCredentialCategory = z.infer<typeof LabCredentialCategorySchema>
export type LabCredentialField = z.infer<typeof LabCredentialFieldSchema>
export type LabHello = z.infer<typeof LabHelloSchema>
export type LabFlow = z.infer<typeof LabFlowSchema>
export type LabCredential = z.infer<typeof LabCredentialSchema>
export type LabDns = z.infer<typeof LabDnsSchema>
export type LabStats = z.infer<typeof LabStatsSchema>
export type LabError = z.infer<typeof LabErrorSchema>
export type LabEvent = z.infer<typeof LabEventSchema>

export type LabNodeRole = 'local' | 'gateway' | 'dns' | 'remote'

export interface LabGraphNode {
  id: string
  role: LabNodeRole
  degree: number
  lastSeen: number
  lastCredentialAt?: number
  risk: LabRisk
  hasCredential: boolean
}

export interface LabGraphEdge {
  id: string
  source: string
  target: string
  protocol: LabProtocol
  count: number
  bytes: number
  lastSeen: number
  lastCredentialAt?: number
  risk: LabRisk
  hasCredential: boolean
}

export interface LabGraph {
  nodes: LabGraphNode[]
  edges: LabGraphEdge[]
}
