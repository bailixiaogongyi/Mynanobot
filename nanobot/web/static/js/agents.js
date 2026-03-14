/**
 * Agent monitoring component for AiMate Web UI
 * Console-style log viewer for subagent execution
 */

const AgentsMonitor = {
  template: `
    <div class="console-monitor">
        <!-- 顶部栏 -->
        <div class="console-topbar">
            <div class="console-title">
                <span class="console-icon">📟</span>
                <span>子Agent执行日志</span>
            </div>
            <div class="console-actions">
                <button class="console-btn" @click="refresh" :disabled="loading">
                    <span :class="{spinning: loading}">🔄</span>
                </button>
            </div>
        </div>

        <!-- Agent标签栏 -->
        <div class="agent-tabs" v-if="agents.length > 0">
            <div 
                v-for="agent in agents" 
                :key="agent.task_id"
                class="agent-tab"
                :class="{active: activeAgentId === agent.task_id, [agent.status]: true}"
                @click="switchAgent(agent.task_id)"
            >
                <span class="tab-icon">{{ agent.role_icon || '🤖' }}</span>
                <span class="tab-name">{{ agent.role }}</span>
                <span class="tab-status" :class="agent.status">{{ getStatusDot(agent.status) }}</span>
                <span class="tab-close" @click.stop="closeAgentLog(agent.task_id)">×</span>
            </div>
            <div v-if="agents.length === 0" class="no-agents">
                暂无运行中的Agent
            </div>
        </div>

        <!-- 主控制台区域 -->
        <div class="console-main">
            <div class="console-viewport" ref="consoleViewport">
                <!-- 空状态 -->
                <div v-if="!activeAgentId || agentLogs[activeAgentId]?.length === 0" class="console-empty">
                    <div class="empty-icon">📟</div>
                    <div class="empty-text">{{ agents.length === 0 ? '暂无运行中的Agent' : '等待日志...' }}</div>
                </div>

                <!-- 日志列表 -->
                <div v-else class="console-logs">
                    <div 
                        v-for="(log, index) in agentLogs[activeAgentId] || []" 
                        :key="index" 
                        class="log-entry"
                        :class="log.level"
                    >
                        <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
                        <span class="log-type">{{ getLogIcon(log.type) }}</span>
                        <span class="log-content">{{ log.message }}</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- 底部状态栏 -->
        <div class="console-statusbar">
            <div class="status-left">
                <span v-if="activeAgentId">
                    {{ agentLogs[activeAgentId]?.length || 0 }} 条日志
                </span>
            </div>
            <div class="status-right">
                <span v-if="lastUpdateTime">最后更新: {{ lastUpdateTime }}</span>
            </div>
        </div>
    </div>
    `,

  data() {
    return {
      agents: [],
      loading: false,
      refreshInterval: null,
      activeAgentId: null,
      agentLogs: {},
      agentLogIndexes: {},
      lastUpdateTime: "",
    };
  },

  computed: {
    runningAgents() {
      return this.agents.filter((a) => a.status === "running");
    },
  },

  async mounted() {
    await this.refresh();
    this.startAutoRefresh();
  },

  beforeDestroy() {
    this.stopAutoRefresh();
  },

  methods: {
    async refresh() {
      this.loading = true;
      try {
        const resp = await fetch("/api/agents/subagents");
        if (resp.ok) {
          this.agents = await resp.json();

          // Auto-switch to first running agent
          if (this.runningAgents.length > 0 && !this.activeAgentId) {
            this.switchAgent(this.runningAgents[0].task_id);
          } else if (this.runningAgents.length === 0) {
            this.activeAgentId = null;
          }

          // Check if active agent is still running
          if (this.activeAgentId) {
            const stillRunning = this.agents.find(
              (a) => a.task_id === this.activeAgentId,
            );
            if (!stillRunning || stillRunning.status !== "running") {
              // Agent finished, don't auto-switch
            }
          }
        }
        this.lastUpdateTime = new Date().toLocaleTimeString("zh-CN", {
          hour12: false,
        });
      } catch (error) {
        console.error("Failed to refresh:", error);
      } finally {
        this.loading = false;
      }
    },

    startAutoRefresh() {
      this.refreshInterval = setInterval(() => {
        this.refreshLogs();
      }, 2000);
    },

    stopAutoRefresh() {
      if (this.refreshInterval) {
        clearInterval(this.refreshInterval);
        this.refreshInterval = null;
      }
    },

    async refreshLogs() {
      for (const agent of this.runningAgents) {
        await this.fetchAgentLogs(agent.task_id);
      }
    },

    async fetchAgentLogs(taskId) {
      try {
        const sinceIndex = this.agentLogIndexes[taskId] || 0;
        const resp = await fetch(
          `/api/agents/subagents/${taskId}/logs?since_index=${sinceIndex}`,
        );
        if (resp.ok) {
          const data = await resp.json();
          if (data.logs && data.logs.length > 0) {
            if (!this.agentLogs[taskId]) {
              this.agentLogs[taskId] = [];
            }
            this.agentLogs[taskId] = [...this.agentLogs[taskId], ...data.logs];
            this.agentLogIndexes[taskId] =
              data.logs[data.logs.length - 1].index + 1;

            // Auto-scroll to bottom
            this.$nextTick(() => {
              const viewport = this.$refs.consoleViewport;
              if (viewport) {
                viewport.scrollTop = viewport.scrollHeight;
              }
            });
          }
        }
      } catch (error) {
        console.error("Failed to fetch logs:", error);
      }
    },

    switchAgent(taskId) {
      this.activeAgentId = taskId;
      this.fetchAgentLogs(taskId);
    },

    closeAgentLog(taskId) {
      delete this.agentLogs[taskId];
      delete this.agentLogIndexes[taskId];
      if (this.activeAgentId === taskId) {
        this.activeAgentId = this.runningAgents[0]?.task_id || null;
      }
    },

    getStatusDot(status) {
      const dots = {
        running: "●",
        pending: "○",
        completed: "✓",
        failed: "✕",
        paused: "⏸",
      };
      return dots[status] || "○";
    },

    getLogIcon(type) {
      const icons = {
        system: "⚙",
        tool: "🔧",
        llm: "🤖",
        progress: "▶",
        error: "✕",
      };
      return icons[type] || "▶";
    },

    formatLogTime(timestamp) {
      const date = new Date(timestamp);
      return date.toLocaleTimeString("zh-CN", { hour12: false });
    },
  },
};
