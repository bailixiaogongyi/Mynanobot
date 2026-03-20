<template>
  <div class="page-container tasks-page">
    <div class="page-header">
      <h2>任务监控</h2>
    </div>

    <div class="dashboard-stats">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total }}</div>
        <div class="stat-label">总任务</div>
      </div>
      <div class="stat-card stat-running">
        <div class="stat-value">{{ stats.running }}</div>
        <div class="stat-label">进行中</div>
      </div>
      <div class="stat-card stat-completed">
        <div class="stat-value">{{ stats.completed }}</div>
        <div class="stat-label">已完成</div>
      </div>
      <div class="stat-card stat-failed">
        <div class="stat-value">{{ stats.failed }}</div>
        <div class="stat-label">失败</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">
          {{ formatDuration(stats.avg_duration_seconds) }}
        </div>
        <div class="stat-label">平均耗时</div>
      </div>
    </div>

    <div class="dashboard-toolbar">
      <div class="tab-group">
        <button
          :class="['tab-btn', { active: activeTab === 'tasks' }]"
          @click="activeTab = 'tasks'"
        >
          📋 任务列表
        </button>
        <button
          :class="['tab-btn', { active: activeTab === 'agents' }]"
          @click="activeTab = 'agents'"
        >
          <svg
            viewBox="0 0 24 24"
            fill="currentColor"
            width="16"
            height="16"
            style="vertical-align: middle; margin-right: 4px"
          >
            <path
              d="M13.5 2c0 .44-.19.84-.5 1.12V5h5a3 3 0 0 1 3 3v10a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3V8a3 3 0 0 1 3-3h5V3.12A1.5 1.5 0 1 1 13.5 2zM0 10h2v6H0v-6zm24 0h-2v6h2v-6zM9 14.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zm6-1.5a1.5 1.5 0 1 0-3 0 1.5 1.5 0 0 0 3 0z"
            />
          </svg>
          Agent监控
          <span v-if="runningAgents.length > 0" class="tab-badge">{{
            runningAgents.length
          }}</span>
        </button>
      </div>
      <button
        class="btn btn-secondary"
        @click="refreshData"
        v-if="activeTab === 'tasks'"
      >
        🔄 刷新
      </button>
    </div>

    <div class="dashboard-content" v-if="activeTab === 'tasks'">
      <div class="task-list-panel">
        <div class="panel-header">
          <h3>任务列表</h3>
          <span class="task-count">{{ filteredTasks.length }} 个任务</span>
        </div>
        <div class="task-list">
          <div
            v-for="task in filteredTasks"
            :key="task.id"
            :class="[
              'task-item',
              task.status,
              { selected: selectedTask?.id === task.id },
            ]"
            @click="selectTask(task)"
          >
            <div class="task-status-icon">
              <span v-if="task.status === 'running'">🔄</span>
              <span v-else-if="task.status === 'completed'">✅</span>
              <span v-else-if="task.status === 'failed'">❌</span>
              <span v-else-if="task.status === 'pending'">⏳</span>
              <span v-else>⬜</span>
            </div>
            <div class="task-info">
              <div class="task-title">{{ task.title }}</div>
              <div class="task-meta">
                <span class="task-role" v-if="task.role">{{
                  getRoleName(task.role)
                }}</span>
                <span class="task-time" v-if="task.created_at">{{
                  formatTime(task.created_at)
                }}</span>
              </div>
            </div>
            <div class="task-progress" v-if="task.status === 'running'">
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  :style="{ width: task.progress + '%' }"
                ></div>
              </div>
              <span class="progress-text">{{ task.progress }}%</span>
            </div>
            <div class="task-badge" v-else-if="task.status === 'completed'">
              已完成
            </div>
            <div
              class="task-badge badge-failed"
              v-else-if="task.status === 'failed'"
            >
              失败
            </div>
          </div>
          <div v-if="filteredTasks.length === 0" class="no-tasks">暂无任务</div>
        </div>
      </div>

      <div class="execution-panel">
        <div class="panel-header">
          <h3>执行详情</h3>
          <span
            v-if="selectedTask"
            :class="['execution-status', selectedTask.status]"
          >
            {{ getStatusText(selectedTask.status) }}
          </span>
        </div>

        <div v-if="selectedTask" class="execution-content">
          <div class="execution-info">
            <div class="info-row">
              <span class="info-label">任务:</span>
              <span class="info-value">{{ selectedTask.title }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">角色:</span>
              <span class="info-value">{{
                getRoleName(selectedTask.role) || "-"
              }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">状态:</span>
              <span class="info-value" :class="selectedTask.status">{{
                getStatusText(selectedTask.status)
              }}</span>
            </div>
            <div class="info-row" v-if="selectedTask.status === 'running'">
              <span class="info-label">进度:</span>
              <div class="progress-inline">
                <div class="progress-bar" style="width: 120px">
                  <div
                    class="progress-fill"
                    :style="{ width: selectedTask.progress + '%' }"
                  ></div>
                </div>
                <span
                  >{{ selectedTask.progress }}% -
                  {{ selectedTask.progress_message || "执行中" }}</span
                >
              </div>
            </div>
            <div class="info-row">
              <span class="info-label">创建:</span>
              <span class="info-value">{{
                formatTime(selectedTask.created_at)
              }}</span>
            </div>
            <div class="info-row" v-if="selectedTask.started_at">
              <span class="info-label">开始:</span>
              <span class="info-value">{{
                formatTime(selectedTask.started_at)
              }}</span>
            </div>
            <div class="info-row" v-if="selectedTask.completed_at">
              <span class="info-label">完成:</span>
              <span class="info-value">{{
                formatTime(selectedTask.completed_at)
              }}</span>
            </div>
          </div>

          <div class="logs-section">
            <div class="logs-header">
              <span>执行日志</span>
              <button class="logs-refresh-btn" @click="loadLogs">🔄</button>
            </div>
            <div class="logs-container" ref="logsContainer">
              <div v-if="logsLoading" class="logs-loading">加载中...</div>
              <div v-else-if="taskLogs.length === 0" class="logs-empty">
                暂无日志
              </div>
              <div v-else class="logs-list">
                <div
                  v-for="(log, index) in taskLogs"
                  :key="index"
                  :class="['log-entry', log.level]"
                >
                  <span class="log-time">{{
                    formatLogTime(log.timestamp)
                  }}</span>
                  <span class="log-icon">{{ getLogIcon(log.type) }}</span>
                  <span class="log-message">{{ log.message }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="execution-controls">
            <button
              class="btn btn-warning"
              @click="pauseTask(selectedTask.id)"
              v-if="selectedTask.status === 'running'"
            >
              ⏸ 暂停
            </button>
            <button
              class="btn btn-danger"
              @click="cancelTask(selectedTask.id)"
              v-if="
                selectedTask.status === 'running' ||
                selectedTask.status === 'pending'
              "
            >
              ⏹ 取消
            </button>
            <button
              class="btn btn-secondary"
              @click="restartTask(selectedTask.id)"
              v-if="
                selectedTask.status === 'pending' ||
                selectedTask.status === 'failed' ||
                selectedTask.status === 'cancelled'
              "
            >
              🔄 重启
            </button>
            <button
              class="btn btn-danger"
              @click="deleteTask(selectedTask.id)"
              v-if="
                selectedTask.status === 'pending' ||
                selectedTask.status === 'failed' ||
                selectedTask.status === 'cancelled' ||
                selectedTask.status === 'completed'
              "
            >
              🗑 删除
            </button>
          </div>

          <div
            class="result-section"
            v-if="selectedTask.result || selectedTask.error"
          >
            <div class="result-header">执行结果</div>
            <div v-if="selectedTask.error" class="result-content error">
              {{ selectedTask.error }}
            </div>
            <div v-else class="result-content">
              {{ truncateResult(selectedTask.result) }}
            </div>
          </div>
        </div>
        <div v-else class="no-selection">
          <p>点击左侧任务查看执行详情</p>
        </div>
      </div>
    </div>

    <div class="dashboard-content agents-panel" v-if="activeTab === 'agents'">
      <div class="console-monitor">
        <div class="console-topbar">
          <div class="console-title">
            <span class="console-icon">📟</span>
            <span>子Agent执行日志</span>
          </div>
          <div class="console-actions">
            <button
              class="console-btn"
              @click="refreshAgents"
              :disabled="agentsLoading"
            >
              <span :class="{ spinning: agentsLoading }">🔄</span>
            </button>
          </div>
        </div>

        <div class="agent-tabs" v-if="agents.length > 0">
          <div
            v-for="agent in agents"
            :key="agent.task_id"
            :class="[
              'agent-tab',
              { active: activeAgentId === agent.task_id },
              agent.status,
            ]"
            @click="switchAgent(agent.task_id)"
          >
            <span class="tab-icon">{{ agent.role_icon || "🤖" }}</span>
            <span class="tab-name">{{ agent.role }}</span>
            <span class="tab-status" :class="agent.status">{{
              getAgentStatusDot(agent.status)
            }}</span>
            <span class="tab-close" @click.stop="closeAgentLog(agent.task_id)"
              >×</span
            >
          </div>
          <div v-if="agents.length === 0" class="no-agents">
            暂无运行中的Agent
          </div>
        </div>

        <div class="console-main">
          <div class="console-viewport" ref="consoleViewport">
            <div
              v-if="
                !activeAgentId || (agentLogs[activeAgentId]?.length ?? 0) === 0
              "
              class="console-empty"
            >
              <div class="empty-icon">📟</div>
              <div class="empty-text">
                {{ agents.length === 0 ? "暂无运行中的Agent" : "等待日志..." }}
              </div>
            </div>
            <div v-else class="console-logs">
              <div
                v-for="(log, index) in agentLogs[activeAgentId] || []"
                :key="index"
                :class="['log-entry', log.level]"
              >
                <span class="log-time">{{
                  formatAgentLogTime(log.timestamp)
                }}</span>
                <span class="log-type">{{ getAgentLogIcon(log.type) }}</span>
                <span class="log-content">{{ log.message }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="console-statusbar">
          <div class="status-left">
            <span v-if="activeAgentId">
              {{ agentLogs[activeAgentId]?.length ?? 0 }} 条日志
            </span>
          </div>
          <div class="status-right">
            <span v-if="lastAgentUpdateTime"
              >最后更新: {{ lastAgentUpdateTime }}</span
            >
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from "vue";
import api from "@/services/api";

interface Task {
  id: string;
  title: string;
  status: string;
  role?: string;
  progress?: number;
  progress_message?: string;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  result?: string;
  error?: string;
}

interface LogEntry {
  timestamp: string;
  type: string;
  message: string;
  level: string;
}

const tasks = ref<Task[]>([]);
const selectedTask = ref<Task | null>(null);
const statusFilter = ref("all");
const logsLoading = ref(false);
const taskLogs = ref<LogEntry[]>([]);
const logsContainer = ref<HTMLElement | null>(null);
let refreshInterval: number | null = null;

const activeTab = ref<"tasks" | "agents">("tasks");

interface Agent {
  task_id: string;
  role: string;
  role_icon?: string;
  status: string;
}

interface AgentLogEntry {
  timestamp: string;
  type: string;
  message: string;
  level: string;
  index?: number;
}

const agents = ref<Agent[]>([]);
const agentsLoading = ref(false);
const activeAgentId = ref<string | null>(null);
const agentLogs = ref<Record<string, AgentLogEntry[]>>({});
const agentLogIndexes = ref<Record<string, number>>({});
const lastAgentUpdateTime = ref("");
const consoleViewport = ref<HTMLElement | null>(null);
let agentRefreshInterval: number | null = null;

const runningAgents = computed(() =>
  agents.value.filter((a) => a.status === "running"),
);

const stats = computed(() => {
  const total = tasks.value.length;
  const running = tasks.value.filter((t) => t.status === "running").length;
  const completed = tasks.value.filter((t) => t.status === "completed").length;
  const failed = tasks.value.filter((t) => t.status === "failed").length;

  const completedTasks = tasks.value.filter(
    (t) => t.completed_at && t.started_at,
  );
  let avgDuration = 0;
  if (completedTasks.length > 0) {
    const totalSeconds = completedTasks.reduce((sum, t) => {
      const start = new Date(t.started_at!).getTime();
      const end = new Date(t.completed_at!).getTime();
      return sum + (end - start) / 1000;
    }, 0);
    avgDuration = totalSeconds / completedTasks.length;
  }

  return {
    total,
    running,
    completed,
    failed,
    avg_duration_seconds: avgDuration,
  };
});

const filteredTasks = computed(() => {
  if (statusFilter.value === "all") return tasks.value;
  return tasks.value.filter((t) => t.status === statusFilter.value);
});

const formatDuration = (seconds: number) => {
  if (!seconds) return "0s";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600)
    return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
};

const formatTime = (time: string | undefined) => {
  if (!time) return "-";
  const date = new Date(time);
  return date.toLocaleString("zh-CN");
};

const formatLogTime = (timestamp: string | undefined) => {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  return date.toLocaleTimeString("zh-CN");
};

const getRoleName = (role: string | undefined) => {
  if (!role) return "-";
  const roleNames: Record<string, string> = {
    planner: "规划师",
    executor: "执行者",
    researcher: "研究者",
    coder: "程序员",
    default: "默认",
  };
  return roleNames[role] || role;
};

const getStatusText = (status: string) => {
  const statusTexts: Record<string, string> = {
    pending: "等待中",
    running: "进行中",
    completed: "已完成",
    failed: "失败",
    cancelled: "已取消",
    paused: "已暂停",
  };
  return statusTexts[status] || status;
};

const getLogIcon = (type: string) => {
  const icons: Record<string, string> = {
    info: "ℹ️",
    warning: "⚠️",
    error: "❌",
    success: "✅",
    step: "👉",
    tool: "🔧",
    result: "📊",
  };
  return icons[type] || "📝";
};

const truncateResult = (result: string | undefined) => {
  if (!result) return "";
  if (result.length > 500) return result.substring(0, 500) + "...";
  return result;
};

const loadTasks = async () => {
  try {
    if (api.tasks) {
      const data = await api.tasks.list();
      tasks.value = data?.tasks || [];
    }
  } catch (e) {
    console.error("[TasksPage] Failed to load tasks:", e);
  }
};

const loadLogs = async () => {
  if (!selectedTask.value) return;
  logsLoading.value = true;
  try {
    if (api.tasks) {
      const data = await api.tasks.logs(selectedTask.value.id);
      taskLogs.value = data?.logs || [];
      await nextTick();
      if (logsContainer.value) {
        logsContainer.value.scrollTop = logsContainer.value.scrollHeight;
      }
    }
  } catch (e) {
    console.error("[TasksPage] Failed to load logs:", e);
  } finally {
    logsLoading.value = false;
  }
};

const selectTask = (task: Task) => {
  selectedTask.value = task;
  loadLogs();
};

const refreshData = () => {
  loadTasks();
};

const pauseTask = async (taskId: string) => {
  try {
    if (api.tasks) {
      await api.tasks.pause(taskId);
      loadTasks();
    }
  } catch (e) {
    console.error("[TasksPage] Failed to pause task:", e);
  }
};

const cancelTask = async (taskId: string) => {
  try {
    if (api.tasks) {
      await api.tasks.cancel(taskId);
      loadTasks();
    }
  } catch (e) {
    console.error("[TasksPage] Failed to cancel task:", e);
  }
};

const restartTask = async (taskId: string) => {
  try {
    if (api.tasks) {
      await api.tasks.restart(taskId);
      loadTasks();
    }
  } catch (e) {
    console.error("[TasksPage] Failed to restart task:", e);
  }
};

const deleteTask = async (taskId: string) => {
  try {
    if (api.tasks) {
      await api.tasks.delete(taskId);
      if (selectedTask.value?.id === taskId) {
        selectedTask.value = null;
      }
      loadTasks();
    }
  } catch (e) {
    console.error("[TasksPage] Failed to delete task:", e);
  }
};

onMounted(() => {
  loadTasks();
  refreshInterval = window.setInterval(loadTasks, 5000);
  refreshAgents();
  agentRefreshInterval = window.setInterval(refreshAgentLogs, 2000);
});

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
  if (agentRefreshInterval) {
    clearInterval(agentRefreshInterval);
  }
});

