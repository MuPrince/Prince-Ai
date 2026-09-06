import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/utils/request', () => ({ default: { get: vi.fn(), post: vi.fn() } }))

import request from '@/utils/request'
import { useRecordStore } from '@/stores/record'

const get = request.get as ReturnType<typeof vi.fn>
const post = request.post as ReturnType<typeof vi.fn>

describe('record store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetches records by task', async () => {
    get.mockResolvedValue([
      {
        id: 1,
        task_id: 1,
        record_type: 'auto',
        content: '',
        started_at: '2026-09-06T10:00:00Z'
      }
    ])
    const store = useRecordStore()
    await store.fetchByTask(1)
    expect(get).toHaveBeenCalledWith('/tasks/1/records')
    expect(store.records.length).toBe(1)
  })

  it('adds manual record', async () => {
    post.mockResolvedValue({
      id: 2,
      task_id: 1,
      record_type: 'manual',
      content: '心得',
      started_at: '2026-09-06T10:00:00Z'
    })
    const store = useRecordStore()
    await store.addManual(1, '2026-09-06T10:00:00Z', '心得')
    expect(post).toHaveBeenCalledWith('/tasks/1/records', expect.anything())
  })
})
