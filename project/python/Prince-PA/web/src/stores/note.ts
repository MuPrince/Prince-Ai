import { defineStore } from 'pinia'

import request from '@/utils/request'
import type { Task } from '@/types'

export const useNoteStore = defineStore('note', {
  state: () => ({
    taskId: 0,
    task: null as Task | null,
    content: '',
    dirty: false,
    summary: null as {
      status: string
      content: string | null
      error: string | null
    } | null
  }),
  actions: {
    async load(taskId: number) {
      this.taskId = taskId
      const [task, note, summary] = await Promise.all([
        request.get(`/tasks/${taskId}`),
        request.get(`/tasks/${taskId}/note`),
        request.get(`/tasks/${taskId}/summary`)
      ])
      this.task = task as Task
      this.content = (note as { content: string }).content
      this.summary = summary as typeof this.summary
      this.dirty = false
    },
    setContent(content: string) {
      this.content = content
      this.dirty = true
    },
    async save() {
      await request.put(`/tasks/${this.taskId}/note`, { content: this.content })
      this.dirty = false
    }
  }
})
