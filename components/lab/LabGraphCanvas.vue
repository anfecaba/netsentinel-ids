<script setup lang="ts">
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  type ForceCenter,
  type ForceLink,
  type Simulation,
  type SimulationLinkDatum,
  type SimulationNodeDatum
} from 'd3-force'
import type { LabGraph, LabNodeRole, LabProtocol, LabRisk } from '~/types/lab'
import { colorForRole, DANGER_COLOR, edgeColorFor, radiusForDegree } from '~/utils/labGraphStyle'
import { advanceFrame, FpsMeter } from '~/utils/labMetrics'

interface SimNode extends SimulationNodeDatum {
  id: string
  role: LabNodeRole
  degree: number
  risk: LabRisk
  hasCredential: boolean
  lastCredentialAt?: number
}

interface SimLink extends SimulationLinkDatum<SimNode> {
  id: string
  risk: LabRisk
  hasCredential: boolean
  protocol: LabProtocol
}

const props = defineProps<{
  graph: LabGraph
  selectedNodeId?: string | null
}>()

const emit = defineEmits<{
  selectNode: [ip: string]
  fps: [fps: number]
}>()

const containerRef = ref<HTMLDivElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const reducedMotion = ref(false)

const FRAME_MS = 1000 / 30
const CREDENTIAL_PULSE_MS = 10_000

let simulation: Simulation<SimNode, SimLink> | null = null
let simNodes: SimNode[] = []
let simLinks: SimLink[] = []
let context: CanvasRenderingContext2D | null = null
let resizeObserver: ResizeObserver | null = null
let mediaQuery: MediaQueryList | null = null
let animationId = 0
let lastFrame = 0
let lastFpsEmit = 0
let width = 0
let height = 0
let pixelRatio = 1
let averageFrameMs = 0
let frameCount = 0
const meter = new FpsMeter()

function createSimulation(): void {
  simulation = forceSimulation<SimNode>([])
    .force(
      'link',
      forceLink<SimNode, SimLink>([])
        .id((node) => node.id)
        .distance(70)
        .strength(0.35)
    )
    .force('charge', forceManyBody<SimNode>().strength(-140))
    .force('center', forceCenter<SimNode>(width / 2, height / 2))
    .force(
      'collide',
      forceCollide<SimNode>().radius((node) => radiusForDegree(node.degree) + 5)
    )
    .stop()
}

function syncGraph(graph: LabGraph): void {
  if (!simulation) createSimulation()

  const previous = new Map(simNodes.map((node) => [node.id, node]))
  const total = Math.max(1, graph.nodes.length)
  const spread = Math.min(width, height) * 0.32

  simNodes = graph.nodes.map((node, index) => {
    const existing = previous.get(node.id)
    if (existing) {
      existing.role = node.role
      existing.degree = node.degree
      existing.risk = node.risk
      existing.hasCredential = node.hasCredential
      existing.lastCredentialAt = node.lastCredentialAt
      return existing
    }

    const angle = (index / total) * Math.PI * 2
    return {
      id: node.id,
      role: node.role,
      degree: node.degree,
      risk: node.risk,
      hasCredential: node.hasCredential,
      lastCredentialAt: node.lastCredentialAt,
      x: width / 2 + Math.cos(angle) * spread,
      y: height / 2 + Math.sin(angle) * spread
    }
  })

  const byId = new Map(simNodes.map((node) => [node.id, node]))
  simLinks = graph.edges
    .filter((edge) => byId.has(edge.source) && byId.has(edge.target))
    .map((edge) => ({
      id: edge.id,
      source: byId.get(edge.source) as SimNode,
      target: byId.get(edge.target) as SimNode,
      risk: edge.risk,
      hasCredential: edge.hasCredential,
      protocol: edge.protocol
    }))

  simulation?.nodes(simNodes)
  const linkForce = simulation?.force('link') as ForceLink<SimNode, SimLink> | undefined
  linkForce?.links(simLinks)
  linkForce?.distance((link) => (link.hasCredential ? 58 : 78))
  simulation?.alpha(0.5)
}

function resize(): void {
  const container = containerRef.value
  const canvas = canvasRef.value
  if (!container || !canvas) return

  const rect = container.getBoundingClientRect()
  width = Math.max(1, rect.width)
  height = Math.max(1, rect.height)
  pixelRatio = Math.min(2, window.devicePixelRatio || 1)

  canvas.width = Math.round(width * pixelRatio)
  canvas.height = Math.round(height * pixelRatio)

  const center = simulation?.force('center') as ForceCenter<SimNode> | undefined
  center?.x(width / 2).y(height / 2)
  simulation?.alpha(0.35)
}

