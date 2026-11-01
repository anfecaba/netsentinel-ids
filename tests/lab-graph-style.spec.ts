import { describe, expect, it } from 'vitest'
import { colorForRole, FALLBACK_COLOR, radiusForDegree, edgeColorFor } from '../utils/labGraphStyle'

describe('colorForRole', () => {
  it('usa el token esmeralda para el nodo local', () => {
    expect(colorForRole('local')).toBe('#34d399')
  })

  it('distingue gateway, dns y remote', () => {
    expect(colorForRole('gateway')).not.toBe(colorForRole('local'))
    expect(colorForRole('dns')).not.toBe(colorForRole('remote'))
  })

  it('cae al gris con roles desconocidos', () => {
    expect(colorForRole('desconocido')).toBe(FALLBACK_COLOR)
  })
})

describe('radiusForDegree', () => {
  it('mantiene un mínimo visible', () => {
    expect(radiusForDegree(0)).toBeGreaterThanOrEqual(6)
  })

  it('crece con el grado pero se mantiene acotado', () => {
    expect(radiusForDegree(50)).toBeLessThanOrEqual(22)
    expect(radiusForDegree(10)).toBeGreaterThan(radiusForDegree(1))
  })

  it('tolera valores inválidos', () => {
    expect(radiusForDegree(Number.NaN)).toBe(6)
    expect(radiusForDegree(-5)).toBe(6)
  })
})

describe('edgeColorFor', () => {
  it('prioriza el rojo cuando hay credencial', () => {
    expect(edgeColorFor('safe', true)).toBe(edgeColorFor('danger', true))
    expect(edgeColorFor('safe', true)).not.toBe(edgeColorFor('safe', false))
  })
})
