<script setup lang="ts">
import { ref, nextTick, watch, onMounted } from 'vue'
import request from '@/utils/request'

interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
}

interface MessageGroup {
  date: string
  messages: Message[]
}

const props = defineProps<{
  featureCode: string
}>()

const messages = ref<Message[]>([])
const messageHistory = ref<MessageGroup[]>([])
const inputMessage = ref('')
const isLoading = ref(false)
const chatContainer = ref<HTMLElement | null>(null)
const showHistory = ref(false)

const scrollToBottom = async () => {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

const loadMessageHistory = async () => {
  try {
    const response = await request.get(`/${props.featureCode}/history`)
    if (response.data && Array.isArray(response.data)) {
      messageHistory.value = response.data.map((item: any) => ({
        date: item.date || new Date().toLocaleDateString(),
        messages: item.messages || []
      }))
    }
  } catch (error) {
    console.error('加载消息记录失败:', error)
  }
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isLoading.value) return

  const userMessage: Message = {
    id: Date.now().toString(),
    content: inputMessage.value,
    role: 'user',
    timestamp: new Date()
  }

  messages.value.push(userMessage)
  inputMessage.value = ''
  await scrollToBottom()

  isLoading.value = true
  try {
    const response = await request.post(`/${props.featureCode}/chat`, {
      message: userMessage.content
    })

    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      content: response.data?.message || response.message || '暂无回复',
      role: 'assistant',
      timestamp: new Date()
    }

    messages.value.push(assistantMessage)
    await scrollToBottom()
  } catch (error) {
    console.error('发送消息失败:', error)
  } finally {
    isLoading.value = false
  }
}

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

const toggleHistory = () => {
  showHistory.value = !showHistory.value
  if (showHistory.value) {
    loadMessageHistory()
  }
}

const formatTime = (date: Date) => {
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

watch(() => props.featureCode, () => {
  messages.value = []
})

onMounted(() => {
  loadMessageHistory()
})
</script>

<template>
  <div class="chat-container">
    <div class="chat-header">
      <span class="chat-title">AI 助手</span>
      <el-button
        :type="showHistory ? 'primary' : 'default'"
        size="small"
        @click="toggleHistory"
      >
        {{ showHistory ? '收起记录' : '消息记录' }}
      </el-button>
    </div>

    <div v-if="showHistory" class="history-panel">
      <div v-if="messageHistory.length === 0" class="empty-history">
        暂无消息记录
      </div>
      <div v-else class="history-list">
        <div v-for="group in messageHistory" :key="group.date" class="history-group">
          <div class="history-date">{{ group.date }}</div>
          <div
            v-for="msg in group.messages"
            :key="msg.id"
            class="history-item"
          >
            <span :class="['history-role', msg.role]">
              {{ msg.role === 'user' ? '我' : 'AI' }}
            </span>
            <span class="history-content">{{ msg.content }}</span>
            <span class="history-time">{{ formatTime(new Date(msg.timestamp)) }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-else ref="chatContainer" class="chat-messages">
      <div
        v-for="message in messages"
        :key="message.id"
        :class="['message-item', message.role]"
      >
        <div class="message-content">{{ message.content }}</div>
        <div class="message-time">{{ formatTime(message.timestamp) }}</div>
      </div>
      <div v-if="isLoading" class="loading-indicator">
        <span>思考中...</span>
      </div>
    </div>

    <div class="chat-input-area">
      <div class="input-wrapper">
        <el-input
          v-model="inputMessage"
          type="textarea"
          :rows="2"
          placeholder="输入消息..."
          @keydown="handleKeydown"
        />
      </div>
      <div class="input-actions">
        <el-button
          type="primary"
          size="small"
          :loading="isLoading"
          @click="sendMessage"
        >
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f8fafc;
  overflow: hidden;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: white;
  border-bottom: 1px solid #e2e8f0;
}

.chat-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.history-panel {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.empty-history {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.history-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-date {
  font-size: 12px;
  color: #94a3b8;
  padding-bottom: 8px;
  border-bottom: 1px solid #e2e8f0;
}

.history-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px;
  background: white;
  border-radius: 8px;
  font-size: 13px;
}

.history-role {
  font-weight: 600;
  min-width: 24px;
}

.history-role.user {
  color: #6366f1;
}

.history-role.assistant {
  color: #22c55e;
}

.history-content {
  flex: 1;
  color: #334155;
}

.history-time {
  font-size: 12px;
  color: #94a3b8;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message-item {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
}

.message-item.user {
  align-self: flex-end;
  background: linear-gradient(135deg, #6366f1 0%, #3b82f6 100%);
  color: white;
  border-bottom-right-radius: 4px;
}

.message-item.assistant {
  align-self: flex-start;
  background: white;
  border: 1px solid #e2e8f0;
  border-bottom-left-radius: 4px;
}

.message-content {
  font-size: 14px;
  line-height: 1.6;
}

.message-time {
  font-size: 12px;
  opacity: 0.7;
  margin-top: 4px;
  text-align: right;
}

.message-item.assistant .message-time {
  text-align: left;
}

.loading-indicator {
  display: flex;
  justify-content: center;
  padding: 12px;
  color: #64748b;
}

.chat-input-area {
  padding: 12px;
  background: white;
  border-top: 1px solid #e2e8f0;
}

.input-wrapper {
  margin-bottom: 8px;
}

.input-wrapper :deep(.el-textarea__inner) {
  border-radius: 8px;
  resize: none;
}

.input-actions {
  display: flex;
  justify-content: flex-end;
}
</style>
