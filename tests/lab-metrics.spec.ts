import { describe, expect, it } from 'vitest'
import { advanceFrame, calculateLatencyMs, FpsMeter } from '../utils/labMetrics'

describe('calculateLatencyMs', () => {
  it('calcula la diferencia entre capturedAt y ahora', () => {
    const capturedAt = '2026-10-29T12:00:00.000Z'
    const now = Date.parse(capturedAt) + 420

    expect(calculateLatencyMs(capturedAt, now)).toBe(420)
  })

  it('nunca devuelve negativo para fechas futuras por desfase de reloj', () => {
    const capturedAt = '2026-10-29T12:00:01.000Z'
    const now = Date.parse(capturedAt) - 500

    expect(calculateLatencyMs(capturedAt, now)).toBe(0)
  })

  it('devuelve -1 si la fecha es inválida', () => {
    expect(calculateLatencyMs('ayer', Date.now())).toBe(-1)
    expect(calculateLatencyMs('', Date.now())).toBe(-1)
  })
})

describe('FpsMeter', () => {
  it('mide 30 fps con fotogramas cada 33 ms', () => {
    const meter = new FpsMeter()
    let now = 0
    for (let frame = 0; frame <= 30; frame += 1) {
      meter.tick(now)
      now += 33
    }
    expect(meter.fps).toBeGreaterThanOrEqual(29)
    expect(meter.fps).toBeLessThanOrEqual(31)
  })

  it('descarta fotogramas viejos de la ventana', () => {
    const meter = new FpsMeter()
    meter.tick(0)
    meter.tick(2000)
    expect(meter.fps).toBe(1)
  })

  it('devuelve 0 sin fotogramas y se reinicia', () => {
    const meter = new FpsMeter()
    expect(meter.fps).toBe(0)
    meter.tick(1000)
    meter.reset()
    expect(meter.fps).toBe(0)
  })
})

describe('advanceFrame', () => {
  const FRAME_MS = 1000 / 30

  /** Simula `seconds` de refresco y devuelve los fotogramas realmente pintados. */
  function simulate(refreshHz: number, seconds = 10): { painted: number, fps: number } {
    const step = 1000 / refreshHz
    let lastFrame = 0
    let painted = 0
    const total = Math.round((seconds * 1000) / step)
    for (let index = 0; index < total; index += 1) {
      const now = index * step
      const gate = advanceFrame(now, lastFrame, FRAME_MS)
      if (gate.due) {
        painted += 1
        lastFrame = gate.lastFrame
      }
    }
    return { painted, fps: painted / seconds }
  }

  it('mantiene ~30 FPS a 60 Hz', () => {
    const { fps } = simulate(60)
    expect(fps).toBeGreaterThanOrEqual(29)
    expect(fps).toBeLessThanOrEqual(31)
  })

  it('mantiene ~30 FPS a 75 Hz sin caer al cuantizar el intervalo', () => {
    const { fps } = simulate(75)
    expect(fps).toBeGreaterThanOrEqual(29)
    expect(fps).toBeLessThanOrEqual(31)
  })

  it('mantiene ~30 FPS a 90 Hz (donde el límite ingenuo da ~22)', () => {
    const { fps } = simulate(90)
    expect(fps).toBeGreaterThanOrEqual(29)
    expect(fps).toBeLessThanOrEqual(31)
  })

  it('mantiene ~30 FPS a 120 Hz', () => {
    const { fps } = simulate(120)
    expect(fps).toBeGreaterThanOrEqual(29)
    expect(fps).toBeLessThanOrEqual(31)
  })

  it('no pinta si no ha pasado el intervalo objetivo', () => {
    expect(advanceFrame(10, 0, FRAME_MS)).toEqual({ due: false, lastFrame: 0 })
  })

  it('se recupera tras una pausa larga sin ráfaga de fotogramas', () => {
    const gate = advanceFrame(10_000, 0, FRAME_MS)
    expect(gate.due).toBe(true)
    expect(gate.lastFrame).toBeGreaterThan(9_900)
    expect(gate.lastFrame).toBeLessThanOrEqual(10_000)
  })
})
