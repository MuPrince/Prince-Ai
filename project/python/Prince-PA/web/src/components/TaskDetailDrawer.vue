<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import request from '@/utils/request'
import type { Task } from '@/types'
import { useRecordStore } from '@/stores/record'

const props = defineProps<{ task: Task | null }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'openNote', id: number): void
}>()

const recordStore = useRecordStore()
const visible = computed(() => props.task !== null)
const manualTime = ref(new Date().toISOString().slice(0, 16))
const manualContent = ref('')
const summary = ref<{
  status: string
  content: string | null
  error: string | null
} | null>(null)

watch(visible, async (show) => {
  if (show && props.task) {
    await recordStore.fetchByTask(props.task.id)
    summary.value = (await request.get(
      `/tasks/${props.task.id}/summary`
    )) as typeof summary.value
  }
})

async function submitManual() {
  if (!props.task) return
  await recordStore.addManual(
    props.task.id,
    new Date(manualTime.value).toISOString(),
    manualContent.value
  )
  manualContent.value = ''
  ElMessage.success('已登记学习记录')
}

async function regenerateSummary() {
  if (!props.task) return
  await request.post(`/tasks/${props.task.id}/summary/regenerate`)
  summary.value = (await request.get(
    `/tasks/${props.task.id}/summary`
  )) as typeof summary.value
}
</script>

<template>
  <el-drawer :model-value="visible" title="任务详情" size="45%" @close="emit('close')">
    <template v-if="task">
      <h2>{{ task.language }} / {{ task.title }}</h2>
      <p>{{ task.description || '暂无描述' }}</p>
      <el-space>
        <el-button type="primary" @click="emit('openNote', task.id)">打开笔记</el-button>
        <el-button v-if="summary?.status === 'failed'" @click="regenerateSummary">
          重新生成总结
        </el-button>
      </el-space>
      <el-divider>学习记录</el-divider>
      <el-timeline>
        <el-timeline-item
          v-for="row in recordStore.records"
          :key="row.id"
          :timestamp="row.started_at"
        >
          {{ row.record_type === 'auto' ? '自动' : '手动' }} ·
          {{ row.content || '开始学习' }}
        </el-timeline-item>
      </el-timeline>
      <el-form label-width="90px">
        <el-form-item label="开始时间">
          <el-date-picker v-model="manualTime" type="datetime" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="manualContent" type="textarea" />
        </el-form-item>
        <el-button type="primary" @click="submitManual">手动登记</el-button>
      </el-form>
      <el-divider>总结</el-divider>
      <el-alert
        v-if="summary?.status === 'failed'"
        :title="summary?.error || '总结生成失败'"
        type="error"
        :closable="false"
      />
      <el-text v-else-if="summary?.status === 'success'">
        总结已生成，可在笔记页查看
      </el-text>
      <el-text v-else>总结生成中…</el-text>
    </template>
  </el-drawer>
</template>
