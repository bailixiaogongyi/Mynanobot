<template>
  <div class="page-container config-page">
    <div class="config-layout">
      <div class="config-sidebar">
        <div class="sidebar-section">
          <div class="sidebar-title">配置导航</div>
          <div
            v-for="section in sections"
            :key="section.id"
            :class="['sidebar-item', { active: activeSection === section.id }]"
            @click="activeSection = section.id"
          >
            <span class="sidebar-icon" v-html="section.icon"></span>
            <span>{{ section.name }}</span>
          </div>
        </div>
      </div>
      <div class="config-main">
        <!-- 总览 -->
        <div v-if="activeSection === 'overview'" class="config-section">
          <div class="service-overview-card">
            <div class="overview-header">
              <h3 class="overview-title">服务状态总览</h3>
            </div>
            <div class="service-overview">
              <div class="overview-main">
                <div class="overview-stat">
                  <svg
                    class="overview-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <path
                      d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2z"
                    />
                    <circle cx="8" cy="14" r="2" />
                    <circle cx="16" cy="14" r="2" />
                  </svg>
                  <div class="overview-info">
                    <span class="overview-label">当前模型</span>
                    <span class="overview-value">{{
                      getModelDisplayName(config.model?.current) || "未设置"
                    }}</span>
                  </div>
                </div>
                <div class="overview-stat">
                  <svg
                    class="overview-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                    <line x1="8" y1="21" x2="16" y2="21" />
                    <line x1="12" y1="17" x2="12" y2="21" />
                  </svg>
                  <div class="overview-info">
                    <span class="overview-label">供应商</span>
                    <span class="overview-value">{{
                      currentProviderName
                    }}</span>
                  </div>
                </div>
              </div>
              <div class="overview-modules">
                <div class="module-status-item">
                  <svg
                    class="module-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                  </svg>
                  <span class="module-label">思考过程</span>
                  <span
                    :class="[
                      'module-value',
                      agentDefaults.enable_reasoning
                        ? 'text-success'
                        : 'text-muted',
                    ]"
                  >
                    {{ agentDefaults.enable_reasoning ? "已启用" : "已禁用" }}
                  </span>
                </div>
                <div class="module-status-item">
                  <svg
                    class="module-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <path
                      d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"
                    />
                  </svg>
                  <span class="module-label">工具调用</span>
                  <span
                    :class="[
                      'module-value',
                      agentDefaults.max_tool_iterations > 0
                        ? 'text-success'
                        : 'text-muted',
                    ]"
                  >
                    {{
                      agentDefaults.max_tool_iterations > 0
                        ? `已启用 (最大 ${agentDefaults.max_tool_iterations} 次)`
                        : "已禁用"
                    }}
                  </span>
                </div>
                <div class="module-status-item">
                  <svg
                    class="module-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <path
                      d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"
                    />
                  </svg>
                  <span class="module-label">通信渠道</span>
                  <span
                    :class="[
                      'module-value',
                      enabledChannelsCount > 0 ? 'text-success' : 'text-muted',
                    ]"
                  >
                    {{ enabledChannelsCount }} /
                    {{ config.channels?.length || 0 }} 已启用
                  </span>
                </div>
                <div class="module-status-item">
                  <svg
                    class="module-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                    <path
                      d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"
                    />
                  </svg>
                  <span class="module-label">知识检索</span>
                  <span
                    :class="[
                      'module-value',
                      config.knowledge?.enabled ? 'text-success' : 'text-muted',
                    ]"
                  >
                    {{ config.knowledge?.enabled ? "已启用" : "已禁用" }}
                  </span>
                </div>
                <div class="module-status-item">
                  <svg
                    class="module-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                  <span class="module-label">文件上传</span>
                  <span
                    :class="[
                      'module-value',
                      upload.enabled ? 'text-success' : 'text-muted',
                    ]"
                  >
                    {{ upload.enabled ? "已启用" : "已禁用" }}
                  </span>
                </div>
                <div class="module-status-item">
                  <svg
                    class="module-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <circle cx="12" cy="12" r="10" />
                    <line x1="2" y1="12" x2="22" y2="12" />
                    <path
                      d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"
                    />
                  </svg>
                  <span class="module-label">Web UI</span>
                  <span
                    :class="[
                      'module-value',
                      gateway?.web_ui_enabled ? 'text-success' : 'text-muted',
                    ]"
                  >
                    {{
                      gateway?.web_ui_enabled
                        ? `运行中 (端口 ${gateway.web_ui_port})`
                        : "已禁用"
                    }}
                  </span>
                </div>
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
                  :class="[
                    'period-btn',
                    { active: tokenPeriod === period.value },
                  ]"
                  @click="loadTokenStats(period.value)"
                >
                  {{ period.label }}
                </button>
              </div>
            </div>
            <div class="token-stats-summary">
              <div class="token-stat token-stat-primary">
                <div class="token-stat-icon">📊</div>
                <div class="token-stat-content">
                  <span class="token-stat-value">{{
                    formatNumber(tokenStats.total_tokens)
                  }}</span>
                  <span class="token-stat-label">Token 总数</span>
                </div>
              </div>
              <div class="token-stat">
                <div class="token-stat-icon">📥</div>
                <div class="token-stat-content">
                  <span class="token-stat-value">{{
                    formatNumber(tokenStats.total_prompt_tokens)
                  }}</span>
                  <span class="token-stat-label">输入 Token</span>
                </div>
              </div>
              <div class="token-stat">
                <div class="token-stat-icon">📤</div>
                <div class="token-stat-content">
                  <span class="token-stat-value">{{
                    formatNumber(tokenStats.total_completion_tokens)
                  }}</span>
                  <span class="token-stat-label">输出 Token</span>
                </div>
              </div>
              <div class="token-stat">
                <div class="token-stat-icon">🔄</div>
                <div class="token-stat-content">
                  <span class="token-stat-value">{{
                    tokenStats.total_requests
                  }}</span>
                  <span class="token-stat-label">请求次数</span>
                </div>
              </div>
              <div class="token-stat">
                <div class="token-stat-icon">👥</div>
                <div class="token-stat-content">
                  <span class="token-stat-value">{{
                    tokenStats.active_sessions
                  }}</span>
                  <span class="token-stat-label">活跃会话</span>
                </div>
              </div>
              <div
                class="token-stat token-stat-cost"
                v-if="tokenStats.estimated_cost"
              >
                <div class="token-stat-icon">💰</div>
                <div class="token-stat-content">
                  <span class="token-stat-value">{{
                    formatCurrency(
                      tokenStats.estimated_cost,
                      tokenStats.currency,
                    )
                  }}</span>
                  <span class="token-stat-label">预估费用</span>
                </div>
              </div>
            </div>

            <!-- 按模型展示消耗 -->
            <div
              v-if="tokenStats.by_model && tokenStats.by_model.length > 0"
              class="token-by-model"
            >
              <h4 class="by-model-title">按模型统计</h4>
              <div class="model-stats-grid">
                <div
                  v-for="modelStat in tokenStats.by_model"
                  :key="modelStat.model || modelStat.model_id"
                  class="model-stat-card"
                >
                  <div class="model-stat-header">
                    <div class="model-info">
                      <div class="model-stat-name-row">
                        <span class="model-stat-name">{{
                          getModelDisplayName(
                            modelStat.model || modelStat.model_id,
                          ) || "未知模型"
                        }}</span>
                        <span class="model-stat-provider">{{
                          getProviderDisplayName(modelStat.provider || "")
                        }}</span>
                      </div>
                    </div>
                  </div>
                  <div class="model-stat-metrics">
                    <div class="metric-item">
                      <span class="metric-icon">📥</span>
                      <div class="metric-info">
                        <span class="metric-value">{{
                          formatNumber(modelStat.total_prompt_tokens)
                        }}</span>
                        <span class="metric-label">输入</span>
                      </div>
                    </div>
                    <div class="metric-item">
                      <span class="metric-icon">📤</span>
                      <div class="metric-info">
                        <span class="metric-value">{{
                          formatNumber(modelStat.total_completion_tokens)
                        }}</span>
                        <span class="metric-label">输出</span>
                      </div>
                    </div>
                    <div class="metric-item">
                      <span class="metric-icon">🔄</span>
                      <div class="metric-info">
                        <span class="metric-value">{{
                          modelStat.request_count || 0
                        }}</span>
                        <span class="metric-label">请求</span>
                      </div>
                    </div>
                    <div
                      class="metric-item metric-cost"
                      v-if="modelStat.estimated_cost"
                    >
                      <span class="metric-icon">💰</span>
                      <div class="metric-info">
                        <span class="metric-value">{{
                          formatCurrency(
                            modelStat.estimated_cost || 0,
                            modelStat.currency || "CNY",
                          )
                        }}</span>
                        <span class="metric-label">费用</span>
                      </div>
                    </div>
                  </div>
                  <div class="model-stat-progress">
                    <div class="progress-bar">
                      <div
                        class="progress-fill"
                        :style="{
                          width: getModelUsagePercent(modelStat) + '%',
                        }"
                      ></div>
                    </div>
                    <span class="progress-label"
                      >{{ getModelUsagePercent(modelStat) }}%</span
                    >
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 模型配置 -->
        <div v-else-if="activeSection === 'model'" class="config-section">
          <div class="config-tip">
            <span class="tip-icon">💡</span>
            <span class="tip-text">模型切换即时生效，无需重启服务</span>
          </div>
          <div class="card">
            <div class="card-header">
              <h3 class="card-title">模型和供应商</h3>
            </div>
            <div class="provider-list">
              <div
                v-for="provider in config.providers"
                :key="provider.name"
                class="provider-item-wrapper"
              >
                <div
                  class="provider-header"
                  @click="toggleProviderExpand(provider.name)"
                >
                  <div class="provider-info">
                    <span class="provider-name">{{
                      provider.display_name || provider.name
                    }}</span>
                    <span
                      v-if="provider.description"
                      class="provider-desc"
                      :title="provider.description"
                      >{{ provider.description }}</span
                    >
                    <span v-if="provider.is_gateway" class="badge badge-info"
                      >网关</span
                    >
                    <span v-if="provider.is_oauth" class="badge badge-info"
                      >OAuth</span
                    >
                    <span
                      :class="[
                        'badge',
                        provider.has_key ? 'badge-success' : 'badge-warning',
                      ]"
                    >
                      {{ provider.has_key ? "已配置" : "未配置" }}
                    </span>
                    <span
                      v-if="isCurrentProvider(provider.name)"
                      class="badge badge-primary"
                      >当前</span
                    >
                  </div>
                  <div class="provider-actions">
                    <span
                      v-if="provider.models && provider.models.length > 0"
                      class="model-count"
                    >
                      {{ provider.models.length }} 模型
                    </span>
                    <span class="expand-icon">{{
                      expandedProvider === provider.name ? "▼" : "▶"
                    }}</span>
                    <button
                      class="btn btn-sm btn-secondary"
                      @click.stop="editProvider(provider)"
                    >
                      {{ provider.has_key ? "编辑" : "配置" }}
                    </button>
                  </div>
                </div>
                <div
                  v-if="expandedProvider === provider.name && provider.models"
                  class="provider-models"
                >
                  <div
                    v-for="model in provider.models"
                    :key="model.model_id"
                    class="model-item"
                  >
                    <div class="model-info">
                      <div class="model-name-row">
                        <span class="model-name">{{
                          model.display_name || model.model_id
                        }}</span>
                        <span class="model-provider"
                          >({{ provider.display_name || provider.name }})</span
                        >
                        <div
                          class="model-caps"
                          v-if="
                            model.supports_vision ||
                            model.supports_function_calling ||
                            model.supports_streaming
                          "
                        >
                          <span
                            v-if="model.supports_vision"
                            class="badge badge-info"
                            >视觉</span
                          >
                          <span
                            v-if="model.supports_function_calling"
                            class="badge badge-info"
                            >函数</span
                          >
                          <span
                            v-if="model.supports_streaming"
                            class="badge badge-info"
                            >流式</span
                          >
                        </div>
                      </div>
                      <span v-if="model.description" class="model-desc">{{
                        model.description
                      }}</span>
                    </div>
                    <div class="model-actions">
                      <span
                        class="model-price"
                        v-if="model.input_price || model.output_price"
                      >
                        ${{ formatPrice(model.input_price) }}/${{
                          formatPrice(model.output_price)
                        }}
                      </span>
                      <div class="model-btn-group">
                        <button
                          class="btn btn-sm btn-icon"
                          title="编辑模型"
                          @click.stop="editModel(provider.name, model)"
                        >
                          <svg
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                          >
                            <path
                              d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"
                            />
                            <path
                              d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"
                            />
                          </svg>
                        </button>
                        <button
                          class="btn btn-sm btn-icon btn-danger"
                          title="删除模型"
                          @click.stop="
                            deleteModel(provider.name, model.model_id)
                          "
                        >
                          <svg
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                          >
                            <polyline points="3 6 5 6 21 6" />
                            <path
                              d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"
                            />
                          </svg>
                        </button>
                      </div>
                      <button
                        :class="[
                          'btn',
                          'btn-sm',
                          isCurrentModel(provider.name, model.model_id)
                            ? 'btn-primary'
                            : 'btn-secondary',
                        ]"
                        @click="switchToModel(provider.name, model.model_id)"
                      >
                        {{
                          isCurrentModel(provider.name, model.model_id)
                            ? "当前"
                            : "选择"
                        }}
                      </button>
                    </div>
                  </div>
                  <div
                    class="model-item add-model-btn"
                    @click="addModel(provider.name)"
                  >
                    <div class="model-info">
                      <span class="model-name">+ 新增模型</span>
                      <span class="model-desc">为此供应商添加自定义模型</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="card" style="margin-top: 1rem">
            <div class="card-header">
              <h3 class="card-title">推理设置</h3>
            </div>
            <div class="card-body">
              <div class="reasoning-settings">
                <div class="reasoning-item">
                  <div class="reasoning-info">
                    <span class="reasoning-name">🧠 思考过程</span>
                    <span class="reasoning-desc"
                      >启用后，AI 的思考过程将以折叠方式显示</span
                    >
                  </div>
                  <label class="switch">
                    <input
                      type="checkbox"
                      v-model="enableReasoning"
                      @change="updateReasoningSetting"
                    />
                    <span class="slider"></span>
                  </label>
                </div>
                <div class="reasoning-item">
                  <div class="reasoning-info">
                    <span class="reasoning-name">🔧 工具调用</span>
                    <span class="reasoning-desc"
                      >允许 AI 调用外部工具获取信息或执行操作</span
                    >
                  </div>
                  <label class="switch">
                    <input
                      type="checkbox"
                      v-model="toolCallEnabled"
                      @change="updateToolCallSetting"
                    />
                    <span class="slider"></span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 通道配置 -->
        <div v-else-if="activeSection === 'channel'" class="config-section">
          <div class="config-tip">
            <span class="tip-icon">💡</span>
            <span class="tip-text"
              >通道的Token、App ID等凭证修改后需要重启服务才能生效</span
            >
          </div>
          <div class="card">
            <div class="card-header">
              <h3 class="card-title">通信渠道</h3>
            </div>
            <div class="channel-list">
              <div
                v-for="channel in config.channels"
                :key="channel.name"
                class="channel-item"
              >
                <div class="channel-info">
                  <span class="channel-name">{{
                    channel.display_name || channel.name
                  }}</span>
                  <span
                    class="channel-status"
                    :class="getChannelStatusClass(channel)"
                  >
                    {{ getChannelStatusText(channel) }}
                  </span>
                </div>
                <div class="channel-actions">
                  <label class="switch">
                    <input
                      type="checkbox"
                      :checked="channel.enabled"
                      @change="toggleChannel(channel)"
                    />
                    <span class="slider"></span>
                  </label>
                  <button
                    class="btn btn-sm btn-secondary"
                    @click="editChannel(channel)"
                  >
                    配置
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Agent配置 -->
        <div v-else-if="activeSection === 'agent'" class="config-section">
          <div class="config-tip">
            <span class="tip-icon">💡</span>
            <span class="tip-text">记忆窗口大小修改后需要重启服务才能生效</span>
          </div>
          <div class="card">
            <div class="card-header">
              <h3 class="card-title">Agent 默认设置</h3>
            </div>
            <div class="card-body">
              <div class="form-group">
                <label class="form-label">最大工具迭代次数</label>
                <input
                  type="number"
                  class="input"
                  v-model.number="agentDefaults.max_tool_iterations"
                  min="0"
                  max="100"
                />
                <p class="form-help">设置为 0 禁用工具调用</p>
              </div>
              <div class="form-group">
                <label class="form-label">最大输出 Tokens</label>
                <input
                  type="number"
                  class="input"
                  v-model.number="agentDefaults.max_tokens"
                  min="1"
                  max="128000"
                />
              </div>
              <div class="form-group">
                <label class="form-label">Temperature</label>
                <input
                  type="number"
                  class="input"
                  v-model.number="agentDefaults.temperature"
                  min="0"
                  max="2"
                  step="0.1"
                />
              </div>
              <div class="form-group">
                <label class="form-label">记忆窗口大小</label>
                <input
                  type="number"
                  class="input"
                  v-model.number="agentDefaults.memory_window"
                  min="1"
                  max="100"
                />
                <p class="form-help">保留最近 N 轮对话作为上下文</p>
              </div>
              <button class="btn btn-primary" @click="saveAgentDefaults">
                保存设置
              </button>
            </div>
          </div>
        </div>

        <!-- 知识检索 -->
        <div v-else-if="activeSection === 'knowledge'" class="config-section">
          <div class="config-tip">
            <span class="tip-icon">💡</span>
            <span class="tip-text"
              >Embedding模型、索引参数修改后需要重建索引，重启服务后生效</span
            >
          </div>
          <div class="card">
            <div class="card-header">
              <h3 class="card-title">知识检索设置</h3>
            </div>
            <div class="card-body">
              <div class="form-group">
                <label class="form-label">
                  <input type="checkbox" v-model="config.knowledge.enabled" />
                  启用知识检索
                </label>
              </div>
              <div class="form-group">
                <label class="form-label">Embedding 模型</label>
                <input
                  type="text"
                  class="input"
                  value="BAAI/bge-small-zh-v1.5"
                  readonly
                  disabled
                />
                <p class="form-help">默认使用本地嵌入模型，无需配置</p>
              </div>
              <div class="form-group">
                <label class="form-label">持久化目录</label>
                <input
                  type="text"
                  class="input"
                  v-model="config.knowledge.persist_dir"
                  placeholder="知识库存储路径"
                  disabled
                />
              </div>
              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">Chunk 大小</label>
                  <input
                    type="number"
                    class="input"
                    v-model.number="config.knowledge.chunk_size"
                    min="100"
                    max="4000"
                  />
                </div>
                <div class="form-group">
                  <label class="form-label">Chunk 重叠</label>
                  <input
                    type="number"
                    class="input"
                    v-model.number="config.knowledge.chunk_overlap"
                    min="0"
                    max="500"
                  />
                </div>
              </div>
              <div class="form-group">
                <label class="form-label">默认 Top K</label>
                <input
                  type="number"
                  class="input"
                  v-model.number="config.knowledge.default_top_k"
                  min="1"
                  max="20"
                />
                <p class="form-help">检索时返回的最相关文档数量</p>
              </div>
              <div class="form-group">
                <label class="form-label">检索方式</label>
                <div class="checkbox-group">
                  <label class="checkbox-label">
                    <input
                      type="checkbox"
                      v-model="config.knowledge.use_vector"
                    />
                    向量检索
                  </label>
                  <label class="checkbox-label">
                    <input
                      type="checkbox"
                      v-model="config.knowledge.use_bm25"
                    />
                    BM25 关键词检索
                  </label>
                  <label class="checkbox-label">
                    <input
                      type="checkbox"
                      v-model="config.knowledge.use_graph"
                    />
                    知识图谱
                  </label>
                </div>
              </div>
              <div class="form-group">
                <label class="form-label">
                  <input
                    type="checkbox"
                    v-model="config.knowledge.use_llm_extract"
                  />
                  启用 LLM 提取
                </label>
                <p class="form-help">使用 LLM 从文档中提取结构化知识</p>
              </div>
              <button class="btn btn-primary" @click="saveKnowledgeConfig">
                保存设置
              </button>
            </div>
          </div>
        </div>

        <!-- 工具配置 -->
        <div v-else-if="activeSection === 'tools'" class="config-section">
          <div class="config-tip">
            <span class="tip-icon">💡</span>
            <span class="tip-text"
              >搜索API Key、天气API
              Key修改后即时生效，其他参数修改需要重启服务</span
            >
          </div>
          <div class="card">
            <div class="card-header">
              <h3 class="card-title">工具配置</h3>
            </div>
            <div class="card-body">
              <!-- 网络搜索配置 -->
              <div class="tool-item">
                <div class="tool-info">
                  <span class="tool-icon">🌐</span>
                  <div class="tool-title-info">
                    <span class="tool-name">网络搜索</span>
                    <span class="tool-desc"
                      >允许 AI 搜索互联网获取最新信息</span
                    >
                  </div>
                </div>
                <div class="tool-actions">
                  <label class="switch" @click.stop>
                    <input type="checkbox" v-model="config.tools.web_search" />
                    <span class="slider"></span>
                  </label>
                  <button
                    class="btn btn-sm btn-secondary"
                    @click="showWebSearchModal = true"
                  >
                    配置
                  </button>
                </div>
              </div>

              <Modal
                :show="showWebSearchModal"
                title="网络搜索配置"
                :close-on-overlay="false"
                @close="showWebSearchModal = false"
              >
                <div class="form-group">
                  <label class="form-label">搜索 API Key</label>
                  <input
                    type="text"
                    class="input"
                    v-model="config.tools.web_search_api_key"
                    placeholder="博查搜索 API Key"
                  />
                  <p class="form-help">博查搜索 (Bocha) API 密钥</p>
                </div>
                <div class="form-group">
                  <label class="form-label">最大结果数</label>
                  <input
                    type="number"
                    class="input"
                    v-model.number="config.tools.web_search_max_results"
                    min="1"
                    max="20"
                  />
                  <p class="form-help">每次搜索返回的最大结果数量</p>
                </div>
                <template #footer>
                  <button
                    class="btn btn-primary"
                    @click="showWebSearchModal = false"
                  >
                    保存
                  </button>
                </template>
              </Modal>

              <!-- 天气查询配置 -->
              <div class="tool-item">
                <div class="tool-info">
                  <span class="tool-icon">🌤️</span>
                  <div class="tool-title-info">
                    <span class="tool-name">天气查询</span>
                    <span class="tool-desc">允许 AI 查询天气信息</span>
                  </div>
                </div>
                <div class="tool-actions">
                  <label class="switch" @click.stop>
                    <input type="checkbox" v-model="config.tools.weather" />
                    <span class="slider"></span>
                  </label>
                  <button
                    class="btn btn-sm btn-secondary"
                    @click="showWeatherModal = true"
                  >
                    配置
                  </button>
                </div>
              </div>

              <Modal
                :show="showWeatherModal"
                title="天气查询配置"
                :close-on-overlay="false"
                @close="showWeatherModal = false"
              >
                <div class="form-group">
                  <label class="form-label">天气 API Key</label>
                  <input
                    type="text"
                    class="input"
                    v-model="config.tools.weather_api_key"
                    placeholder="心知天气 API Key"
                  />
                  <p class="form-help">心知天气 (Seniverse) API 密钥</p>
                </div>
                <template #footer>
                  <button
                    class="btn btn-primary"
                    @click="showWeatherModal = false"
                  >
                    保存
                  </button>
                </template>
              </Modal>

              <!-- MCP 服务配置 -->
              <div class="tool-item">
                <div class="tool-info">
                  <span class="tool-icon">🔗</span>
                  <div class="tool-title-info">
                    <span class="tool-name">MCP 工具</span>
                    <span class="tool-desc"
                      >Model Context Protocol 服务配置</span
                    >
                  </div>
                </div>
                <div class="tool-actions">
                  <label class="switch" @click.stop>
                    <input type="checkbox" v-model="config.tools.mcp" />
                    <span class="slider"></span>
                  </label>
                  <button
                    class="btn btn-sm btn-secondary"
                    @click="toggleToolConfig('mcp')"
                  >
                    配置
                  </button>
                </div>
              </div>
              <div class="tool-config-body" v-if="expandedTools.mcp">
                <div class="mcp-servers-list">
                  <div
                    v-for="(server, name) in config.tools.mcp_servers"
                    :key="name"
                    class="mcp-server-item"
                  >
                    <div class="mcp-server-header">
                      <span class="mcp-server-name">{{ name }}</span>
                      <div class="mcp-server-type">
                        <span
                          class="badge"
                          :class="server.url ? 'badge-success' : 'badge-info'"
                        >
                          {{ server.url ? "HTTP" : "Stdio" }}
                        </span>
                      </div>
                    </div>
                    <div class="mcp-server-details">
                      <span v-if="server.url" class="mcp-server-url">{{
                        server.url
                      }}</span>
                      <span v-else class="mcp-server-cmd"
                        >{{ server.command }} {{ server.args?.join(" ") }}</span
                      >
                    </div>
                  </div>
                  <div
                    v-if="
                      !config.tools.mcp_servers ||
                      Object.keys(config.tools.mcp_servers).length === 0
                    "
                    class="mcp-empty"
                  >
                    <p>暂无 MCP 服务配置</p>
                    <p class="mcp-help">请在配置文件中添加 mcp_servers 配置</p>
                  </div>
                </div>
              </div>

              <!-- 高级设置 -->
              <div class="tool-settings" style="margin-top: 1.5rem">
                <h4
                  style="
                    margin-bottom: 1rem;
                    color: var(--color-text-secondary);
                  "
                >
                  高级设置
                </h4>
                <div class="form-group">
                  <label class="form-label">
                    <input
                      type="checkbox"
                      v-model="config.tools.restrict_to_workspace"
                    />
                    限制在工作空间内执行
                  </label>
                  <p class="form-help">
                    工具只能在指定的工作空间目录中执行操作
                  </p>
                </div>
                <div class="form-group">
                  <label class="form-label">执行超时时间 (秒)</label>
                  <input
                    type="number"
                    class="input"
                    v-model.number="config.tools.exec_timeout"
                    min="1"
                    max="300"
                  />
                  <p class="form-help">工具执行的最大等待时间</p>
                </div>
              </div>

              <button
                class="btn btn-primary"
                style="margin-top: 1.5rem"
                @click="saveToolsConfig"
              >
                保存设置
              </button>
            </div>
          </div>
        </div>

        <!-- 子Agent角色配置 -->
        <div v-else-if="activeSection === 'roles'" class="config-section">
          <div class="config-tip">
            <span class="tip-icon">💡</span>
            <span class="tip-text"
              >子Agent角色配置修改后需要重启服务才能生效</span
            >
          </div>
          <div class="card">
            <div class="card-header">
              <h3 class="card-title">子Agent角色配置</h3>
              <p class="card-desc">为每个子Agent角色配置独立的模型和参数</p>
            </div>
            <div class="card-body">
              <div class="roles-list">
                <div
                  v-for="role in rolesList"
                  :key="role.key"
                  class="role-card"
                >
                  <div class="role-header">
                    <span class="role-icon">{{ role.icon }}</span>
                    <div class="role-info">
                      <h4 class="role-name">{{ role.name }}</h4>
                      <p class="role-desc">{{ role.description }}</p>
                    </div>
                    <button
                      class="btn btn-sm btn-secondary"
                      @click="editRole(role)"
                    >
                      配置
                    </button>
                  </div>
                  <div class="role-model-info">
                    <span
                      :class="[
                        'model-badge',
                        role.has_custom_model ? 'custom' : 'default',
                      ]"
                    >
                      {{
                        role.has_custom_model ? "自定义模型" : "使用主Agent模型"
                      }}
                    </span>
                    <span v-if="role.model_config" class="model-detail">
                      {{ role.model_config.provider }}/{{
                        role.model_config.model
                      }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 系统配置 -->
        <div v-else-if="activeSection === 'system'" class="config-section">
          <div class="card">
            <div class="card-header">
              <h3 class="card-title">网关设置</h3>
            </div>
            <div class="card-body">
              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">主机</label>
                  <input type="text" class="input" v-model="gateway.host" />
                </div>
                <div class="form-group">
                  <label class="form-label">端口</label>
                  <input
                    type="number"
                    class="input"
                    v-model.number="gateway.port"
                  />
                </div>
              </div>
              <div class="form-group">
                <label class="form-label">
                  <input type="checkbox" v-model="gateway.web_ui_enabled" />
                  启用 Web UI
                </label>
              </div>
              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">Web UI 主机</label>
                  <input
                    type="text"
                    class="input"
                    v-model="gateway.web_ui_host"
                  />
                </div>
                <div class="form-group">
                  <label class="form-label">Web UI 端口</label>
                  <input
                    type="number"
                    class="input"
                    v-model.number="gateway.web_ui_port"
                  />
                </div>
              </div>
              <div class="form-group">
                <label class="form-label">
                  <input
                    type="checkbox"
                    v-model="gateway.web_ui_auth_enabled"
                  />
                  启用 Web UI 认证
                </label>
                <p class="form-help">启用后访问 Web UI 需要登录认证</p>
              </div>
              <button class="btn btn-primary" @click="saveGatewayConfig">
                保存设置
              </button>
            </div>
          </div>

          <div class="card" style="margin-top: 1rem">
            <div class="card-header">
              <h3 class="card-title">文件上传设置</h3>
            </div>
            <div class="card-body">
              <div class="form-group">
                <label class="form-label">
                  <input type="checkbox" v-model="upload.enabled" />
                  启用文件上传
                </label>
              </div>
              <div class="form-group">
                <label class="form-label">最大文件大小 (MB)</label>
                <input
                  type="number"
                  class="input"
                  v-model.number="uploadMaxSizeMB"
                  min="1"
                  max="100"
                />
              </div>
              <button class="btn btn-primary" @click="saveUploadConfig">
                保存设置
              </button>
            </div>
          </div>

          <div class="card" style="margin-top: 1rem">
            <div class="card-header">
              <h3 class="card-title">系统操作</h3>
            </div>
            <div class="card-body">
              <div class="form-group">
                <button
                  class="btn btn-danger"
                  @click="showRestartConfirm = true"
                >
                  🔄 重启系统
                </button>
                <p class="form-help">重启后将重新加载所有配置和服务</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Provider编辑弹窗 -->
    <Teleport to="body">
      <div
        v-if="editingProvider"
        class="modal-overlay"
        @click.self="editingProvider = null"
      >
        <div class="modal">
          <div class="modal-header">
            <h3>{{ editingProvider.display_name || editingProvider.name }}</h3>
            <button class="modal-close" @click="editingProvider = null">
              ×
            </button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label class="form-label">API Key</label>
              <input
                type="password"
                class="input"
                v-model="providerForm.apiKey"
                placeholder="输入 API Key"
              />
            </div>
            <div class="form-group">
              <label class="form-label">API Base URL (可选)</label>
              <input
                type="text"
                class="input"
                v-model="providerForm.apiBase"
                placeholder="如: https://api.openai.com/v1"
              />
            </div>
            <div
              v-if="testConnectionResult"
              :class="[
                'test-result',
                testConnectionResult.success ? 'success' : 'error',
              ]"
            >
              {{ testConnectionResult.message }}
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="testConnection">
              测试连接
            </button>
            <button class="btn btn-primary" @click="saveProvider">保存</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 通道配置弹窗 -->
    <Modal
      :show="showChannelModal"
      :title="`配置 ${editingChannel?.display_name || editingChannel?.name || '通道'}`"
      size="md"
      :close-on-overlay="false"
      @close="showChannelModal = false"
    >
      <div class="form-group">
        <label class="form-label">
          <input type="checkbox" v-model="channelForm.enabled" />
          启用通道
        </label>
      </div>

      <template v-if="editingChannel">
        <div
          v-for="field in getChannelFields(editingChannel.name)"
          :key="field.key"
          class="form-group"
        >
          <label class="form-label">{{ field.label }}</label>
          <input
            :type="field.type"
            class="input"
            v-model="channelForm[field.key]"
            :placeholder="field.placeholder || ''"
          />
          <p v-if="field.help" class="form-help">{{ field.help }}</p>
        </div>
      </template>

      <template #footer>
        <button class="btn btn-secondary" @click="showChannelModal = false">
          取消
        </button>
        <button class="btn btn-primary" @click="saveChannelConfig">保存</button>
      </template>
    </Modal>

    <!-- 模型编辑弹窗 -->
    <Modal
      :show="showModelModal"
      :title="editingModel ? '编辑模型' : '新增模型'"
      size="md"
      :close-on-overlay="false"
      @close="closeModelModal"
    >
      <div class="form-group">
        <label class="form-label">模型 ID</label>
        <input
          type="text"
          class="input"
          v-model="modelForm.model_id"
          placeholder="如: gpt-4o-mini"
        />
        <p class="form-help">模型的唯一标识符</p>
      </div>
      <div class="form-group">
        <label class="form-label">显示名称</label>
        <input
          type="text"
          class="input"
          v-model="modelForm.display_name"
          placeholder="如: GPT-4o Mini"
        />
      </div>
      <div class="form-group">
        <label class="form-label">描述</label>
        <input
          type="text"
          class="input"
          v-model="modelForm.description"
          placeholder="模型描述"
        />
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">输入价格 (CNY/1K tokens)</label>
          <input
            type="number"
            class="input"
            v-model.number="modelForm.input_price"
            min="0"
            step="0.001"
          />
        </div>
        <div class="form-group">
          <label class="form-label">输出价格 (CNY/1K tokens)</label>
          <input
            type="number"
            class="input"
            v-model.number="modelForm.output_price"
            min="0"
            step="0.001"
          />
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">最大 Tokens (k)</label>
          <input
            type="number"
            class="input"
            v-model.number="modelForm.max_tokens"
            min="1"
          />
        </div>
        <div class="form-group">
          <label class="form-label">限额 Tokens (M)</label>
          <input
            type="number"
            class="input"
            v-model.number="modelForm.token_quota"
            min="0"
          />
        </div>
      </div>
      <div class="form-group">
        <label class="form-label">能力</label>
        <div class="checkbox-group">
          <label class="checkbox-label">
            <input type="checkbox" v-model="modelForm.supports_vision" />
            支持视觉
          </label>
          <label class="checkbox-label">
            <input
              type="checkbox"
              v-model="modelForm.supports_function_calling"
            />
            支持函数调用
          </label>
          <label class="checkbox-label">
            <input type="checkbox" v-model="modelForm.supports_streaming" />
            支持流式输出
          </label>
        </div>
      </div>
      <template #footer>
        <button class="btn btn-secondary" @click="closeModelModal">取消</button>
        <button class="btn btn-primary" @click="saveModel">保存</button>
      </template>
    </Modal>

    <!-- 重启确认弹窗 -->
    <Modal
      :show="showRestartConfirm"
      title="确认重启"
      size="sm"
      @close="showRestartConfirm = false"
    >
      <p>确定要重启系统吗？这将中断当前正在进行的任务。</p>
      <template #footer>
        <button class="btn btn-secondary" @click="showRestartConfirm = false">
          取消
        </button>
        <button
          class="btn btn-primary"
          :disabled="restarting"
          @click="restartSystem"
        >
          {{ restarting ? "重启中..." : "确认重启" }}
        </button>
      </template>
    </Modal>

    <!-- 角色配置弹窗 -->
    <Modal
      :show="showRoleModal"
      :title="`配置 ${editingRole?.name || '角色'}`"
      size="md"
      :close-on-overlay="false"
      @close="closeRoleModal"
    >
      <div class="form-group">
        <label class="form-label">
          <input type="checkbox" v-model="roleForm.useCustomModel" />
          使用自定义模型
        </label>
        <p class="form-help">启用后此角色将使用独立的模型配置</p>
      </div>

      <template v-if="roleForm.useCustomModel">
        <div class="form-group">
          <label class="form-label">Provider</label>
          <select class="input" v-model="roleForm.provider">
            <option value="">选择 Provider</option>
            <option v-for="p in availableProviders" :key="p" :value="p">
              {{ p }}
            </option>
          </select>
        </div>

        <div class="form-group">
          <label class="form-label">模型</label>
          <select
            class="input"
            v-model="roleForm.model"
            :disabled="!roleForm.provider"
          >
            <option value="">选择模型</option>
            <option
              v-for="m in getModelsForProvider(roleForm.provider)"
              :key="m.model_id"
              :value="m.model_id"
            >
              {{ m.display_name }}
              <span v-if="m.supports_vision"> (视觉)</span>
            </option>
          </select>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Temperature</label>
            <input
              type="number"
              class="input"
              v-model.number="roleForm.temperature"
              min="0"
              max="2"
              step="0.1"
            />
          </div>
          <div class="form-group">
            <label class="form-label">Max Tokens</label>
            <input
              type="number"
              class="input"
              v-model.number="roleForm.max_tokens"
              min="256"
              max="128000"
              step="256"
            />
          </div>
        </div>
      </template>

      <div
        v-if="roleSaveResult"
        :class="['save-result', roleSaveResult.success ? 'success' : 'error']"
      >
        {{ roleSaveResult.message }}
      </div>

      <template #footer>
        <button class="btn btn-secondary" @click="closeRoleModal">取消</button>
        <button
          class="btn btn-primary"
          :disabled="savingRole"
          @click="saveRoleConfig"
        >
          {{ savingRole ? "保存中..." : "保存" }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useUIStore } from "@/stores/ui";
