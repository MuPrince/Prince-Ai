<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useChatStore } from '@/stores/chat'

const store = useChatStore()
const input = ref('')

onMounted(() => store.init())

async function sendMessage() {
  const text = input.value.trim()
  if (!text) return
  input.value = ''
  await store.send(text)
}
</script>

<template>
  <section class="chat-panel">
    <header class="chat-header">
      <el-button text @click="store.newSession">＋ 新会话</el-button>
      <el-select
        :model-value="store.activeSessionId"
        size="small"
        style="flex: 1"
        @update:model-value="store.select"
      >
        <el-option
          v-for="s in store.sessions"
          :key="s.id"
          :value="s.id"
          :label="s.title"
        />
      </el-select>
    </header>
    <div class="messages">
      <div v-for="(m, index) in store.messages" :key="index" class="message" :class="m.role">
        <pre>{{ m.content }}</pre>
      </div>
    </div>
    <footer class="chat-input">
      <el-input
        v-model="input"
        type="textarea"
        :rows="2"
        placeholder="告诉学习助理你想做什么…"
        @keydown.enter.exact.prevent="sendMessage"
      />
      <el-button type="primary" :loading="store.streaming" @click="sendMessage">发送</el-button>
    </footer>
  </section>
</template>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100vh;
  border-left: 1px solid #e5e7eb;
  background: #fff;
}
.chat-header {
  padding: 12px;
  border-bottom: 1px solid #eee;
  display: flex;
  gap: 8px;
  align-items: center;
}
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}
.message {
  margin-bottom: 10px;
}
.message.user {
  text-align: right;
}
.message pre {
  white-space: pre-wrap;
  background: #f3f4f6;
  border-radius: 8px;
  padding: 8px;
  text-align: left;
}
.message.user pre {
  background: #3b82f6;
  color: #fff;
}
.chat-input {
  padding: 12px;
  border-top: 1px solid #eee;
}
</style>
