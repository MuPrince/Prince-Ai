<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { Task } from '@/types'

const props = defineProps<{ task: Task }>()
const emit = defineEmits<{
  (e: 'start', task: Task): void
  (e: 'complete', task: Task): void
  (e: 'detail', task: Task): void
}>()

const router = useRouter()

const statusText = {
  todo: '待学习',
  in_progress: '学习中',
  completed: '已完成'
} as const
const statusType = {
  todo: 'info',
  in_progress: 'warning',
  completed: 'success'
} as const

function openNote() {
  router.push(`/tasks/${props.task.id}/note`)
}
</script>

<template>
  <el-card class="task-card" shadow="hover" @click="emit('detail', task)">
    <div class="card-header">
      <el-tag size="small">{{ task.language }}</el-tag>
      <el-tag :type="statusType[task.status]" size="small">{{ statusText[task.status] }}</el-tag>
    </div>
    <h3>{{ task.title }}</h3>
    <p class="desc">{{ task.description || '暂无描述' }}</p>
    <div class="actions" @click.stop>
      <el-button
        v-if="task.status !== 'completed'"
        size="small"
        @click="emit('start', task)"
      >
        {{ task.status === 'todo' ? '开始学习' : '继续学习' }}
      </el-button>
      <el-button
        v-if="task.status !== 'completed'"
        size="small"
        type="success"
        plain
        @click="emit('complete', task)"
      >
        完成
      </el-button>
      <el-button size="small" type="primary" plain @click="openNote">笔记</el-button>
      <el-button size="small" @click="emit('detail', task)">详情</el-button>
    </div>
  </el-card>
</template>

<style scoped>
.task-card {
  cursor: pointer;
}
.card-header {
  display: flex;
  gap: 6px;
  justify-content: space-between;
}
.desc {
  color: #6b7280;
  min-height: 38px;
}
.actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
</style>