const getAgentStatusDot = (status: string) => {
  const dots: Record<string, string> = {
    running: "●",
    completed: "✓",
    failed: "✗",
    pending: "○",
  };
  return dots[status] || "○";
};

const getAgentLogIcon = (type: string) => {
  const icons: Record<string, string> = {
    info: "ℹ",
    warning: "⚠",
    error: "❌",
    success: "✅",
    step: "👉",
    tool: "🔧",
    result: "📊",
  };
  return icons[type] || "📝";
};

const formatAgentLogTime = (timestamp: string) => {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  return date.toLocaleTimeString("zh-CN", { hour12: false });
};

const refreshAgents = async () => {
  agentsLoading.value = true;
  try {
    const data = await api.agents.list();
    agents.value = Array.isArray(data) ? data : (data?.agents || []);

    if (runningAgents.value.length > 0 && !activeAgentId.value) {
      switchAgent(runningAgents.value[0].task_id);
    } else if (runningAgents.value.length === 0) {
      activeAgentId.value = null;
    }
    lastAgentUpdateTime.value = new Date().toLocaleTimeString("zh-CN", {
      hour12: false,
    });
  } catch (error) {
    console.error("[TasksPage] Failed to refresh agents:", error);
  } finally {
    agentsLoading.value = false;
  }
};

