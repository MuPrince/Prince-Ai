<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElButton, ElDialog, ElInput } from 'element-plus'
import request from '@/utils/request'

interface UploadedFile {
  id: string
  name: string
  size: number
  uploadTime: Date
  url?: string
}

interface SplitDetail {
  id: string
  content: string
}

const files = ref<UploadedFile[]>([])
const isUploading = ref(false)
const showUploadDialog = ref(false)
const selectedFile = ref<File | null>(null)
const splitDetails = ref<SplitDetail[]>([])
const isConfirming = ref(false)
const isAddingKnowledge = ref(false)

const loadFileList = async () => {
  try {
    const response = await request.get('/rag/list')
    if (response.data && Array.isArray(response.data)) {
      files.value = response.data.map(item => ({
        id: "",
        name: item.name,
        size: 0,
        uploadTime: new Date()
      }))
    }
  } catch (error) {
    console.error('加载文件列表失败:', error)
  }
}

const openUploadDialog = () => {
  showUploadDialog.value = true
  selectedFile.value = null
  splitDetails.value = []
}

const closeUploadDialog = () => {
  showUploadDialog.value = false
  selectedFile.value = null
  splitDetails.value = []
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  selectedFile.value = target.files?.[0] || null
}

const handleConfirmUpload = async () => {
  if (!selectedFile.value) return

  isConfirming.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    const response = await request.put('/rag/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

    console.log(response.data)
    if (response.data && Array.isArray(response.data.splits)) {
      splitDetails.value = response.data.splits.map((item: any, index: number) => ({
        id: `split_${index}`,
        content: item.content || item.text || ''
      }))
    }
    // console.log(splitDetails.value)
  } catch (error) {
    console.error('上传失败:', error)
  } finally {
    isConfirming.value = false
  }
}

const handleConfirmAddKnowledge = async () => {
  isAddingKnowledge.value = true
  try {
    const details = splitDetails.value.map(item => item.content)
    await request.post('/rag/add', {
      filename: selectedFile.value?.name,
      splits: details
    })

    closeUploadDialog()
    loadFileList()
  } catch (error) {
    console.error('添加知识库失败:', error)
  } finally {
    isAddingKnowledge.value = false
  }
}

const deleteFile = async (id: string) => {
  try {
    await request.delete('/rag/delete', {
      params: { file_path: id }
    })
    files.value = files.value.filter(f => f.id !== id)
  } catch (error) {
    console.error('删除失败:', error)
  }
}

const formatSize = (bytes: number) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const updateSplitContent = (index: number, content: string) => {
  splitDetails.value[index].content = content
}

onMounted(() => {
  loadFileList()
})
</script>