function draw(): void {
  if (!context) return

  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)
  context.clearRect(0, 0, width, height)

  for (const link of simLinks) {
    const source = link.source as SimNode
    const target = link.target as SimNode
    if (typeof source === 'string' || typeof target === 'string') continue
    if (source.x == null || source.y == null || target.x == null || target.y == null) continue

    context.beginPath()
    context.strokeStyle = edgeColorFor(link.risk, link.hasCredential)
    context.lineWidth = link.hasCredential ? 2 : 1
    context.moveTo(source.x, source.y)
    context.lineTo(target.x, target.y)
    context.stroke()
  }

  const now = Date.now()

  for (const node of simNodes) {
    if (node.x == null || node.y == null) continue

    const radius = radiusForDegree(node.degree)
    const recentCredential =
      node.hasCredential &&
      typeof node.lastCredentialAt === 'number' &&
      now - node.lastCredentialAt < CREDENTIAL_PULSE_MS

    if (recentCredential && !reducedMotion.value && typeof node.lastCredentialAt === 'number') {
      const phase = ((now - node.lastCredentialAt) % 1200) / 1200
      context.beginPath()
      context.arc(node.x, node.y, radius + phase * 14, 0, Math.PI * 2)
      context.strokeStyle = `rgba(251, 113, 133, ${(0.55 * (1 - phase)).toFixed(3)})`
      context.lineWidth = 2
      context.stroke()
    }

    context.beginPath()
    context.arc(node.x, node.y, radius, 0, Math.PI * 2)
    context.fillStyle = recentCredential ? DANGER_COLOR : colorForRole(node.role)
    context.fill()

    if (node.risk === 'danger' && !recentCredential) {
      context.strokeStyle = 'rgba(251, 113, 133, 0.6)'
      context.lineWidth = 1.5
      context.stroke()
    }

    if (node.id === props.selectedNodeId) {
      context.beginPath()
      context.arc(node.x, node.y, radius + 4, 0, Math.PI * 2)
      context.strokeStyle = '#e2e8f0'
      context.lineWidth = 2
      context.stroke()
    }

    if (node.degree >= 3 || node.id === props.selectedNodeId) {
      const label = node.id.length > 18 ? `${node.id.slice(0, 17)}…` : node.id
      context.font = '10px "JetBrains Mono", monospace'
      context.textAlign = 'center'
      context.textBaseline = 'bottom'
      context.fillStyle = node.id === props.selectedNodeId ? '#f8fafc' : 'rgba(203, 213, 225, 0.85)'
      context.fillText(label, node.x, node.y - radius - 4)
    }
  }
}

function handleClick(event: MouseEvent): void {
  const canvas = canvasRef.value
  if (!canvas) return

  const rect = canvas.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top

  let closest: SimNode | null = null
  let bestDistance = Number.POSITIVE_INFINITY

  for (const node of simNodes) {
    if (node.x == null || node.y == null) continue
    const distance = Math.hypot(node.x - x, node.y - y)
    const hitRadius = radiusForDegree(node.degree) + 8
    if (distance <= hitRadius && distance < bestDistance) {
      bestDistance = distance
      closest = node
    }
  }

  if (closest) emit('selectNode', closest.id)
}

function startLoop(): void {
  const loop = (now: number) => {
    animationId = requestAnimationFrame(loop)
    if (document.hidden) return
    const gate = advanceFrame(now, lastFrame, FRAME_MS)
    if (!gate.due) return
    lastFrame = gate.lastFrame

    const startedAt = performance.now()
    if (simulation && simulation.alpha() > 0.004) {
      simulation.tick()
    }
    draw()
    const cost = performance.now() - startedAt
    averageFrameMs = averageFrameMs === 0 ? cost : averageFrameMs * 0.9 + cost * 0.1
    frameCount += 1

    meter.tick(now)
    if (now - lastFpsEmit >= 1000) {
      lastFpsEmit = now
      emit('fps', meter.fps)
      // Diagnóstico para la evidencia: coste real del fotograma.
      ;(window as unknown as Record<string, unknown>).__labPerf = {
        fps: meter.fps,
        avgFrameMs: Math.round(averageFrameMs * 10) / 10,
        frames: frameCount,
        nodes: simNodes.length,
        links: simLinks.length
      }
    }
  }
  animationId = requestAnimationFrame(loop)
}

function handleMotionChange(event: MediaQueryListEvent): void {
  reducedMotion.value = event.matches
}

onMounted(() => {
  const canvas = canvasRef.value
  const container = containerRef.value
  if (!canvas || !container) return

  context = canvas.getContext('2d')
  createSimulation()
  resize()
  syncGraph(props.graph)

  resizeObserver = new ResizeObserver(() => {
    resize()
    draw()
  })
  resizeObserver.observe(container)

  mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
  reducedMotion.value = mediaQuery.matches
  mediaQuery.addEventListener('change', handleMotionChange)

  startLoop()
})

watch(
  () => props.graph,
  (graph) => {
    syncGraph(graph)
  }
)

onUnmounted(() => {
  cancelAnimationFrame(animationId)
  resizeObserver?.disconnect()
  resizeObserver = null
  mediaQuery?.removeEventListener('change', handleMotionChange)
  mediaQuery = null
  simulation?.stop()
  simulation = null
})
</script>

<template>
  <div ref="containerRef" class="relative h-[420px] w-full lg:h-[520px]">
    <canvas
      ref="canvasRef"
      class="absolute inset-0 h-full w-full cursor-crosshair"
      role="img"
      aria-label="Grafo de tráfico de red: cada nodo es una IP y cada arista un flujo"
      @click="handleClick"
    />
    <p
      v-if="graph.nodes.length === 0"
      class="pointer-events-none absolute inset-0 flex items-center justify-center text-xs text-muted-foreground"
    >
      Sin tráfico todavía
    </p>
  </div>
</template>
