const ChatPage = {
  template: `
        <div class="page-container chat-page-single">
            <div class="content-area">
                <div class="chat-header">
                    <h2>AI助手</h2>
                    <button class="btn btn-sm btn-secondary" @click="clearHistory" :disabled="messages.length === 0" title="清空对话历史">🗑️ 清空</button>
                </div>
                <div class="chat-messages" ref="messagesContainer">
                    <div 
                        v-for="msg in messages" 
                        :key="msg.id"
                        :class="['message', msg.role, { thinking: msg.isStreaming, error: msg.isError }, msg.sender_id === 'agent' ? 'agent' : '']">
                        <div class="message-avatar" v-html="getMessageAvatar(msg)"></div>
                        <div class="message-wrapper">
                            <!-- 处理步骤时间线 -->
                            <div v-if="msg.steps && msg.steps.length > 0" class="process-timeline">
                                <div class="timeline-header">
                                    <span class="timeline-title">
                                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                                        处理过程
                                    </span>
                                    <span class="timeline-step-count">{{ msg.steps.length }} 个步骤</span>
                                </div>
                                <div class="timeline-steps">
                                    <div v-for="(step, index) in msg.steps" :key="index" class="timeline-step" :class="step.status">
                                        <div class="step-content">
                                            <div class="step-header">
                                                <span class="step-type" v-html="getStepTypeIcon(step.type)"></span>
                                                <span class="step-name">{{ step.name }}</span>
                                                <span :class="['step-status-badge', step.status]">{{ getStepStatusText(step.status) }}</span>
                                            </div>
                                            <div v-if="step.args && Object.keys(step.args).length > 0" class="step-args">
                                                <span class="args-label">输入:</span>
                                                <code class="args-preview">{{ formatArgs(step.args) }}</code>
                                            </div>
                                            <div v-if="step.result" class="step-result" :class="{expanded: step.resultExpanded}">
                                                <div class="result-header" @click="step.result.length > 200 && (step.resultExpanded = !step.resultExpanded)">
                                                    <span class="result-label">输出:</span>
                                                    <span class="result-length">{{ step.result.length }} 字符</span>
                                                    <span v-if="step.result.length > 200" class="result-toggle-icon">{{ step.resultExpanded ? '▲' : '▼' }}</span>
                                                </div>
                                                <div class="result-content" :class="{collapsed: !step.resultExpanded}">
                                                    <pre>{{ step.result }}</pre>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- 思考过程 -->
                            <div v-if="enableReasoning && msg.reasoning" class="message-reasoning">
                                <details open>
                                    <summary>💭 思考过程</summary>
                                    <div class="reasoning-content">{{ msg.reasoning }}</div>
                                </details>
                            </div>
                            
                            <!-- 附件展示 -->
                            <div v-if="msg.attachments && msg.attachments.length > 0" class="message-attachments">
                                <div v-for="att in msg.attachments" :key="att.file_id" class="attachment-item" :class="att.file_type">
                                    <div class="attachment-icon">{{ att.file_type === 'image' ? '🖼️' : '📄' }}</div>
                                    <div class="attachment-info">
                                        <span class="attachment-name">{{ att.original_name }}</span>
                                        <span class="attachment-hint">点击预览或下载</span>
                                    </div>
                                    <div class="attachment-actions">
                                        <button class="btn btn-sm btn-preview" @click="previewParsedFile(att)" title="预览">
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                                        </button>
                                        <a :href="getAttachmentUrl(att)" download class="btn btn-sm btn-download" title="下载">
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                                        </a>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- 文件下载展示 -->
                            <div v-if="msg.files && msg.files.length > 0" class="message-files">
                                <div v-for="file in msg.files" :key="file.file_id" class="file-download-item" :class="file.file_type">
                                    <div class="file-icon">{{ file.file_type === 'image' ? '🖼️' : '📄' }}</div>
                                    <div class="file-info">
                                        <span class="file-name">{{ file.original_name }}</span>
                                        <span class="file-hint">点击预览或下载</span>
                                    </div>
                                    <div class="file-actions">
                                        <button class="btn btn-sm btn-preview" @click="previewFile(file)" title="预览">
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                                        </button>
                                        <a :href="'/api/upload/files/' + file.filename" download class="btn btn-sm btn-download" title="下载">
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                                        </a>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- 消息内容 -->
                            <div class="message-content" v-if="shouldShowContent(msg)" v-html="renderMarkdown(cleanContent(msg.content))"></div>
                            
                            <!-- 消息底部 -->
                            <div class="message-footer">
                                <span class="message-time">{{ formatMessageTime(msg.timestamp) }}</span>
                                <span v-if="msg.isStreaming" class="streaming-indicator">● 正在输入...</span>
                                <button 
                                    v-if="msg.isError && msg.retryContent" 
                                    class="btn btn-sm btn-secondary retry-btn"
                                    @click="retryMessage(msg.retryContent)">
                                    🔄 重试
                                </button>
                            </div>
                        </div>
                    </div>
                    <div v-if="messages.length === 0" class="empty-state">
                        <div class="empty-icon">💬</div>
                        <p>开始对话吧</p>
                    </div>
                </div>
                <div class="chat-input-area">
                    <div v-if="uploadedFiles.length > 0" class="attachment-bar">
                        <div v-for="file in uploadedFiles" :key="file.file_id" class="attachment-chip">
                            <span class="chip-icon">{{ file.file_type === 'image' ? '🖼️' : '📄' }}</span>
                            <span class="chip-name">{{ file.original_name }}</span>
                            <button class="chip-remove" @click="removeUploadedFile(file)">✕</button>
                        </div>
                    </div>
                    <div class="chat-input">
                        <div class="input-container">
                            <textarea 
                                v-model="inputMessage" 
                                @keydown.enter.exact.prevent="sendMessage()"
                                @input="autoResizeTextarea"
                                ref="messageInput"
                                placeholder="输入消息... (Enter 发送)"
                                rows="1"></textarea>
                            <div class="input-actions">
                                <button class="btn btn-icon" @click="triggerFileUpload" title="上传文件/图片" :disabled="uploading">
                                    {{ uploading ? '⏳' : '📎' }}
                                </button>
                                <input type="file" 
                                       ref="fileInput" 
                                       @change="onFileSelect"
                                       multiple
                                       accept=".jpg,.jpeg,.png,.gif,.webp,.bmp,.pdf,.doc,.docx,.txt,.md,.csv,.xlsx,.xls,.pptx"
                                       style="display: none">
                                <button v-if="sending" class="btn btn-danger" @click="cancelGeneration()" title="停止生成">
                                    ⏹ 停止
                                </button>
                                <button v-else class="btn btn-primary" @click="sendMessage()" :disabled="sending">
                                    发送
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
  data() {
    return {
      currentSession: "default",
      messages: [],
      inputMessage: "",
      sending: false,
      streamConnection: null,
      currentStreamingMessage: null,
      textBuffer: "",
      reasoningBuffer: "",
      flushTimer: null,
      lastScrollTime: 0,
      typewriterQueue: "",
      typewriterTimer: null,
      typewriterSpeed: 20,
      enableReasoning: true,
      lastChunkTime: Date.now(),
      chunksPerSecond: 0,
      streamFinalized: false,
      uploadedFiles: [],
      uploading: false,
      currentStatus: "",
    };
  },
  mounted() {
    this.initChat();
  },
  activated() {
    if (!this.streamConnection || !this.streamConnection.isConnected()) {
      this.initStreamingConnection();
    }
    this.$nextTick(() => this.scrollToBottom());
  },
  beforeUnmount() {
    this.closeStreamingConnection();
    if (this.flushTimer) {
      clearTimeout(this.flushTimer);
    }
    if (this.typewriterTimer) {
      clearTimeout(this.typewriterTimer);
    }
  },
  methods: {
    getMessageAvatar(msg) {
      if (msg.role === "user")
        return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>';
      if (msg.sender_id === "agent")
        return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>';
      return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2z"/><circle cx="8" cy="14" r="2"/><circle cx="16" cy="14" r="2"/></svg>';
    },
    autoResizeTextarea() {
      const textarea = this.$refs.messageInput;
      if (!textarea) return;

      const minRows = 1;
      const maxRows = 10;
      const lineHeight = 20;

      textarea.style.height = "auto";
      let rows = Math.ceil(textarea.scrollHeight / lineHeight);
      rows = Math.max(minRows, Math.min(rows, maxRows));

      textarea.style.height = rows * lineHeight + "px";
    },
    async initChat() {
      await this.loadHistory();
      await this.loadChatConfig();
      this.initStreamingConnection();
    },
    async loadChatConfig() {
      try {
        const config = await API.config.get();
        this.enableReasoning = config.model?.enable_reasoning ?? true;
      } catch (e) {
        console.error("Failed to load chat config:", e);
      }
    },
    initStreamingConnection() {
      if (this.streamConnection && this.streamConnection.isConnected()) {
        console.log("WebSocket already connected, skipping init");
        return;
      }

      if (this.streamConnection && this.streamConnection.isConnecting()) {
        console.log("WebSocket already connecting, skipping init");
        return;
      }

      this.closeStreamingConnection();

      let reconnectAttempts = 0;
      const maxReconnectAttempts = 3;

      const doConnect = () => {
        this.streamConnection = API.chat.createStreamingConnection(
          this.currentSession,
          {
            onOpen: () => {
              console.log("WebSocket connected successfully");
              reconnectAttempts = 0;
            },
            onTextDelta: (content) => {
              this.appendToStreamingMessage(content);
            },
            onReasoningDelta: (content) => {
              this.appendToReasoningBlock(content);
            },
            onToolStart: (metadata) => {
              if (metadata && metadata.tool_name) {
                this.addToolStep(metadata.tool_name, metadata.tool_args);
              }
            },
            onToolResult: (content, metadata) => {
              if (metadata && metadata.tool_name) {
                this.updateToolStepResult(metadata.tool_name, content);
              }
            },
            onStatus: (status) => {
              this.currentStatus = status;
              this.updateCurrentStepStatus(status);
            },
            onDone: (content) => {
              console.log(
                "Stream done, content length:",
                content ? content.length : 0,
              );
              this.finalizeStreamingMessage(content);
              this.sending = false;
              this.currentStatus = "";
            },
            onError: (error) => {
              console.error("Stream error:", error);
              this.showError(error);
            },
            onNotification: (content, data) => {
              console.log("Received notification:", content);
              this.showNotification(content, data);
            },
            onConnectionError: (event) => {
              console.warn("WebSocket connection failed:", event);
            },
            onClose: (event) => {
              console.log("WebSocket closed:", event.code, event.reason);
              this.streamConnection = null;

              if (
                !this.sending &&
                reconnectAttempts < maxReconnectAttempts &&
                event.code !== 1005
              ) {
                reconnectAttempts++;
                console.log(
                  `Reconnecting... attempt ${reconnectAttempts}/${maxReconnectAttempts}`,
                );
                setTimeout(() => {
                  if (!this.sending && !this.streamConnection) {
                    doConnect();
                  }
                }, 2000);
              }
            },
          },
        );
      };

      doConnect();
    },
    async loadHistory() {
      try {
        const result = await API.chat.getHistory(this.currentSession);
        console.log("[loadHistory] Raw messages:", result.messages?.length);

        const rawMessages = result.messages || [];
        const processed = [];
        let i = 0;

        while (i < rawMessages.length) {
          const m = rawMessages[i];

          if (m.role === "user") {
            let content = m.content || "";
            let attachments = m.attachments || [];

            if (!attachments || attachments.length === 0) {
              const parsed = this.parseAttachmentsFromContent(content);
              if (parsed.attachments.length > 0) {
                attachments = parsed.attachments;
                content = parsed.cleanContent;
              }
            }

            processed.push({
              id: i,
              role: "user",
              content: content,
              timestamp: m.timestamp || new Date().toISOString(),
              tools: [],
              steps: [],
              reasoning: m.reasoning_content || "",
              attachments: attachments,
              files: m.files || [],
              isStreaming: false,
            });
            i++;
          } else if (m.role === "assistant") {
            const tools = [];
            const steps = [];
            let content = m.content || "";
            let reasoning = m.reasoning_content || "";
            let timestamp = m.timestamp || new Date().toISOString();
            const attachments = m.attachments || [];
            const files = [];

            if (
              m.tool_calls &&
              Array.isArray(m.tool_calls) &&
              m.tool_calls.length > 0
            ) {
              for (const tc of m.tool_calls) {
                const toolName = tc.function?.name || tc.name || "unknown";
                const toolArgs = tc.function?.arguments || tc.arguments || {};
                tools.push({
                  name: toolName,
                  status: "done",
                  result: "",
                });
                steps.push({
                  type: "tool",
                  name: toolName,
                  args:
                    typeof toolArgs === "string"
                      ? JSON.parse(toolArgs || "{}")
                      : toolArgs,
                  result: "",
                  status: "done",
                  resultExpanded: false,
                });
              }

              let j = i + 1;
              while (j < rawMessages.length) {
                const next = rawMessages[j];
                if (next.role === "tool") {
                  if (
                    next.content &&
                    next.content.startsWith("FILE_RETURNED:")
                  ) {
                    try {
                      const jsonStr = next.content.substring(
                        "FILE_RETURNED:".length,
                      );
                      const fileInfo = JSON.parse(jsonStr);
                      files.push(fileInfo);
                    } catch (e) {
                      console.error("Failed to parse FILE_RETURNED:", e);
                    }
                  }
                  j++;
                  continue;
                }
                if (next.role === "assistant") {
                  if (next.tool_calls && next.tool_calls.length > 0) {
                    for (const tc of next.tool_calls) {
                      const toolName =
                        tc.function?.name || tc.name || "unknown";
                      if (!tools.find((t) => t.name === toolName)) {
                        const toolArgs =
                          tc.function?.arguments || tc.arguments || {};
                        tools.push({
                          name: toolName,
                          status: "done",
                          result: "",
                        });
                        steps.push({
                          type: "tool",
                          name: toolName,
                          args:
                            typeof toolArgs === "string"
                              ? JSON.parse(toolArgs || "{}")
                              : toolArgs,
                          result: "",
                          status: "done",
                          resultExpanded: false,
                        });
                      }
                    }
                    j++;
                    continue;
                  }
                  if (next.content) {
                    content = next.content;
                  }
                  if (next.reasoning_content) {
                    reasoning = next.reasoning_content;
                  }
                  if (next.timestamp) {
                    timestamp = next.timestamp;
                  }
                  j++;
                  break;
                }
                break;
              }
              i = j;
            } else {
              if (m.content) {
                content = m.content;
              }
              if (m.reasoning_content) {
                reasoning = m.reasoning_content;
              }
              i++;
            }

            if (
              content ||
              tools.length > 0 ||
              steps.length > 0 ||
              files.length > 0
            ) {
              const msgData = {
                id: processed.length,
                role: "assistant",
                content: content,
                reasoning: reasoning,
                tools: tools,
                steps: steps,
                timestamp: timestamp,
                isStreaming: false,
                attachments: attachments,
                files: files,
              };

              processed.push(msgData);
            }
          } else if (m.role === "tool") {
            if (processed.length > 0) {
              const lastMsg = processed[processed.length - 1];
              const toolName = m.name || "";
              const toolResult = m.content || "";

              if (toolResult.startsWith("FILE_RETURNED:")) {
                try {
                  const jsonStr = toolResult.substring("FILE_RETURNED:".length);
                  const fileInfo = JSON.parse(jsonStr);
                  if (!lastMsg.files) {
                    lastMsg.files = [];
                  }
                  lastMsg.files.push(fileInfo);
                } catch (e) {
                  console.error(
                    "Failed to parse FILE_RETURNED:",
                    e,
                    toolResult,
                  );
                }
              }

              if (lastMsg.steps) {
                const step = lastMsg.steps.find(
                  (s) =>
                    s.name === toolName && s.status === "done" && !s.result,
                );
                if (step) {
                  step.result = toolResult;
                }
              }
              if (lastMsg.tools) {
                const tool = lastMsg.tools.find(
                  (t) => t.name === toolName && !t.result,
                );
                if (tool) {
                  tool.result = toolResult;
                }
              }
            }
            i++;
          } else {
            i++;
          }
        }

        this.messages = processed;
        console.log(
          "[loadHistory] Processed messages:",
          this.messages.length,
          "with",
          this.messages.filter((m) => m.tools.length > 0).length,
          "having tools",
        );
        this.$nextTick(() => this.scrollToBottom());
      } catch (e) {
        console.error("Failed to load history:", e);
        this.messages = [];
      }
    },
    async clearHistory() {
      this.$root.showConfirm(
        "清空对话",
        "确定清空当前会话的所有聊天记录?",
        async () => {
          try {
            await API.chat.clearHistory(this.currentSession);
            this.messages = [];
            this.$root.showToast("对话历史已清空");
          } catch (e) {
            this.$root.showToast("清空失败: " + e.message, "error");
          }
        },
      );
    },
    sendMessage(retryContent = null) {
      const content = retryContent || this.inputMessage.trim();
      const hasAttachments = this.uploadedFiles.length > 0;
      if ((!content && !hasAttachments) || this.sending) return;

      const attachments = [...this.uploadedFiles];

      if (!retryContent) {
        this.inputMessage = "";
        this.messages.push({
          id: Date.now(),
          role: "user",
          content: content,
          attachments: attachments,
          timestamp: new Date().toISOString(),
        });
        this.uploadedFiles = [];
        this.$nextTick(() => {
          this.autoResizeTextarea();
          this.scrollToBottom();
        });
      }

      this.sending = true;

      this.currentStreamingMessage = {
        id: Date.now() + 1,
        role: "assistant",
        content: "",
        reasoning: "",
        tools: [],
        timestamp: new Date().toISOString(),
        isStreaming: true,
      };
      this.messages.push(this.currentStreamingMessage);

      const sendViaWebSocket = () => {
        if (this.streamConnection && this.streamConnection.isConnected()) {
          console.log(
            "Sending via WebSocket, readyState:",
            this.streamConnection.getReadyState(),
          );
          const messageData = {
            content: content,
            attachments: attachments.map((f) => f.path),
          };
          this.streamConnection.send(JSON.stringify(messageData));
          return true;
        }
        return false;
      };

      if (sendViaWebSocket()) {
        return;
      }

      const maxWaitTime = 2000;
      const checkInterval = 50;
      let waited = 0;

      const waitForConnection = () => {
        waited += checkInterval;

        if (this.streamConnection && this.streamConnection.isConnected()) {
          console.log("WebSocket connected after", waited, "ms");
          const messageData = {
            content: content,
            attachments: attachments.map((f) => f.path),
          };
          this.streamConnection.send(JSON.stringify(messageData));
          return;
        }

        if (waited >= maxWaitTime) {
          console.log(
            "WebSocket connection timeout after",
            waited,
            "ms, falling back to HTTP",
          );
          this.fallbackToHttp(content, attachments);
          return;
        }

        if (this.streamConnection && this.streamConnection.isConnecting()) {
          setTimeout(waitForConnection, checkInterval);
        } else {
          console.log("WebSocket not connecting, reinitializing...");
          this.initStreamingConnection();
          setTimeout(waitForConnection, checkInterval);
        }
      };

      if (this.streamConnection && this.streamConnection.isConnecting()) {
        waitForConnection();
      } else {
        console.log("No WebSocket connection, initializing...");
        this.initStreamingConnection();
        setTimeout(waitForConnection, checkInterval);
      }
    },
    async fallbackToHttp(content, attachments = []) {
      console.log("Using HTTP fallback");
      try {
        const response = await API.chat.send(
          content,
          this.currentSession,
          attachments.map((f) => f.path),
        );
        if (this.currentStreamingMessage) {
          const idx = this.messages.findIndex(
            (m) => m.id === this.currentStreamingMessage.id,
          );
          if (idx > -1) {
            this.currentStreamingMessage.content = response.content;
            this.currentStreamingMessage.isStreaming = false;
            this.$set(this.messages, idx, { ...this.currentStreamingMessage });
          }
          this.currentStreamingMessage = null;
        }
        this.sending = false;
        this.$nextTick(() => this.scrollToBottom());
      } catch (e) {
        this.showError(e.message || "请求失败");
        this.sending = false;
      }
    },
    appendToStreamingMessage(content) {
      if (this.currentStreamingMessage) {
        this.currentStreamingMessage.content =
          (this.currentStreamingMessage.content || "") + content;
        this.$nextTick(() => this.scrollToBottom());
      }
    },
    appendToReasoningBlock(content) {
      if (this.currentStreamingMessage) {
        this.reasoningBuffer += content;
        this.scheduleFlush();
      }
    },
    startTypewriter() {
      if (this.typewriterTimer) return;
      this.runTypewriter();
    },
    runTypewriter() {
      if (!this.typewriterQueue || !this.currentStreamingMessage) {
        this.typewriterTimer = null;
        // Check if stream is finalized and queue is empty
        if (
          this.streamFinalized &&
          !this.typewriterQueue &&
          this.currentStreamingMessage
        ) {
          this.completeStreamingMessage();
        }
        return;
      }

      // Dynamic speed adjustment based on queue length
      const queueLength = this.typewriterQueue.length;
      let speed = this.typewriterSpeed;
      let charsToProcess = 1;

      if (queueLength > 100) {
        // Large backlog: process multiple chars at once, very fast
        speed = 5;
        charsToProcess = Math.min(5, queueLength);
      } else if (queueLength > 50) {
        // Medium backlog: process 3 chars at once
        speed = 10;
        charsToProcess = 3;
      } else if (queueLength > 20) {
        // Small backlog: process 2 chars at once
        speed = 15;
        charsToProcess = 2;
      }
      // else: normal speed, 1 char at a time

      // Extract characters to process
      const chars = this.typewriterQueue.substring(0, charsToProcess);
      this.typewriterQueue = this.typewriterQueue.slice(charsToProcess);

      // Add to message content
      this.currentStreamingMessage.content += chars;

      this.throttledScrollToBottom();

      if (this.typewriterQueue) {
        this.typewriterTimer = setTimeout(() => {
          this.runTypewriter();
        }, speed);
      } else {
        this.typewriterTimer = null;
        // Check if stream is finalized and queue is empty
        if (this.streamFinalized && this.currentStreamingMessage) {
          this.completeStreamingMessage();
        }
      }
    },
    stopTypewriter() {
      // Don't clear the timer - let it finish naturally
      // This prevents the "sudden burst" effect at the end
      // The typewriter will stop automatically when queue is empty
    },
    scheduleFlush() {
      if (this.flushTimer) return;
      this.flushTimer = setTimeout(() => {
        this.flushBuffers();
      }, 16);
    },
    flushBuffers() {
      this.flushTimer = null;
      if (this.currentStreamingMessage) {
        if (this.reasoningBuffer) {
          this.currentStreamingMessage.reasoning += this.reasoningBuffer;
          this.reasoningBuffer = "";
        }
      }
    },
    throttledScrollToBottom() {
      const now = Date.now();
      if (now - this.lastScrollTime > 50) {
        this.lastScrollTime = now;
        requestAnimationFrame(() => {
          const container = this.$refs.messagesContainer;
          if (container) {
            const isNearBottom =
              container.scrollHeight -
                container.scrollTop -
                container.clientHeight <
              150;
            if (isNearBottom) {
              container.scrollTop = container.scrollHeight;
            }
          }
        });
      }
    },
    showToolIndicator(toolName, toolArgs) {
      if (this.currentStreamingMessage) {
        this.currentStreamingMessage.tools.push({
          name: toolName,
          args: toolArgs,
          status: "running",
          result: "",
        });
      }
    },
    updateToolResult(toolName, result) {
      if (this.currentStreamingMessage) {
        const tool = this.currentStreamingMessage.tools.find(
          (t) => t.name === toolName && t.status === "running",
        );
        if (tool) {
          tool.status = "done";
          tool.result = result;
        }
      }
    },
    addToolStep(toolName, toolArgs) {
      if (!this.currentStreamingMessage) return;

      if (!this.currentStreamingMessage.steps) {
        this.currentStreamingMessage.steps = [];
      }

      this.currentStreamingMessage.steps.push({
        type: "tool",
        name: toolName,
        args: toolArgs || {},
        result: "",
        status: "running",
        resultExpanded: false,
      });

      this.$nextTick(() => this.scrollToBottom());
    },
    updateToolStepResult(toolName, result) {
      if (!this.currentStreamingMessage || !this.currentStreamingMessage.steps)
        return;

      const step = this.currentStreamingMessage.steps.find(
        (s) => s.name === toolName && s.status === "running",
      );
      if (step) {
        step.status = "done";

        if (result.startsWith("FILE_RETURNED:")) {
          try {
            const jsonStr = result.substring("FILE_RETURNED:".length);
            const fileInfo = JSON.parse(jsonStr);
            step.result = "";
            step.file = fileInfo;

            if (!this.currentStreamingMessage.files) {
              this.currentStreamingMessage.files = [];
            }
            this.currentStreamingMessage.files.push(fileInfo);
          } catch (e) {
            console.error(
              "Failed to parse FILE_RETURNED in streaming:",
              e,
              result,
            );
            step.result = result;
          }
        } else {
          step.result = result;
        }
      }

      this.$nextTick(() => this.scrollToBottom());
    },
    updateCurrentStepStatus(status) {
      if (!this.currentStreamingMessage || !this.currentStreamingMessage.steps)
        return;

      const runningStep = this.currentStreamingMessage.steps.find(
        (s) => s.status === "running",
      );
      if (runningStep) {
        return;
      }

      const lastDoneStep = [...this.currentStreamingMessage.steps]
        .reverse()
        .find((s) => s.status === "done");
      if (lastDoneStep) {
        lastDoneStep.status = "done";
      }
    },
    getStepTypeIcon(type) {
      const iconMap = {
        tool: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>',
        reasoning:
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
        text: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
        status:
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
      };
      return (
        iconMap[type] ||
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>'
      );
    },
    getStepStatusText(status) {
      const statusMap = {
        running: "执行中",
        done: "已完成",
        pending: "等待中",
        error: "失败",
      };
      return statusMap[status] || status;
    },
    formatArgs(args) {
      if (!args || typeof args !== "object") return JSON.stringify(args);
      try {
        const toolName = args.tool_name || "";
        let display = {};

        if (toolName.includes("web_search") || toolName.includes("search")) {
          display = { query: args.query, count: args.count || 10 };
        } else if (
          toolName.includes("write_file") ||
          toolName.includes("save")
        ) {
          const path = args.path || "";
          display = { file: path.split(/[/\\]/).pop() || path };
        } else if (
          toolName.includes("read_file") ||
          toolName.includes("load")
        ) {
          const path = args.path || "";
          display = { file: path.split(/[/\\]/).pop() || path };
        } else if (
          toolName.includes("python") ||
          toolName.includes("execute")
        ) {
          display = {
            code: args.code ? args.code.substring(0, 50) + "..." : "",
          };
        } else if (toolName.includes("browser")) {
          display = { action: args.action, url: args.url || "" };
        } else {
          const keys = Object.keys(args)
            .filter((k) => k !== "tool_name")
            .slice(0, 3);
          keys.forEach((k) => (display[k] = args[k]));
        }

        const str = JSON.stringify(display, null, 1);
        return str.length > 200 ? str.substring(0, 200) + "..." : str;
      } catch (e) {
        return String(args);
      }
    },
    previewFile(file) {
      const url = "/api/upload/files/" + file.filename;
      if (file.file_type === "image") {
        window.open(url, "_blank");
      } else {
        window.open(url, "_blank");
      }
    },
    getAttachmentUrl(att) {
      if (!att) return "#";
      if (att.filename) {
        return "/api/upload/files/" + att.filename.split(/[/\\]/).pop();
      }
      if (att.path) {
        const fileName = att.path.split(/[/\\]/).pop();
        return "/api/upload/files/" + fileName;
      }
      return "#";
    },
    previewParsedFile(att) {
      const url = this.getAttachmentUrl(att);
      window.open(url, "_blank");
    },
    updateStatusIndicator(status) {
      // 可以在这里更新状态指示器
    },
    finalizeStreamingMessage(content) {
      this.streamFinalized = true;

      if (this.flushTimer) {
        clearTimeout(this.flushTimer);
        this.flushTimer = null;
      }

      this.flushBuffers();

      if (this.currentStreamingMessage) {
        if (content && !this.currentStreamingMessage.content) {
          this.currentStreamingMessage.content = content;
        }
        this.completeStreamingMessage();
      }
    },
    completeStreamingMessage() {
      if (this.currentStreamingMessage) {
        this.currentStreamingMessage.isStreaming = false;
        this.currentStreamingMessage = null;
      }
      this.streamFinalized = false;
      this.sending = false;
      this.$nextTick(() => this.scrollToBottom());
    },
    showError(error) {
      console.error("Chat error:", error);
      let errorMsg = "未知错误";
      if (typeof error === "string") {
        errorMsg = error;
      } else if (error && error.message) {
        errorMsg = error.message;
      } else if (error && error.type) {
        errorMsg = "WebSocket 连接错误";
      }
      if (this.currentStreamingMessage) {
        this.currentStreamingMessage.content = "❌ " + errorMsg;
        this.currentStreamingMessage.isStreaming = false;
        this.currentStreamingMessage.isError = true;
        this.currentStreamingMessage = null;
      } else {
        this.messages.push({
          id: Date.now(),
          role: "assistant",
          content: "❌ " + errorMsg,
          timestamp: new Date().toISOString(),
          isError: true,
        });
      }
      this.sending = false;
      this.$nextTick(() => this.scrollToBottom());
    },
    showNotification(content, data) {
      const notificationMsg = {
        id: Date.now(),
        role: "assistant",
        content: content,
        timestamp: data.timestamp || new Date().toISOString(),
        tools: [],
        reasoning: "",
        isStreaming: false,
        isNotification: true,
      };
      this.messages.push(notificationMsg);
      this.$nextTick(() => this.scrollToBottom());
    },
    closeStreamingConnection() {
      if (this.flushTimer) {
        clearTimeout(this.flushTimer);
        this.flushTimer = null;
      }
      this.typewriterQueue = "";
      this.reasoningBuffer = "";

      if (this.streamConnection) {
        const conn = this.streamConnection;
        this.streamConnection = null;
        conn.close();
      }
    },
    retryMessage(content) {
      const errorIndex = this.messages.findIndex(
        (m) => m.retryContent === content,
      );
      if (errorIndex > -1) {
        this.messages.splice(errorIndex, 1);
      }
      this.sendMessage(content);
    },
    scrollToBottom() {
      const container = this.$refs.messagesContainer;
      if (container) {
        container.scrollTop = container.scrollHeight;
        setTimeout(() => {
          container.scrollTop = container.scrollHeight;
        }, 50);
      }
    },
    shouldShowContent(msg) {
      if (!msg.content) return false;
      if (msg.steps && msg.steps.length > 0) {
        const cleanContent = this.cleanContent(msg.content);
        if (!cleanContent || cleanContent.length < 10) {
          return false;
        }
        const looksLikeToolCall = /^\w+\s*\n\s*\{[\s\S]*\}$/.test(cleanContent);
        if (looksLikeToolCall) {
          return false;
        }
      }
      return true;
    },
    cleanContent(content) {
      if (!content) return "";
      return content
        .replace(/\n?\[Runtime Context\][\s\S]*$/g, "")
        .replace(/\n?\[附件: [^\]]+\]/g, "")
        .trim();
    },
    parseAttachmentsFromContent(content) {
      if (!content) return { attachments: [], cleanContent: content };

      const attachments = [];

      const newFileHintRegex =
        /\[已上传文件，请使用相应工具读取：\s*([\s\S]*?)\]/g;
      let match;
      while ((match = newFileHintRegex.exec(content)) !== null) {
        const hintContent = match[1];
        const lineRegex = /-\s*([^\(]+)\s*\(路径:\s*([^)]+)\)/g;
        let lineMatch;
        while ((lineMatch = lineRegex.exec(hintContent)) !== null) {
          const fileName = lineMatch[1].trim();
          const filePath = lineMatch[2].trim();
          const isImage = /\.(jpg|jpeg|png|gif|webp|bmp)$/i.test(fileName);

          attachments.push({
            file_id:
              "parsed_" +
              Date.now() +
              "_" +
              Math.random().toString(36).substr(2, 9),
            original_name: fileName,
            filename: filePath.split(/[/\\]/).pop() || filePath,
            file_type: isImage ? "image" : "document",
            path: filePath,
          });
        }
      }

      const attachmentRegex = /\[附件: ([^\]]+)\]/g;
      while ((match = attachmentRegex.exec(content)) !== null) {
        const filePath = match[1].trim();
        const fileName = filePath.split(/[/\\]/).pop() || filePath;
        const isImage = /\.(jpg|jpeg|png|gif|webp|bmp)$/i.test(fileName);

        attachments.push({
          file_id:
            "parsed_" +
            Date.now() +
            "_" +
            Math.random().toString(36).substr(2, 9),
          original_name: fileName,
          filename: filePath,
          file_type: isImage ? "image" : "document",
          path: filePath,
        });
      }

      const cleanContent = content
        .replace(/\[已上传文件，请使用相应工具读取：[\s\S]*?\]/g, "")
        .replace(/\[附件: [^\]]+\]/g, "")
        .replace(/\n{3,}/g, "\n\n")
        .trim();

      return {
        attachments: attachments,
        cleanContent: cleanContent,
      };
    },
    formatTime(isoString) {
      if (!isoString) return "";
      const date = new Date(isoString);
      const now = new Date();
      const diff = now - date;
      if (diff < 60000) return "刚刚";
      if (diff < 3600000) return Math.floor(diff / 60000) + "分钟前";
      if (diff < 86400000) return Math.floor(diff / 3600000) + "小时前";
      return date.toLocaleDateString();
    },
    formatMessageTime(isoString) {
      if (!isoString) return "";
      const date = new Date(isoString);
      const now = new Date();
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const msgDate = new Date(
        date.getFullYear(),
        date.getMonth(),
        date.getDate(),
      );

      let dateStr = "";
      if (msgDate.getTime() === today.getTime()) {
        dateStr = "今天";
      } else if (msgDate.getTime() === today.getTime() - 86400000) {
        dateStr = "昨天";
      } else {
        dateStr = date.toLocaleDateString("zh-CN", {
          month: "2-digit",
          day: "2-digit",
        });
      }

      const timeStr = date.toLocaleTimeString("zh-CN", {
        hour: "2-digit",
        minute: "2-digit",
      });

      return dateStr + " " + timeStr;
    },
    renderMarkdown(content) {
      if (!content) return "";
      if (typeof marked !== "undefined") {
        marked.setOptions({ breaks: true, gfm: true });
        return marked.parse(content);
      }
      return content.replace(/\n/g, "<br>");
    },
    triggerFileUpload() {
      this.$refs.fileInput.click();
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

      const formData = new FormData();
      formData.append("file", file);

      try {
        const response = await fetch("/api/upload/upload", {
          method: "POST",
          body: formData,
        });

        if (response.ok) {
          const result = await response.json();
          this.uploadedFiles.push(result);
          this.$root.showToast(`已上传: ${result.original_name}`);
        } else {
          const error = await response.json();
          this.$root.showToast(`上传失败: ${error.detail}`, "error");
        }
      } catch (error) {
        console.error("Upload error:", error);
        this.$root.showToast(`上传失败: ${error.message}`, "error");
      } finally {
        this.uploading = false;
      }
    },
    removeUploadedFile(file) {
      const index = this.uploadedFiles.findIndex(
        (f) => f.file_id === file.file_id,
      );
      if (index >= 0) {
        this.uploadedFiles.splice(index, 1);
      }
    },
    cancelGeneration() {
      if (this.streamConnection && this.streamConnection.isConnected()) {
        this.streamConnection.send(
          JSON.stringify({ type: "cancel", chat_id: this.currentSession }),
        );
        console.log("Cancel request sent for session:", this.currentSession);
      }
      if (this.currentStreamingMessage) {
        this.currentStreamingMessage.content += "\n\n⚠️ 生成已被用户中断";
        this.currentStreamingMessage.isStreaming = false;
        this.currentStreamingMessage = null;
      }
      this.sending = false;
      this.streamFinalized = false;
    },
  },
};

const NotesPage = {
  template: `
        <div class="page-container notes-page">
            <div :class="['sidebar', { collapsed: sidebarCollapsed }]">
                <div class="sidebar-header" v-if="!sidebarCollapsed">
                    <span class="sidebar-title">目录</span>
                    <button class="btn btn-sm btn-primary" @click="createNote">+ 新建</button>
                </div>
                <div class="sidebar-content" v-if="!sidebarCollapsed">
                    <div class="search-wrapper" style="padding: 0.5rem;">
                        <input class="input search-input" v-model="searchQuery" @keyup.enter="search" placeholder="搜索笔记...">
                        <button class="btn btn-sm btn-primary" @click="search" style="margin-top: 0.5rem; width: 100%;">搜索</button>
                    </div>
                    <div v-for="dir in directories" :key="dir">
                        <div :class="['list-item', { active: currentDir === dir }]" @click="loadDirectory(dir)">
                            <span class="list-item-icon">📁</span>
                            <span>{{ dir }}</span>
                        </div>
                    </div>
                </div>
                <button :class="['sidebar-toggle', { collapsed: sidebarCollapsed }]" @click="sidebarCollapsed = !sidebarCollapsed">
                    {{ sidebarCollapsed ? '📁' : '◀' }}
                </button>
            </div>
            <div class="content-area notes-content">
                <div :class="['notes-sidebar', { collapsed: filesCollapsed }]">
                    <div class="sidebar-header" v-if="!filesCollapsed">
                        <span class="sidebar-title">文件</span>
                        <button class="btn btn-sm btn-secondary" @click="indexNotes" :disabled="indexing">{{ indexing ? '索引中...' : '索引' }}</button>
                    </div>
                    <div class="sidebar-content" v-if="!filesCollapsed">
                        <div v-if="currentDirPath" class="breadcrumb" style="padding: 0.5rem; font-size: 0.75rem; color: var(--text-secondary); border-bottom: 1px solid var(--border-color);">
                            <span class="breadcrumb-link" @click="goToParentDir" style="cursor: pointer;">📁 ..</span>
                            <span> / {{ currentDirPath }}</span>
                        </div>
                        <div v-for="subDir in subDirectories" :key="subDir.path" :class="['list-item']" @click="loadSubDirectory(subDir.path)">
                            <span class="list-item-icon">📁</span>
                            <div class="list-item-content">
                                <div class="list-item-title">{{ subDir.name }}</div>
                            </div>
                        </div>
                        <div v-for="file in files" :key="file.path" :class="['list-item', { active: currentFile === file.path }]" @click="loadFile(file.path)">
                            <span class="list-item-icon">📄</span>
                            <div class="list-item-content">
                                <div class="list-item-title">{{ file.name }}</div>
                                <div class="list-item-subtitle">{{ formatSize(file.size) }}</div>
                            </div>
                        </div>
                        <div v-if="files.length === 0 && subDirectories.length === 0" class="empty-state"><p>暂无文件</p></div>
                    </div>
                    <button :class="['files-toggle', { collapsed: filesCollapsed }]" @click="filesCollapsed = !filesCollapsed">
                        {{ filesCollapsed ? '📄' : '◀' }}
                    </button>
                </div>
                <div class="notes-editor">
                    <div class="editor-toolbar" v-if="currentFile">
                        <span class="editor-filename">{{ currentFile }}</span>
                        <div class="editor-actions">
                            <button class="btn btn-sm btn-primary" @click="saveNote">保存</button>
                        </div>
                    </div>
                    <textarea v-model="editorContent" class="editor-textarea" placeholder="选择或创建笔记..." :disabled="!currentFile"></textarea>
                </div>
            </div>
            <div class="modal-overlay" v-if="showSearchResults" @click.self="showSearchResults = false">
                <div class="modal">
                    <div class="modal-header">
                        <h3 class="modal-title">搜索结果: {{ searchQuery }}</h3>
                        <button class="btn-icon" @click="showSearchResults = false">✕</button>
                    </div>
                    <div class="modal-body">
                        <div v-for="result in searchResults" :key="result.id" class="search-result-item" @click="openSearchResult(result)">
                            <div class="result-score">相关度: {{ (result.score * 100).toFixed(1) }}%</div>
                            <div class="result-content">{{ result.content.substring(0, 200) }}...</div>
                            <div class="result-source">{{ result.source }}</div>
                        </div>
                        <div v-if="searchResults.length === 0" class="empty-state"><p>未找到相关内容</p></div>
                    </div>
                </div>
            </div>
        </div>
    `,
  data() {
    return {
      directories: [],
      currentDir: null,
      currentDirPath: "",
      subDirectories: [],
      files: [],
      currentFile: null,
      editorContent: "",
      searchQuery: "",
      searchResults: [],
      showSearchResults: false,
      sidebarCollapsed: false,
      filesCollapsed: false,
      indexing: false,
    };
  },
  mounted() {
    this.loadDirectories();
  },
  methods: {
    async loadDirectories() {
      try {
        const result = await API.notes.dirs();
        this.directories = Array.isArray(result)
          ? result
          : result.directories || [];
        if (this.directories.length > 0) {
          this.loadDirectory(this.directories[0]);
        }
      } catch (e) {
        console.error("Failed to load directories:", e);
      }
    },
    async loadDirectory(dir) {
      this.currentDir = dir;
      this.currentDirPath = "";
      try {
        const result = await API.notes.list(dir);
        this.subDirectories = result.directories || [];
        this.files = result.files || [];
      } catch (e) {
        console.error("Failed to load files:", e);
        this.subDirectories = [];
        this.files = [];
      }
    },
    async loadSubDirectory(path) {
      this.currentDirPath = path;
      try {
        const result = await API.notes.list(path);
        this.subDirectories = result.directories || [];
        this.files = result.files || [];
      } catch (e) {
        console.error("Failed to load subdirectory:", e);
        this.subDirectories = [];
        this.files = [];
      }
    },
    goToParentDir() {
      if (this.currentDirPath) {
        const parts = this.currentDirPath.split("/");
        parts.pop();
        if (parts.length === 0) {
          this.loadDirectory(this.currentDir);
        } else {
          this.loadSubDirectory(parts.join("/"));
        }
      }
    },
    async loadFile(path) {
      this.currentFile = path;
      try {
        const result = await API.notes.read(path);
        this.editorContent = result.content || "";
      } catch (e) {
        console.error("Failed to load file:", e);
        this.editorContent = "";
      }
    },
    async saveNote() {
      if (!this.currentFile) return;
      try {
        await API.notes.save(this.currentFile, this.editorContent);
        this.$root.showToast("保存成功");
      } catch (e) {
        this.$root.showToast("保存失败: " + e.message, "error");
      }
    },
    async createNote() {
      const name = prompt("输入笔记名称:");
      if (!name) return;
      const basePath = this.currentDirPath || this.currentDir;
      const path = `${basePath}/${name}.md`;
      try {
        await API.notes.create(path);
        this.$root.showToast("创建成功");
        if (this.currentDirPath) {
          this.loadSubDirectory(this.currentDirPath);
        } else {
          this.loadDirectory(this.currentDir);
        }
        this.loadFile(path);
      } catch (e) {
        this.$root.showToast("创建失败: " + e.message, "error");
      }
    },
    async deleteCurrentNote() {
      if (!this.currentFile || !confirm("确定删除此笔记?")) return;
      try {
        await API.notes.delete(this.currentFile);
        this.$root.showToast("删除成功");
        this.currentFile = null;
        this.editorContent = "";
        if (this.currentDirPath) {
          this.loadSubDirectory(this.currentDirPath);
        } else {
          this.loadDirectory(this.currentDir);
        }
      } catch (e) {
        this.$root.showToast("删除失败: " + e.message, "error");
      }
    },
    async search() {
      if (!this.searchQuery.trim()) return;
      try {
        const result = await API.notes.search(this.searchQuery);
        this.searchResults = result.results || [];
        this.showSearchResults = true;
      } catch (e) {
        this.$root.showToast("搜索失败: " + e.message, "error");
      }
    },
    openSearchResult(result) {
      this.showSearchResults = false;
      this.loadFile(result.source);
    },
    async indexNotes() {
      if (!this.currentDir) {
        this.$root.showToast("请先选择一个目录", "info");
        return;
      }
      this.indexing = true;
      try {
        const result = await API.notes.index(this.currentDir, false);
        if (result.indexed > 0) {
          this.$root.showToast(
            `索引完成: 已索引 ${result.indexed} 个片段 from ${result.total_files} 个文件`,
            "success",
          );
        } else {
          this.$root.showToast("没有需要索引的新文件", "info");
        }
      } catch (e) {
        console.error("Index error:", e);
        this.$root.showToast(
          "索引失败: " + (e.message || e.detail || "未知错误"),
          "error",
        );
      } finally {
        this.indexing = false;
      }
    },
    formatSize(bytes) {
      if (!bytes) return "0 B";
      if (bytes < 1024) return bytes + " B";
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
      return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    },
  },
};

const SkillsPage = {
  template: `
        <div class="page-container">
            <div class="content-area" style="flex-direction: column;">
                <div class="page-header">
                    <h2>技能列表</h2>
                </div>
                <div class="skills-filter" style="padding: 0.5rem 1rem; display: flex; gap: 0.5rem; border-bottom: 1px solid var(--border-color);">
                    <button :class="['btn btn-sm', filterSource === 'all' ? 'btn-primary' : 'btn-secondary']" @click="filterSource = 'all'">全部</button>
                    <button :class="['btn btn-sm', filterSource === 'builtin' ? 'btn-primary' : 'btn-secondary']" @click="filterSource = 'builtin'">内置技能</button>
                    <button :class="['btn btn-sm', filterSource === 'workspace' ? 'btn-primary' : 'btn-secondary']" @click="filterSource = 'workspace'">自建技能</button>
                </div>
                <div class="skills-grid">
                    <div v-for="skill in filteredSkills" :key="skill.name + skill.source" class="skill-card" @click="showSkillDetail(skill)">
                        <div class="skill-header">
                            <span class="skill-icon">{{ getSkillIcon(skill.name) }}</span>
                            <div class="skill-info">
                                <h3 class="skill-name">{{ skill.name }}</h3>
                                <p class="skill-description">{{ skill.meta?.description || skill.description || '' }}</p>
                            </div>
                        </div>
                        <div class="skill-meta">
                            <span :class="['skill-badge', 'skill-type-' + skill.source]">
                                {{ skill.source === 'builtin' ? '内置' : '自建' }}
                            </span>
                            <span :class="['skill-badge', (skill.meta?.always || skill.always) ? 'always' : 'on-demand']">
                                {{ (skill.meta?.always || skill.always) ? '始终加载' : '按需加载' }}
                            </span>
                        </div>
                    </div>
                </div>
                <div v-if="filteredSkills.length === 0" class="empty-state">
                    <div class="empty-icon">🔧</div>
                    <p>暂无技能</p>
                </div>
            </div>
            <div class="modal-overlay" v-if="selectedSkill" @click.self="selectedSkill = null">
                <div class="modal modal-lg">
                    <div class="modal-header">
                        <h3 class="modal-title">{{ selectedSkill.name }}</h3>
                        <button class="btn-icon" @click="selectedSkill = null">✕</button>
                    </div>
                    <div class="modal-body">
                        <div class="skill-detail-info" style="margin-bottom: 1rem; padding: 1rem; background: var(--bg-color); border-radius: 0.5rem;">
                            <div style="display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 0.75rem;">
                                <div>
                                    <span class="skill-detail-label">来源:</span>
                                    <span :class="['skill-badge', 'skill-type-' + selectedSkill.source]" style="margin-left: 0.25rem;">
                                        {{ selectedSkill.source === 'builtin' ? '内置技能' : '自建技能' }}
                                    </span>
                                </div>
                                <div>
                                    <span class="skill-detail-label">加载方式:</span>
                                    <span :class="['skill-badge', (selectedSkill.meta?.always || selectedSkill.always) ? 'always' : 'on-demand']" style="margin-left: 0.25rem;">
                                        {{ (selectedSkill.meta?.always || selectedSkill.always) ? '始终加载' : '按需加载' }}
                                    </span>
                                </div>
                            </div>
                            <div v-if="selectedSkill.meta?.description" style="font-size: 0.875rem; color: var(--text-secondary);">
                                <strong>描述:</strong> {{ selectedSkill.meta.description }}
                            </div>
                        </div>
                        <div class="skill-content" v-html="renderMarkdown(selectedSkill.content)"></div>
                    </div>
                </div>
            </div>
        </div>
    `,
  data() {
    return {
      skills: [],
      selectedSkill: null,
      filterSource: "all",
    };
  },
  computed: {
    filteredSkills() {
      if (this.filterSource === "all") {
        return this.skills;
      }
      return this.skills.filter((s) => s.source === this.filterSource);
    },
  },
  mounted() {
    this.loadSkills();
  },
  methods: {
    async loadSkills() {
      try {
        const result = await API.skills.list();
        this.skills = Array.isArray(result) ? result : result.skills || [];
      } catch (e) {
        console.error("Failed to load skills:", e);
      }
    },
    async showSkillDetail(skill) {
      try {
        const result = await API.skills.get(skill.name, skill.source);
        this.selectedSkill = result;
      } catch (e) {
        this.$root.showToast("加载失败: " + e.message, "error");
      }
    },
    getSkillIcon(name) {
      const icons = {
        memory: "📝",
        "daily-note": "📅",
        archive: "📦",
        "topic-note": "📚",
        "temp-note": "⚡",
        "project-note": "🎯",
        "note-search": "🔍",
        cron: "⏰",
        weather: "🌤️",
        github: "🐙",
        tmux: "💻",
        summarize: "📄",
        "skill-creator": "🛠️",
        clawhub: "🌐",
        "ai-news-bulletin": "📰",
      };
      return icons[name] || "🔧";
    },
    renderMarkdown(content) {
      if (!content) return "";
      if (typeof marked !== "undefined") {
        marked.setOptions({ breaks: true, gfm: true });
        return marked.parse(content);
      }
      return content.replace(/\n/g, "<br>");
    },
  },
};

const ConfigPage = {
  template: `
        <div class="page-container">
            <div class="config-content">
                <div class="service-overview-card">
                    <div class="overview-header"><h3 class="overview-title">服务状态总览</h3></div>
                    <div class="service-overview">
                    <div class="overview-main">
                        <div class="overview-stat">
                            <svg class="overview-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2z"/><circle cx="8" cy="14" r="2"/><circle cx="16" cy="14" r="2"/></svg>
                            <div class="overview-info">
                                <span class="overview-label">当前模型</span>
                                <span class="overview-value">{{ getModelDisplayName(config.model.current) || '未设置' }}</span>
                            </div>
                        </div>
                        <div class="overview-stat">
                            <svg class="overview-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
                            <div class="overview-info">
                                <span class="overview-label">供应商</span>
                                <span class="overview-value">{{ currentProviderName }}</span>
                            </div>
                        </div>
                        <div class="overview-stat">
                            <svg class="overview-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                            <div class="overview-info">
                                <span class="overview-label">思考过程</span>
                                <span :class="['overview-value', config.model.enable_reasoning ? 'text-success' : 'text-warning']">
                                    {{ config.model.enable_reasoning ? '已启用' : '已禁用' }}
                                </span>
                            </div>
                        </div>
                    </div>
                    <div class="overview-modules">
                        <div class="module-status-item">
                            <svg class="module-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                            <span class="module-label">通信渠道</span>
                            <span :class="['module-value', enabledChannelsCount > 0 ? 'text-success' : 'text-muted']">
                                {{ enabledChannelsCount }} / {{ config.channels.length }} 已启用
                            </span>
                        </div>
                        <div class="module-status-item">
                            <svg class="module-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
                            <span class="module-label">知识检索</span>
                            <span :class="['module-value', config.knowledge.enabled ? 'text-success' : 'text-muted']">
                                {{ config.knowledge.enabled ? '已启用' : '已禁用' }}
                            </span>
                        </div>
                        <div class="module-status-item">
                            <svg class="module-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                            <span class="module-label">文件上传</span>
                            <span :class="['module-value', upload.enabled ? 'text-success' : 'text-muted']">
                                {{ upload.enabled ? '已启用' : '已禁用' }}
                            </span>
                        </div>
                        <div class="module-status-item">
                            <svg class="module-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
                            <span class="module-label">Web UI</span>
                            <span :class="['module-value', gateway.web_ui_enabled ? 'text-success' : 'text-muted']">
                                {{ gateway.web_ui_enabled ? '运行中 (端口 ' + gateway.web_ui_port + ')' : '已禁用' }}
                            </span>
                        </div>
                    </div>
                    <div class="overview-actions">
                        <span class="form-hint">⚠️ 部分配置更改后需重启服务才能生效</span>
                        <button class="btn btn-primary" @click="restartService" :disabled="restarting">
                            {{ restarting ? '重启中...' : '重启服务' }}
                        </button>
                    </div>
                </div>
            </div>

                <div class="token-stats-card">
                    <div class="overview-header">
                        <h3 class="overview-title">Token 使用统计</h3>
                        <div class="period-selector">
                            <button 
                                v-for="period in tokenPeriods" 
                                :key="period.value"
                                :class="['period-btn', { active: tokenPeriod === period.value }]"
                                @click="loadTokenStats(period.value)"
                            >
                                {{ period.label }}
                            </button>
                        </div>
                    </div>
                    <div class="token-stats-summary">
                        <div class="token-stat">
                            <span class="token-stat-value">{{ formatNumber(tokenStats.total_tokens) }}</span>
                            <span class="token-stat-label">Token 总数</span>
                        </div>
                        <div class="token-stat">
                            <span class="token-stat-value">{{ formatNumber(tokenStats.total_prompt_tokens) }}</span>
                            <span class="token-stat-label">输入 Token</span>
                        </div>
                        <div class="token-stat">
                            <span class="token-stat-value">{{ formatNumber(tokenStats.total_completion_tokens) }}</span>
                            <span class="token-stat-label">输出 Token</span>
                        </div>
                        <div class="token-stat">
                            <span class="token-stat-value">{{ tokenStats.total_requests }}</span>
                            <span class="token-stat-label">请求次数</span>
                        </div>
                        <div class="token-stat">
                            <span class="token-stat-value">{{ tokenStats.active_sessions }}</span>
                            <span class="token-stat-label">活跃会话</span>
                        </div>
                    </div>
                    <div class="token-model-stats" v-if="tokenStats.by_model && tokenStats.by_model.length > 0">
                        <div class="model-stats-header">按模型统计</div>
                        <div class="model-stats-list">
                            <div class="model-stat-item" v-for="model in tokenStats.by_model" :key="model.model">
                                <div class="model-stat-info">
                                    <span class="model-name">{{ model.model }}</span>
                                    <span class="model-sessions">{{ model.session_count }} 会话</span>
                                </div>
                                <div class="model-stat-values">
                                    <span class="model-tokens">{{ formatNumber(model.total_tokens) }} Token</span>
                                    <span class="model-requests">{{ model.request_count }} 次请求</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

            <div class="card">
                    <div class="card-header"><h3 class="card-title">模型和供应商</h3></div>
                    <div class="provider-list">
                        <div v-for="provider in config.providers" :key="provider.name" class="provider-item">
                            <div class="provider-info">
                                <span class="provider-name">{{ provider.display_name || provider.name }}</span>
                                <span v-if="provider.is_gateway" class="badge badge-info">网关</span>
                                <span v-if="provider.is_oauth" class="badge badge-info">OAuth</span>
                                <span v-if="provider.is_local" class="badge badge-info">本地</span>
                                <span :class="['badge', provider.has_key ? 'badge-success' : 'badge-warning']">
                                    {{ provider.has_key ? '已配置' : '未配置' }}
                                </span>
                                <span v-if="isCurrentProvider(provider.name)" class="badge badge-primary">当前</span>
                            </div>
                            <div class="provider-actions">
                                <button class="btn btn-sm btn-secondary" @click="editProvider(provider)">
                                    {{ provider.has_key ? '编辑' : '配置' }}
                                </button>
                                <button v-if="provider.has_key && !isCurrentProvider(provider.name)" class="btn btn-sm btn-primary" @click="switchToProvider(provider)">启用</button>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><h3 class="card-title">Agent 默认配置</h3></div>
                    <div class="form-group">
                        <label class="form-label">最大 Token</label>
                        <input class="input" type="number" v-model.number="agentDefaults.max_tokens" @change="saveAgentDefaults">
                    </div>
                    <div class="form-group">
                        <label class="form-label">温度 (Temperature)</label>
                        <input class="input" :class="{ error: validationErrors.temperature }" type="number" step="0.1" min="0" max="2" v-model.number="agentDefaults.temperature" @change="saveAgentDefaults">
                        <p v-if="validationErrors.temperature" class="form-error">{{ validationErrors.temperature }}</p>
                    </div>
                    <div class="form-group">
                        <label class="form-label">最大工具迭代次数</label>
                        <input class="input" :class="{ error: validationErrors.max_tool_iterations }" type="number" v-model.number="agentDefaults.max_tool_iterations" @change="saveAgentDefaults">
                        <p v-if="validationErrors.max_tool_iterations" class="form-error">{{ validationErrors.max_tool_iterations }}</p>
                    </div>
                    <div class="form-group">
                        <label class="form-label">记忆窗口大小</label>
                        <input class="input" :class="{ error: validationErrors.memory_window }" type="number" v-model.number="agentDefaults.memory_window" @change="saveAgentDefaults">
                        <p v-if="validationErrors.memory_window" class="form-error">{{ validationErrors.memory_window }}</p>
                    </div>
                    <div class="form-group">
                        <label class="form-label">工作目录</label>
                        <input class="input" v-model="agentDefaults.workspace" @change="saveAgentDefaults">
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><h3 class="card-title">子代理配置</h3></div>
                    <div class="form-group">
                        <label class="form-label">
                            <input type="checkbox" v-model="subagent.enabled" @change="saveSubagent"> 启用子代理
                        </label>
                    </div>
                    <div class="form-group">
                        <label class="form-label">最大并发数</label>
                        <input class="input" :class="{ error: validationErrors.max_concurrent }" type="number" v-model.number="subagent.max_concurrent" @change="saveSubagent">
                        <p v-if="validationErrors.max_concurrent" class="form-error">{{ validationErrors.max_concurrent }}</p>
                    </div>
                    <div class="form-group">
                        <label class="form-label">默认超时 (秒)</label>
                        <input class="input" :class="{ error: validationErrors.default_timeout }" type="number" v-model.number="subagent.default_timeout" @change="saveSubagent">
                        <p v-if="validationErrors.default_timeout" class="form-error">{{ validationErrors.default_timeout }}</p>
                    </div>
                    <div class="form-group">
                        <label class="form-label">
                            <input type="checkbox" v-model="subagent.workspace_isolation" @change="saveSubagent"> 工作空间隔离
                        </label>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><h3 class="card-title">知识检索配置</h3></div>
                    <div class="form-group">
                        <label class="form-label"><input type="checkbox" v-model="config.knowledge.enabled" @change="toggleKnowledge"> 启用向量检索</label>
                    </div>
                    <template v-if="config.knowledge.enabled">
                        <div class="form-group">
                            <label class="form-label"><input type="checkbox" v-model="config.knowledge.use_graph" @change="saveKnowledge"> 启用知识图谱</label>
                            <p class="form-hint">启用实体检索和关系推理</p>
                        </div>
                        <div class="form-group">
                            <label class="form-label"><input type="checkbox" v-model="config.knowledge.use_llm_extract" @change="saveKnowledge"> 启用实体抽取</label>
                            <p class="form-hint">自动从笔记中抽取实体和关系</p>
                        </div>
                        <div class="form-group">
                            <label class="form-label">嵌入模型</label>
                            <input class="input" :value="config.knowledge.embedding_model" disabled>
                        </div>
                        <div class="form-group">
                            <label class="form-label">持久化目录</label>
                            <input class="input" :value="config.knowledge.persist_dir" disabled>
                        </div>
                        <div class="form-group">
                            <label class="form-label">分块大小</label>
                            <input class="input" type="number" v-model.number="config.knowledge.chunk_size" @change="saveKnowledge">
                        </div>
                        <div class="form-group">
                            <label class="form-label">分块重叠</label>
                            <input class="input" type="number" v-model.number="config.knowledge.chunk_overlap" @change="saveKnowledge">
                        </div>
                        <div class="form-group">
                            <label class="form-label">默认返回数量 (Top K)</label>
                            <input class="input" type="number" v-model.number="config.knowledge.default_top_k" @change="saveKnowledge">
                        </div>
                    </template>
                </div>
                <div class="card">
                    <div class="card-header"><h3 class="card-title">上传配置</h3></div>
                    <div class="form-group">
                        <label class="form-label">
                            <input type="checkbox" v-model="upload.enabled" @change="saveUpload"> 启用文件上传
                        </label>
                    </div>
                    <div class="form-group">
                        <label class="form-label">最大文件大小 (字节)</label>
                        <input class="input" type="number" v-model.number="upload.max_file_size" @change="saveUpload">
                        <p class="form-hint">当前: {{ formatSize(upload.max_file_size) }}</p>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><h3 class="card-title">Gateway 服务配置</h3></div>
                    <div class="form-group">
                        <label class="form-label">服务地址</label>
                        <input class="input" v-model="gateway.host" @change="saveGateway">
                    </div>
                    <div class="form-group">
                        <label class="form-label">服务端口</label>
                        <input class="input" type="number" v-model.number="gateway.port" @change="saveGateway">
                    </div>
                    <p class="form-hint">Gateway 服务配置更改后需要重启才能生效。</p>
                </div>
                <div class="card">
                    <div class="card-header"><h3 class="card-title">Web UI 配置</h3></div>
                    <div class="form-group">
                        <label class="form-label">
                            <input type="checkbox" v-model="gateway.web_ui_enabled" @change="saveWebUI"> 启用 Web UI
                        </label>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Web UI 端口</label>
                        <input class="input" type="number" v-model.number="gateway.web_ui_port" @change="saveWebUI">
                    </div>
                    <div class="form-group">
                        <label class="form-label">
                            <input type="checkbox" v-model="gateway.web_ui_auth_enabled" @change="saveWebUI"> 启用认证
                        </label>
                    </div>
                    <p class="form-hint">Web UI 配置更改后需要重启才能生效。</p>
                </div>
                <div class="card">
                    <div class="card-header"><h3 class="card-title">工具配置</h3></div>
                    <div class="form-group">
                        <label class="form-label">
                            <input type="checkbox" v-model="toolsConfig.restrict_to_workspace" @change="saveToolsConfig"> 限制工作空间
                        </label>
                        <p class="form-hint">限制文件操作只能在指定工作目录内进行</p>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Shell 执行超时 (秒)</label>
                        <input class="input" type="number" v-model.number="toolsConfig.exec_timeout" @change="saveToolsConfig">
                    </div>
                    <div class="tool-item">
                        <div class="tool-info">
                            <span class="tool-name">博查搜索 (网络搜索)</span>
                            <span :class="['badge', config.tools?.web_search_api_key ? 'badge-success' : 'badge-warning']">
                                {{ config.tools?.web_search_api_key ? '已配置' : '未配置' }}
                            </span>
                        </div>
                        <button class="btn btn-sm btn-secondary" @click="editTool('web_search')">
                            {{ config.tools?.web_search_api_key ? '编辑' : '配置' }}
                        </button>
                    </div>
                    <div class="tool-item">
                        <div class="tool-info">
                            <span class="tool-name">心知天气 (天气查询)</span>
                            <span :class="['badge', config.tools?.weather_api_key ? 'badge-success' : 'badge-warning']">
                                {{ config.tools?.weather_api_key ? '已配置' : '未配置' }}
                            </span>
                        </div>
                        <button class="btn btn-sm btn-secondary" @click="editTool('weather')">
                            {{ config.tools?.weather_api_key ? '编辑' : '配置' }}
                        </button>
                    </div>
                    <div class="tool-item">
                        <div class="tool-info">
                            <span class="tool-name">MCP 服务器</span>
                            <span class="badge badge-info">{{ toolsConfig.mcp_servers_count || 0 }} 个</span>
                        </div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header"><h3 class="card-title">通信渠道</h3></div>
                    <div v-for="channel in config.channels" :key="channel.name" class="channel-item">
                        <div class="channel-info">
                            <span class="channel-name">{{ channel.display_name || channel.name }}</span>
                            <span :class="['badge', channel.enabled ? 'badge-success' : 'badge-warning']">
                                {{ channel.enabled ? '已启用' : '未启用' }}
                            </span>
                        </div>
                        <button class="btn btn-sm btn-secondary" @click="editChannel(channel)">
                            {{ channel.has_credentials ? '编辑' : '配置' }}
                        </button>
                    </div>
                </div>
                </div>
            </div>
            <div class="modal-overlay" v-if="editingProvider" @click.self="editingProvider = null">
                <div class="modal modal-lg">
                    <div class="modal-header">
                        <h3 class="modal-title">配置 {{ editingProvider.display_name || editingProvider.name }}</h3>
                        <button class="btn-icon" @click="editingProvider = null">✕</button>
                    </div>
                    <div class="modal-body">
                        <div class="form-hint" style="margin-bottom: 1rem;" v-if="editingProvider.description">
                            {{ editingProvider.description }}
                        </div>
                        <div class="form-group">
                            <label class="form-label">API Key</label>
                            <input class="input" type="text" v-model="providerForm.apiKey" :placeholder="editingProvider.key_masked || '输入 API Key'">
                        </div>
                        <div class="form-group">
                            <label class="form-label">API Base (可选)</label>
                            <input class="input" v-model="providerForm.apiBase" :placeholder="editingProvider.api_base || '使用默认地址'">
                        </div>
                        <div class="form-group">
                            <label class="form-label">选择模型</label>
                            <div v-if="recentModels.length > 0" class="recent-models">
                                <div class="recent-models-header">最近使用</div>
                                <div class="recent-models-list">
                                    <div v-for="item in recentModels" :key="item.model" 
                                         :class="['recent-model-item', { active: selectedModel === item.model }]" 
                                         @click="selectRecentModel(item.model)">
                                        {{ getModelDisplayName(item.model) }}
                                    </div>
                                </div>
                            </div>
                            <div class="model-list">
                                <div v-for="model in filteredModels" :key="model" :class="['model-item', { active: selectedModel === model }]" @click="selectedModel = model">
                                    {{ getModelDisplayName(model) }}
                                    <span v-if="selectedModel === model" class="check">✓</span>
                                </div>
                            </div>
                        </div>
                        <div class="form-group">
                            <label class="form-label">自定义模型</label>
                            <div class="custom-model-input">
                                <input class="input" v-model="customModel" placeholder="输入自定义模型名称">
                                <button class="btn btn-secondary" @click="addCustomModel" type="button">添加</button>
                            </div>
                        </div>
                        <div class="form-group">
                            <label class="form-label">
                                <input type="checkbox" v-model="enableReasoning"> 
                                启用思考过程显示
                            </label>
                            <p class="form-hint">开启后，如果模型支持，将显示 AI 的思考过程</p>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" @click="editingProvider = null">取消</button>
                        <button class="btn btn-primary" @click="saveProvider">保存</button>
                    </div>
                </div>
            </div>
            <div class="modal-overlay" v-if="editingChannel" @click.self="editingChannel = null">
                <div class="modal">
                    <div class="modal-header">
                        <h3 class="modal-title">配置 {{ editingChannel.display_name || editingChannel.name }}</h3>
                        <button class="btn-icon" @click="editingChannel = null">✕</button>
                    </div>
                    <div class="modal-body">
                        <div class="form-hint" style="margin-bottom: 1rem;" v-if="editingChannel.description">
                            {{ editingChannel.description }}
                        </div>
                        <div class="form-group" v-if="editingChannel.name === 'telegram'">
                            <label class="form-label">Bot Token</label>
                            <input class="input" type="text" v-model="channelForm.token" :placeholder="channelForm.tokenMasked || '输入 Bot Token'">
                        </div>
                        <div class="form-group" v-if="editingChannel.name === 'whatsapp'">
                            <label class="form-label">Bridge Token</label>
                            <input class="input" type="text" v-model="channelForm.bridgeToken" :placeholder="channelForm.bridgeTokenMasked || '输入 Bridge Token'">
                        </div>
                        <template v-if="editingChannel.name === 'feishu'">
                            <div class="form-group">
                                <label class="form-label">App ID</label>
                                <input class="input" v-model="channelForm.appId" :placeholder="channelForm.appIdMasked || '输入 App ID'">
                            </div>
                            <div class="form-group">
                                <label class="form-label">App Secret</label>
                                <input class="input" type="text" v-model="channelForm.appSecret" :placeholder="channelForm.appSecretMasked || '输入 App Secret'">
                            </div>
                        </template>
                        <template v-if="editingChannel.name === 'dingtalk'">
                            <div class="form-group">
                                <label class="form-label">Client ID (AppKey)</label>
                                <input class="input" v-model="channelForm.clientId" :placeholder="channelForm.clientIdMasked || '输入 AppKey'">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Client Secret (AppSecret)</label>
                                <input class="input" type="text" v-model="channelForm.clientSecret" :placeholder="channelForm.clientSecretMasked || '输入 AppSecret'">
                            </div>
                        </template>
                        <div class="form-group" v-if="editingChannel.name === 'discord'">
                            <label class="form-label">Bot Token</label>
                            <input class="input" type="text" v-model="channelForm.token" :placeholder="channelForm.tokenMasked || '输入 Bot Token'">
                        </div>
                        <div class="form-group" v-if="editingChannel.name === 'slack'">
                            <label class="form-label">Bot Token</label>
                            <input class="input" type="text" v-model="channelForm.botToken" :placeholder="channelForm.botTokenMasked || '输入 Bot Token'">
                        </div>
                        <template v-if="editingChannel.name === 'email'">
                            <div class="form-group">
                                <label class="form-label">IMAP 主机</label>
                                <input class="input" v-model="channelForm.imapHost" :placeholder="channelForm.imapHostMasked || '例如: imap.gmail.com'">
                            </div>
                            <div class="form-group">
                                <label class="form-label">IMAP 端口</label>
                                <input class="input" type="number" v-model="channelForm.imapPort" placeholder="993">
                            </div>
                            <div class="form-group">
                                <label class="form-label">IMAP 用户名</label>
                                <input class="input" v-model="channelForm.imapUsername" :placeholder="channelForm.imapUsernameMasked || '邮箱地址'">
                            </div>
                            <div class="form-group">
                                <label class="form-label">IMAP 密码</label>
                                <input class="input" type="password" v-model="channelForm.imapPassword" placeholder="输入密码">
                            </div>
                            <div class="form-group">
                                <label class="form-label">SMTP 主机</label>
                                <input class="input" v-model="channelForm.smtpHost" :placeholder="channelForm.smtpHostMasked || '例如: smtp.gmail.com'">
                            </div>
                            <div class="form-group">
                                <label class="form-label">SMTP 端口</label>
                                <input class="input" type="number" v-model="channelForm.smtpPort" placeholder="587">
                            </div>
                            <div class="form-group">
                                <label class="form-label">SMTP 用户名</label>
                                <input class="input" v-model="channelForm.smtpUsername" :placeholder="channelForm.smtpUsernameMasked || '邮箱地址'">
                            </div>
                            <div class="form-group">
                                <label class="form-label">SMTP 密码</label>
                                <input class="input" type="password" v-model="channelForm.smtpPassword" placeholder="输入密码">
                            </div>
                        </template>
                        <template v-if="editingChannel.name === 'mochat'">
                            <div class="form-group">
                                <label class="form-label">Base URL</label>
                                <input class="input" v-model="channelForm.baseUrl" :placeholder="channelForm.baseUrlMasked || 'https://mochat.io'">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Claw Token</label>
                                <input class="input" type="text" v-model="channelForm.clawToken" :placeholder="channelForm.clawTokenMasked || '输入 Claw Token'">
                            </div>
                        </template>
                        <template v-if="editingChannel.name === 'qq'">
                            <div class="form-group">
                                <label class="form-label">App ID (机器人 ID)</label>
                                <input class="input" v-model="channelForm.appId" :placeholder="channelForm.appIdMasked || '从 q.qq.com 获取'">
                            </div>
                            <div class="form-group">
                                <label class="form-label">App Secret (机器人密钥)</label>
                                <input class="input" type="text" v-model="channelForm.secret" :placeholder="channelForm.secretMasked || '输入 App Secret'">
                            </div>
                        </template>
                        <div class="form-group">
                            <label class="form-label">
                                <input type="checkbox" v-model="channelForm.enabled"> 启用此通道
                            </label>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" @click="editingChannel = null">取消</button>
                        <button class="btn btn-primary" @click="saveChannel">保存</button>
                    </div>
                </div>
            </div>
            <div class="modal-overlay" v-if="editingTool" @click.self="editingTool = null">
                <div class="modal">
                    <div class="modal-header">
                        <h3 class="modal-title">配置 {{ getToolName(editingTool) }}</h3>
                        <button class="btn-icon" @click="editingTool = null">✕</button>
                    </div>
                    <div class="modal-body">
                        <div class="form-group">
                            <label class="form-label">API Key</label>
                            <input class="input" type="text" v-model="toolForm.apiKey" :placeholder="toolForm.keyMasked || '输入 API Key'">
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" @click="editingTool = null">取消</button>
                        <button class="btn btn-primary" @click="saveTool">保存</button>
                    </div>
                </div>
            </div>
        </div>
    `,
  data() {
    return {
      config: {
        model: { current: "", available: [] },
        providers: [],
        channels: [],
        knowledge: {
          enabled: false,
          embedding_model: "",
          persist_dir: "",
          chunk_size: 512,
          chunk_overlap: 50,
          default_top_k: 5,
        },
        tools: {},
      },
      agentDefaults: {
        max_tokens: 4096,
        temperature: 0.7,
        max_tool_iterations: 10,
        memory_window: 10,
        enable_reasoning: true,
        workspace: "",
      },
      subagent: {
        enabled: true,
        max_concurrent: 3,
        default_timeout: 300,
        workspace_isolation: true,
      },
      upload: {
        enabled: true,
        max_file_size: 10485760,
      },
      gateway: {
        host: "0.0.0.0",
        port: 18790,
        web_ui_enabled: true,
        web_ui_host: "0.0.0.0",
        web_ui_port: 8080,
        web_ui_auth_enabled: false,
      },
      toolsConfig: {
        restrict_to_workspace: true,
        exec_timeout: 60,
        mcp_servers_count: 0,
        web_search_enabled: false,
        weather_enabled: false,
      },
      editingProvider: null,
      editingChannel: null,
      editingTool: null,
      providerForm: { apiKey: "", apiBase: "" },
      channelForm: {
        appId: "",
        appSecret: "",
        token: "",
        bridgeToken: "",
        botToken: "",
        enabled: false,
      },
      toolForm: { apiKey: "", keyMasked: "" },
      selectedModel: "",
      recentModels: [],
      customModel: "",
      customModels: [],
      enableReasoning: true,
      restarting: false,
      validationErrors: {},
      tokenStats: {
        total_prompt_tokens: 0,
        total_completion_tokens: 0,
        total_tokens: 0,
        total_requests: 0,
        active_sessions: 0,
        by_model: [],
      },
      tokenPeriod: "all",
      tokenPeriods: [
        { label: "今日", value: "today" },
        { label: "本周", value: "week" },
        { label: "本月", value: "month" },
        { label: "全部", value: "all" },
      ],
    };
  },
  computed: {
    currentProviderName() {
      const current = this.config.model.current || "";
      if (current.includes("/")) {
        return current.split("/")[0];
      }
      for (const provider of this.config.providers) {
        if (provider.has_key && provider.enabled) {
          return provider.name;
        }
      }
      return current || "未设置";
    },
    enabledChannelsCount() {
      return this.config.channels
        ? this.config.channels.filter((c) => c.enabled).length
        : 0;
    },
    filteredModels() {
      if (!this.editingProvider) return [];
      const providerName = this.editingProvider.name;
      const builtIn = this.config.model.available.filter(
        (m) => m.startsWith(providerName + "/") || m === providerName,
      );
      return [...builtIn, ...this.customModels];
    },
  },
  mounted() {
    this.loadConfig();
  },
  methods: {
    async loadConfig() {
      try {
        this.config = await API.config.get();
        this.selectedModel = this.config.model.current;
        this.enableReasoning = this.config.model.enable_reasoning ?? true;
        if (this.config.agent_defaults) {
          this.agentDefaults = {
            ...this.agentDefaults,
            ...this.config.agent_defaults,
          };
        }
        if (this.config.subagent) {
          this.subagent = { ...this.subagent, ...this.config.subagent };
        }
        if (this.config.upload) {
          this.upload = { ...this.upload, ...this.config.upload };
        }
        if (this.config.gateway) {
          this.gateway = { ...this.gateway, ...this.config.gateway };
        }
        if (this.config.tools_config) {
          this.toolsConfig = {
            ...this.toolsConfig,
            ...this.config.tools_config,
          };
        }
        if (this.config.recent_models) {
          this.recentModels = this.config.recent_models;
        }
        if (this.config.knowledge) {
          this.config.knowledge.chunk_size =
            this.config.knowledge.chunk_size || 512;
          this.config.knowledge.chunk_overlap =
            this.config.knowledge.chunk_overlap || 50;
          this.config.knowledge.default_top_k =
            this.config.knowledge.default_top_k || 5;
        }
      } catch (e) {
        console.error("Failed to load config:", e);
      }
      this.loadTokenStats();
    },
    async loadTokenStats(period) {
      if (period) {
        this.tokenPeriod = period;
      }
      try {
        const res = await fetch(`/api/stats/tokens?period=${this.tokenPeriod}`);
        if (res.ok) {
          this.tokenStats = await res.json();
        }
      } catch (e) {
        console.error("Failed to load token stats:", e);
      }
    },
    formatNumber(num) {
      if (!num || num === 0) return "0";
      if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + "M";
      }
      if (num >= 1000) {
        return (num / 1000).toFixed(1) + "K";
      }
      return num.toString();
    },
    isCurrentProvider(providerName) {
      const current = this.config.model.current || "";
      if (current.includes("/")) {
        return current.split("/")[0] === providerName;
      }
      const provider = this.config.providers.find(
        (p) => p.name === providerName,
      );
      return (
        provider &&
        provider.has_key &&
        provider.enabled &&
        !current.includes("/")
      );
    },
    getChannelStatusClass(channel) {
      if (channel.enabled && channel.has_credentials) return "status-online";
      if (channel.has_credentials) return "status-standby";
      return "status-offline";
    },
    getChannelStatusText(channel) {
      if (channel.enabled && channel.has_credentials) return "运行中";
      if (channel.has_credentials) return "待启用";
      return "未配置";
    },
    async editProvider(provider) {
      this.editingProvider = provider;
      this.providerForm = {
        apiKey: "",
        apiBase: provider.api_base || "",
      };
      this.selectedModel = this.config.model.current;
    },
    addCustomModel() {
      const modelName = this.customModel.trim();
      if (modelName) {
        if (!this.customModels.includes(modelName)) {
          this.customModels.push(modelName);
        }
        this.selectedModel = modelName;
        this.customModel = "";
      }
    },
    selectRecentModel(model) {
      this.selectedModel = model;
    },
    getModelDisplayName(model) {
      if (!model) return "";
      if (model.includes("/")) {
        return model.split("/").slice(1).join("/");
      }
      return model;
    },
    async saveProvider() {
      const apiKeyToSend = this.providerForm.apiKey
        ? this.providerForm.apiKey.trim()
        : null;
      if (!apiKeyToSend && !this.editingProvider.has_key) {
        this.$root.showToast("请输入 API Key", "error");
        return;
      }
      try {
        if (apiKeyToSend || this.providerForm.apiBase) {
          await API.config.setProviderKey(
            this.editingProvider.name,
            apiKeyToSend,
            this.providerForm.apiBase || null,
          );
        }
        if (this.selectedModel) {
          await API.config.setModel(this.selectedModel, this.enableReasoning);
        }
        this.$root.showToast("保存成功");
        this.editingProvider = null;
        await this.loadConfig();
      } catch (e) {
        this.$root.showToast("保存失败: " + e.message, "error");
      }
    },
    async switchToProvider(provider) {
      const models = {
        openai: "openai/gpt-4o-mini",
        anthropic: "anthropic/claude-3-haiku-20240307",
        deepseek: "deepseek/deepseek-chat",
        zhipu: "zhipu/glm-4-flash",
        moonshot: "moonshot/moonshot-v1-8k",
        minimax: "minimax/abab6.5s-chat",
        openrouter: "openrouter/auto",
        groq: "groq/llama-3.1-8b-instant",
        dashscope: "dashscope/qwen-turbo",
        siliconflow: "siliconflow/Qwen/Qwen2.5-7B-Instruct",
      };
      const model = models[provider.name] || `${provider.name}/default`;
      try {
        await API.config.setModel(model);
        this.$root.showToast("已切换到 " + provider.name);
        await this.loadConfig();
      } catch (e) {
        this.$root.showToast("切换失败: " + e.message, "error");
      }
    },
    editChannel(channel) {
      this.editingChannel = channel;
      const creds = channel.credentials_masked || {};
      this.channelForm = {
        appId: "",
        appSecret: "",
        clientId: "",
        clientSecret: "",
        secret: "",
        token: "",
        bridgeToken: "",
        botToken: "",
        baseUrl: "",
        clawToken: "",
        imapHost: "",
        imapPort: null,
        imapUsername: "",
        imapPassword: "",
        smtpHost: "",
        smtpPort: null,
        smtpUsername: "",
        smtpPassword: "",
        enabled: channel.enabled,
        appIdMasked: creds.app_id || "",
        appSecretMasked: creds.app_secret || "",
        clientIdMasked: creds.client_id || "",
        clientSecretMasked: creds.client_secret || "",
        secretMasked: creds.secret || "",
        tokenMasked: creds.token || "",
        bridgeTokenMasked: creds.bridge_token || "",
        botTokenMasked: creds.bot_token || "",
        baseUrlMasked: creds.base_url || "",
        clawTokenMasked: creds.claw_token || "",
        imapHostMasked: creds.imap_host || "",
        imapUsernameMasked: creds.imap_username || "",
        smtpHostMasked: creds.smtp_host || "",
        smtpUsernameMasked: creds.smtp_username || "",
      };
    },
    async saveChannel() {
      const payload = { enabled: this.channelForm.enabled };
      if (this.channelForm.token) payload.token = this.channelForm.token;
      if (this.channelForm.bridgeToken)
        payload.bridge_token = this.channelForm.bridgeToken;
      if (this.channelForm.appId) payload.app_id = this.channelForm.appId;
      if (this.channelForm.appSecret)
        payload.app_secret = this.channelForm.appSecret;
      if (this.channelForm.botToken)
        payload.bot_token = this.channelForm.botToken;
      if (this.channelForm.clientId)
        payload.client_id = this.channelForm.clientId;
      if (this.channelForm.clientSecret)
        payload.client_secret = this.channelForm.clientSecret;
      if (this.channelForm.secret) payload.secret = this.channelForm.secret;
      if (this.channelForm.baseUrl) payload.base_url = this.channelForm.baseUrl;
      if (this.channelForm.clawToken)
        payload.claw_token = this.channelForm.clawToken;
      if (this.channelForm.imapHost)
        payload.imap_host = this.channelForm.imapHost;
      if (this.channelForm.imapPort)
        payload.imap_port = this.channelForm.imapPort;
      if (this.channelForm.imapUsername)
        payload.imap_username = this.channelForm.imapUsername;
      if (this.channelForm.imapPassword)
        payload.imap_password = this.channelForm.imapPassword;
      if (this.channelForm.smtpHost)
        payload.smtp_host = this.channelForm.smtpHost;
      if (this.channelForm.smtpPort)
        payload.smtp_port = this.channelForm.smtpPort;
      if (this.channelForm.smtpUsername)
        payload.smtp_username = this.channelForm.smtpUsername;
      if (this.channelForm.smtpPassword)
        payload.smtp_password = this.channelForm.smtpPassword;
      try {
        await API.config.setChannelConfig(this.editingChannel.name, payload);
        this.$root.showToast("保存成功");
        this.editingChannel = null;
        await this.loadConfig();
      } catch (e) {
        this.$root.showToast("保存失败: " + e.message, "error");
      }
    },
    getToolName(tool) {
      const names = {
        web_search: "博查搜索",
        weather: "心知天气",
      };
      return names[tool] || tool;
    },
    editTool(tool) {
      this.editingTool = tool;
      const keyField = tool + "_api_key_masked";
      this.toolForm = {
        apiKey: "",
        keyMasked: this.config.tools?.[keyField] || "",
      };
    },
    async saveTool() {
      if (!this.toolForm.apiKey.trim()) {
        this.$root.showToast("请输入 API Key", "error");
        return;
      }
      try {
        await API.config.setToolConfig(this.editingTool, this.toolForm);
        this.$root.showToast("保存成功");
        this.editingTool = null;
        await this.loadConfig();
      } catch (e) {
        this.$root.showToast("保存失败: " + e.message, "error");
      }
    },
    async toggleKnowledge() {
      try {
        await API.config.toggleKnowledge(this.config.knowledge.enabled);
        this.$root.showToast(
          this.config.knowledge.enabled ? "已启用向量检索" : "已禁用向量检索",
        );
      } catch (e) {
        this.$root.showToast("操作失败: " + e.message, "error");
      }
    },
    async saveAgentDefaults() {
      this.validationErrors = {};
      if (
        this.agentDefaults.temperature < 0 ||
        this.agentDefaults.temperature > 2
      ) {
        this.validationErrors.temperature = "温度值必须在 0-2 之间";
        this.$root.showToast("温度值必须在 0-2 之间", "error");
        return;
      }
      if (this.agentDefaults.max_tool_iterations < 1) {
        this.validationErrors.max_tool_iterations =
          "最大工具迭代次数必须大于 0";
        this.$root.showToast("最大工具迭代次数必须大于 0", "error");
        return;
      }
      if (this.agentDefaults.memory_window < 1) {
        this.validationErrors.memory_window = "记忆窗口大小必须大于 0";
        this.$root.showToast("记忆窗口大小必须大于 0", "error");
        return;
      }
      try {
        await fetch("/api/config/agent/defaults", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(this.agentDefaults),
        });
        this.$root.showToast("Agent 配置已保存");
      } catch (e) {
        this.$root.showToast("保存失败: " + e.message, "error");
      }
    },
    async saveSubagent() {
      this.validationErrors = {};
      if (this.subagent.max_concurrent < 1) {
        this.validationErrors.max_concurrent = "最大并发数必须大于 0";
        this.$root.showToast("最大并发数必须大于 0", "error");
        return;
      }
      if (this.subagent.default_timeout < 1) {
        this.validationErrors.default_timeout = "超时时间必须大于 0";
        this.$root.showToast("超时时间必须大于 0", "error");
        return;
      }
      try {
        await fetch("/api/config/subagent", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(this.subagent),
        });
        this.$root.showToast("子代理配置已保存");
      } catch (e) {
        this.$root.showToast("保存失败: " + e.message, "error");
      }
    },
    async saveUpload() {
      try {
        await fetch("/api/config/upload", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(this.upload),
        });
        this.$root.showToast("上传配置已保存");
      } catch (e) {
        this.$root.showToast("保存失败: " + e.message, "error");
      }
    },
    async saveGateway() {
      try {
        await fetch("/api/config/gateway", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            host: this.gateway.host,
            port: this.gateway.port,
          }),
        });
        this.$root.showToast("Gateway 配置已保存，重启后生效");
      } catch (e) {
        this.$root.showToast("保存失败: " + e.message, "error");
      }
    },
    async saveWebUI() {
      try {
        await fetch("/api/config/webui", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            enabled: this.gateway.web_ui_enabled,
            port: this.gateway.web_ui_port,
            auth_enabled: this.gateway.web_ui_auth_enabled,
          }),
        });
        this.$root.showToast("WebUI 配置已保存，重启后生效");
      } catch (e) {
        this.$root.showToast("保存失败: " + e.message, "error");
      }
    },
    async saveToolsConfig() {
      try {
        await fetch("/api/config/tools/config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            restrict_to_workspace: this.toolsConfig.restrict_to_workspace,
            exec_timeout: this.toolsConfig.exec_timeout,
          }),
        });
        this.$root.showToast("工具配置已保存");
      } catch (e) {
        this.$root.showToast("保存失败: " + e.message, "error");
      }
    },
    async saveKnowledge() {
      try {
        await fetch("/api/config/knowledge/config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            chunk_size: this.config.knowledge.chunk_size,
            chunk_overlap: this.config.knowledge.chunk_overlap,
            default_top_k: this.config.knowledge.default_top_k,
            use_graph: this.config.knowledge.use_graph,
            use_llm_extract: this.config.knowledge.use_llm_extract,
          }),
        });
        this.$root.showToast("知识库配置已保存");
      } catch (e) {
        this.$root.showToast("保存失败: " + e.message, "error");
      }
    },
    formatSize(bytes) {
      if (!bytes) return "0 B";
      if (bytes < 1024) return bytes + " B";
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
      return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    },
    async restartService() {
      this.$root.showConfirm(
        "重启服务",
        "确定要重启服务吗？这将短暂中断所有连接。",
        async () => {
          this.restarting = true;
          try {
            await API.config.restart();
            this.$root.showToast("服务正在重启，请稍候...");

            let attempts = 0;
            const maxAttempts = 30;
            const checkInterval = 2000;

            const checkRestart = async () => {
              attempts++;
              try {
                const status = await API.config.restartStatus();
                if (status.status === "restarted") {
                  this.$root.showToast("服务重启成功，正在刷新页面...");
                  setTimeout(() => window.location.reload(), 1000);
                  return;
                }
              } catch (e) {
                // 服务可能还在重启中，继续等待
              }

              if (attempts < maxAttempts) {
                setTimeout(checkRestart, checkInterval);
              } else {
                this.restarting = false;
                this.$root.showToast("重启超时，请手动刷新页面", "warning");
              }
            };

            setTimeout(checkRestart, 3000);
          } catch (e) {
            this.restarting = false;
            this.$root.showToast("重启请求失败: " + e.message, "error");
          }
        },
      );
    },
  },
};

const App = {
  template: `
        <div id="app-inner">
            <!-- Confirm Modal -->
            <div class="modal-overlay" v-if="confirmModal.show" @click.self="confirmModal.show = false">
                <div class="confirm-modal">
                    <div class="confirm-icon">⚠️</div>
                    <h3 class="confirm-title">{{ confirmModal.title }}</h3>
                    <p class="confirm-message">{{ confirmModal.message }}</p>
                    <div class="confirm-actions">
                        <button class="btn btn-secondary" @click="confirmModal.show = false">取消</button>
                        <button class="btn btn-danger" @click="confirmAction">确定</button>
                    </div>
                </div>
            </div>
            <header class="header">
                <div class="logo">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2z"/><circle cx="8" cy="14" r="2"/><circle cx="16" cy="14" r="2"/></svg>
                    AiMate
                </div>
                <nav class="nav">
                    <button v-for="item in menuItems" :key="item.id" :class="['nav-btn', { active: currentPage === item.id }]" @click="currentPage = item.id">
                        {{ item.icon }} {{ item.name }}
                    </button>
                </nav>
            </header>
            <main class="main">
                <keep-alive>
                    <component :is="currentComponent"></component>
                </keep-alive>
            </main>
            <div v-for="toast in toasts" :key="toast.id" :class="['toast', 'toast-' + toast.type]">
                {{ toast.message }}
            </div>
        </div>
    `,
  data() {
    return {
      currentPage: "chat",
      menuItems: [
        { id: "chat", name: "对话", icon: "💬" },
        { id: "dashboard", name: "任务", icon: "📋" },
        { id: "notes", name: "笔记", icon: "📝" },
        { id: "skills", name: "技能", icon: "🛠" },
        { id: "config", name: "配置", icon: "⚙" },
      ],
      toasts: [],
      confirmModal: {
        show: false,
        title: "",
        message: "",
        onConfirm: null,
      },
    };
  },
  computed: {
    currentComponent() {
      const components = {
        chat: ChatPage,
        dashboard: DashboardMonitor,
        notes: NotesPage,
        skills: SkillsPage,
        config: ConfigPage,
      };
      return components[this.currentPage] || ChatPage;
    },
  },
  methods: {
    showToast(message, type = "info") {
      const id = Date.now();
      this.toasts.push({ id, message, type });
      setTimeout(() => {
        this.toasts = this.toasts.filter((t) => t.id !== id);
      }, 3000);
    },
    showConfirm(title, message, onConfirm) {
      this.confirmModal = {
        show: true,
        title: title,
        message: message,
        onConfirm: onConfirm,
      };
    },
    hideConfirm() {
      this.confirmModal.show = false;
      this.confirmModal.onConfirm = null;
    },
    confirmAction() {
      if (this.confirmModal.onConfirm) {
        this.confirmModal.onConfirm();
      }
      this.hideConfirm();
    },
  },
};
