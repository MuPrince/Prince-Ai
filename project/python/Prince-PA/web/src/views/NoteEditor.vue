<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MdEditor, MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import { ElMessage } from 'element-plus'

import ResizableSplit from '@/components/ResizableSplit.vue'
import { useNoteStore } from '@/stores/note'

const route = useRoute()
const router = useRouter()
const noteStore = useNoteStore()
const taskId = Number(route.params.id)
const leftRatio = ref(50)
const saving = ref(false)

const contentModel = computed({
  get: () => noteStore.content,
  set: (value: string) => noteStore.setContent(value)
})
const summaryText = computed(() => noteStore.summary?.content || '总结尚未生成')

onMounted(async () => {
  await noteStore.load(taskId)
})

async function saveNote() {
  saving.value = true
  try {
    await noteStore.save()
    ElMessage.success('已保存')
  } finally {
    saving.value = false
  }
}

function onKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
    e.preventDefault()
    void saveNote()
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="editor-page">
    <aside class="task-info">
      <el-button text @click="router.push('/')">← 返回看板</el-button>
      <h2>{{ noteStore.task?.language }} / {{ noteStore.task?.title }}</h2>
      <p>{{ noteStore.task?.description || '暂无描述' }}</p>
      <el-divider>总结（Agent 生成）</el-divider>
      <MdPreview :model-value="summaryText" preview-theme="default" />
      <el-button type="primary" :loading="saving" :disabled="!noteStore.dirty" @click="saveNote">
        保存笔记
      </el-button>
    </aside>
    <ResizableSplit v-model:left-ratio="leftRatio" class="split">
      <template #left>
        <MdEditor
          v-model="contentModel"
          :preview="false"
          class="md-editor"
        />
      </template>
      <template #right>
        <div class="preview-pane">
          <MdPreview :model-value="noteStore.content" />
        </div>
      </template>
    </ResizableSplit>
  </div>
</template>

<style scoped>
.editor-page {
  display: flex;
  height: 100vh;
}
.task-info {
  width: 20%;
  min-width: 220px;
  border-right: 1px solid #ddd;
  padding: 16px;
  overflow-y: auto;
}
.split {
  flex: 1;
  display: flex;
  min-width: 0;
}
.md-editor {
  height: 100%;
}
.preview-pane {
  height: 100%;
  overflow-y: auto;
  padding: 0 12px;
  box-sizing: border-box;
}
</style>
