import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/utils/request', () => ({ default: { get: vi.fn(), post: vi.fn() } }))

import request from '@/utils/request'
import { useProfileStore } from '@/stores/profile'

const get = request.get as ReturnType<typeof vi.fn>
const post = request.post as ReturnType<typeof vi.fn>

describe('profile store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetches and confirms preference', async () => {
    get.mockResolvedValue({
      profile: {},
      pending: [{ id: 1, dimension: 'summary_style', value: '详细' }]
    })
    post.mockResolvedValue({
      id: 1,
      dimension: 'summary_style',
      value: '详细',
      status: 'confirmed'
    })
    const store = useProfileStore()
    await store.fetch()
    expect(store.pending.length).toBe(1)
    await store.confirm(1)
    expect(post).toHaveBeenCalledWith('/profile/preferences/1/confirm')
    expect(store.pending.length).toBe(0)
  })
})
