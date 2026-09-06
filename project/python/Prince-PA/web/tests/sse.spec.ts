import { describe, expect, it } from 'vitest'
import { parseSseBlock } from '@/utils/sse'

describe('parseSseBlock', () => {
  it('parses data json event', () => {
    const event = parseSseBlock('data: {"type":"token","content":"你好"}\n\n')
    expect(event?.type).toBe('token')
    expect(event?.content).toBe('你好')
  })
})
