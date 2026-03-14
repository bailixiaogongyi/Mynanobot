/**
 * File upload component for AiMate Web UI
 */

const FileUploader = {
  template: `
    <div class="file-uploader">
        <div class="upload-area" 
             @click="triggerUpload"
             @dragover.prevent="onDragOver"
             @dragleave.prevent="onDragLeave"
             @drop.prevent="onDrop"
             :class="{ 'drag-over': isDragging }">
            <div class="upload-icon">📎</div>
            <p>点击或拖拽文件到此处上传</p>
            <p class="upload-hint">支持: 图片(jpg,png,gif), 文档(pdf,doc,docx,txt,md)</p>
        </div>
        
        <input type="file" 
               ref="fileInput" 
               @change="onFileSelect"
               multiple
               accept=".jpg,.jpeg,.png,.gif,.webp,.bmp,.pdf,.doc,.docx,.txt,.md,.csv,.xlsx,.xls"
               style="display: none">
        
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
    `,

  data() {
    return {
      uploading: false,
      uploadProgress: 0,
      uploadedFiles: [],
      isDragging: false,
    };
  },

  methods: {
    triggerUpload() {
      this.$refs.fileInput.click();
    },

    onDragOver() {
      this.isDragging = true;
    },

    onDragLeave() {
      this.isDragging = false;
    },

    onDrop(event) {
      this.isDragging = false;
      const files = event.dataTransfer.files;
      this.handleFiles(files);
    },

    onFileSelect(event) {
      const files = event.target.files;
      this.handleFiles(files);
      event.target.value = "";
    },

    async handleFiles(files) {
      for (const file of files) {
        await this.uploadFile(file);
      }
    },

    async uploadFile(file) {
      this.uploading = true;
      this.uploadProgress = 0;

      const formData = new FormData();
      formData.append("file", file);

      try {
        const xhr = new XMLHttpRequest();

        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            this.uploadProgress = Math.round((e.loaded / e.total) * 100);
          }
        };

        xhr.onload = () => {
          if (xhr.status === 200) {
            const response = JSON.parse(xhr.responseText);
            this.uploadedFiles.push(response);
            this.$emit("uploaded", response);
          } else {
            try {
              const error = JSON.parse(xhr.responseText);
              alert(`上传失败: ${error.detail}`);
            } catch {
              alert(`上传失败: ${xhr.statusText}`);
            }
          }
          this.uploading = false;
        };

        xhr.onerror = () => {
          alert("上传失败，请检查网络连接");
          this.uploading = false;
        };

        xhr.open("POST", "/api/upload/upload");
        xhr.send(formData);
      } catch (error) {
        console.error("Upload error:", error);
        alert(`上传失败: ${error.message}`);
        this.uploading = false;
      }
    },

    removeFile(file) {
      const index = this.uploadedFiles.findIndex(
        (f) => f.file_id === file.file_id,
      );
      if (index >= 0) {
        this.uploadedFiles.splice(index, 1);
        this.$emit("removed", file);
      }
    },

    formatSize(bytes) {
      if (bytes < 1024) return bytes + " B";
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
      return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    },

    getFilePaths() {
      return this.uploadedFiles.map((f) => f.path);
    },

    clearFiles() {
      this.uploadedFiles = [];
    },
  },
};

if (typeof window !== "undefined") {
  window.FileUploader = FileUploader;
}
