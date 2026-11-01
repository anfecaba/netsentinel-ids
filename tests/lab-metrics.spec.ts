import { describe, expect, it } from 'vitest'
import { calculateLatencyMs, FpsMeter } from '../utils/labMetrics'

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
