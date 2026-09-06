import { defineStore } from 'pinia'

import request from '@/utils/request'
import type { Language, Task, TaskCreatePayload, TaskStatus } from '@/types'

interface TaskFilter {
  language: string
  status: TaskStatus | ''
  keyword: string
}

export const useTaskStore = defineStore('task', {
  state: () => ({
    languages: [] as Language[],
    tasks: [] as Task[],
    filter: { language: '', status: '', keyword: '' } as TaskFilter
  }),
  actions: {
    async fetchLanguages() {
      this.languages = (await request.get('/languages')) as Language[]
    },
    async fetchTasks() {
      const params: Record<string, string> = {}
      if (this.filter.language) params.language = this.filter.language
      if (this.filter.status) params.status = this.filter.status
      if (this.filter.keyword) params.keyword = this.filter.keyword
      this.tasks = (await request.get('/tasks', { params })) as Task[]
    },
    async init() {
      await Promise.all([this.fetchLanguages(), this.fetchTasks()])
    },
    async createTask(payload: TaskCreatePayload) {
      const created = (await request.post('/tasks', payload)) as Task
      this.tasks.unshift(created)
      return created
    },
    async updateTask(id: number, data: Partial<Task>) {
      const updated = (await request.patch(`/tasks/${id}`, data)) as Task
      const index = this.tasks.findIndex((t) => t.id === id)
      if (index >= 0) this.tasks[index] = updated
      return updated
    },
    async startTask(id: number) {
      const updated = (await request.post(`/tasks/${id}/start`)) as Task
      const index = this.tasks.findIndex((t) => t.id === id)
      if (index >= 0) this.tasks[index] = updated
      return updated
    },
    async completeTask(id: number) {
      const updated = (await request.post(`/tasks/${id}/complete`)) as Task
      const index = this.tasks.findIndex((t) => t.id === id)
      if (index >= 0) this.tasks[index] = updated
      return updated
    }
  }
})
