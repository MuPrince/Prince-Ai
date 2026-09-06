import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/utils/request', () => ({ default: { get: vi.fn(), put: vi.fn() } }))

import request from '@/utils/request'
import { useNoteStore } from '@/stores/note'

const get = request.get as ReturnType<typeof vi.fn>
const put = request.put as ReturnType<typeof vi.fn>

describe('note store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loads task note and summary', async () => {
    get.mockResolvedValueOnce({ id: 1, language: 'Python', title: 'LangChain' })
    get.mockResolvedValueOnce({ content: '# 笔记' })
    get.mockResolvedValueOnce({ status: 'success', content: '# 总结', error: null })
    const store = useNoteStore()
    await store.load(1)
    expect(store.content).toBe('# 笔记')
    expect(store.summary?.content).toBe('# 总结')
  })

  it('saves note', async () => {
    put.mockResolvedValue({ content: 'new' })
    const store = useNoteStore()
    store.taskId = 1
    store.content = 'new'
    await store.save()
    expect(put).toHaveBeenCalledWith('/tasks/1/note', { content: 'new' })
  })
})
