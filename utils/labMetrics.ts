/** Métricas puras del laboratorio: latencia y FPS. */

export function calculateLatencyMs(capturedAt: string, now: number = Date.now()): number {
  const parsed = Date.parse(capturedAt)
  if (Number.isNaN(parsed)) return -1
  return Math.max(0, now - parsed)
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
