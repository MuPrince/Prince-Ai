<script setup lang="ts">
import { ref } from 'vue'
import RagPanel from './RagPanel.vue'
import ChatPanel from './ChatPanel.vue'

interface Tab {
  id: string
  code: string
  name: string
}

const props = defineProps<{
  initialCode: string
}>()

const tabs = ref<Tab[]>([
  { id: 'rag', code: 'rag', name: 'RAG知识库' },
  { id: 'service', code: 'service', name: '智能客服' }
])

const activeTab = ref(props.initialCode)
const leftWidth = ref(60)
const isDragging = ref(false)

const closeTab = (id: string) => {
  const index = tabs.value.findIndex(t => t.id === id)
  if (index !== -1) {
    tabs.value.splice(index, 1)
    if (activeTab.value === id && tabs.value.length > 0) {
      activeTab.value = tabs.value[0].id
    }
  }
}

const startDrag = (e: MouseEvent) => {
  isDragging.value = true
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
}

const onDrag = (e: MouseEvent) => {
  if (!isDragging.value) return
  const container = document.querySelector('.tab-container') as HTMLElement
  if (!container) return
  const rect = container.getBoundingClientRect()
  const percentage = ((e.clientX - rect.left) / rect.width) * 100
  leftWidth.value = Math.max(30, Math.min(70, percentage))
}

const stopDrag = () => {
  isDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
}
</script>

<template>
  <div class="tab-container">
    <div class="tab-header">
      <div
        v-for="tab in tabs"
        :key="tab.id"
        :class="['tab-item', { active: activeTab === tab.id }]"
        @click="activeTab = tab.id"
      >
        <span>{{ tab.name }}</span>
        <span
          v-if="tabs.length > 1"
          class="close-btn"
          @click.stop="closeTab(tab.id)"
        >×</span>
      </div>
    </div>
    <div class="tab-content">
      <div class="left-panel" :style="{ width: leftWidth + '%' }">
        <RagPanel v-if="activeTab === 'rag'" />
        <div v-else class="empty-feature">
          <p>功能区域</p>
        </div>
      </div>
      <div
        class="drag-handle"
        :class="{ dragging: isDragging }"
        @mousedown="startDrag"
      >
        <span class="drag-line"></span>
      </div>
      <div class="right-panel" :style="{ width: (100 - leftWidth) + '%' }">
        <ChatPanel :feature-code="activeTab" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.tab-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.tab-header {
  display: flex;
  gap: 4px;
  padding: 8px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.tab-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  color: #64748b;
  transition: all 0.3s ease;
}

.tab-item.active {
  background: linear-gradient(135deg, #6366f1 0%, #3b82f6 100%);
  color: white;
}

.close-btn {
  margin-left: 4px;
  font-size: 16px;
  line-height: 1;
}

.tab-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.left-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.right-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.drag-handle {
  width: 8px;
  cursor: col-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f1f5f9;
  transition: background 0.3s ease;
}

.drag-handle:hover,
.drag-handle.dragging {
  background: #e2e8f0;
}

.drag-line {
  width: 2px;
  height: 40px;
  background: #cbd5e1;
  border-radius: 1px;
}

.empty-feature {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
  background: #f8fafc;
}
</style>
