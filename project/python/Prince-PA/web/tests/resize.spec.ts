import { describe, expect, it } from 'vitest'
import { applyRatio } from '@/utils/resize'

describe('applyRatio', () => {
  it('clamps and converts ratio to percent', () => {
    expect(applyRatio(-1, 100, 0.2)).toBe(20)
    expect(applyRatio(0.5, 100, 0.2)).toBe(50)
    expect(applyRatio(2, 100, 0.2)).toBe(80)
  })
})
