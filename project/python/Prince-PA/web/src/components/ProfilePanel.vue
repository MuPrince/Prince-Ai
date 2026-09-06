<script setup lang="ts">
import { useProfileStore } from '@/stores/profile'

const store = useProfileStore()

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

async function runExtract() {
  await store.extract()
  for (let i = 0; i < 10 && store.pending.length === 0; i += 1) {
    await sleep(1000)
    await store.fetch()
  }
}
</script>

<template>
  <el-dialog v-model="store.visible" title="用户画像/偏好" width="60%">
    <el-button @click="runExtract">立即提炼</el-button>
    <el-divider>待确认偏好</el-divider>
    <el-empty v-if="store.pending.length === 0" description="暂无待确认项" />
    <el-card v-for="item in store.pending" :key="item.id" class="pending-item">
      <p>{{ item.dimension }}：{{ item.value }}</p>
      <el-text type="info">{{ item.evidence }}</el-text>
      <div>
        <el-button type="primary" @click="store.confirm(item.id)">确认</el-button>
        <el-button @click="store.dismiss(item.id)">忽略</el-button>
      </div>
    </el-card>
    <el-divider>当前画像</el-divider>
    <pre>{{ store.profile }}</pre>
  </el-dialog>
</template>

<style scoped>
.pending-item {
  margin-bottom: 12px;
}
</style>
