import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "@/services/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  steps?: any[];
  reasoning?: string;
  tool_calls?: ToolCall[];
  attachments?: any[];
  isStreaming?: boolean;
  isError?: boolean;
  sender_id?: string;
  status?: string;
}

interface ToolCall {
  id: string;
  name: string;
  arguments: string;
  result?: string;
  resultExpanded?: boolean;
  file_info?: {
    file_id: string;
    filename: string;
    original_name: string;
    file_type: string;
  };
  generated_images?: Array<{
    path: string;
    original_name: string;
  }>;
}

type WSStatus = "connecting" | "connected" | "disconnected" | "reconnecting";

export const useChatStore = defineStore("chat", () => {
  const messages = ref<Message[]>([]);
  const currentSessionId = ref("default");
  const isStreaming = ref(false);
  const enableReasoning = ref(true);
  const wsStatus = ref<WSStatus>("disconnected");
  const wsConnection = ref<WebSocket | null>(null);

  const reconnectAttempts = ref(0);
  const maxReconnectAttempts = 5;
  const reconnectDelay = 3000;
  const pendingMessages = ref<any[]>([]);

  const messageCount = computed(() => messages.value.length);
  const lastMessage = computed(() => messages.value[messages.value.length - 1]);

  const loadHistory = async () => {
    try {
      if (api?.chat) {
        const history = await api.chat.getHistory(currentSessionId.value);
        if (history?.messages) {
          messages.value = history.messages.map((msg: any) => {
            const normalizedToolCalls = (msg.tool_calls || []).map((tc: any) => ({
              id: tc.id || tc.tool_call_id || "",
              name: tc.function?.name || tc.name || "",
              arguments: typeof tc.function?.arguments === "object"
                ? JSON.stringify(tc.function.arguments)
                : tc.function?.arguments || tc.arguments || "",
              result: tc.result || "",
              resultExpanded: false,
              file_info: tc.file_info || undefined,
              generated_images: tc.generated_images || [],
            }));
            return {
              ...msg,
              isStreaming: false,
              isError: false,
              steps: msg.steps || [],
              reasoning: msg.reasoning || msg.reasoning_content || "",
              tool_calls: normalizedToolCalls,
              attachments: msg.attachments || [],
            };
          });
        }
      }
    } catch (e) {
      console.error("[ChatStore] Failed to load history:", e);
    }
  };

  const loadConfig = async () => {
    try {
      if (api?.config) {
        const config = await api.config.get();
        enableReasoning.value = config.model?.enable_reasoning ?? true;
      }
    } catch (e) {
      console.error("[ChatStore] Failed to load config:", e);
    }
  };

  const initWebSocket = () => {
    if (wsConnection.value) {
      wsConnection.value.close();
    }

    wsStatus.value = "connecting";
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${location.host}/api/chat/ws/${currentSessionId.value}`;

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log("[ChatStore] WebSocket connected");
        wsStatus.value = "connected";
        reconnectAttempts.value = 0;
        flushPendingMessages();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (e) {
          console.error("[ChatStore] Failed to parse message:", e);
        }
      };

      ws.onerror = (error) => {
        console.error("[ChatStore] WebSocket error:", error);
      };

      ws.onclose = (event) => {
        console.log("[ChatStore] WebSocket closed:", event.code);
        wsStatus.value = "disconnected";

        if (event.code !== 1000 && event.code !== 1001) {
          scheduleReconnect();
        }
      };

      wsConnection.value = ws;
    } catch (e) {
      console.error("[ChatStore] Failed to create WebSocket:", e);
      wsStatus.value = "disconnected";
      scheduleReconnect();
    }
  };

  const scheduleReconnect = () => {
    if (reconnectAttempts.value >= maxReconnectAttempts) {
      console.error("[ChatStore] Max reconnect attempts reached");
      return;
    }

    wsStatus.value = "reconnecting";
    reconnectAttempts.value++;

    const delay = reconnectDelay * Math.pow(2, reconnectAttempts.value - 1);
    console.log(
      `[ChatStore] Reconnecting in ${delay}ms (attempt ${reconnectAttempts.value})`,
    );

    setTimeout(() => {
      initWebSocket();
    }, delay);
  };

  const disconnectWebSocket = () => {
    if (wsConnection.value) {
      wsConnection.value.close(1000, "Manual close");
      wsConnection.value = null;
    }
    wsStatus.value = "disconnected";
  };

  const sendWebSocketMessage = (data: any) => {
    if (wsStatus.value === "connected" && wsConnection.value) {
      wsConnection.value.send(JSON.stringify(data));
    } else {
      pendingMessages.value.push({
        id: Date.now(),
        data,
        timestamp: Date.now(),
      });

      if (wsStatus.value === "disconnected") {
        initWebSocket();
      }
    }
  };

  const flushPendingMessages = () => {
    while (pendingMessages.value.length > 0 && wsStatus.value === "connected") {
      const pending = pendingMessages.value.shift();
      if (pending) {
        wsConnection.value?.send(JSON.stringify(pending.data));
      }
    }
  };

  const handleWebSocketMessage = (data: any) => {
    switch (data.type) {
      case "content":
        appendContent(data.content);
        break;
      case "reasoning":
      case "reasoning_delta":
        appendReasoning(data.content);
        break;
      case "step":
        addStep(data.step);
        break;
      case "tool_start":
        addToolCall(data);
        break;
      case "tool_result":
        updateToolCallResult(data);
        break;
      case "status":
        setMessageStatus(data.content);
        break;
      case "done":
        isStreaming.value = false;
        const lastMsg = messages.value[messages.value.length - 1];
        if (lastMsg) {
          lastMsg.isStreaming = false;
          lastMsg.status = undefined;
        }
        break;
      case "error":
        handleError(data.content || data.message);
        break;
      default:
        if (data.content) {
          appendContent(data.content);
        }
    }
  };

  const appendContent = (content: string | unknown) => {
    const lastMsg = messages.value[messages.value.length - 1];
    let contentStr: string;
    if (typeof content === "string") {
      contentStr = content;
    } else if (Array.isArray(content)) {
      contentStr = content
        .map((item: unknown) => {
          if (typeof item === "string") return item;
          if (item && typeof item === "object") {
            const obj = item as Record<string, unknown>;
            if (obj.text) return String(obj.text);
            if (obj.content) return String(obj.content);
            return JSON.stringify(item);
          }
          return String(item);
        })
        .join("");
    } else if (content) {
      contentStr = String(content);
    } else {
      contentStr = "";
    }

    if (lastMsg?.role === "assistant") {
      lastMsg.content += contentStr;
    } else {
      messages.value.push({
        id: Date.now().toString(),
        role: "assistant",
        content: contentStr,
        sender_id: "agent",
        isStreaming: true,
        isError: false,
        timestamp: Date.now(),
        steps: [],
        reasoning: "",
        attachments: [],
      });
    }
  };

  const appendReasoning = (content: string) => {
    const lastMsg = messages.value[messages.value.length - 1];
    if (lastMsg?.role === "assistant") {
      lastMsg.reasoning = (lastMsg.reasoning || "") + content;
    }
  };

  const setMessageStatus = (status: string) => {
    const lastMsg = messages.value[messages.value.length - 1];
    if (lastMsg?.role === "assistant") {
      lastMsg.status = status;
    }
  };

  const addStep = (step: any) => {
    const lastMsg = messages.value[messages.value.length - 1];
    if (lastMsg?.role === "assistant") {
      if (!lastMsg.steps) lastMsg.steps = [];
      lastMsg.steps.push({ ...step, resultExpanded: false });
    }
  };

  const addToolCall = (data: any) => {
    const lastMsg = messages.value[messages.value.length - 1];
    if (lastMsg?.role === "assistant") {
      if (!lastMsg.tool_calls) lastMsg.tool_calls = [];
      const metadata = data.metadata || {};
      lastMsg.tool_calls.push({
        id: Date.now().toString(),
        name: metadata.tool_name || "unknown",
        arguments: JSON.stringify(metadata.tool_args || {}),
        result: undefined,
        resultExpanded: false,
        generated_images: metadata.generated_images || [],
      });
    }
  };

  const updateToolCallResult = (data: any) => {
    const lastMsg = messages.value[messages.value.length - 1];
    if (
      lastMsg?.role === "assistant" &&
      lastMsg.tool_calls &&
      lastMsg.tool_calls.length > 0
    ) {
      const lastToolCall = lastMsg.tool_calls[lastMsg.tool_calls.length - 1];
      lastToolCall.result = data.content || data.result || "completed";
      if (data.metadata?.file_info) {
        lastToolCall.file_info = data.metadata.file_info;
      }
      if (data.metadata?.generated_images) {
        lastToolCall.generated_images = data.metadata.generated_images;
      }
    }
  };

  const handleError = (message: string) => {
    const lastMsg = messages.value[messages.value.length - 1];
    if (lastMsg?.isStreaming) {
      lastMsg.isStreaming = false;
      lastMsg.isError = true;
      lastMsg.content += "\n\n❌ 错误: " + message;
    } else {
      messages.value.push({
        id: Date.now().toString(),
        role: "assistant",
        content: "❌ 发生错误: " + message,
        sender_id: "agent",
        isStreaming: false,
        isError: true,
        timestamp: Date.now(),
        steps: [],
        reasoning: "",
        attachments: [],
      });
    }
    isStreaming.value = false;
  };

  const sendMessage = async (content: string, attachments: any[] = []) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content,
      timestamp: Date.now(),
      attachments,
    };

    messages.value.push(userMessage);
    isStreaming.value = true;

    const aiMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: "assistant",
      content: "",
      sender_id: "agent",
      isStreaming: true,
      isError: false,
      timestamp: Date.now(),
      steps: [],
      reasoning: "",
      attachments: [],
    };
    messages.value.push(aiMessage);

    if (wsStatus.value === "connected") {
      sendWebSocketMessage({
        type: "message",
        content,
        attachments,
        session_id: currentSessionId.value,
      });
    } else {
      try {
        if (api?.chat) {
          const response = await api.chat.send(
            content,
            currentSessionId.value,
            attachments,
          );
          if (response?.content) {
            const lastMsg = messages.value[messages.value.length - 1];
            if (lastMsg && lastMsg.role === "assistant") {
              lastMsg.content = response.content;
              lastMsg.isStreaming = false;
              lastMsg.reasoning = response.reasoning || "";
            }
          }
          isStreaming.value = false;
        }
      } catch (e) {
        handleError((e as Error).message || "请求失败");
      }
    }
  };

  const clearHistory = async () => {
    try {
      if (api?.chat) {
        await api.chat.clearHistory(currentSessionId.value);
      }
      messages.value = [];
    } catch (e) {
      console.error("[ChatStore] Failed to clear history:", e);
    }
  };

  return {
    messages,
    currentSessionId,
    isStreaming,
    enableReasoning,
    wsStatus,
    messageCount,
    lastMessage,
    loadHistory,
    loadConfig,
    initWebSocket,
    disconnectWebSocket,
    sendMessage,
    clearHistory,
  };
});
