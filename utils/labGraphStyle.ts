/** Tokens visuales del grafo del laboratorio. */

import type { LabNodeRole, LabRisk } from '../types/lab'

export const ROLE_COLORS: Record<LabNodeRole, string> = {
  local: '#34d399',
  gateway: '#22d3ee',
  dns: '#fbbf24',
  remote: '#a78bfa'
}

export const FALLBACK_COLOR = '#94a3b8'

export const DANGER_COLOR = '#fb7185'
export const WARNING_COLOR = '#fbbf24'
export const SAFE_COLOR = '#94a3b8'

export const EDGE_COLORS: Record<LabRisk, string> = {
  safe: 'rgba(148, 163, 184, 0.22)',
  warning: 'rgba(251, 191, 36, 0.30)',
  danger: 'rgba(251, 113, 133, 0.75)'
}

export function colorForRole(role: LabNodeRole | string): string {
  return ROLE_COLORS[role as LabNodeRole] ?? FALLBACK_COLOR
}

export function radiusForDegree(degree: number): number {
  const safe = Number.isFinite(degree) ? Math.max(0, degree) : 0
  return Math.min(22, 6 + Math.sqrt(safe) * 2.1)
}

export function edgeColorFor(risk: LabRisk, hasCredential: boolean): string {
  if (hasCredential) return EDGE_COLORS.danger
  return EDGE_COLORS[risk] ?? EDGE_COLORS.safe
}