const refreshAgentLogs = async () => {
  for (const agent of runningAgents.value) {
    await fetchAgentLogs(agent.task_id);
  }
};

const fetchAgentLogs = async (taskId: string) => {
  try {
    const sinceIndex = agentLogIndexes.value[taskId] || 0;
    const data = await api.agents.logs(taskId, sinceIndex);
    if (data.logs && data.logs.length > 0) {
      if (!agentLogs.value[taskId]) {
        agentLogs.value[taskId] = [];
      }
      agentLogs.value[taskId] = [...agentLogs.value[taskId], ...data.logs];
      const lastIndex = data.logs[data.logs.length - 1]?.index;
      if (lastIndex !== undefined) {
        agentLogIndexes.value[taskId] = lastIndex + 1;
      }

      await nextTick();
      if (consoleViewport.value) {
        consoleViewport.value.scrollTop = consoleViewport.value.scrollHeight;
      }
    }
  } catch (error) {
    console.error("[TasksPage] Failed to fetch agent logs:", error);
  }
};

const switchAgent = (taskId: string) => {
  activeAgentId.value = taskId;
  fetchAgentLogs(taskId);
};

const closeAgentLog = (taskId: string) => {
  delete agentLogs.value[taskId];
  delete agentLogIndexes.value[taskId];
  if (activeAgentId.value === taskId) {
    const remaining = Object.keys(agentLogs.value);
    activeAgentId.value = remaining.length > 0 ? remaining[0] : null;
  }
};
</script>

