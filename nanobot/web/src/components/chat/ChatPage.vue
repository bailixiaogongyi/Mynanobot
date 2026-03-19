<template>
  <div class="chat-page">
    <div class="chat-container">
      <div class="chat-header">
        <span class="chat-title">AI 助手</span>
        <button
          class="clear-btn"
          @click="handleClearSession"
          :disabled="chatStore.messageCount === 0"
          title="清空会话"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            width="16"
            height="16"
          >
            <polyline points="3 6 5 6 21 6"></polyline>
            <path
              d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"
            ></path>
          </svg>
          <span>清空</span>
        </button>
      </div>
      <div class="chat-messages" ref="messagesContainer">
        <div v-if="chatStore.messageCount === 0" class="chat-welcome">
          <div class="welcome-icon">
            <svg viewBox="0 0 24 24" fill="currentColor" width="48" height="48">
              <path
                d="M13.5 2c0 .44-.19.84-.5 1.12V5h5a3 3 0 0 1 3 3v10a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3V8a3 3 0 0 1 3-3h5V3.12A1.5 1.5 0 1 1 13.5 2zM0 10h2v6H0v-6zm24 0h-2v6h2v-6zM9 14.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zm6-1.5a1.5 1.5 0 1 0-3 0 1.5 1.5 0 0 0 3 0z"
              />
            </svg>
          </div>
          <h2 class="welcome-title">你好，我是 AI 助手</h2>
          <p class="welcome-desc">我可以帮助你回答问题、编写代码、分析数据等</p>
          <div class="welcome-suggestions">
            <button
              class="suggestion-btn"
              @click="useSuggestion('帮我写一个 Python 脚本')"
            >
              <span class="suggestion-icon">💻</span>
              <span>编写代码</span>
            </button>
            <button
              class="suggestion-btn"
              @click="useSuggestion('解释一下什么是机器学习')"
            >
              <span class="suggestion-icon">🧠</span>
              <span>解答问题</span>
            </button>
            <button
              class="suggestion-btn"
              @click="useSuggestion('帮我分析这段数据的趋势')"
            >
              <span class="suggestion-icon">📊</span>
              <span>数据分析</span>
            </button>
            <button
              class="suggestion-btn"
              @click="useSuggestion('帮我写一封工作邮件')"
            >
              <span class="suggestion-icon">✉️</span>
              <span>撰写文档</span>
            </button>
          </div>
        </div>

        <div
          v-for="msg in chatStore.messages"
          :key="msg.id"
          :class="['message-row', msg.role]"
        >
          <div class="message-inner">
            <div class="message-avatar" :class="msg.role">
              <template v-if="msg.role === 'user'">
                <svg
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  width="20"
                  height="20"
                >
                  <path
                    d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"
                  />
                </svg>
              </template>
              <template v-else>
                <svg
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  width="20"
                  height="20"
                >
                  <path
                    d="M13.5 2c0 .44-.19.84-.5 1.12V5h5a3 3 0 0 1 3 3v10a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3V8a3 3 0 0 1 3-3h5V3.12A1.5 1.5 0 1 1 13.5 2zM0 10h2v6H0v-6zm24 0h-2v6h2v-6zM9 14.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zm6-1.5a1.5 1.5 0 1 0-3 0 1.5 1.5 0 0 0 3 0z"
                  />
                </svg>
              </template>
            </div>
            <div class="message-body">
              <div class="message-header">
                <span class="message-sender">{{
                  msg.role === "user" ? "你" : "AI 助手"
                }}</span>
                <span v-if="msg.status" class="message-status">{{
                  msg.status === "thinking" ? "思考中..." : msg.status
                }}</span>
                <span class="message-time">{{
                  formatTime(msg.timestamp)
                }}</span>
              </div>

              <div v-if="msg.reasoning" class="message-reasoning">
                <details>
                  <summary>
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      width="16"
                      height="16"
                    >
                      <circle cx="12" cy="12" r="10" />
                      <path d="M12 16v-4M12 8h.01" />
                    </svg>
                    <span>思考过程</span>
                  </summary>
                  <div class="reasoning-content">{{ msg.reasoning }}</div>
                </details>
              </div>

              <div
                class="message-content"
                :class="{ streaming: msg.isStreaming, error: msg.isError }"
                v-html="renderMarkdown(msg.content)"
              ></div>

              <div
                v-if="msg.attachments && msg.attachments.length > 0"
                class="message-attachments"
              >
                <div
                  v-for="(attachment, index) in msg.attachments"
                  :key="index"
                  class="attachment-item"
                  :class="(attachment.file_type === 'image' || isImageFile(attachment.name)) ? 'image' : (attachment.file_type || 'file')"
                >
                  <template
                    v-if="
                      attachment.file_type === 'image' ||
                      isImageFile(attachment.name)
                    "
                  >
                    <img
                      :src="getAttachmentUrl(attachment)"
                      :alt="attachment.name"
                      class="attachment-image"
                    />
                  </template>
                  <template v-else>
                    <span class="attachment-icon">📄</span>
                    <span class="attachment-name">{{ attachment.name }}</span>
                  </template>
                </div>
              </div>

              <div
                v-if="msg.tool_calls && msg.tool_calls.length > 0"
                class="message-tool-calls"
              >
                <details>
                  <summary>
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      width="16"
                      height="16"
                    >
                      <path
                        d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"
                      />
                    </svg>
                    <span>工具调用 ({{ msg.tool_calls.length }})</span>
                  </summary>
                  <div class="tool-calls-list">
                    <div
                      v-for="(toolCall, index) in msg.tool_calls"
                      :key="index"
                      class="tool-call-item"
                    >
                      <div class="tool-call-name">🔧 {{ toolCall.name }}</div>
                      <div class="tool-call-args" v-if="toolCall.arguments">
                        {{ toolCall.arguments }}
                      </div>
                      <div class="tool-call-result" v-if="toolCall.result">
                        <details>
                          <summary>查看结果</summary>
                          <div class="tool-result-content">
                            {{ toolCall.result }}
                          </div>
                        </details>
                        <div
                          v-if="toolCall.file_info"
                          class="file-download-section"
                        >
                          <a
                            :href="
                              getFileDownloadUrl(toolCall.file_info.filename)
                            "
                            :download="toolCall.file_info.original_name"
                            class="file-download-btn"
                            target="_blank"
                          >
                            <svg
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              stroke-width="2"
                              width="16"
                              height="16"
                            >
                              <path
                                d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"
                              />
                              <polyline points="7 10 12 15 17 10" />
                              <line x1="12" y1="15" x2="12" y2="3" />
                            </svg>
                            下载 {{ toolCall.file_info.original_name }}
                          </a>
                        </div>
                        <div
                          v-if="
                            toolCall.generated_images &&
                            toolCall.generated_images.length > 0
                          "
                          class="generated-images-section"
                        >
                          <div class="generated-images-label">生成的图片：</div>
                          <div class="generated-images-grid">
                            <div
                              v-for="(
                                img, imgIndex
                              ) in toolCall.generated_images"
                              :key="imgIndex"
                              class="generated-image-item"
                            >
                              <img
                                :src="getGeneratedImageUrl(img.path)"
                                :alt="img.original_name"
                                class="generated-image"
                                @click="
                                  openImagePreview(
                                    getGeneratedImageUrl(img.path),
                                  )
                                "
                              />
                              <div class="generated-image-actions">
                                <a
                                  :href="getGeneratedImageUrl(img.path)"
                                  :download="img.original_name"
                                  class="download-link"
                                  title="下载原图"
                                >
                                  <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    stroke-width="2"
                                  >
                                    <path
                                      d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"
                                    />
                                    <polyline points="7 10 12 15 17 10" />
                                    <line x1="12" y1="15" x2="12" y2="3" />
                                  </svg>
                                  下载
                                </a>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </details>
              </div>

              <div
                v-if="msg.isStreaming && !msg.content"
                class="typing-indicator"
              >
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="chat-input-area">
        <div class="input-card">
          <div v-if="uploadedFiles.length > 0" class="uploaded-files-bar">
            <div
              v-for="(file, index) in uploadedFiles"
              :key="index"
              class="uploaded-file-tag"
            >
              <span class="file-icon">📎</span>
              <span class="file-name">{{ file.name }}</span>
              <button
                class="file-remove-btn"
                @click="removeUploadedFile(index)"
              >
                ×
              </button>
            </div>
          </div>
          <div class="input-upper">
            <textarea
              ref="textareaRef"
              v-model="inputMessage"
              :disabled="chatStore.isStreaming"
              placeholder="输入消息... (Shift + Enter 换行)"
              @keydown="handleKeydown"
              @input="autoResizeTextarea"
              rows="1"
            ></textarea>
          </div>
          <div class="input-lower">
            <div class="input-actions">
              <button
                class="action-btn attach-btn"
                @click="triggerFileUpload"
                title="上传文件"
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  width="18"
                  height="18"
                >
                  <path
                    d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"
                  />
                </svg>
              </button>
              <input
                ref="fileInputRef"
                type="file"
                multiple
                style="display: none"
                @change="handleFileSelect"
              />
            </div>
            <div class="input-actions-right">
              <span class="status-dot" :class="wsStatusClass"></span>
              <button
                class="action-btn send-btn"
                :disabled="chatStore.isStreaming || !inputMessage.trim()"
                @click="handleSend"
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  width="18"
                  height="18"
                >
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from "vue";
import { marked } from "marked";
import { useChatStore } from "@/stores/chat";
import { useUIStore } from "@/stores/ui";
import api from "@/services/api";