import api from "@/services/api";
import Modal from "@/components/ui/Modal.vue";

const uiStore = useUIStore();

const activeSection = ref("overview");
const expandedTools = ref({
  webSearch: false,
  weather: false,
  mcp: false,
});

const showWebSearchModal = ref(false);
const showWeatherModal = ref(false);
const config = ref<any>({
  model: { current: "", enable_reasoning: true },
  providers: [],
  channels: [],
  knowledge: {
    enabled: false,
    embedding_model: "",
    persist_dir: "",
    chunk_size: 512,
    chunk_overlap: 50,
    default_top_k: 5,
    use_vector: true,
    use_bm25: true,
    use_graph: false,
    use_llm_extract: false,
  },
  tools: {
    web_search: true,
    web_search_api_key: "",
    web_search_max_results: 10,
    weather: true,
    weather_api_key: "",
    mcp: false,
    restrict_to_workspace: true,
    exec_timeout: 60,
    mcp_servers_count: 0,
  },
});
const agentDefaults = ref({
  max_tokens: 4096,
  temperature: 0.7,
  max_tool_iterations: 10,
  memory_window: 10,
  enable_reasoning: true,
  workspace: "",
});
const upload = ref({ enabled: true, max_file_size: 10485760 });
const gateway = ref({
  host: "0.0.0.0",
  port: 18790,
  web_ui_enabled: true,
  web_ui_host: "0.0.0.0",
  web_ui_port: 8080,
  web_ui_auth_enabled: false,
});
const enableReasoning = ref(true);
const toolCallEnabled = computed(() => {
  const tools = config.value.tools;
  return (
    tools &&
    (tools.web_search ||
      tools.weather ||
      tools.mcp ||
      tools.restrict_to_workspace)
  );
});

