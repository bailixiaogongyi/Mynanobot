const API = {
  baseUrl: "/api",
  fingerprint: null,

  async getFingerprint() {
    if (this.fingerprint) return this.fingerprint;
    const FINGERPRINT_KEY = "nanobot_device_id";
    
    try {
      let stored = localStorage.getItem(FINGERPRINT_KEY);
      if (stored) {
        this.fingerprint = stored;
        return stored;
      }
    } catch (e) {
      console.warn("localStorage access blocked, using in-memory fingerprint");
    }
    
    const components = [];
    components.push(navigator.userAgent);
    components.push(navigator.language);
    components.push(screen.width + "x" + screen.height);
    components.push(screen.colorDepth);
    components.push(new Date().getTimezoneOffset());
    components.push(navigator.platform);
    components.push(navigator.hardwareConcurrency || "unknown");
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.textBaseline = "top";
      ctx.font = "14px 'Arial'";
      ctx.textBaseline = "alphabetic";
      ctx.fillStyle = "#f60";
      ctx.fillRect(125, 1, 62, 20);
      ctx.fillStyle = "#069";
      ctx.fillText("Nanobot FP", 2, 15);
      components.push(canvas.toDataURL());
    }
    const data = components.join("|||");
    let hash = 0;
    for (let i = 0; i < data.length; i++) {
      const char = data.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash;
    }
    this.fingerprint =
      Math.abs(hash).toString(16).padStart(8, "0") +
      Date.now().toString(16).slice(-8);
    
    try {
      localStorage.setItem(FINGERPRINT_KEY, this.fingerprint);
    } catch (e) {
      console.warn("localStorage write blocked, fingerprint stored in memory only");
    }
    
    return this.fingerprint;
  },

  async request(path, options = {}) {
    const url = this.baseUrl + path;
    const fp = await this.getFingerprint();
    const timeout = options.timeout || 120000;
    let response;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      response = await fetch(url, {
        headers: {
          "Content-Type": "application/json",
          "X-Device-Fingerprint": fp,
          ...options.headers,
        },
        ...options,
        signal: controller.signal,
      });
    } catch (networkError) {
      clearTimeout(timeoutId);
      if (networkError.name === "AbortError") {
        throw new Error("请求超时，请稍后重试");
      }
      throw new Error(`网络错误: ${networkError.message || networkError}`);
    } finally {
      clearTimeout(timeoutId);
    }

    if (response.status === 401) {
      window.location.href = "/login.html";
      throw new Error("Unauthorized");
    }

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}`;
      try {
        const errorData = await response.json();
        if (typeof errorData === "string") {
          errorMessage = errorData;
        } else if (errorData.detail) {
          errorMessage =
            typeof errorData.detail === "string"
              ? errorData.detail
              : JSON.stringify(errorData.detail);
        } else if (errorData.message) {
          errorMessage =
            typeof errorData.message === "string"
              ? errorData.message
              : JSON.stringify(errorData.message);
        } else if (errorData.error) {
          errorMessage =
            typeof errorData.error === "string"
              ? errorData.error
              : JSON.stringify(errorData.error);
        } else {
          errorMessage = JSON.stringify(errorData);
        }
      } catch {
        errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      }
      throw new Error(errorMessage);
    }

    return response.json();
  },

  async get(path) {
    return this.request(path, { method: "GET" });
  },

  async post(path, data) {
    return this.request(path, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async delete(path) {
    return this.request(path, { method: "DELETE" });
  },

  chat: {
    async send(content, chatId = "default", attachments = []) {
      return API.post("/chat/send", { content, chat_id: chatId, attachments });
    },

    async listSessions() {
      return API.get("/chat/sessions");
    },

    async createSession(name) {
      return API.post("/chat/sessions", { name });
    },

    async deleteSession(chatId) {
      return API.delete(`/chat/sessions/${chatId}`);
    },

    async getHistory(chatId, limit = 100) {
      return API.get(`/chat/sessions/${chatId}/history?limit=${limit}`);
    },

    async clearHistory(chatId) {
      return API.delete(`/chat/sessions/${chatId}/history`);
    },

    connectWebSocket(chatId, onMessage, onError, onClose) {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const ws = new WebSocket(
        `${protocol}//${window.location.host}/api/chat/ws/${chatId}`,
      );

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "ping") {
          ws.send(JSON.stringify({ type: "pong" }));
          return;
        }
        onMessage(data);
      };

      ws.onerror = (error) => {
        if (onError) onError(error);
      };

      ws.onclose = () => {
        if (onClose) onClose();
      };

      return ws;
    },

    createStreamingConnection(chatId, handlers) {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/api/chat/ws/${chatId}`;
      console.log("[WS] Creating connection to:", wsUrl);

      const ws = new WebSocket(wsUrl);

      const messageQueue = [];
      let processing = false;
      let connectionError = null;
      let connectionResolved = false;

      const processQueue = async () => {
        if (processing || messageQueue.length === 0) return;
        processing = true;
        while (messageQueue.length > 0) {
          const msg = messageQueue.shift();
          console.log(
            "[WS] Processing message:",
            msg.type,
            msg.content ? msg.content.substring(0, 50) : "",
          );
          try {
            await this._handleStreamMessage(msg, handlers);
          } catch (e) {
            console.error("[WS] Error handling stream message:", e);
          }
        }
        processing = false;
      };

      ws.onopen = () => {
        console.log("[WS] Connection opened");
        connectionResolved = true;
        if (handlers.onOpen) handlers.onOpen();
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log("[WS] Received:", data.type);
        if (data.type === "ping") {
          ws.send(JSON.stringify({ type: "pong" }));
          return;
        }
        messageQueue.push(data);
        processQueue();
      };

      ws.onerror = (event) => {
        console.error("[WS] Error event:", event);
        connectionError = event;
        if (!connectionResolved && handlers.onConnectionError) {
          handlers.onConnectionError(event);
        }
      };

      ws.onclose = (event) => {
        console.log("[WS] Closed, code:", event.code, "reason:", event.reason);
        if (handlers.onClose) handlers.onClose(event);
      };

      return {
        ws,
        send: (content) => {
          console.log("[WS] Sending, readyState:", ws.readyState);
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(content);
            console.log("[WS] Sent successfully");
          } else {
            console.warn(
              "[WS] Cannot send, not open. readyState:",
              ws.readyState,
            );
          }
        },
        cancel: () => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "cancel" }));
          }
        },
        close: () => {
          if (
            ws.readyState === WebSocket.OPEN ||
            ws.readyState === WebSocket.CONNECTING
          ) {
            ws.close();
          }
        },
        isConnected: () => ws.readyState === WebSocket.OPEN,
        isConnecting: () => ws.readyState === WebSocket.CONNECTING,
        getReadyState: () => ws.readyState,
      };
    },

    async _handleStreamMessage(data, handlers) {
      switch (data.type) {
        case "text_delta":
          if (handlers.onTextDelta) handlers.onTextDelta(data.content, data);
          break;
        case "reasoning_delta":
          if (handlers.onReasoningDelta)
            handlers.onReasoningDelta(data.content, data);
          break;
        case "tool_start":
          if (handlers.onToolStart) handlers.onToolStart(data.metadata, data);
          break;
        case "tool_result":
          if (handlers.onToolResult)
            handlers.onToolResult(data.content, data.metadata, data);
          break;
        case "status":
          if (handlers.onStatus) handlers.onStatus(data.content, data);
          break;
        case "done":
          if (handlers.onDone) handlers.onDone(data.content, data);
          break;
        case "error":
          if (handlers.onError) handlers.onError(data.content, data);
          break;
        case "notification":
          if (handlers.onNotification)
            handlers.onNotification(data.content, data);
          break;
        default:
          if (handlers.onMessage) handlers.onMessage(data);
      }
    },
  },

  notes: {
    async list(directory = null) {
      const params = directory
        ? `?directory=${encodeURIComponent(directory)}`
        : "";
      return API.get(`/notes/list${params}`);
    },

    async dirs() {
      return API.get("/notes/dirs");
    },

    async read(path) {
      return API.get(`/notes/read?path=${encodeURIComponent(path)}`);
    },

    async save(path, content) {
      return API.post("/notes/save", { path, content });
    },

    async create(path, content = "") {
      return API.post(
        `/notes/create?path=${encodeURIComponent(path)}&content=${encodeURIComponent(content)}`,
      );
    },

    async delete(path) {
      return API.delete(`/notes/delete?path=${encodeURIComponent(path)}`);
    },

    async search(query, topK = 5) {
      return API.get(
        `/notes/search?q=${encodeURIComponent(query)}&top_k=${topK}`,
      );
    },

    async index(directory, force = false) {
      return API.post(
        `/notes/index?directory=${encodeURIComponent(directory)}&force=${force}`,
      );
    },

    async indexStatus() {
      return API.get("/notes/index/status");
    },
  },

  skills: {
    async list(source = null) {
      const params = source ? `?source=${source}` : "";
      return API.get(`/skills/list${params}`);
    },

    async get(name, source = null) {
      const params = source ? `?source=${source}` : "";
      return API.get(`/skills/${name}${params}`);
    },

    async sources() {
      return API.get("/skills/sources");
    },
  },

  config: {
    async get() {
      return API.get("/config/");
    },

    async setModel(model, enableReasoning = null) {
      const payload = { model };
      if (enableReasoning !== null) {
        payload.enable_reasoning = enableReasoning;
      }
      return API.post("/config/model", payload);
    },

    async deleteModel(provider, modelId) {
      return API.delete(`/config/provider/${provider}/models/custom/${encodeURIComponent(modelId)}`);
    },

    async saveCustomModel(provider, modelConfig) {
      return API.post(`/config/provider/${provider}/models/custom`, modelConfig);
    },

    async getCustomModels(provider) {
      return API.get(`/config/provider/${provider}/models/custom`);
    },

    async setProviderKey(provider, apiKey, apiBase = null) {
      return API.post(`/config/provider/${provider}`, {
        api_key: apiKey,
        api_base: apiBase,
      });
    },

    async testProviderConnection(provider) {
      return API.post(`/config/provider/${provider}/test`);
    },

    async setChannelConfig(channel, config) {
      return API.post(`/config/channel/${channel}`, config);
    },

    async setToolConfig(tool, config) {
      return API.post(`/config/tool/${tool}`, config);
    },

    async toggleKnowledge(enabled) {
      return API.post(`/config/knowledge/toggle?enabled=${enabled}`);
    },

    async workspace() {
      return API.get("/config/workspace");
    },

    async models() {
      return API.get("/config/providers/models");
    },

    async reset() {
      return API.post("/config/reset");
    },

    async restart() {
      return API.post("/config/restart");
    },

    async restartStatus() {
      return API.get("/config/restart/status");
    },
  },

  health: {
    async check() {
      return API.get("/health");
    },
  },

  auth: {
    async login(password) {
      const fingerprint = await API.getFingerprint();
      return API.post("/auth/login", { password, fingerprint });
    },

    async verify() {
      const fingerprint = await API.getFingerprint();
      return API.post("/auth/verify", { fingerprint });
    },

    async status() {
      return API.get("/auth/status");
    },
  },
};
