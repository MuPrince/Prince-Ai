<script setup lang="ts">
import { ref } from 'vue'

interface Feature {
  code: string
  name: string
  icon: string
}

const features: Feature[] = [
  { code: 'rag', name: 'RAG知识库', icon: 'Document' },
  { code: 'service', name: '智能客服', icon: 'ChatDotRound' }
]

const activeFeature = ref('rag')

const emit = defineEmits<{
  (e: 'select', code: string): void
}>()

const handleSelect = (code: string) => {
  activeFeature.value = code
  emit('select', code)
}
</script>

<template>
  <div class="feature-list">
    <div class="list-header">
      <span class="header-title">功能列表</span>
    </div>
    <el-menu
      :default-active="activeFeature"
      mode="vertical"
      class="feature-menu"
    >
      <el-menu-item
        v-for="feature in features"
        :key="feature.code"
        :index="feature.code"
        @click="handleSelect(feature.code)"
      >
        <span>{{ feature.name }}</span>
      </el-menu-item>
    </el-menu>
  </div>
</template>

<style scoped>
.feature-list {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #6366f1 0%, #3b82f6 100%);
  border-radius: 8px;
  padding: 16px;
  box-sizing: border-box;
}

.list-header {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.feature-menu {
  border: none;
  background: transparent;
}

.feature-menu :deep(.el-menu-item) {
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 8px;
  border-radius: 6px;
  transition: all 0.3s ease;
}

.feature-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.15);
}

.feature-menu :deep(.el-menu-item.is-active) {
  background: rgba(255, 255, 255, 0.25);
  color: white;
}
</style>