const editingProvider = ref<any>(null);
const providerForm = ref({ apiKey: "", apiBase: "" });
const testingConnection = ref(false);
const testConnectionResult = ref<any>(null);
const expandedProvider = ref<string | null>(null);

interface ModelStat {
  model?: string;
  model_name?: string;
  model_id?: string;
  provider?: string;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens?: number;
  request_count?: number;
  estimated_cost?: number;
  currency?: string;
}

const tokenStats = ref<{
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_requests: number;
  active_sessions: number;
  estimated_cost: number;
  currency: string;
  by_model: ModelStat[];
}>({
  total_prompt_tokens: 0,
  total_completion_tokens: 0,
  total_tokens: 0,
  total_requests: 0,
  active_sessions: 0,
  estimated_cost: 0,
  currency: "CNY",
  by_model: [],
});
const tokenPeriod = ref("all");
const showChannelModal = ref(false);
const editingChannel = ref<any>(null);
const channelForm = ref<any>({});
const showModelModal = ref(false);
const editingModel = ref<any>(null);
const editingModelProvider = ref<string>("");
const modelForm = ref({
  model_id: "",
  display_name: "",
  description: "",
  input_price: 0,
  output_price: 0,
  max_tokens: 4096,
  token_quota: 0,
  supports_vision: false,
  supports_function_calling: true,
  supports_streaming: true,
  currency: "CNY",
});
const showRestartConfirm = ref(false);
const restarting = ref(false);

