<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { itemApi } from '@/api'

const props = defineProps<{ itemId: number }>()
const emit = defineEmits<{ uploaded: [] }>()

const dragging = ref(false)
const uploading = ref(false)

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files[0]) uploadFile(input.files[0])
}

function onDrop(e: DragEvent) {
  dragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) uploadFile(file)
}

async function uploadFile(file: File) {
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    await itemApi.uploadImage(props.itemId, fd)
    ElMessage.success('图片上传成功')
    emit('uploaded')
  } finally {
    uploading.value = false
  }
}

async function onPaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      const blob = item.getAsFile()
      if (blob) {
        uploading.value = true
        try {
          await itemApi.pasteImage(props.itemId, blob)
          ElMessage.success('截图已粘贴上传')
          emit('uploaded')
        } finally {
          uploading.value = false
        }
      }
    }
  }
}
</script>

<template>
  <div
    class="image-upload"
    :class="{ dragging }"
    @dragover.prevent="dragging = true"
    @dragleave.prevent="dragging = false"
    @drop.prevent="onDrop"
    @paste="onPaste"
    tabindex="0"
  >
    <div v-if="uploading" class="upload-hint">上传中…</div>
    <div v-else class="upload-hint">
      <div class="icon">＋</div>
      <div>拖入图片 / Ctrl+V 粘贴截图</div>
      <div class="muted">支持 PNG / JPG，自动去重</div>
    </div>
    <input type="file" accept="image/*" style="display: none" @change="onFileChange" />
  </div>
</template>

<style scoped>
.image-upload {
  border: 2px dashed #d3d6db;
  border-radius: 10px;
  min-height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: #fafbfc;
  transition: all 0.2s;
}
.image-upload.dragging {
  border-color: #3b82f6;
  background: #eff6ff;
}
.upload-hint {
  text-align: center;
  color: #909399;
  font-size: 13px;
}
.upload-hint .icon {
  font-size: 36px;
  color: #c0c4cc;
  margin-bottom: 8px;
}
.upload-hint .muted {
  font-size: 12px;
  margin-top: 6px;
  color: #c0c4cc;
}
</style>
