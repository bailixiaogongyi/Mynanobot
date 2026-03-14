/**
 * Dashboard component for AiMate Web UI
 * Task monitoring and statistics dashboard with execution details
 */

const DashboardMonitor = {
  template: `
    <div class="dashboard-monitor">
        <!-- Stats Cards -->
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
                <div class="stat-value">{{ formatDuration(stats.avg_duration_seconds) }}</div>
                <div class="stat-label">平均耗时</div>
            </div>
        </div>

        <!-- Filter and Actions -->
        <div class="dashboard-toolbar">
            <div class="filter-group">
                <button 
                    v-for="filter in filters" 
                    :key="filter.value"
                    :class="['filter-btn', { active: statusFilter === filter.value }]"
                    @click="statusFilter = filter.value"
                >
                    {{ filter.label }}
                </button>
            </div>
            <button class="action-btn" @click="refreshData">
                🔄 刷新
            </button>
        </div>

        <!-- Main Content: Task List + Execution Details -->
        <div class="dashboard-content">
            <!-- Left: Task List (40%) -->
            <div class="task-list-panel">
                <div class="panel-header">
                    <h3>任务列表</h3>
                    <span class="task-count">{{ filteredTasks.length }} 个任务</span>
                </div>
                <div class="task-list">
                    <div
                        v-for="task in filteredTasks"
                        :key="task.id"
                        class="task-item"
                        :class="[task.status, { selected: selectedTask?.id === task.id }]"
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
                                <span class="task-role" v-if="task.role">{{ getRoleName(task.role) }}</span>
                                <span class="task-time" v-if="task.created_at">{{ formatTime(task.created_at) }}</span>
                            </div>
                        </div>
                        <div class="task-progress" v-if="task.status === 'running'">
                            <div class="progress-bar">
                                <div class="progress-fill" :style="{width: task.progress + '%'}"></div>
                            </div>
                            <span class="progress-text">{{ task.progress }}%</span>
                        </div>
                        <div class="task-badge" v-else-if="task.status === 'completed'">
                            已完成
                        </div>
                        <div class="task-badge badge-failed" v-else-if="task.status === 'failed'">
                            失败
                        </div>
                    </div>
                    <div v-if="filteredTasks.length === 0" class="no-tasks">
                        暂无任务
                    </div>
                </div>
            </div>

            <!-- Right: Execution Details (60%) -->
            <div class="execution-panel">
                <div class="panel-header">
                    <h3>执行详情</h3>
                    <span v-if="selectedTask" class="execution-status" :class="selectedTask.status">
                        {{ getStatusText(selectedTask.status) }}
                    </span>
                </div>
                
                <div v-if="selectedTask" class="execution-content">
                    <!-- Task Info -->
                    <div class="execution-info">
                        <div class="info-row">
                            <span class="info-label">任务:</span>
                            <span class="info-value">{{ selectedTask.title }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">角色:</span>
                            <span class="info-value">{{ getRoleName(selectedTask.role) || '-' }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">状态:</span>
                            <span class="info-value" :class="selectedTask.status">{{ getStatusText(selectedTask.status) }}</span>
                        </div>
                        <div class="info-row" v-if="selectedTask.status === 'running'">
                            <span class="info-label">进度:</span>
                            <div class="progress-inline">
                                <div class="progress-bar" style="width: 120px;">
                                    <div class="progress-fill" :style="{width: selectedTask.progress + '%'}"></div>
                                </div>
                                <span>{{ selectedTask.progress }}% - {{ selectedTask.progress_message || '执行中' }}</span>
                            </div>
                        </div>
                        <div class="info-row">
                            <span class="info-label">创建:</span>
                            <span class="info-value">{{ formatTime(selectedTask.created_at) }}</span>
                        </div>
                        <div class="info-row" v-if="selectedTask.started_at">
                            <span class="info-label">开始:</span>
                            <span class="info-value">{{ formatTime(selectedTask.started_at) }}</span>
                        </div>
                        <div class="info-row" v-if="selectedTask.completed_at">
                            <span class="info-label">完成:</span>
                            <span class="info-value">{{ formatTime(selectedTask.completed_at) }}</span>
                        </div>
                    </div>

                    <!-- Execution Logs -->
                    <div class="logs-section">
                        <div class="logs-header">
                            <span>执行日志</span>
                            <button class="logs-refresh-btn" @click="loadLogs">🔄</button>
                        </div>
                        <div class="logs-container" ref="logsContainer">
                            <div v-if="logsLoading" class="logs-loading">加载中...</div>
                            <div v-else-if="taskLogs.length === 0" class="logs-empty">暂无日志</div>
                            <div v-else class="logs-list">
                                <div 
                                    v-for="(log, index) in taskLogs" 
                                    :key="index"
                                    class="log-entry"
                                    :class="log.level"
                                >
                                    <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
                                    <span class="log-icon">{{ getLogIcon(log.type) }}</span>
                                    <span class="log-message">{{ log.message }}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Control Buttons -->
                    <!-- Task controls -->
                    <div class="execution-controls">
                        <!-- Running task controls -->
                        <button class="control-btn btn-pause" @click="pauseTask(selectedTask.id)" v-if="selectedTask.status === 'running'">
                            ⏸ 暂停
                        </button>
                        <button class="control-btn btn-cancel" @click="cancelTask(selectedTask.id)" v-if="selectedTask.status === 'running' || selectedTask.status === 'pending'">
                            ⏹ 取消
                        </button>
                        <!-- Non-running task controls -->
                        <button class="control-btn btn-restart" @click="restartTask(selectedTask.id)" v-if="selectedTask.status === 'pending' || selectedTask.status === 'failed' || selectedTask.status === 'cancelled'">
                            🔄 重启
                        </button>
                        <button class="control-btn btn-delete" @click="deleteTask(selectedTask.id)" v-if="selectedTask.status === 'pending' || selectedTask.status === 'failed' || selectedTask.status === 'cancelled' || selectedTask.status === 'completed'">
                            🗑 删除
                        </button>
                    </div>

                    <!-- Result/Error -->
                    <div class="result-section" v-if="selectedTask.result || selectedTask.error">
                        <div class="result-header">执行结果</div>
                        <div v-if="selectedTask.error" class="result-content error">
                            {{ selectedTask.error }}
                        </div>
                        <div v-else class="result-content">
                            {{ truncateResult(selectedTask.result) }}
                        </div>
                    </div>
                </div>

                <div v-else class="execution-empty">
                    <p>点击左侧任务查看执行详情</p>
                </div>
            </div>
        </div>

        <!-- Agent Status Bar -->
        <div class="agent-status-bar" v-if="agents.length > 0">
            <span class="agent-label">Agent状态:</span>
            <div class="agent-list">
                <span 
                    v-for="agent in agents" 
                    :key="agent.task_id"
                    class="agent-badge"
                    :class="agent.status"
                >
                    {{ agent.role_icon || '🤖' }} {{ getRoleName(agent.role) || 'Agent' }}
                </span>
            </div>
        </div>
    </div>
    `,

  data() {
    return {
      tasks: [],
      stats: {
        total: 0,
        completed: 0,
        failed: 0,
        running: 0,
        pending: 0,
        success_rate: 0,
        avg_duration_seconds: 0,
      },
      agents: [],
      filters: [
        { label: "全部", value: "" },
        { label: "进行中", value: "running" },
        { label: "已完成", value: "completed" },
        { label: "失败", value: "failed" },
        { label: "等待中", value: "pending" },
      ],
      statusFilter: "",
      selectedTask: null,
      taskLogs: [],
      logsLoading: false,
      refreshInterval: null,
      loading: false,
    };
  },

  computed: {
    filteredTasks() {
      if (!this.statusFilter) return this.tasks;
      return this.tasks.filter((t) => t.status === this.statusFilter);
    },
  },

  async mounted() {
    await this.loadData();
    this.startAutoRefresh();
  },

  beforeDestroy() {
    this.stopAutoRefresh();
  },

  methods: {
    async loadData() {
      this.loading = true;
      try {
        const [statsRes, tasksRes, agentsRes] = await Promise.all([
          fetch("/api/dashboard/stats"),
          fetch("/api/dashboard/tasks"),
          fetch("/api/dashboard/agents"),
        ]);

        if (statsRes.ok) {
          this.stats = await statsRes.json();
        }
        if (tasksRes.ok) {
          const data = await tasksRes.json();
          this.tasks = data.tasks || [];
        }
        if (agentsRes.ok) {
          const agentsData = await agentsRes.json();
          this.agents = agentsData.agents || [];
        }

        if (this.selectedTask) {
          const updatedTask = this.tasks.find(
            (t) => t.id === this.selectedTask.id,
          );
          if (updatedTask) {
            this.selectedTask = updatedTask;
          }
        }
      } catch (error) {
        console.error("Failed to load dashboard data:", error);
      } finally {
        this.loading = false;
      }
    },

    async loadLogs() {
      if (!this.selectedTask) return;

      this.logsLoading = true;
      try {
        const res = await fetch(
          `/api/dashboard/tasks/${this.selectedTask.id}/logs?since=0&limit=200`,
        );
        if (res.ok) {
          const data = await res.json();
          this.taskLogs = data.logs || [];
        }
      } catch (error) {
        console.error("Failed to load logs:", error);
      } finally {
        this.logsLoading = false;
      }
    },

    startAutoRefresh() {
      this.refreshInterval = setInterval(() => {
        this.loadData();
      }, 5000);
    },

    stopAutoRefresh() {
      if (this.refreshInterval) {
        clearInterval(this.refreshInterval);
        this.refreshInterval = null;
      }
    },

    async refreshData() {
      await this.loadData();
    },

    async selectTask(task) {
      this.selectedTask = task;
      await this.loadLogs();
    },

    async pauseTask(taskId) {
      try {
        const res = await fetch(`/api/dashboard/tasks/${taskId}/pause`, {
          method: "POST",
        });
        if (res.ok) {
          await this.loadData();
        }
      } catch (error) {
        console.error("Failed to pause task:", error);
      }
    },

    async resumeTask(taskId) {
      try {
        const res = await fetch(`/api/dashboard/tasks/${taskId}/resume`, {
          method: "POST",
        });
        if (res.ok) {
          await this.loadData();
        }
      } catch (error) {
        console.error("Failed to resume task:", error);
      }
    },

    async cancelTask(taskId) {
      window.$root.showConfirm("取消任务", "确定要取消此任务吗？", async () => {
        try {
          const res = await fetch(`/api/dashboard/tasks/${taskId}/cancel`, {
            method: "POST",
          });
          if (res.ok) {
            await this.loadData();
          }
        } catch (error) {
          console.error("Failed to cancel task:", error);
        }
      });
    },

    async deleteTask(taskId) {
      window.$root.showConfirm(
        "删除任务",
        "确定要删除此任务吗？此操作不可恢复。",
        async () => {
          try {
            const res = await fetch(`/api/dashboard/tasks/${taskId}`, {
              method: "DELETE",
            });
            if (res.ok) {
              this.selectedTask = null;
              await this.loadData();
            }
          } catch (error) {
            console.error("Failed to delete task:", error);
          }
        },
      );
    },

    async restartTask(taskId) {
      window.$root.showConfirm(
        "重启任务",
        "确定要重新执行此任务吗？",
        async () => {
          try {
            const res = await fetch(`/api/dashboard/tasks/${taskId}/restart`, {
              method: "POST",
            });
            if (res.ok) {
              await this.loadData();
            }
          } catch (error) {
            console.error("Failed to restart task:", error);
          }
        },
      );
    },

    formatTime(timestamp) {
      if (!timestamp) return "-";
      const date = new Date(timestamp);
      return date.toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    },

    formatLogTime(timestamp) {
      if (!timestamp) return "";
      const date = new Date(timestamp);
      return date.toLocaleTimeString("zh-CN", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    },

    formatDuration(seconds) {
      if (!seconds) return "-";
      seconds = Math.round(seconds);
      if (seconds < 60) return `${seconds}s`;
      const m = Math.floor(seconds / 60);
      const s = seconds % 60;
      return `${m}m${s}s`;
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

    truncateResult(result, maxLen = 500) {
      if (!result) return "";
      if (result.length <= maxLen) return result;
      return result.substring(0, maxLen) + "...";
    },

    getRoleName(role) {
      const roleNames = {
        document_writer: "文档编写",
        code_developer: "代码开发",
        data_analyst: "数据分析",
        researcher: "研究分析",
        general_assistant: "通用助手",
      };
      return roleNames[role] || role || "";
    },

    getStatusText(status) {
      const statusMap = {
        pending: "等待中",
        running: "进行中",
        completed: "已完成",
        failed: "失败",
        paused: "已暂停",
        cancelled: "已取消",
      };
      return statusMap[status] || status;
    },

    getLogIcon(type) {
      const iconMap = {
        system: "📋",
        tool: "🔧",
        progress: "📊",
        llm: "🤖",
        error: "❌",
        info: "ℹ️",
      };
      return iconMap[type] || "📋";
    },
  },
};
