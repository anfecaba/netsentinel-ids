/** Métricas puras del laboratorio: latencia y FPS. */

export function calculateLatencyMs(capturedAt: string, now: number = Date.now()): number {
  const parsed = Date.parse(capturedAt)
  if (Number.isNaN(parsed)) return -1
  return Math.max(0, now - parsed)
}

export interface FrameGate {
  /** Si este fotograma toca dibujar. */
  due: boolean
  /** Referencia temporal para el siguiente ciclo (sin cambios si no toca). */
  lastFrame: number
}

/**
 * Decide si toca dibujar manteniendo una cadencia objetivo.
 *
 * Un límite del tipo `now - lastFrame >= frameMs` se **cuantiza** al refresco
 * de la pantalla: a 90 Hz el intervalo cae en 44,4 ms (~22,5 FPS) y a 120 Hz
 * en 33,3 ms (30 FPS), aunque el objetivo sea el mismo. Avanzar la referencia
 * en múltiplos del objetivo conserva ~30 FPS en cualquier refresco, a cambio de
 * una variación de un fotograma entre pintadas consecutivas.
 */
export function advanceFrame(now: number, lastFrame: number, frameMs: number): FrameGate {
  const elapsed = now - lastFrame
  if (elapsed < frameMs) return { due: false, lastFrame }
  return { due: true, lastFrame: now - (elapsed % frameMs) }
}

/**
 * Cuenta fotogramas en una ventana móvil de 1 s.
 * No usa temporizadores propios: el bucle de render llama `tick`.
 */
export class FpsMeter {
  private readonly windowMs: number
  private frames: number[] = []

  constructor(windowMs = 1000) {
    this.windowMs = windowMs
  }

  tick(now: number = Date.now()): void {
    this.frames.push(now)
    const cutoff = now - this.windowMs
    while (this.frames.length > 0 && this.frames[0] < cutoff) {
      this.frames.shift()
    }
  }

  get fps(): number {
    if (this.frames.length === 0) return 0
    if (this.frames.length === 1) return 1
    const span = this.frames[this.frames.length - 1] - this.frames[0]
    if (span <= 0) return this.frames.length
    return Math.round(((this.frames.length - 1) / span) * 1000)
  }

  reset(): void {
    this.frames = []
  }
}
