<script setup lang="ts">
import { onMounted, ref } from 'vue'
import TaskCard from '@/components/TaskCard.vue'
import TaskFilter from '@/components/TaskFilter.vue'
import TaskFormDialog from '@/components/TaskFormDialog.vue'
import { useTaskStore } from '@/stores/task'

const store = useTaskStore()
const showForm = ref(false)
onMounted(() => store.init())
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
        />
      </div>
      <el-empty v-if="store.tasks.length === 0" description="暂无任务" />
    </main>
    <TaskFormDialog v-model="showForm" />
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