<template>
  <div class="rag-panel">
    <div class="files-section">
      <div class="section-header">
        <span class="section-title">文件列表</span>
        <span class="file-count">{{ files.length }} 个文件</span>
      </div>
      <div class="files-list">
        <div v-if="files.length === 0" class="empty-state">
          <p>暂无上传文件</p>
          <p class="empty-hint">点击下方按钮添加知识库</p>
        </div>
        <div v-else class="files-container">
          <div
            v-for="file in files"
            :key="file.id"
            class="file-item"
          >
            <div class="file-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
              </svg>
            </div>
            <div class="file-info">
              <span class="file-name">{{ file.name }}</span>
              <span class="file-meta">{{ formatSize(file.size) }} · {{ file.uploadTime.toLocaleString() }}</span>
            </div>
            <ElButton
              type="text"
              size="small"
              class="delete-btn"
              @click="deleteFile(file.id)"
            >
              删除
            </ElButton>
          </div>
        </div>
      </div>
    </div>

    <div class="upload-section">
      <ElButton
        type="primary"
        size="small"
        @click="openUploadDialog"
      >
        添加知识库
      </ElButton>
    </div>

    <ElDialog
      title="添加知识库"
      v-model="showUploadDialog"
      :width="'80%'"
      class="upload-dialog"
      :style="{ height: '80vh' }"
      :show-close="true"
    >
      <div class="dialog-content">
        <div class="left-panel">
          <div class="config-section">
            <label class="config-label">选择文件</label>
            <input
              type="file"
              id="dialog-file-upload"
              class="dialog-file-input"
              accept=".pdf,.txt,.md,.doc,.docx"
              @change="handleFileSelect"
            />
            <label for="dialog-file-upload" class="file-select-label">
              <span v-if="selectedFile">{{ selectedFile.name }}</span>
              <span v-else>点击选择文件</span>
            </label>
          </div>
          
          <div class="config-spacer"></div>
          
          <div class="config-actions">
            <ElButton
              type="primary"
              :loading="isConfirming"
              :disabled="!selectedFile"
              @click="handleConfirmUpload"
            >
              {{ isConfirming ? '上传中...' : '确认上传' }}
            </ElButton>
          </div>
        </div>

        <div class="right-panel">
          <div class="details-header">
            <span class="details-title">文件切分详情</span>
          </div>
          <div class="details-content">
            <div v-if="splitDetails.length === 0" class="details-empty">
              <p>请先上传文件获取切分详情</p>
            </div>
            <div v-else class="details-list">
              <div
                v-for="(detail, index) in splitDetails"
                :key="detail.id"
                class="detail-item"
              >
                <span class="detail-index">{{ index + 1 }}.</span>
                <ElInput
                  type="textarea"
                  :model-value="detail.content"
                  @update:model-value="updateSplitContent(index, $event)"
                  class="detail-input"
                  :rows="3"
                  resize="none"
                />
              </div>
            </div>
          </div>
          <div class="details-actions">
            <ElButton
              type="primary"
              :loading="isAddingKnowledge"
              :disabled="splitDetails.length === 0"
              @click="handleConfirmAddKnowledge"
            >
              {{ isAddingKnowledge ? '添加中...' : '确认添加知识库' }}
            </ElButton>
          </div>
        </div>
      </div>
    </ElDialog>
  </div>
</template>

<style scoped>
.rag-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f8fafc;
}

.files-section {
  flex: 4;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: white;
  margin: 16px;
  margin-bottom: 8px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
  border-radius: 8px 8px 0 0;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.file-count {
  font-size: 12px;
  color: #64748b;
}

.files-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
}

.empty-hint {
  font-size: 12px;
  margin-top: 8px;
}

.files-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
  transition: background 0.2s ease;
}

.file-item:hover {
  background: #f1f5f9;
}

.file-icon {
  color: #6366f1;
}

.file-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  color: #334155;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta {
  font-size: 12px;
  color: #94a3b8;
}

.delete-btn {
  color: #ef4444;
}

.upload-section {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px 16px;
  margin: 8px 16px 16px 16px;
  background: white;
  border-radius: 8px;
  border: 1px dashed #cbd5e1;
}

.upload-dialog {
  .el-dialog__body {
    padding: 0;
    height: calc(100% - 60px);
  }
}

.dialog-content {
  display: flex;
  height: 100%;
}

.left-panel {
  width: 20%;
  display: flex;
  flex-direction: column;
  padding: 16px;
  border-right: 1px solid #e2e8f0;
}

.config-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-label {
  font-size: 14px;
  font-weight: 500;
  color: #334155;
}

.dialog-file-input {
  display: none;
}

.file-select-label {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  color: #64748b;
  transition: border-color 0.2s ease;
}

.file-select-label:hover {
  border-color: #6366f1;
}

.config-spacer {
  flex: 1;
}

.config-actions {
  display: flex;
  justify-content: flex-end;
}

.right-panel {
  width: 80%;
  display: flex;
  flex-direction: column;
}

.details-header {
  padding: 16px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}

.details-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.details-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.details-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
}

.details-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-item {
  display: flex;
  gap: 8px;
}

.detail-index {
  font-size: 14px;
  color: #64748b;
  font-weight: 500;
  flex-shrink: 0;
  margin-top: 8px;
}

.detail-input {
  flex: 1;
}

.details-actions {
  padding: 12px 16px;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
}
</style>
