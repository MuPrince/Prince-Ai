import { defineStore } from 'pinia'

import request from '@/utils/request'
import { parseSseBlock } from '@/utils/sse'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}
export interface ChatSession {
  id: number
  title: string
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    sessions: [] as ChatSession[],
    activeSessionId: 0,
    messages: [] as ChatMessage[],
    streaming: false
  }),
  actions: {
    async init() {
      this.sessions = (await request.get<ChatSession[]>('/chat/sessions')) as ChatSession[]
      if (this.sessions.length === 0) await this.newSession()
      else await this.select(this.sessions[0].id)
    },
    async newSession() {
      const session = (await request.post<ChatSession>('/chat/sessions')) as ChatSession
      this.sessions.unshift(session)
      await this.select(session.id)
    },
    async select(sessionId: number) {
      this.activeSessionId = sessionId
      const rows = (await request.get<Array<{ role: string; content: string }>>(
        `/chat/sessions/${sessionId}/messages`
      )) as Array<{ role: string; content: string }>
      this.messages = rows.map((row) => ({
        role: row.role as ChatMessage['role'],
        content: row.content || ''
      }))
    },
    async send(content: string) {
      if (!this.activeSessionId || this.streaming) return
      this.streaming = true
      this.messages.push({ role: 'user', content })
      this.messages.push({ role: 'assistant', content: '' })
      const base = import.meta.env.VITE_API_BASE_URL || '/api'
      try {
        const response = await fetch(
          `${base}/chat/sessions/${this.activeSessionId}/messages`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
          }
        )
        const reader = response.body?.getReader()
        if (!reader) return
        const decoder = new TextDecoder()
        let buffer = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const blocks = buffer.split('\n\n')
          buffer = blocks.pop() || ''
          for (const block of blocks) {
            const event = parseSseBlock(block)
            if (!event) continue
            if (event.type === 'token') {
              const last = this.messages.at(-1)
              if (last?.role === 'assistant') last.content += event.content || ''
            } else if (event.type === 'error') {
              const last = this.messages.at(-1)
              if (last?.role === 'assistant') last.content = `（错误）${event.content || ''}`
            }
          }
        }
      } catch (error) {
        const last = this.messages.at(-1)
        if (last?.role === 'assistant') last.content = `（请求失败）${String(error)}`
      } finally {
        this.streaming = false
      }
    }
  }
})