marked.setOptions({
  breaks: true,
  gfm: true,
});

const chatStore = useChatStore();
const uiStore = useUIStore();

const inputMessage = ref("");
const uploadedFiles = ref<{ name: string; path: string }[]>([]);
const messagesContainer = ref<HTMLElement | null>(null);
const textareaRef = ref<HTMLTextAreaElement | null>(null);
const fileInputRef = ref<HTMLInputElement | null>(null);

const wsStatusClass = computed(() => {
  switch (chatStore.wsStatus) {
    case "connected":
      return "connected";
    case "connecting":
    case "reconnecting":
      return "connecting";
    default:
      return "disconnected";
  }
});

const autoResizeTextarea = () => {
  if (textareaRef.value) {
    textareaRef.value.style.height = "auto";
    const newHeight = Math.min(textareaRef.value.scrollHeight, 200);
    textareaRef.value.style.height = newHeight + "px";
  }
};

const triggerFileUpload = () => {
  fileInputRef.value?.click();
};

const removeUploadedFile = (index: number) => {
  uploadedFiles.value.splice(index, 1);
};

const handleFileSelect = async (event: Event) => {
  const input = event.target as HTMLInputElement;
  const files = input.files;
  if (!files || files.length === 0) return;

  for (const file of files) {
    try {
      const result = await api.upload.upload(file);

      if (result) {
        uiStore.showToast(`文件 ${file.name} 上传成功`, "success");
        uploadedFiles.value.push({
          name: file.name,
          path: result.local_path || result.path || "",
        });
      }
    } catch (error) {
      console.error("Upload error:", error);
      uiStore.showToast(`文件 ${file.name} 上传失败`, "error");
    }
  }

  if (fileInputRef.value) {
    fileInputRef.value.value = "";
  }
};

