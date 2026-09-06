<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useTaskStore } from '@/stores/task'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: boolean): void }>()
const store = useTaskStore()
const visible = ref(props.modelValue)
const form = reactive({ language: '', title: '', description: '' })

watch(
  () => props.modelValue,
  (value) => {
    visible.value = value
    if (value) {
      form.language = store.languages[0]?.name || ''
    }
  }
)
watch(visible, (value) => emit('update:modelValue', value))

async function submit() {
  if (!form.title.trim()) {
    ElMessage.warning('请输入任务标题')
    return
  }
  await store.createTask({ ...form })
  visible.value = false
  form.title = ''
  form.description = ''
}
</script>

<template>
  <el-dialog v-model="visible" title="新增学习任务" width="500px">
    <el-form label-width="80px">
      <el-form-item label="语言">
        <el-select
          v-model="form.language"
          filterable
          allow-create
          default-first-option
          placeholder="选择或输入语言"
          style="width: 100%"
        >
          <el-option
            v-for="lang in store.languages"
            :key="lang.id"
            :label="lang.name"
            :value="lang.name"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="主题">
        <el-input v-model="form.title" placeholder="例如：LangChain 工具调用" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="form.description" type="textarea" :rows="3" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="submit">新增</el-button>
    </template>
  </el-dialog>
</template>
