<script setup lang="ts">
import { useTaskStore } from '@/stores/task'

const store = useTaskStore()
</script>

<template>
  <div class="filter-panel">
    <el-input
      v-model="store.filter.keyword"
      clearable
      placeholder="搜索任务"
      @change="store.fetchTasks"
    />
    <el-divider>语言</el-divider>
    <el-radio-group v-model="store.filter.language" class="filter-group" @change="store.fetchTasks">
      <el-radio-button value="">全部</el-radio-button>
      <el-radio-button v-for="lang in store.languages" :key="lang.id" :value="lang.name">
        {{ lang.name }}
      </el-radio-button>
    </el-radio-group>
    <el-divider>状态</el-divider>
    <el-radio-group v-model="store.filter.status" class="filter-group" @change="store.fetchTasks">
      <el-radio-button value="">全部</el-radio-button>
      <el-radio-button value="todo">待学习</el-radio-button>
      <el-radio-button value="in_progress">学习中</el-radio-button>
      <el-radio-button value="completed">已完成</el-radio-button>
    </el-radio-group>
  </div>
</template>

<style scoped>
.filter-group {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}
</style>