const formatTime = (timestamp: number) => {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();

  if (diff < 60000) return "刚刚";
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`;

  return date.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  });
};

const useSuggestion = (text: string) => {
  inputMessage.value = text;
  textareaRef.value?.focus();
};

const renderMarkdown = (content: string | undefined | null) => {
  if (!content) return "";
  if (typeof content !== "string") return String(content);
  try {
    return marked.parse(content) as string;
  } catch (e) {
    console.error("Markdown parse error:", e);
    return content;
  }
};

const getFileDownloadUrl = (filename: string) => {
  const baseUrl = window.location.origin;
  return `${baseUrl}/api/upload/files/${filename}`;
};

const getGeneratedImageUrl = (filePath: string) => {
  const baseUrl = window.location.origin;
  const filename = filePath.split(/[/\\]/).pop() || filePath;
  return `${baseUrl}/api/upload/generated/${filename}`;
};

const isImageFile = (filename: string) => {
  if (!filename) return false;
  const ext = filename.toLowerCase().split(".").pop() || "";
  return ["jpg", "jpeg", "png", "gif", "webp", "bmp", "svg"].includes(ext);
};

const openImagePreview = (url: string) => {
  uiStore.openImagePreview(url);
};

const closeImagePreview = () => {
  uiStore.closeImagePreview();
};

const getAttachmentUrl = (attachment: any) => {
  if (attachment.url) return attachment.url;
  if (attachment.path) {
    const baseUrl = window.location.origin;
    const filename = attachment.path.split(/[/\\]/).pop() || attachment.path;
    return `${baseUrl}/api/upload/files/${filename}`;
  }
  return "";
};

const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    handleSend();
  }
};

const handleSend = async () => {
  if (!inputMessage.value.trim() && uploadedFiles.value.length === 0) return;
  if (chatStore.isStreaming) return;

  const attachments =
    uploadedFiles.value.length > 0 ? uploadedFiles.value : undefined;
  await chatStore.sendMessage(inputMessage.value, attachments);
  inputMessage.value = "";
  uploadedFiles.value = [];

  if (textareaRef.value) {
    textareaRef.value.style.height = "auto";
  }

  await nextTick();
  scrollToBottom();
};

const handleClearSession = async () => {
  if (chatStore.messageCount === 0) return;

  const confirmed = await uiStore.showConfirm(
    "确认清空",
    "确定要清空当前会话的所有消息吗？此操作不可撤销。",
  );
  if (!confirmed) return;

  await chatStore.clearHistory();
  uiStore.showToast("会话已清空", "success");
};

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTo({
      top: messagesContainer.value.scrollHeight,
      behavior: "smooth",
    });
  }
};

watch(
  () => chatStore.messages.length,
  (newLen, oldLen) => {
    if (newLen > (oldLen || 0)) {
      nextTick(() => scrollToBottom());
    }
  },
);

onMounted(async () => {
  await chatStore.loadHistory();
  await chatStore.loadConfig();
  chatStore.initWebSocket();
  scrollToBottom();
  nextTick(() => autoResizeTextarea());
});

onUnmounted(() => {
  chatStore.disconnectWebSocket();
});
</script>

<style scoped lang="scss">
.chat-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--color-bg-base);
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
  min-height: 0;
  padding: 0 1rem;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 0.5rem 0.75rem;
  border-bottom: 1px solid var(--color-border-light);
  background-color: var(--color-bg-surface);
  margin: 0 -1rem;
  padding-left: 1rem;
  padding-right: 1rem;
}

.chat-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-text-primary);
  display: flex;
  align-items: center;
  gap: 0.5rem;

  &::before {
    content: "";
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);
  }
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem 0;
  scroll-behavior: smooth;
  min-height: 0;
}

.chat-welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 2rem;
  text-align: center;
}

.welcome-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary) 0%, #8b5cf6 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1.5rem;
  color: white;
}

.welcome-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 0.5rem;
}

.welcome-desc {
  font-size: 0.9375rem;
  color: var(--color-text-secondary);
  margin: 0 0 2rem;
}

.welcome-suggestions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
  max-width: 400px;
  width: 100%;
}

.suggestion-btn {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  background-color: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-fast);
  text-align: left;

  &:hover {
    border-color: var(--color-primary);
    background-color: var(--color-primary-light);
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }

  .suggestion-icon {
    font-size: 1.25rem;
  }

  span:last-child {
    font-size: 0.875rem;
    color: var(--color-text-primary);
    font-weight: 500;
  }
}

.message-row {
  margin-bottom: 0.75rem;
  display: flex;

  &.user {
    justify-content: flex-end;

    .message-inner {
      flex-direction: row-reverse;
    }

    .message-body {
      align-items: flex-end;
    }

    .message-header {
      flex-direction: row-reverse;
    }

    .message-content {
      background-color: var(--color-primary);
      color: white;
      border-radius: var(--radius-lg) 4px var(--radius-lg) var(--radius-lg);

      :deep(code) {
        background-color: rgba(255, 255, 255, 0.2);
        color: white;
      }

      :deep(pre) {
        background-color: rgba(0, 0, 0, 0.2);

        code {
          background: none;
        }
      }
    }
  }

  &.assistant {
    .message-content {
      border-radius: 4px var(--radius-lg) var(--radius-lg) var(--radius-lg);
    }
  }
}

.message-inner {
  display: flex;
  gap: 1rem;
  max-width: 85%;

  &.user {
    flex-direction: row-reverse;
  }
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  &.user {
    background-color: var(--color-primary);
    color: white;
  }

  &:not(.user) {
    background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);
    color: white;
  }
}

.message-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.message-sender {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.message-time {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.message-status {
  font-size: 0.75rem;
  color: var(--color-primary);
  font-weight: 500;
}

.message-reasoning {
  margin-bottom: 0.5rem;

  details {
    background-color: var(--color-bg-muted);
    border-radius: var(--radius-md);
    overflow: hidden;
  }

  summary {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.625rem 0.875rem;
    cursor: pointer;
    font-size: 0.8125rem;
    color: var(--color-text-secondary);
    user-select: none;

    &:hover {
      background-color: var(--color-border-light);
    }

    svg {
      opacity: 0.6;
    }
  }

  .reasoning-content {
    padding: 0.75rem 0.875rem;
    font-size: 0.8125rem;
    color: var(--color-text-secondary);
    white-space: pre-wrap;
    border-top: 1px solid var(--color-border);
    line-height: 1.6;
  }
}

.message-tool-calls {
  margin-top: 0.5rem;

  details {
    background-color: var(--color-bg-muted);
    border-radius: var(--radius-md);
    overflow: hidden;
  }

  summary {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.625rem 0.875rem;
    cursor: pointer;
    font-size: 0.8125rem;
    color: var(--color-text-secondary);
    user-select: none;

    &:hover {
      background-color: var(--color-border-light);
    }

    svg {
      opacity: 0.6;
    }
  }

  .tool-calls-list {
    padding: 0.5rem;
    border-top: 1px solid var(--color-border);
  }

  .tool-call-item {
    padding: 0.5rem;
    margin-bottom: 0.5rem;
    background-color: var(--color-bg-surface);
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-border);

    &:last-child {
      margin-bottom: 0;
    }
  }

  .tool-call-name {
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--color-text-primary);
    margin-bottom: 0.25rem;
  }

  .tool-call-args {
    font-size: 0.75rem;
    color: var(--color-text-secondary);
    font-family: monospace;
    background-color: var(--color-bg-muted);
    padding: 0.25rem 0.5rem;
    border-radius: var(--radius-sm);
    margin-bottom: 0.25rem;
    word-break: break-all;
  }

  .tool-call-result {
    margin-top: 0.25rem;

    details {
      background: none;
      border: none;
    }

    summary {
      padding: 0.25rem 0.5rem;
      font-size: 0.75rem;
      color: var(--color-primary);
    }

    .tool-result-content {
      padding: 0.5rem;
      font-size: 0.75rem;
      color: var(--color-text-secondary);
      white-space: pre-wrap;
      word-break: break-all;
      max-height: 200px;
      overflow-y: auto;
    }
  }

  .file-download-section {
    margin-top: 0.5rem;
    padding-top: 0.5rem;
    border-top: 1px solid var(--color-border);

    .file-download-btn {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 0.75rem;
      background-color: var(--color-primary);
      color: white;
      border-radius: var(--radius-md);
      font-size: 0.8125rem;
      text-decoration: none;
      transition: background-color 0.2s;

      &:hover {
        background-color: var(--color-primary-hover, #2563eb);
      }

      svg {
        flex-shrink: 0;
      }
    }
  }

  .generated-images-section {
    margin-top: 0.75rem;
    padding-top: 0.75rem;
    border-top: 1px solid var(--color-border);

    .generated-images-label {
      font-size: 0.8125rem;
      color: var(--color-text-secondary);
      margin-bottom: 0.5rem;
    }

    .generated-images-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
      gap: 0.75rem;

      .generated-image-item {
        position: relative;
        border-radius: var(--radius-md);
        overflow: hidden;
        box-shadow: var(--shadow-sm);

        .generated-image {
          width: 100%;
          height: auto;
          display: block;
          transition: transform 0.2s;
          cursor: pointer;

          &:hover {
            transform: scale(1.02);
          }
        }

        .generated-image-actions {
          position: absolute;
          bottom: 0;
          left: 0;
          right: 0;
          padding: 0.5rem;
          background: linear-gradient(transparent, rgba(0, 0, 0, 0.7));
          display: flex;
          justify-content: flex-end;
          opacity: 0;
          transition: opacity 0.2s;

          .download-link {
            display: flex;
            align-items: center;
            gap: 0.25rem;
            color: white;
            font-size: 0.75rem;
            text-decoration: none;
            padding: 0.25rem 0.5rem;
            background-color: rgba(255, 255, 255, 0.2);
            border-radius: var(--radius-sm);
            transition: background-color 0.2s;

            &:hover {
              background-color: rgba(255, 255, 255, 0.3);
            }
          }
        }

        &:hover .generated-image-actions {
          opacity: 1;
        }
      }
    }
  }
}

.message-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--color-border-light);
}

.attachment-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.625rem;
  background-color: var(--color-bg-muted);
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
  color: var(--color-text-secondary);

  .attachment-icon {
    font-size: 1rem;
  }

  .attachment-name {
    max-width: 150px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &.image {
    padding: 0.25rem;
    background-color: transparent;

    .attachment-image {
      max-width: 280px;
      max-height: 200px;
      border-radius: var(--radius-sm);
      object-fit: contain;
      cursor: pointer;

      &:hover {
        opacity: 0.8;
      }
    }
  }
}

.message-content {
  padding: 0.875rem 1rem;
  border-radius: 4px var(--radius-lg) var(--radius-lg) var(--radius-lg);
  background-color: var(--color-bg-surface);
  font-size: 0.9375rem;
  line-height: 1.65;
  color: var(--color-text-primary);
  box-shadow: var(--shadow-sm);
  word-wrap: break-word;

  &.streaming {
    &::after {
      content: "▋";
      animation: blink 1s infinite;
      margin-left: 2px;
    }
  }

  &.error {
    border: 1px solid var(--color-error);
    background-color: var(--color-error-bg);
  }

  :deep(p) {
    margin: 0 0 0.75rem;

    &:last-child {
      margin-bottom: 0;
    }
  }

  :deep(ul),
  :deep(ol) {
    margin: 0 0 0.75rem;
    padding-left: 1.5rem;

    &:last-child {
      margin-bottom: 0;
    }
  }

  :deep(li) {
    margin-bottom: 0.25rem;
  }

  :deep(pre) {
    background-color: var(--color-code-bg);
    padding: 0.875rem;
    border-radius: var(--radius-md);
    overflow-x: auto;
    margin: 0.5rem 0;
    border: 1px solid var(--color-border);

    &:first-child {
      margin-top: 0;
    }

    &:last-child {
      margin-bottom: 0;
    }
  }

  :deep(pre + pre) {
    margin-top: 0.5rem;
  }

  :deep(pre + p) {
    margin-top: 0.5rem;
  }

  :deep(p + pre) {
    margin-top: 0.5rem;
  }

  :deep(code) {
    background-color: var(--color-code-bg);
    padding: 0.125rem 0.375rem;
    border-radius: var(--radius-sm);
    font-size: 0.8125em;
    font-family: "Consolas", "Monaco", "SF Mono", monospace;
  }

  :deep(pre code) {
    background: none;
    padding: 0;
    font-size: 0.8125rem;
  }

  :deep(blockquote) {
    margin: 0.75rem 0;
    padding: 0.625rem 0.875rem;
    border-left: 3px solid var(--color-primary);
    background-color: var(--color-bg-muted);
    border-radius: 0 var(--radius-md) var(--radius-md) 0;

    &:first-child {
      margin-top: 0;
    }

    &:last-child {
      margin-bottom: 0;
    }
  }

  :deep(table) {
    width: 100%;
    border-collapse: collapse;
    margin: 0.75rem 0;
    font-size: 0.875rem;

    th,
    td {
      padding: 0.5rem 0.75rem;
      border: 1px solid var(--color-border);
      text-align: left;
    }

    th {
      background-color: var(--color-bg-muted);
      font-weight: 600;
    }
  }

  :deep(h1),
  :deep(h2),
  :deep(h3),
  :deep(h4) {
    margin: 1rem 0 0.5rem;
    font-weight: 600;
    line-height: 1.4;

    &:first-child {
      margin-top: 0;
    }
  }

  :deep(h1) {
    font-size: 1.25rem;
  }
  :deep(h2) {
    font-size: 1.125rem;
  }
  :deep(h3) {
    font-size: 1rem;
  }
  :deep(h4) {
    font-size: 0.9375rem;
  }
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 0.5rem 0;

  span {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: var(--color-text-muted);
    animation: typing 1.4s infinite ease-in-out;

    &:nth-child(1) {
      animation-delay: 0s;
    }
    &:nth-child(2) {
      animation-delay: 0.2s;
    }
    &:nth-child(3) {
      animation-delay: 0.4s;
    }
  }
}

@keyframes typing {
  0%,
  60%,
  100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-4px);
    opacity: 1;
  }
}

@keyframes blink {
  0%,
  50% {
    opacity: 1;
  }
  51%,
  100% {
    opacity: 0;
  }
}

.chat-input-area {
  padding: 0.75rem 0 1rem;
  flex-shrink: 0;
  max-width: 100%;
}

.clear-btn {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.625rem;
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);

  svg {
    flex-shrink: 0;
  }

  &:hover:not(:disabled) {
    border-color: var(--color-error);
    color: var(--color-error);
    background-color: var(--color-error-light, rgba(239, 68, 68, 0.08));
  }

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
}

.input-card {
  max-width: 100%;
  background-color: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}

.input-upper {
  padding: 0.625rem 0.875rem 0;

  textarea {
    width: 100%;
    min-height: 24px;
    max-height: 200px;
    padding: 0;
    border: none;
    background: transparent;
    color: var(--color-text-primary);
    resize: none;
    overflow-y: auto;
    line-height: 1.5;
    font-size: 0.9375rem;

    &:focus {
      outline: none;
    }

    &::placeholder {
      color: var(--color-text-muted);
    }
  }
}

.input-lower {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.375rem 0.5rem 0.5rem;
  min-height: 36px;
}

.uploaded-files-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--color-border-light);
  background-color: var(--color-bg-muted);
}

.uploaded-file-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.5rem;
  background-color: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
  color: var(--color-text-secondary);

  .file-icon {
    font-size: 0.875rem;
  }

  .file-name {
    max-width: 150px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .file-remove-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    padding: 0;
    margin-left: 0.25rem;
    background: none;
    border: none;
    border-radius: 50%;
    font-size: 1rem;
    line-height: 1;
    color: var(--color-text-muted);
    cursor: pointer;

    &:hover {
      background-color: var(--color-border);
      color: var(--color-text-primary);
    }
  }
}

.input-actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.input-actions-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  border: none;
  cursor: pointer;
  transition: all var(--transition-fast);

  &.attach-btn {
    background-color: transparent;
    color: var(--color-text-secondary);

    &:hover {
      background-color: var(--color-bg-muted);
      color: var(--color-text-primary);
    }
  }

  &.send-btn {
    background-color: var(--color-primary);
    color: white;

    &:hover:not(:disabled) {
      background-color: var(--color-primary-hover);
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;

  &.connected {
    background-color: var(--color-success);
  }

  &.connecting {
    background-color: var(--color-warning);
    animation: pulse 1.5s infinite;
  }

  &.disconnected {
    background-color: var(--color-error);
  }
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@media (max-width: 640px) {
  .chat-messages {
    padding: 1rem;
  }

  .welcome-suggestions {
    grid-template-columns: 1fr;
  }

  .message-inner {
    max-width: 95%;
  }

  .chat-input-area {
    padding: 0.5rem;
  }

  .input-upper {
    padding: 0.5rem 0.75rem 0;
  }

  .input-lower {
    padding: 0.25rem 0.375rem 0.375rem;
  }

  .action-btn {
    width: 28px;
    height: 28px;
  }
}
</style>