<style scoped lang="scss">
.tasks-page {
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

.dashboard-stats {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 20px;

  .stat-card {
    background: var(--color-bg-surface, #fff);
    border: 1px solid var(--color-border, #e2e8f0);
    border-radius: 8px;
    padding: 16px;
    text-align: center;

    .stat-value {
      font-size: 28px;
      font-weight: 600;
      color: var(--color-text-primary, #1e293b);
    }

    .stat-label {
      font-size: 14px;
      color: var(--color-text-secondary, #64748b);
      margin-top: 4px;
    }

    &.stat-running .stat-value {
      color: #3b82f6;
    }
    &.stat-completed .stat-value {
      color: #10b981;
    }
    &.stat-failed .stat-value {
      color: #ef4444;
    }
  }
}

.dashboard-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  .filter-group {
    display: flex;
    gap: 8px;

    .filter-btn {
      padding: 8px 16px;
      border: 1px solid var(--color-border, #e2e8f0);
      background: var(--color-bg-surface, #fff);
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        background: var(--color-bg-muted, #f1f5f9);
      }

      &.active {
        background: var(--color-primary, #3b82f6);
        color: #fff;
        border-color: var(--color-primary, #3b82f6);
      }
    }
  }
}

.dashboard-content {
  display: grid;
  grid-template-columns: 40% 60%;
  gap: 20px;
  height: calc(100vh - 300px);
}

.task-list-panel,
.execution-panel {
  background: var(--color-bg-surface, #fff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);

  h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
  }

  .task-count {
    font-size: 14px;
    color: var(--color-text-secondary, #64748b);
  }
}

.task-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: var(--color-bg-muted, #f1f5f9);
  }

  &.selected {
    background: var(--color-primary-light, #dbeafe);
  }

  .task-status-icon {
    font-size: 20px;
  }

  .task-info {
    flex: 1;
    min-width: 0;

    .task-title {
      font-weight: 500;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .task-meta {
      display: flex;
      gap: 8px;
      font-size: 12px;
      color: var(--color-text-secondary, #64748b);
      margin-top: 4px;
    }
  }

  .task-progress {
    display: flex;
    align-items: center;
    gap: 8px;

    .progress-bar {
      width: 60px;
      height: 6px;
      background: var(--color-bg-muted, #f1f5f9);
      border-radius: 3px;
      overflow: hidden;

      .progress-fill {
        height: 100%;
        background: var(--color-primary, #3b82f6);
        transition: width 0.3s;
      }
    }

    .progress-text {
      font-size: 12px;
      color: var(--color-text-secondary, #64748b);
    }
  }

  .task-badge {
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 4px;
    background: #d1fae5;
    color: #065f46;

    &.badge-failed {
      background: #fee2e2;
      color: #991b1b;
    }
  }
}

.no-tasks {
  text-align: center;
  padding: 40px;
  color: var(--color-text-muted, #94a3b8);
}

.execution-panel {
  .execution-content {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
  }

  .execution-status {
    font-size: 14px;
    padding: 4px 12px;
    border-radius: 4px;

    &.running {
      background: #dbeafe;
      color: #1e40af;
    }
    &.completed {
      background: #d1fae5;
      color: #065f46;
    }
    &.failed {
      background: #fee2e2;
      color: #991b1b;
    }
  }
}

.execution-info {
  margin-bottom: 20px;

  .info-row {
    display: flex;
    gap: 12px;
    padding: 8px 0;
    border-bottom: 1px solid var(--color-border-light, #f1f5f9);

    .info-label {
      width: 60px;
      color: var(--color-text-secondary, #64748b);
    }

    .info-value {
      flex: 1;

      &.running {
        color: #3b82f6;
      }
      &.completed {
        color: #10b981;
      }
      &.failed {
        color: #ef4444;
      }
    }
  }

  .progress-inline {
    display: flex;
    align-items: center;
    gap: 8px;

    .progress-bar {
      height: 6px;
      background: var(--color-bg-muted, #f1f5f9);
      border-radius: 3px;
      overflow: hidden;

      .progress-fill {
        height: 100%;
        background: var(--color-primary, #3b82f6);
      }
    }
  }
}

.logs-section {
  margin-bottom: 20px;

  .logs-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    font-weight: 500;

    .logs-refresh-btn {
      background: none;
      border: none;
      cursor: pointer;
      font-size: 16px;
    }
  }

  .logs-container {
    height: 200px;
    overflow-y: auto;
    background: var(--color-bg-muted, #f1f5f9);
    border-radius: 6px;
    padding: 12px;
    font-size: 13px;

    .log-entry {
      display: flex;
      gap: 8px;
      padding: 4px 0;

      .log-time {
        color: var(--color-text-muted, #94a3b8);
      }

      .log-icon {
        flex-shrink: 0;
      }
    }
  }
}

.execution-controls {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.result-section {
  .result-header {
    font-weight: 500;
    margin-bottom: 8px;
  }

  .result-content {
    background: var(--color-bg-muted, #f1f5f9);
    padding: 12px;
    border-radius: 6px;
    font-size: 13px;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 200px;
    overflow-y: auto;

    &.error {
      background: #fee2e2;
      color: #991b1b;
    }
  }
}

.no-selection {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-muted, #94a3b8);
}

.agents-panel {
  height: calc(100vh - 280px);
}

.console-monitor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-bg-surface, #fff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  overflow: hidden;
}

.console-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--color-bg-muted, #f1f5f9);
  border-bottom: 1px solid var(--color-border, #e2e8f0);

  .console-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    font-size: 14px;
  }

  .console-btn {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 16px;
    padding: 4px 8px;
    border-radius: 4px;
    transition: background 0.2s;

    &:hover {
      background: var(--color-bg-surface, #fff);
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .spinning {
      display: inline-block;
      animation: spin 1s linear infinite;
    }
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.agent-tabs {
  display: flex;
  gap: 4px;
  padding: 8px 12px;
  background: var(--color-bg-base, #f8fafc);
  border-bottom: 1px solid var(--color-border, #e2e8f0);
  overflow-x: auto;

  .agent-tab {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    background: var(--color-bg-surface, #fff);
    border: 1px solid var(--color-border, #e2e8f0);
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    white-space: nowrap;
    transition: all 0.2s;

    &:hover {
      background: var(--color-bg-muted, #f1f5f9);
    }

    &.active {
      background: var(--color-primary-light, #dbeafe);
      border-color: var(--color-primary, #3b82f6);
    }

    &.running .tab-status {
      color: #3b82f6;
    }
    &.completed .tab-status {
      color: #10b981;
    }
    &.failed .tab-status {
      color: #ef4444;
    }

    .tab-close {
      margin-left: 4px;
      opacity: 0.5;
      &:hover {
        opacity: 1;
      }
    }
  }
}

.no-agents {
  padding: 8px;
  color: var(--color-text-muted, #94a3b8);
  font-size: 13px;
}

.console-main {
  flex: 1;
  overflow: hidden;
}

.console-viewport {
  height: 100%;
  overflow-y: auto;
  padding: 12px;
  background: #1e1e1e;
  color: #d4d4d4;
  font-family: "Consolas", "Monaco", monospace;
  font-size: 13px;
}

.console-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #666;

  .empty-icon {
    font-size: 48px;
    margin-bottom: 16px;
  }
}

.console-logs {
  .log-entry {
    display: flex;
    gap: 8px;
    padding: 2px 0;
    line-height: 1.5;

    .log-time {
      color: #666;
      flex-shrink: 0;
    }

    .log-type {
      flex-shrink: 0;
    }

    &.error {
      color: #f14c4c;
    }
    &.warning {
      color: #cca700;
    }
    &.success {
      color: #4ec9b0;
    }
  }
}

.console-statusbar {
  display: flex;
  justify-content: space-between;
  padding: 8px 16px;
  background: var(--color-bg-muted, #f1f5f9);
  border-top: 1px solid var(--color-border, #e2e8f0);
  font-size: 12px;
  color: var(--color-text-secondary, #64748b);
}

.tab-group {
  display: flex;
  gap: 4px;

  .tab-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    background: var(--color-bg-surface, #fff);
    border: 1px solid var(--color-border, #e2e8f0);
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    transition: all 0.2s;

    &:hover {
      background: var(--color-bg-muted, #f1f5f9);
    }

    &.active {
      background: var(--color-primary-light, #dbeafe);
      border-color: var(--color-primary, #3b82f6);
      color: var(--color-primary, #3b82f6);
    }

    .tab-badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 18px;
      height: 18px;
      padding: 0 5px;
      background: #ef4444;
      color: #fff;
      border-radius: 9px;
      font-size: 12px;
      font-weight: 600;
    }
  }
}
</style>