interface RoleInfo {
  key: string;
  name: string;
  description: string;
  icon: string;
  enabled: boolean;
  has_custom_model: boolean;
  model_config?: {
    provider?: string;
    model?: string;
  };
}

const rolesList = ref<RoleInfo[]>([]);
const showRoleModal = ref(false);
const editingRole = ref<RoleInfo | null>(null);
const savingRole = ref(false);
const roleSaveResult = ref<{ success: boolean; message: string } | null>(null);
const roleForm = ref({
  useCustomModel: false,
  provider: "",
  model: "",
  temperature: 0.7,
  max_tokens: 4096,
});

const tokenPeriods = [
  { label: "今日", value: "today" },
  { label: "本周", value: "week" },
  { label: "本月", value: "month" },
  { label: "全部", value: "all" },
];

const sections = [
  {
    id: "overview",
    name: "总览",
    icon: '<svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>',
  },
  {
    id: "model",
    name: "模型配置",
    icon: '<svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2z"/></svg>',
  },
  {
    id: "channel",
    name: "通道配置",
    icon: '<svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>',
  },
  {
    id: "agent",
    name: "Agent配置",
    icon: '<svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
  },
  {
    id: "knowledge",
    name: "知识检索",
    icon: '<svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
  },
  {
    id: "tools",
    name: "工具配置",
    icon: '<svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>',
  },
  {
    id: "roles",
    name: "子Agent配置",
    icon: '<svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
  },
  {
    id: "system",
    name: "系统配置",
    icon: '<svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
  },
];

