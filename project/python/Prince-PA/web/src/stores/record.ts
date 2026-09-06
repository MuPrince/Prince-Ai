import { defineStore } from 'pinia'

import request from '@/utils/request'

export interface LearningRecord {
  id: number
  task_id: number
  record_type: 'auto' | 'manual'
  content: string
  started_at: string
  created_at: string
}

export const useRecordStore = defineStore('record', {
  state: () => ({ records: [] as LearningRecord[] }),
  actions: {
    async fetchByTask(taskId: number) {
      this.records = (await request.get(`/tasks/${taskId}/records`)) as LearningRecord[]
    },
    async addManual(taskId: number, startedAt: string, content: string) {
      const row = (await request.post(`/tasks/${taskId}/records`, {
        started_at: startedAt,
        content
      })) as LearningRecord
      this.records.unshift(row)
      return row
    }
  }
})
