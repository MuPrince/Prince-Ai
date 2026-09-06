<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import TaskDetailDrawer from '@/components/TaskDetailDrawer.vue'
import TaskCard from '@/components/TaskCard.vue'
import TaskFilter from '@/components/TaskFilter.vue'
import TaskFormDialog from '@/components/TaskFormDialog.vue'
import { useTaskStore } from '@/stores/task'
import type { Task } from '@/types'

const store = useTaskStore()
const router = useRouter()
const showForm = ref(false)
const selectedTask = ref<Task | null>(null)
onMounted(() => store.init())

function openNote(id: number) {
  router.push(`/tasks/${id}/note`)
}
</script>

<template>
  <div class="board-layout">
    <aside class="left-filter">
      <TaskFilter />
    </aside>
    <main class="center">
      <header class="board-header">
        <h2>学习任务</h2>
        <el-button type="primary" @click="showForm = true">新增任务</el-button>
      </header>
      <div class="task-grid">
        <TaskCard
          v-for="task in store.tasks"
          :key="task.id"
          :task="task"
          @start="store.startTask(task.id)"
          @complete="store.completeTask(task.id)"
          @detail="selectedTask = $event"
        />
      </div>
      <el-empty v-if="store.tasks.length === 0" description="暂无任务" />
    </main>
    <TaskFormDialog v-model="showForm" />
    <TaskDetailDrawer
      :task="selectedTask"
      @close="selectedTask = null"
      @open-note="openNote"
    />
  </div>
</template>

<style scoped>
.board-layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  height: 100vh;
}
.left-filter {
  padding: 16px;
  border-right: 1px solid #e5e7eb;
  overflow-y: auto;
}
.center {
  padding: 16px 24px;
  overflow-y: auto;
}
.board-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.task-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
</style>
