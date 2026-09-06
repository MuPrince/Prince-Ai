import { defineStore } from 'pinia'

import request from '@/utils/request'

export interface Preference {
  id: number
  dimension: string
  value: string
  source: 'auto' | 'manual'
  status: 'pending' | 'confirmed' | 'dismissed'
  confidence: number
  evidence?: string | null
}

export const useProfileStore = defineStore('profile', {
  state: () => ({
    profile: {} as Record<string, { value: string }>,
    pending: [] as Preference[],
    visible: false
  }),
  actions: {
    async fetch() {
      const data = (await request.get<{
        profile: Record<string, { value: string }>
        pending: Preference[]
      }>('/profile')) as { profile: Record<string, { value: string }>; pending: Preference[] }
      this.profile = data.profile
      this.pending = data.pending
    },
    async extract() {
      await request.post('/profile/extract')
      await this.fetch()
    },
    async confirm(id: number) {
      const updated = (await request.post<Preference>(
        `/profile/preferences/${id}/confirm`
      )) as Preference
      this.pending = this.pending.filter((item) => item.id !== id)
      this.profile[updated.dimension] = { value: updated.value }
    },
    async dismiss(id: number) {
      await request.post(`/profile/preferences/${id}/dismiss`)
      this.pending = this.pending.filter((item) => item.id !== id)
    },
    async open() {
      this.visible = true
      await this.fetch()
    }
  }
})
