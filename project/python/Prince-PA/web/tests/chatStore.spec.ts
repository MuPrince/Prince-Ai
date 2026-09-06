import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/utils/request', () => ({
  default: { get: vi.fn(), post: vi.fn() }
}))

import request from '@/utils/request'
import { useChatStore } from '@/stores/chat'

const get = request.get as ReturnType<typeof vi.fn>
const post = request.post as ReturnType<typeof vi.fn>

function streamResponse(...chunks: string[]) {
  return new Response(
    new ReadableStream({
      start(controller) {
        chunks.forEach((chunk) => controller.enqueue(new TextEncoder().encode(chunk)))
        controller.close()
      }
    })
  )
}

describe('chat store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.stubGlobal('fetch', vi.fn())
  })

  it('reads SSE and collects assistant text', async () => {
    get.mockResolvedValue([])
    post.mockResolvedValue({ id: 1 })
    const fetchMock = fetch as ReturnType<typeof vi.fn>
    fetchMock.mockResolvedValue(
      streamResponse(
        'data: {"type":"token","content":"已创建"}\n\n',
        'data: {"type":"done"}\n\n'
      )
    )

    const store = useChatStore()
    await store.init()
    await store.send('帮我加任务')
    expect(fetchMock).toHaveBeenCalled()
    expect(store.messages.at(-1)?.content).toContain('已创建')
  })
})