const currentProviderName = computed(() => {
  const current = config.value.model?.current || "";
  let providerName = "";
  if (current.includes("/")) {
    providerName = current.split("/")[0];
  } else {
    for (const provider of config.value.providers || []) {
      if (provider.has_key && provider.enabled) {
        providerName = provider.name;
        break;
      }
    }
  }
  return getProviderDisplayName(providerName) || providerName || "未设置";
});

const enabledChannelsCount = computed(() => {
  return config.value.channels
    ? config.value.channels.filter((c: any) => c.enabled).length
    : 0;
});

const uploadMaxSizeMB = computed({
  get: () => Math.round((upload.value.max_file_size || 10485760) / 1048576),
  set: (value: number) => {
    upload.value.max_file_size = (value || 10) * 1048576;
  },
});

const availableProviders = computed(() => {
  return (config.value.providers || [])
    .filter((p: any) => p.has_key && p.enabled)
    .map((p: any) => p.name);
});

const getModelsForProvider = (providerName: string) => {
  if (!providerName) return [];
  const provider = config.value.providers?.find(
    (p: any) => p.name === providerName,
  );
  return provider?.models || [];
};

const getModelDisplayName = (modelId: string) => {
  if (!modelId) return "";
  if (modelId.includes("/")) {
    const [provider, model] = modelId.split("/", 1);
    const providerData = config.value.providers?.find(
      (p: any) => p.name === provider,
    );
    if (providerData?.models) {
      const modelData = providerData.models.find(
        (m: any) => m.model_id === model,
      );
      return modelData?.display_name || model;
    }
    return model;
  }
  for (const provider of config.value.providers || []) {
    if (provider?.models) {
      const modelData = provider.models.find(
        (m: any) => m.model_id === modelId,
      );
      if (modelData) {
        return modelData.display_name || modelId;
      }
    }
  }
  return modelId;
};

const getProviderDisplayName = (providerName: string) => {
  if (!providerName) return "";
  const provider = config.value.providers?.find(
    (p: any) => p.name === providerName,
  );
  return provider?.display_name || providerName;
};

const isCurrentProvider = (providerName: string) => {
  const current = config.value.model?.current || "";
  return current.includes("/") && current.split("/")[0] === providerName;
};

const isCurrentModel = (providerName: string, modelId: string) => {
  const current = config.value.model?.current || "";
  return current === modelId || current === `${providerName}/${modelId}`;
};

const formatNumber = (num: number) => {
  if (!num || num === 0) return "0";
  if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
  if (num >= 1000) return (num / 1000).toFixed(1) + "K";
  return num.toString();
};

const formatCurrency = (amount: number, currency: string = "CNY") => {
  if (!amount || amount === 0) return "¥ 0.00";
  const symbol = currency === "CNY" ? "¥" : "$";
  return `${symbol} ${amount.toFixed(2)}`;
};

const getModelUsagePercent = (modelStat: any) => {
  if (!tokenStats.value.total_tokens || tokenStats.value.total_tokens === 0)
    return 0;
  const modelTokens = modelStat.total_tokens || 0;
  return Math.min(
    100,
    Math.round((modelTokens / tokenStats.value.total_tokens) * 100),
  );
};

const formatPrice = (price: number) => {
  if (price === undefined || price === null) return "0.00";
  return price.toFixed(2);
};

const getChannelStatusClass = (channel: any) => {
  if (channel.enabled && channel.has_credentials) return "status-online";
  if (channel.has_credentials) return "status-standby";
  return "status-offline";
};

const getChannelStatusText = (channel: any) => {
  if (channel.enabled && channel.has_credentials) return "运行中";
  if (channel.has_credentials) return "待启用";
  return "未配置";
};

