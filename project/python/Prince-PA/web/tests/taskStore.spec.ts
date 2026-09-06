import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/utils/request', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn()
  }
}))

import request from '@/utils/request'
import { useTaskStore } from '@/stores/task'

const get = request.get as ReturnType<typeof vi.fn>
const post = request.post as ReturnType<typeof vi.fn>

describe('task store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetch tasks and languages', async () => {
    get.mockResolvedValueOnce([{ id: 1, name: 'Python' }])
    get.mockResolvedValueOnce([
      { id: 10, language: 'Python', title: 'LangChain', status: 'todo' }
    ])
    const store = useTaskStore()
    await store.init()
    expect(store.languages.length).toBe(1)
    expect(store.tasks.length).toBe(1)
  })

  it('create task and complete', async () => {
    post.mockResolvedValueOnce({
      id: 1,
      language: 'Python',
      title: 'T',
      status: 'todo'
    })
    post.mockResolvedValueOnce({
      id: 1,
      language: 'Python',
      title: 'T',
      status: 'completed'
    })
    const store = useTaskStore()
    await store.createTask({ language: 'Python', title: 'T', description: '' })
    expect(post).toHaveBeenCalledWith('/tasks', expect.anything())
    await store.completeTask(1)
    expect(post).toHaveBeenCalledWith('/tasks/1/complete')
  })
})
