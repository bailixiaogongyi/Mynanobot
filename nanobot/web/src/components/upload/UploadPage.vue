<template>
  <div class="page-container upload-page">
    <div class="page-header">
      <h2>文件上传</h2>
    </div>

    <div class="upload-container">
      <div 
        class="upload-area" 
        @click="triggerUpload"
        @dragover.prevent="onDragOver"
        @dragleave.prevent="onDragLeave"
        @drop.prevent="onDrop"
        :class="{ 'drag-over': isDragging }"
      >
        <div class="upload-icon">📎</div>
        <p>点击或拖拽文件到此处上传</p>
        <p class="upload-hint">支持: 图片(jpg,png,gif), 文档(pdf,doc,docx,txt,md)</p>
      </div>
      
      <input 
        type="file" 
        ref="fileInput" 
        @change="onFileSelect"
        multiple
        accept=".jpg,.jpeg,.png,.gif,.webp,.bmp,.pdf,.doc,.docx,.txt,.md,.csv,.xlsx,.xls"
        style="display: none"
      >
      
      <div v-if="uploading" class="upload-progress">
        <div class="progress-bar">
          <div class="progress-fill" :style="{width: uploadProgress + '%'}"></div>
        </div>
        <span>上传中... {{ uploadProgress }}%</span>
      </div>
      
      <div v-if="uploadedFiles.length > 0" class="uploaded-files">
        <div v-for="file in uploadedFiles" :key="file.file_id" class="uploaded-file">
          <span class="file-icon">{{ file.file_type === 'image' ? '🖼️' : '📄' }}</span>
          <span class="file-name">{{ file.original_name }}</span>
          <span class="file-size">{{ formatSize(file.size) }}</span>
          <button class="remove-btn" @click="removeFile(file)">✕</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

interface UploadedFile {
  file_id: string;
  original_name: string;
  file_type: string;
  size: number;
  path: string;
}

const emit = defineEmits<{
  (e: 'uploaded', file: UploadedFile): void;
  (e: 'removed', file: UploadedFile): void;
}>();

const uploading = ref(false);
const uploadProgress = ref(0);
const uploadedFiles = ref<UploadedFile[]>([]);
const isDragging = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);

const triggerUpload = () => {
  fileInput.value?.click();
};

const onDragOver = () => {
  isDragging.value = true;
};

const onDragLeave = () => {
  isDragging.value = false;
};

const onDrop = (event: DragEvent) => {
  isDragging.value = false;
  const files = event.dataTransfer?.files;
  if (files) {
    handleFiles(files);
  }
};

const onFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement;
  const files = target.files;
  if (files) {
    handleFiles(files);
  }
  target.value = '';
};

const handleFiles = async (files: FileList) => {
  for (let i = 0; i < files.length; i++) {
    await uploadFile(files[i]);
  }
};

const uploadFile = (file: File) => {
  return new Promise<void>((resolve) => {
    uploading.value = true;
    uploadProgress.value = 0;

    const formData = new FormData();
    formData.append('file', file);

    const xhr = new XMLHttpRequest();

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        uploadProgress.value = Math.round((e.loaded / e.total) * 100);
      }
    };

    xhr.onload = () => {
      if (xhr.status === 200) {
        const response: UploadedFile = JSON.parse(xhr.responseText);
        uploadedFiles.value.push(response);
        emit('uploaded', response);
      } else {
        try {
          const error = JSON.parse(xhr.responseText);
          alert(`上传失败: ${error.detail}`);
        } catch {
          alert(`上传失败: ${xhr.statusText}`);
        }
      }
      uploading.value = false;
      resolve();
    };

    xhr.onerror = () => {
      alert('上传失败，请检查网络连接');
      uploading.value = false;
      resolve();
    };

    xhr.open('POST', '/api/upload/upload');
    xhr.send(formData);
  });
};

const removeFile = (file: UploadedFile) => {
  const index = uploadedFiles.value.findIndex((f) => f.file_id === file.file_id);
  if (index >= 0) {
    uploadedFiles.value.splice(index, 1);
    emit('removed', file);
  }
};

const formatSize = (bytes: number) => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
};

const getFilePaths = () => {
  return uploadedFiles.value.map((f) => f.path);
};

const clearFiles = () => {
  uploadedFiles.value = [];
};

defineExpose({
  getFilePaths,
  clearFiles,
  uploadedFiles
});
</script>

<style scoped lang="scss">
.upload-page {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
  
  h2 {
    margin: 0;
    font-size: 24px;
    font-weight: 600;
  }
}

.upload-container {
  max-width: 800px;
}

.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 40px;
  border: 2px dashed var(--color-border, #e2e8f0);
  border-radius: 12px;
  background: var(--color-bg-surface, #fff);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--color-primary, #3b82f6);
    background: var(--color-primary-light, #dbeafe);
  }

  &.drag-over {
    border-color: var(--color-primary, #3b82f6);
    background: var(--color-primary-light, #dbeafe);
  }

  .upload-icon {
    font-size: 48px;
    margin-bottom: 16px;
  }

  p {
    margin: 0;
    color: var(--color-text-primary, #1e293b);
  }

  .upload-hint {
    margin-top: 8px;
    font-size: 13px;
    color: var(--color-text-muted, #94a3b8);
  }
}

.upload-progress {
  margin-top: 20px;
  padding: 16px;
  background: var(--color-bg-surface, #fff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;

  .progress-bar {
    height: 8px;
    background: var(--color-bg-muted, #f1f5f9);
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 8px;

    .progress-fill {
      height: 100%;
      background: var(--color-primary, #3b82f6);
      transition: width 0.3s;
    }
  }

  span {
    font-size: 14px;
    color: var(--color-text-secondary, #64748b);
  }
}

.uploaded-files {
  margin-top: 20px;

  .uploaded-file {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    background: var(--color-bg-surface, #fff);
    border: 1px solid var(--color-border, #e2e8f0);
    border-radius: 8px;
    margin-bottom: 8px;

    .file-icon {
      font-size: 20px;
    }

    .file-name {
      flex: 1;
      font-weight: 500;
    }

    .file-size {
      color: var(--color-text-secondary, #64748b);
      font-size: 13px;
    }

    .remove-btn {
      background: none;
      border: none;
      cursor: pointer;
      font-size: 16px;
      color: var(--color-text-muted, #94a3b8);
      padding: 4px;
      
      &:hover {
        color: #ef4444;
      }
    }
  }
}
</style>
