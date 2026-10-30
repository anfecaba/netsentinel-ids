import type {
  LabCredential,
  LabFlow,
  LabGraph,
  LabGraphEdge,
  LabGraphNode,
  LabNodeRole,
  LabProtocol,
  LabRisk
} from '../types/lab'

const RISK_RANK: Record<LabRisk, number> = {
  safe: 0,
  warning: 1,
  danger: 2
}

function parseTime(iso: string): number {
  const parsed = Date.parse(iso)
  return Number.isNaN(parsed) ? 0 : parsed
}

function higherRisk(a: LabRisk, b: LabRisk): LabRisk {
  return RISK_RANK[b] > RISK_RANK[a] ? b : a
}

function isPrivateIpv4(ip: string): boolean {
  const parts = ip.split('.')
  if (parts.length !== 4) return false
  const octets = parts.map((part) => Number.parseInt(part, 10))
  if (octets.some((value) => !Number.isInteger(value) || value < 0 || value > 255)) {
    return false
  }
  const [first, second] = octets
  return (
    first === 10 ||
    (first === 172 && second >= 16 && second <= 31) ||
    (first === 192 && second === 168) ||
    first === 127
  )
}

function roleFor(ip: string, isDestination: boolean, protocol: LabProtocol, destinationPort: number): LabNodeRole {
  if (protocol === 'DNS' || destinationPort === 53) return 'dns'
  if (!isPrivateIpv4(ip)) return 'remote'
  return isDestination ? 'remote' : 'local'
}

function ensureNode(
  nodes: Map<string, LabGraphNode>,
  ip: string,
  role: LabNodeRole,
  time: number,
  risk: LabRisk
): LabGraphNode {
  const existing = nodes.get(ip)
  if (existing) {
    if (time > existing.lastSeen) existing.lastSeen = time
    existing.risk = higherRisk(existing.risk, risk)
    return existing
  }

  const node: LabGraphNode = {
    id: ip,
    role,
    degree: 0,
    lastSeen: time,
    risk,
    hasCredential: false
  }
  nodes.set(ip, node)
  return node
}

function markCredential(
  nodes: Map<string, LabGraphNode>,
  edges: Map<string, LabGraphEdge>,
  credential: LabCredential
): void {
  const time = parseTime(credential.capturedAt)
  const edgeId = `${credential.sourceIp}->${credential.destinationIp}:HTTP`
  let edge = edges.get(edgeId)

  if (!edge) {
    edge = {
      id: edgeId,
      source: credential.sourceIp,
      target: credential.destinationIp,
      protocol: 'HTTP',
      count: 1,
      bytes: 0,
      lastSeen: time,
      risk: 'danger',
      hasCredential: true
    }
    edges.set(edgeId, edge)
  }

  edge.hasCredential = true
  edge.lastCredentialAt = Math.max(edge.lastCredentialAt ?? 0, time)
  edge.risk = 'danger'

  for (const ip of [credential.sourceIp, credential.destinationIp]) {
    const node = ensureNode(nodes, ip, roleFor(ip, ip === credential.destinationIp, 'HTTP', 80), time, 'danger')
    node.hasCredential = true
    node.lastCredentialAt = Math.max(node.lastCredentialAt ?? 0, time)
    node.risk = 'danger'
  }
}

export function buildLabGraph(
  flows: LabFlow[],
  credentials: LabCredential[],
  maxNodes = 100
): LabGraph {
  const nodes = new Map<string, LabGraphNode>()
  const edges = new Map<string, LabGraphEdge>()

  for (const flow of flows) {
    const time = parseTime(flow.capturedAt)
    ensureNode(
      nodes,
      flow.sourceIp,
      roleFor(flow.sourceIp, false, flow.protocol, flow.destinationPort),
      time,
      flow.riskLevel
    )
    ensureNode(
      nodes,
      flow.destinationIp,
      roleFor(flow.destinationIp, true, flow.protocol, flow.destinationPort),
      time,
      flow.riskLevel
    )

    const edgeId = `${flow.sourceIp}->${flow.destinationIp}:${flow.protocol}`
    const existing = edges.get(edgeId)
    if (existing) {
      existing.count += 1
      existing.bytes += flow.bytes
      existing.lastSeen = Math.max(existing.lastSeen, time)
      existing.risk = higherRisk(existing.risk, flow.riskLevel)
    } else {
      edges.set(edgeId, {
        id: edgeId,
        source: flow.sourceIp,
        target: flow.destinationIp,
        protocol: flow.protocol,
        count: 1,
        bytes: flow.bytes,
        lastSeen: time,
        risk: flow.riskLevel,
        hasCredential: false
      })
    }
  }

  for (const credential of credentials) {
    markCredential(nodes, edges, credential)
  }

  const keptNodes = Array.from(nodes.values())
    .sort((a, b) => b.lastSeen - a.lastSeen)
    .slice(0, Math.max(1, maxNodes))
  const keptIds = new Set(keptNodes.map((node) => node.id))
  const keptEdges = Array.from(edges.values()).filter(
    (edge) => keptIds.has(edge.source) && keptIds.has(edge.target)
  )

  const degrees = new Map<string, number>()
  for (const edge of keptEdges) {
    degrees.set(edge.source, (degrees.get(edge.source) ?? 0) + 1)
    degrees.set(edge.target, (degrees.get(edge.target) ?? 0) + 1)
  }
  for (const node of keptNodes) {
    node.degree = degrees.get(node.id) ?? 0
  }

  return {
    nodes: keptNodes,
    edges: keptEdges
  }
}