const getChannelFields = (channelName: string): any[] => {
  const fieldDefinitions: Record<string, any[]> = {
    telegram: [
      {
        key: "token",
        label: "Bot Token",
        type: "password",
        placeholder: "输入 Telegram Bot Token",
      },
    ],
    whatsapp: [
      {
        key: "bridge_token",
        label: "桥接 Token",
        type: "password",
        placeholder: "输入 WhatsApp 桥接 Token",
      },
    ],
    feishu: [
      {
        key: "app_id",
        label: "App ID",
        type: "text",
        placeholder: "输入飞书 App ID",
      },
      {
        key: "app_secret",
        label: "App Secret",
        type: "password",
        placeholder: "输入飞书 App Secret",
      },
    ],
    dingtalk: [
      {
        key: "client_id",
        label: "Client ID",
        type: "text",
        placeholder: "输入钉钉 Client ID",
      },
      {
        key: "client_secret",
        label: "Client Secret",
        type: "password",
        placeholder: "输入钉钉 Client Secret",
      },
    ],
    discord: [
      {
        key: "token",
        label: "Bot Token",
        type: "password",
        placeholder: "输入 Discord Bot Token",
      },
    ],
    slack: [
      {
        key: "bot_token",
        label: "Bot Token",
        type: "password",
        placeholder: "输入 Slack Bot Token",
      },
    ],
    email: [
      {
        key: "imap_host",
        label: "IMAP 主机",
        type: "text",
        placeholder: "如 imap.gmail.com",
      },
      {
        key: "imap_port",
        label: "IMAP 端口",
        type: "text",
        placeholder: "如 993",
      },
      {
        key: "imap_username",
        label: "IMAP 用户名",
        type: "text",
        placeholder: "邮箱地址",
      },
      {
        key: "imap_password",
        label: "IMAP 密码",
        type: "password",
        placeholder: "邮箱密码或应用密码",
      },
      {
        key: "smtp_host",
        label: "SMTP 主机",
        type: "text",
        placeholder: "如 smtp.gmail.com",
      },
      {
        key: "smtp_port",
        label: "SMTP 端口",
        type: "text",
        placeholder: "如 587",
      },
      {
        key: "smtp_username",
        label: "SMTP 用户名",
        type: "text",
        placeholder: "邮箱地址",
      },
      {
        key: "smtp_password",
        label: "SMTP 密码",
        type: "password",
        placeholder: "邮箱密码或应用密码",
      },
    ],
    mochat: [
      {
        key: "base_url",
        label: "API 地址",
        type: "text",
        placeholder: "输入 Mochat API 地址",
      },
      {
        key: "claw_token",
        label: "Claw Token",
        type: "password",
        placeholder: "输入 Claw Token",
      },
    ],
    qq: [
      {
        key: "app_id",
        label: "App ID",
        type: "text",
        placeholder: "输入 QQ App ID",
      },
      {
        key: "secret",
        label: "Secret",
        type: "password",
        placeholder: "输入 QQ Secret",
      },
    ],
  };

  return fieldDefinitions[channelName] || [];
};

const toggleProviderExpand = (providerName: string) => {
  expandedProvider.value =
    expandedProvider.value === providerName ? null : providerName;
};

const editProvider = (provider: any) => {
  editingProvider.value = provider;
  providerForm.value = { apiKey: "", apiBase: provider.api_base || "" };
  testConnectionResult.value = null;
};

const editChannel = (channel: any) => {
  editingChannel.value = channel;
  const fields = getChannelFields(channel.name);
  const form: Record<string, any> = {
    enabled: channel.enabled || false,
  };
  fields.forEach((field) => {
    if (
      channel.credentials_masked &&
      channel.credentials_masked[field.key] !== undefined
    ) {
      form[field.key] = "";
    } else {
      form[field.key] = "";
    }
  });
  channelForm.value = form;
  showChannelModal.value = true;
};

const saveChannelConfig = async () => {
  try {
    if (api?.config?.updateChannel && editingChannel.value) {
      const payload: Record<string, any> = {
        enabled: channelForm.value.enabled,
      };
      const fields = getChannelFields(editingChannel.value.name);
      fields.forEach((field) => {
        const value = channelForm.value[field.key];
        if (value && value.trim() !== "") {
          payload[field.key] = value;
        }
      });

      await api.config.updateChannel(editingChannel.value.name, payload);

      editingChannel.value.enabled = payload.enabled;
      if (editingChannel.value.credentials_masked) {
        fields.forEach((field) => {
          if (payload[field.key]) {
            editingChannel.value.credentials_masked[field.key] = "******";
          }
        });
      }
      editingChannel.value.has_credentials = true;

      uiStore.showToast("渠道配置已保存", "success");
      showChannelModal.value = false;
    }
  } catch (e) {
    uiStore.showToast("保存失败", "error");
  }
};

const restartSystem = async () => {
  restarting.value = true;
  try {
    if (api?.config?.restart) {
      await api.config.restart();
      uiStore.showToast("系统正在重启...", "success");
    } else {
      uiStore.showToast("重启功能暂不可用", "warning");
    }
  } catch (e) {
    uiStore.showToast("重启请求失败", "error");
  } finally {
    restarting.value = false;
    showRestartConfirm.value = false;
  }
};

const loadRoles = async () => {
  try {
    const response = await fetch("/api/agents/roles");
    if (response.ok) {
      rolesList.value = await response.json();
    }
  } catch (e) {
    console.error("Failed to load roles:", e);
  }
};

const editRole = (role: RoleInfo) => {
  editingRole.value = role;
  roleSaveResult.value = null;

  if (role.has_custom_model && role.model_config) {
    roleForm.value = {
      useCustomModel: true,
      provider: role.model_config.provider || "",
      model: role.model_config.model || "",
      temperature: 0.7,
      max_tokens: 4096,
    };
  } else {
    roleForm.value = {
      useCustomModel: false,
      provider: "",
      model: "",
      temperature: 0.7,
      max_tokens: 4096,
    };
  }

  showRoleModal.value = true;
};

const closeRoleModal = () => {
  showRoleModal.value = false;
  editingRole.value = null;
  roleSaveResult.value = null;
};

