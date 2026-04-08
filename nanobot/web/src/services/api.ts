const API_BASE = "/api";

const MAX_RETRIES = 5;
const RETRY_DELAY = 3000;

async function request(
  endpoint: string,
  options: RequestInit = {},
  retryCount = 0,
): Promise<any> {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (response.status === 429 && retryCount < MAX_RETRIES) {
    const retryAfter = response.headers.get("Retry-After");
    const baseDelay = retryAfter
      ? parseInt(retryAfter, 10) * 1000
      : RETRY_DELAY;
    const delay = baseDelay * Math.pow(2, retryCount);
    console.log(
      `[API] Rate limited, retrying in ${delay / 1000}s (attempt ${retryCount + 1}/${MAX_RETRIES})`,
    );
    await new Promise((resolve) => setTimeout(resolve, delay));
    return request(endpoint, options, retryCount + 1);
  }

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `API Error: ${response.status} ${response.statusText}${errorText ? ` - ${errorText}` : ""}`,
    );
  }

  return response.json();
}

export const api = {
  config: {
    get: () => request("/config/"),
    setModel: (model: string, enableReasoning?: boolean, provider?: string) => {
      const payload: any = { model };
      if (enableReasoning !== null) {
        payload.enable_reasoning = enableReasoning;
      }
      if (provider) {
        payload.provider = provider;
      }
      return request("/config/model", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    setReasoning: (enableReasoning: boolean) =>
      request("/config/agent/defaults", {
        method: "POST",
        body: JSON.stringify({ enable_reasoning: enableReasoning }),
      }),
    setToolCall: (enabled: boolean) =>
      request("/config/tools", {
        method: "POST",
        body: JSON.stringify({ enabled }),
      }),
    updateTools: (config: any) =>
      request("/config/tools/config", {
        method: "POST",
        body: JSON.stringify(config),
      }),
    updateProvider: (provider: string, config: any) =>
      request(`/config/provider/${provider}`, {
        method: "POST",
        body: JSON.stringify(config),
      }),
    testProvider: (provider: string) =>
      request(`/config/provider/${provider}/test`, { method: "POST" }),
    updateChannel: (channel: string, config: any) =>
      request(`/config/channel/${channel}`, {
        method: "POST",
        body: JSON.stringify(config),
      }),
    updateAgentDefaults: (config: any) =>
      request("/config/agent/defaults", {
        method: "POST",
        body: JSON.stringify(config),
      }),
    updateKnowledge: (config: any) =>
      request("/config/knowledge/config", {
        method: "POST",
        body: JSON.stringify(config),
      }),
    updateGateway: (config: any) =>
      request("/config/gateway", {
        method: "POST",
        body: JSON.stringify(config),
      }),
    updateUpload: (config: any) =>
      request("/config/upload", {
        method: "POST",
        body: JSON.stringify(config),
      }),
    addCustomModel: (model: any) =>
      request(`/config/provider/${model.provider}/models/custom`, {
        method: "POST",
        body: JSON.stringify(model),
      }),
    deleteCustomModel: (provider: string, modelId: string) =>
      request(
        `/config/provider/${provider}/models/custom?model_id=${encodeURIComponent(modelId)}`,
        {
          method: "DELETE",
        },
      ),
    restart: () => request("/config/restart", { method: "POST" }),
  },

  chat: {
    getHistory: (sessionId: string = "default") =>
      request(`/chat/sessions/${sessionId}/history`),
    send: (
      message: string,
      sessionId: string = "default",
      attachments?: any[],
    ) =>
      request(`/chat/send`, {
        method: "POST",
        body: JSON.stringify({
          content: message,
          chat_id: sessionId,
          attachments: attachments || [],
        }),
      }),
    clearHistory: (sessionId: string = "default") =>
      request(`/chat/sessions/${sessionId}/history`, { method: "DELETE" }),
  },

  tasks: {
    list: () => request("/dashboard/tasks"),
    logs: (taskId: string) => request(`/dashboard/tasks/${taskId}/logs`),
    pause: (taskId: string) =>
      request(`/dashboard/tasks/${taskId}/pause`, { method: "POST" }),
    cancel: (taskId: string) =>
      request(`/dashboard/tasks/${taskId}/cancel`, { method: "POST" }),
    restart: (taskId: string) =>
      request(`/dashboard/tasks/${taskId}/restart`, { method: "POST" }),
    delete: (taskId: string) =>
      request(`/dashboard/tasks/${taskId}`, { method: "DELETE" }),
  },

  agents: {
    list: () => request("/dashboard/agents"),
    logs: (taskId: string, sinceIndex: number = 0) =>
      request(`/dashboard/tasks/${taskId}/logs?since=${sinceIndex}`),
  },

  upload: {
    upload: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return fetch("/api/upload/upload", {
        method: "POST",
        body: formData,
      }).then((res) => {
        if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
        return res.json();
      });
    },
  },

  notes: {
    dirs: () => request("/notes/dirs"),
    list: (dir?: string) =>
      request(
        `/notes/list${dir ? `?directory=${encodeURIComponent(dir)}` : ""}`,
      ),
    read: (path: string) =>
      request(`/notes/read?path=${encodeURIComponent(path)}`),
    write: (path: string, content: string) =>
      request("/notes/save", {
        method: "POST",
        body: JSON.stringify({ path, content }),
      }),
    delete: (path: string) =>
      request("/notes/delete", {
        method: "POST",
        body: JSON.stringify({ path }),
      }),
    search: (query: string) =>
      request(`/notes/search?q=${encodeURIComponent(query)}`),
    index: (directory: string = "notes", force: boolean = false) =>
      request(
        `/notes/index?directory=${encodeURIComponent(directory)}&force=${force}`,
        {
          method: "POST",
        },
      ),
    indexStatus: () => request("/notes/index/status"),
  },

  skills: {
    list: () => request("/skills/list"),
    get: (name: string) => request(`/skills/${name}`),
  },

  marketplace: {
    sources: () => request("/marketplace/sources"),
    list: (
      params: {
        source?: string;
        query?: string;
        limit?: number;
        cursor?: string;
      } = {},
    ) => {
      const searchParams = new URLSearchParams();
      if (params.source) searchParams.append("source", params.source);
      if (params.query) searchParams.append("query", params.query);
      if (params.limit) searchParams.append("limit", String(params.limit));
      if (params.cursor) searchParams.append("cursor", params.cursor);
      const queryString = searchParams.toString();
      return request(
        `/marketplace/list${queryString ? `?${queryString}` : ""}`,
      );
    },
    detail: (slug: string) => request(`/marketplace/detail/${slug}`),
    search: (query: string) =>
      request(`/marketplace/search?q=${encodeURIComponent(query)}`),
    install: (slug: string, source: string) =>
      request("/marketplace/install", {
        method: "POST",
        body: JSON.stringify({ slug, source }),
      }),
    uninstall: (slug: string) =>
      request("/marketplace/uninstall", {
        method: "POST",
        body: JSON.stringify({ slug }),
      }),
    update: (slug: string, source: string) =>
      request("/marketplace/update", {
        method: "POST",
        body: JSON.stringify({ slug, source }),
      }),
  },

  stats: {
    getTokenStats: (period: string = "all") =>
      request(`/stats/tokens?period=${period}`),
    getDashboard: () => request("/dashboard/stats"),
  },

  dashboard: {
    getStats: () => request("/dashboard/stats"),
    getTasks: (status?: string) =>
      request(`/dashboard/tasks${status ? `?status=${status}` : ""}`),
    getTask: (taskId: string) => request(`/dashboard/tasks/${taskId}`),
    getTaskLogs: (taskId: string, since: number = 0) =>
      request(`/dashboard/tasks/${taskId}/logs?since=${since}`),
    pauseTask: (taskId: string) =>
      request(`/dashboard/tasks/${taskId}/pause`, { method: "POST" }),
    resumeTask: (taskId: string) =>
      request(`/dashboard/tasks/${taskId}/resume`, { method: "POST" }),
    cancelTask: (taskId: string) =>
      request(`/dashboard/tasks/${taskId}/cancel`, { method: "POST" }),
    deleteTask: (taskId: string) =>
      request(`/dashboard/tasks/${taskId}`, { method: "DELETE" }),
    restartTask: (taskId: string) =>
      request(`/dashboard/tasks/${taskId}/restart`, { method: "POST" }),
    getAgents: () => request("/dashboard/agents"),
    getEvents: (limit: number = 100) =>
      request(`/dashboard/events?limit=${limit}`),
    getMemory: () => request("/dashboard/memory"),
  },
};

export default api;