const saveRoleConfig = async () => {
  if (!editingRole.value) return;

  savingRole.value = true;
  roleSaveResult.value = null;

  try {
    const updateData: any = {};

    if (roleForm.value.useCustomModel) {
      if (!roleForm.value.provider || !roleForm.value.model) {
        roleSaveResult.value = {
          success: false,
          message: "请选择 Provider 和模型",
        };
        savingRole.value = false;
        return;
      }

      updateData.model_settings = {
        provider: roleForm.value.provider,
        model: roleForm.value.model,
        temperature: roleForm.value.temperature,
        max_tokens: roleForm.value.max_tokens,
      };
    } else {
      updateData.model_settings = null;
    }

    const response = await fetch(`/api/agents/roles/${editingRole.value.key}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updateData),
    });

    const result = await response.json();

    if (result.success) {
      roleSaveResult.value = { success: true, message: "保存成功" };
      await loadRoles();
      setTimeout(() => {
        closeRoleModal();
      }, 1000);
    } else {
      roleSaveResult.value = {
        success: false,
        message: result.message || "保存失败",
      };
    }
  } catch (e) {
    roleSaveResult.value = { success: false, message: "请求失败" };
  } finally {
    savingRole.value = false;
  }
};

const toggleChannel = async (channel: any) => {
  if (!channel.enabled) {
    const fields = getChannelFields(channel.name);
    const hasConfig = fields.some((field) => {
      const maskedValue = channel.credentials_masked?.[field.key];
      return (
        maskedValue && maskedValue.trim() !== "" && maskedValue !== "******"
      );
    });
    if (!hasConfig) {
      uiStore.showToast("请先配置渠道参数", "error");
      return;
    }
  }
  try {
    if (api?.config?.updateChannel) {
      await api.config.updateChannel(channel.name, {
        enabled: !channel.enabled,
      });
      channel.enabled = !channel.enabled;
      uiStore.showToast("渠道已更新", "success");
    }
  } catch (e) {
    uiStore.showToast("更新失败", "error");
  }
};

const switchToModel = async (providerName: string, modelId: string) => {
  try {
    if (api?.config?.setModel) {
      await api.config.setModel(modelId, undefined, providerName);
      await loadConfig();
      uiStore.showToast(`已切换到 ${modelId}`, "success");
    }
  } catch (e) {
    uiStore.showToast("切换失败", "error");
  }
};

const testConnection = async () => {
  testingConnection.value = true;
  testConnectionResult.value = null;
  try {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    testConnectionResult.value = { success: true, message: "连接成功" };
  } catch (e) {
    testConnectionResult.value = { success: false, message: "连接失败" };
  }
  testingConnection.value = false;
};

const saveProvider = async () => {
  try {
    if (api?.config?.updateProvider) {
      await api.config.updateProvider(editingProvider.value.name, {
        api_key: providerForm.value.apiKey,
        api_base: providerForm.value.apiBase,
      });
      uiStore.showToast("保存成功", "success");
    }
    editingProvider.value = null;
  } catch (e) {
    uiStore.showToast("保存失败", "error");
  }
};

const addModel = (providerName: string) => {
  editingModel.value = null;
  editingModelProvider.value = providerName;
  modelForm.value = {
    model_id: "",
    display_name: "",
    description: "",
    input_price: 0,
    output_price: 0,
    max_tokens: 4096,
    token_quota: 0,
    supports_vision: false,
    supports_function_calling: true,
    supports_streaming: true,
    currency: "CNY",
  };
  showModelModal.value = true;
};

const editModel = (providerName: string, model: any) => {
  editingModel.value = model;
  editingModelProvider.value = providerName;
  modelForm.value = {
    model_id: model.model_id,
    display_name: model.display_name || "",
    description: model.description || "",
    input_price: model.input_price || 0,
    output_price: model.output_price || 0,
    max_tokens: model.max_tokens || 4096,
    token_quota: model.token_quota || 0,
    supports_vision: model.supports_vision || false,
    supports_function_calling: model.supports_function_calling !== false,
    supports_streaming: model.supports_streaming !== false,
    currency: model.currency || "CNY",
  };
  showModelModal.value = true;
};

const closeModelModal = () => {
  showModelModal.value = false;
  editingModel.value = null;
  editingModelProvider.value = "";
};

const saveModel = async () => {
  try {
    if (!modelForm.value.model_id) {
      uiStore.showToast("请输入模型 ID", "error");
      return;
    }

    const modelData = {
      ...modelForm.value,
      provider: editingModelProvider.value,
      is_custom: true,
      status: "active",
    };

    if (api?.config?.addCustomModel) {
      await api.config.addCustomModel(modelData);
      uiStore.showToast(
        editingModel.value ? "模型已更新" : "模型已添加",
        "success",
      );
      await loadConfig();
      closeModelModal();
    } else {
      uiStore.showToast("API 不可用", "error");
    }
  } catch (e) {
    uiStore.showToast("保存失败", "error");
  }
};

const deleteModel = async (providerName: string, modelId: string) => {
  const confirmed = await uiStore.showConfirm(
    "确认删除",
    `确定要删除模型 "${modelId}" 吗？此操作不可撤销。`,
  );
  if (!confirmed) return;

  try {
    if (api?.config?.deleteCustomModel) {
      await api.config.deleteCustomModel(providerName, modelId);
      uiStore.showToast("模型已删除", "success");
      await loadConfig();
    } else {
      uiStore.showToast("删除模型功能开发中", "info");
    }
  } catch (e) {
    uiStore.showToast("删除失败", "error");
  }
};

const updateReasoningSetting = async () => {
  try {
    if (api?.config?.setReasoning) {
      await api.config.setReasoning(enableReasoning.value);
      agentDefaults.value.enable_reasoning = enableReasoning.value;
      uiStore.showToast("设置已保存", "success");
    }
  } catch (e) {
    uiStore.showToast("保存失败", "error");
  }
};

const updateToolCallSetting = async () => {
  try {
    if (api?.config?.setToolCall) {
      await api.config.setToolCall(toolCallEnabled.value);
      uiStore.showToast("设置已保存", "success");
    }
  } catch (e) {
    uiStore.showToast("保存失败", "error");
  }
};

const saveAgentDefaults = async () => {
  try {
    if (api?.config?.updateAgentDefaults) {
      await api.config.updateAgentDefaults(agentDefaults.value);
      uiStore.showToast("设置已保存", "success");
    }
  } catch (e) {
    uiStore.showToast("保存失败", "error");
  }
};

const saveKnowledgeConfig = async () => {
  try {
    if (api?.config?.updateKnowledge) {
      await api.config.updateKnowledge(config.value.knowledge);
      uiStore.showToast("设置已保存", "success");
    }
  } catch (e) {
    uiStore.showToast("保存失败", "error");
  }
};

const saveGatewayConfig = async () => {
  try {
    if (api?.config?.updateGateway) {
      await api.config.updateGateway(gateway.value);
      uiStore.showToast("设置已保存", "success");
    }
  } catch (e) {
    uiStore.showToast("保存失败", "error");
  }
};

const saveUploadConfig = async () => {
  try {
    if (api?.config?.updateUpload) {
      await api.config.updateUpload(upload.value);
      uiStore.showToast("设置已保存", "success");
    }
  } catch (e) {
    uiStore.showToast("保存失败", "error");
  }
};

const saveToolsConfig = async () => {
  try {
    if (api?.config?.updateTools) {
      await api.config.updateTools({
        restrict_to_workspace: config.value.tools.restrict_to_workspace,
        exec_timeout: config.value.tools.exec_timeout,
        web_search_enabled: config.value.tools.web_search,
        web_search_api_key: config.value.tools.web_search_api_key,
        web_search_max_results: config.value.tools.web_search_max_results,
        weather_enabled: config.value.tools.weather,
        weather_api_key: config.value.tools.weather_api_key,
        mcp_enabled: config.value.tools.mcp,
      });
      await loadConfig();
      uiStore.showToast("工具配置已保存", "success");
    } else {
      uiStore.showToast("保存功能不可用", "error");
    }
  } catch (e) {
    uiStore.showToast("保存失败", "error");
  }
};

const toggleToolConfig = (tool: string) => {
  expandedTools.value[tool as keyof typeof expandedTools.value] =
    !expandedTools.value[tool as keyof typeof expandedTools.value];
};

const loadConfig = async () => {
  try {
    if (api?.config?.get) {
      const data = await api.config.get();
      config.value = { ...config.value, ...data };
      enableReasoning.value = data.model?.enable_reasoning ?? true;
      agentDefaults.value.enable_reasoning = enableReasoning.value;
      if (data.agent_defaults) {
        agentDefaults.value = {
          ...agentDefaults.value,
          ...data.agent_defaults,
        };
      }
      if (data.upload) {
        upload.value = { ...upload.value, ...data.upload };
      }
      if (data.gateway) {
        gateway.value = { ...gateway.value, ...data.gateway };
      }
    }
  } catch (e) {
    console.error("Failed to load config:", e);
  }
  loadTokenStats();
};

const loadTokenStats = async (period?: string) => {
  if (period) {
    tokenPeriod.value = period;
  }
  try {
    const data = await api.stats.getTokenStats(tokenPeriod.value);
    tokenStats.value = data;
  } catch (e) {
    console.error("Failed to load token stats:", e);
  }
};

onMounted(() => {
  loadConfig();
  loadRoles();
});
</script>

<style scoped lang="scss">
.config-page {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background-color: var(--color-bg-base);
}

.config-layout {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.config-sidebar {
  width: 240px;
  background-color: var(--color-sidebar-bg);
  border-right: 1px solid var(--color-border);
  padding: 1rem 0;
  flex-shrink: 0;
  overflow-y: auto;
  transition: width var(--transition-normal);

  @media (max-width: 768px) {
    width: 60px;
    padding: 1rem 0.25rem;

    .sidebar-title,
    .sidebar-item span:not(.sidebar-icon) {
      display: none;
    }

    .sidebar-item {
      justify-content: center;
      padding: 0.75rem 0.5rem;
    }

    .sidebar-icon {
      margin-right: 0;
    }
  }
}

.config-main {
  flex: 1;
  padding: 1.5rem;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

.sidebar-section {
  padding: 0 0.5rem;
}

.sidebar-title {
  padding: 0.5rem 1rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  font-size: 0.75rem;
  text-transform: uppercase;
}

.sidebar-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-text-primary);
  transition: background-color var(--transition-fast);

  &:hover {
    background-color: var(--color-sidebar-item-hover);
  }

  &.active {
    background-color: var(--color-sidebar-item-active);
    color: var(--color-primary);
  }
}

.sidebar-icon {
  width: 18px;
  height: 18px;
}

.config-section {
  max-width: 900px;
}

.card {
  background-color: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.config-tip {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  background-color: var(--color-primary-light);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-primary);

  .tip-icon {
    font-size: 1rem;
  }

  .tip-text {
    font-size: 0.875rem;
    color: var(--color-primary);
  }
}

.card-header {
  padding: 1rem;
  border-bottom: 1px solid var(--color-border);

  h3 {
    margin: 0;
    font-size: 1.125rem;
    font-weight: 600;
  }
}

.card-body {
  padding: 1rem;
}

.service-overview-card,
.token-stats-card {
  background-color: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  margin-bottom: 1rem;
  overflow: hidden;
}

.overview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  border-bottom: 1px solid var(--color-border);
}

.overview-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0;
}

.overview-main {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  padding: 1.5rem;
}

.overview-stat {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem;
  background-color: var(--color-bg-muted);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  transition: all var(--transition-fast);

  &:hover {
    border-color: var(--color-primary);
    box-shadow: var(--shadow-sm);
  }
}

.overview-icon {
  width: 48px;
  height: 48px;
  padding: 0.75rem;
  color: var(--color-primary);
  background-color: var(--color-primary-light);
  border-radius: var(--radius-md);
  flex-shrink: 0;
}

.overview-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.overview-label {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.overview-value {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.overview-modules {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  padding: 1rem;
  border-top: 1px solid var(--color-border);
}

.module-status-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border-radius: var(--radius-md);
  background-color: var(--color-bg-muted);
  min-width: 0;
}

.module-status-item > * {
  flex-shrink: 0;
}

.module-label {
  flex-shrink: 0;
  white-space: nowrap;
}

.module-value {
  flex-shrink: 0;
  white-space: nowrap;
}

.module-icon {
  width: 20px;
  height: 20px;
  color: var(--color-text-secondary);
}

.module-label {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.module-value {
  font-size: 0.875rem;
  font-weight: 500;
  margin-left: auto;

  &.text-success {
    color: var(--color-success);
  }

  &.text-muted {
    color: var(--color-text-muted);
  }
}

.period-selector {
  display: flex;
  gap: 0.25rem;
}

.period-btn {
  padding: 0.25rem 0.75rem;
  border: 1px solid var(--color-border);
  background: var(--color-bg-surface);
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  cursor: pointer;

  &.active {
    background: var(--color-primary);
    color: white;
    border-color: var(--color-primary);
  }

  &:hover:not(.active) {
    background: var(--color-bg-muted);
  }
}

.token-stats-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  padding: 1.25rem;
}

.token-stat {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  padding: 1rem 1.25rem;
  background: linear-gradient(
    135deg,
    var(--color-bg-muted) 0%,
    var(--color-bg-surface) 100%
  );
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  transition: all var(--transition-fast);

  &:hover {
    border-color: var(--color-primary);
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }

  &.token-stat-primary {
    grid-column: span 1;
    background: linear-gradient(
      135deg,
      var(--color-primary-light) 0%,
      var(--color-bg-surface) 100%
    );
    border-color: var(--color-primary);

    .token-stat-icon {
      background: var(--color-primary);
      color: white;
    }

    .token-stat-value {
      color: var(--color-primary);
    }
  }

  &.token-stat-cost {
    .token-stat-icon {
      background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    }

    .token-stat-value {
      color: #10b981;
    }
  }
}

.token-stat-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  background: var(--color-bg-muted);
  border-radius: var(--radius-md);
  flex-shrink: 0;
}

.token-stat-content {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  min-width: 0;
}

.token-stat-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1.2;
}

.token-stat-label {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.token-by-model {
  margin-top: 0.5rem;
  padding: 1.25rem;
  border-top: 1px solid var(--color-border);
}

.by-model-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 1rem;
}

.model-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}

.model-stat-card {
  padding: 1.25rem;
  background: var(--color-bg-muted);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  transition: all var(--transition-fast);

  &:hover {
    border-color: var(--color-primary);
    box-shadow: var(--shadow-sm);
  }
}

.model-stat-header {
  margin-bottom: 0.875rem;
}

.model-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.model-stat-name {
  font-weight: 600;
  font-size: 1rem;
  color: var(--color-text-primary);
}

.model-stat-name-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  min-width: 0;
}

.model-stat-provider {
  font-size: 0.6875rem;
  padding: 0.125rem 0.5rem;
  background: var(--color-primary-light);
  color: var(--color-primary);
  border-radius: var(--radius-full);
  font-weight: 500;
  flex-shrink: 0;
}

.model-stat-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.metric-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;

  &.metric-cost {
    .metric-value {
      color: #10b981;
    }
  }
}

.metric-icon {
  font-size: 0.875rem;
  flex-shrink: 0;
}

.metric-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.metric-value {
  font-weight: 600;
  font-size: 0.8125rem;
  color: var(--color-text-primary);
  line-height: 1.2;
}

.metric-label {
  font-size: 0.625rem;
  color: var(--color-text-muted);
  line-height: 1;
}

.model-stat-progress {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: var(--color-bg-surface);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary) 0%, #60a5fa 100%);
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
}

.progress-label {
  font-size: 0.6875rem;
  color: var(--color-text-secondary);
  font-weight: 500;
  min-width: 32px;
  text-align: right;
}

.provider-list {
  padding: 0.75rem;
}

.provider-item-wrapper {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  margin-bottom: 0.75rem;
  overflow: hidden;
  transition: all var(--transition-fast);

  &:hover {
    border-color: var(--color-primary);
    box-shadow: var(--shadow-sm);
  }
}

.provider-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  cursor: pointer;
  background-color: var(--color-bg-surface);

  &:hover {
    background-color: var(--color-bg-muted);
  }
}

.provider-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.provider-name {
  font-weight: 600;
  font-size: 0.9375rem;
}

.provider-desc {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.provider-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.model-count {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  padding: 0.125rem 0.5rem;
  background-color: var(--color-bg-muted);
  border-radius: var(--radius-sm);
}

.expand-icon {
  font-size: 0.625rem;
  color: var(--color-text-muted);
  transition: transform var(--transition-fast);
}

.provider-models {
  border-top: 1px solid var(--color-border);
  padding: 0.75rem;
  background-color: var(--color-bg-muted);
}

.model-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.875rem 1rem;
  margin-bottom: 0.5rem;
  background-color: var(--color-bg-surface);
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  transition: all var(--transition-fast);

  &:last-child {
    margin-bottom: 0;
  }

  &:hover {
    border-color: var(--color-border);
    box-shadow: var(--shadow-sm);
  }
}

.model-info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.25rem;
  flex: 1;
  min-width: 0;
}

.model-name-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.model-name {
  font-weight: 600;
  font-size: 0.9375rem;
}

.model-provider {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.model-desc {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.model-caps {
  display: flex;
  gap: 0.375rem;
}

.model-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.model-price {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  font-family: "SF Mono", "Consolas", monospace;
}

.model-btn-group {
  display: flex;
  gap: 0.25rem;
}

.btn-icon {
  padding: 0.375rem;
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);

  &:hover {
    background-color: var(--color-bg-muted);
    color: var(--color-text-primary);
    border-color: var(--color-text-secondary);
  }

  &.btn-danger:hover {
    background-color: var(--color-error-bg);
    color: var(--color-error);
    border-color: var(--color-error);
  }
}

.channel-list {
  padding: 0.5rem;
}

.channel-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  margin-bottom: 0.5rem;
}

.channel-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.channel-name {
  font-weight: 500;
}

.channel-status {
  font-size: 0.75rem;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;

  &.status-online {
    background-color: var(--color-success-bg);
    color: var(--color-success);
  }

  &.status-standby {
    background-color: var(--color-warning-bg);
    color: var(--color-warning);
  }

  &.status-offline {
    background-color: var(--color-bg-muted);
    color: var(--color-text-muted);
  }
}

.channel-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;

  input {
    opacity: 0;
    width: 0;
    height: 0;
  }
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--color-border);
  transition: 0.3s;
  border-radius: 22px;

  &:before {
    position: absolute;
    content: "";
    height: 16px;
    width: 16px;
    left: 3px;
    bottom: 3px;
    background-color: white;
    transition: 0.3s;
    border-radius: 50%;
  }
}

input:checked + .slider {
  background-color: var(--color-primary);
}

input:checked + .slider:before {
  transform: translateX(18px);
}

.form-group {
  margin-bottom: 1rem;
  padding: 1rem;
  background: var(--color-bg-muted);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.form-label {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-weight: 500;
  margin-bottom: 0;
  cursor: pointer;

  input[type="checkbox"] {
    width: 18px;
    height: 18px;
    accent-color: var(--color-primary);
    cursor: pointer;
  }
}

.form-help {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  margin-top: 0.5rem;
  padding-left: 0;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background-color: var(--color-bg-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  min-width: 400px;
  max-width: 90vw;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  border-bottom: 1px solid var(--color-border);

  h3 {
    font-size: 1.125rem;
    font-weight: 600;
    margin: 0;
  }
}

.modal-close {
  font-size: 1.5rem;
  line-height: 1;
  color: var(--color-text-muted);
  background: none;
  border: none;
  cursor: pointer;

  &:hover {
    color: var(--color-text-primary);
  }
}

.modal-body {
  padding: 1rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 1rem;
  border-top: 1px solid var(--color-border);
}

.test-result {
  padding: 0.5rem;
  border-radius: var(--radius-sm);
  margin-top: 0.5rem;
  font-size: 0.875rem;

  &.success {
    background-color: var(--color-success-bg);
    color: var(--color-success);
  }

  &.error {
    background-color: var(--color-error-bg);
    color: var(--color-error);
  }
}

.tool-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  margin-bottom: 0.5rem;
}

.tool-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.tool-icon {
  font-size: 1.25rem;
  line-height: 1;
}

.tool-title-info {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.tool-name {
  font-weight: 500;
}

.tool-desc {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.tool-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.tool-config-body {
  padding: 1rem;
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border);
  border-top: none;
  border-radius: 0 0 var(--radius-md) var(--radius-md);
  margin-bottom: 0.5rem;
}

.mcp-servers-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.mcp-server-item {
  padding: 0.75rem;
  background: var(--color-bg-surface);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.mcp-server-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.375rem;
}

.mcp-server-name {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--color-text-primary);
}

.mcp-server-details {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  font-family: monospace;
}

.mcp-server-url,
.mcp-server-cmd {
  word-break: break-all;
}

.mcp-empty {
  text-align: center;
  padding: 1.5rem;
  color: var(--color-text-muted);

  p {
    margin: 0.25rem 0;
  }

  .mcp-help {
    font-size: 0.75rem;
  }
}

.reasoning-settings {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.reasoning-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  background: var(--color-bg-muted);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.reasoning-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.reasoning-name {
  font-weight: 600;
  font-size: 0.9375rem;
  color: var(--color-text-primary);
}

.reasoning-desc {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.reasoning-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: 500;

  &.enabled {
    background: var(--color-success-light);
    color: var(--color-success);
  }

  &.disabled {
    background: var(--color-bg-surface);
    color: var(--color-text-muted);
  }
}

.status-detail {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.roles-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.role-card {
  padding: 1rem;
  background: var(--color-bg-muted);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.role-header {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
}

.role-icon {
  font-size: 1.5rem;
  line-height: 1;
}

.role-info {
  flex: 1;
}

.role-name {
  font-weight: 600;
  font-size: 0.9375rem;
  color: var(--color-text-primary);
  margin: 0 0 0.25rem 0;
}

.role-desc {
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
  margin: 0;
}

.role-model-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--color-border);
}

.model-badge {
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 500;

  &.default {
    background: var(--color-bg-surface);
    color: var(--color-text-muted);
  }

  &.custom {
    background: var(--color-primary-light);
    color: var(--color-primary);
  }
}

.model-detail {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.save-result {
  padding: 0.75rem;
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
  margin-top: 1rem;

  &.success {
    background: var(--color-success-light);
    color: var(--color-success);
  }

  &.error {
    background: var(--color-danger-light);
    color: var(--color-danger);
  }
}
</style>
