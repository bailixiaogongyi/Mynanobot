<template>
  <div class="page-container">
    <div class="content-area">
      <div class="page-header">
        <h2>我的技能</h2>
        <p class="page-description">
          已安装的技能列表，包括内置技能和从市场安装的技能
        </p>
      </div>
      <div class="skills-filter">
        <button
          :class="[
            'btn',
            'btn-sm',
            filterSource === 'all' ? 'btn-primary' : 'btn-secondary',
          ]"
          @click="filterSource = 'all'"
        >
          全部
        </button>
        <button
          :class="[
            'btn',
            'btn-sm',
            filterSource === 'builtin' ? 'btn-primary' : 'btn-secondary',
          ]"
          @click="filterSource = 'builtin'"
        >
          内置技能
        </button>
        <button
          :class="[
            'btn',
            'btn-sm',
            filterSource === 'marketplace' ? 'btn-primary' : 'btn-secondary',
          ]"
          @click="filterSource = 'marketplace'"
        >
          市场技能
        </button>
        <button
          :class="[
            'btn',
            'btn-sm',
            filterSource === 'workspace' ? 'btn-primary' : 'btn-secondary',
          ]"
          @click="filterSource = 'workspace'"
        >
          自建技能
        </button>
        <router-link
          to="/marketplace"
          class="btn btn-sm btn-secondary"
          style="margin-left: auto"
        >
          浏览市场
        </router-link>
      </div>
      <div class="skills-grid">
        <div
          v-for="skill in filteredSkills"
          :key="skill.name + skill.source"
          class="skill-card"
          @click="showSkillDetail(skill)"
        >
          <div class="skill-header">
            <span class="skill-icon">{{ getSkillIcon(skill.name) }}</span>
            <div class="skill-info">
              <h3 class="skill-name">{{ skill.meta?.name || skill.name }}</h3>
              <p class="skill-description">
                {{ skill.meta?.description || skill.description || "" }}
              </p>
            </div>
          </div>
          <div class="skill-meta">
            <span :class="['skill-badge', 'skill-type-' + skill.source]">
              {{
                skill.source === "builtin"
                  ? "内置"
                  : skill.source === "marketplace"
                    ? "市场"
                    : "自建"
              }}
            </span>
            <span
              :class="[
                'skill-badge',
                skill.meta?.always || skill.always ? 'always' : 'on-demand',
              ]"
            >
              {{ skill.meta?.always || skill.always ? "始终加载" : "按需加载" }}
            </span>
          </div>
        </div>
      </div>
      <div v-if="filteredSkills.length === 0" class="empty-state">
        <div class="empty-icon">🔧</div>
        <p>暂无技能</p>
        <router-link
          to="/marketplace"
          class="btn btn-primary"
          style="margin-top: 1rem"
        >
          浏览技能市场
        </router-link>
      </div>
    </div>

    <!-- 技能详情弹窗 -->
    <Modal
      :show="!!selectedSkill"
      title="技能详情"
      size="lg"
      @close="selectedSkill = null"
    >
      <div class="skill-detail-wrapper">
        <div class="skill-detail-header">
          <div class="skill-detail-icon">
            {{ getSkillIcon(selectedSkill?.name || "") }}
          </div>
          <h3 class="skill-detail-title">
            {{ selectedSkill?.meta?.name || selectedSkill?.name }}
          </h3>
        </div>
        <div class="skill-detail-meta">
          <div class="skill-detail-badges">
            <span
              :class="['skill-badge', 'skill-type-' + selectedSkill?.source]"
            >
              <span class="badge-icon">{{
                selectedSkill?.source === "builtin" ? "📦" : "📁"
              }}</span>
              {{
                selectedSkill?.source === "builtin" ? "内置技能" : "自建技能"
              }}
            </span>
            <span
              :class="[
                'skill-badge',
                selectedSkill?.meta?.always || selectedSkill?.always
                  ? 'always'
                  : 'on-demand',
              ]"
            >
              <span class="badge-icon">{{
                selectedSkill?.meta?.always || selectedSkill?.always
                  ? "⚡"
                  : "🔄"
              }}</span>
              {{
                selectedSkill?.meta?.always || selectedSkill?.always
                  ? "始终加载"
                  : "按需加载"
              }}
            </span>
          </div>
          <p v-if="selectedSkill?.meta?.description" class="skill-detail-desc">
            {{ selectedSkill.meta.description }}
          </p>
        </div>

        <div class="skill-detail-section">
          <div
            class="skill-content"
            v-html="renderMarkdown(selectedSkill?.content || '')"
          ></div>
        </div>
      </div>

      <template #footer>
        <div class="modal-footer-actions">
          <div class="footer-left">
            <span class="skill-source-info">
              <span class="source-label">来源:</span>
              <span class="source-value">{{
                selectedSkill?.source === "builtin" ? "系统内置" : "工作空间"
              }}</span>
            </span>
          </div>
          <div class="footer-right">
            <button class="btn btn-secondary" @click="selectedSkill = null">
              关闭
            </button>
            <button
              v-if="
                selectedSkill?.source === 'workspace' ||
                selectedSkill?.source === 'marketplace'
              "
              class="btn btn-danger"
              @click="deleteSkill(selectedSkill)"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <polyline points="3 6 5 6 21 6"></polyline>
                <path
                  d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"
                ></path>
              </svg>
              删除技能
            </button>
          </div>
        </div>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onActivated } from "vue";
import { marked } from "marked";
import api from "@/services/api";
import Modal from "@/components/ui/Modal.vue";

const skills = ref<any[]>([]);
const selectedSkill = ref<any | null>(null);
const filterSource = ref<"all" | "builtin" | "workspace">("all");

const filteredSkills = computed(() => {
  if (filterSource.value === "all") {
    return skills.value;
  }
  return skills.value.filter((s) => s.source === filterSource.value);
});

const loadSkills = async () => {
  try {
    if (api.skills) {
      const result = await api.skills.list();
      skills.value = Array.isArray(result) ? result : result.skills || [];
    }
  } catch (e) {
    console.error("Failed to load skills:", e);
  }
};

const showSkillDetail = async (skill: any) => {
  try {
    if (api.skills) {
      const result = await api.skills.get(skill.name);
      selectedSkill.value = result;
    }
  } catch (e) {
    console.error("Failed to load skill detail:", e);
  }
};

const getSkillIcon = (name: string) => {
  const iconMap: Record<string, string> = {
    archive: "📦",
    "browser-automation": "🌐",
    cron: "⏰",
    "daily-note": "📅",
    "excel-operations": "📊",
    github: "🐙",
    memory: "🧠",
    "ocr-operations": "👁️",
    "pdf-operations": "📕",
    "pptx-operations": "📽️",
    "project-note": "📁",
    "skill-creator": "🛠️",
    summarize: "📝",
    "temp-note": "📋",
    tmux: "💻",
    "topic-note": "📑",
    weather: "🌤️",
    "word-operations": "📘",
    Search: "🔍",
    "Web fetch": "🌐",
    Calculator: "🧮",
    "Code runner": "💻",
    "File read": "📄",
    "File write": "📝",
    "Image generation": "🎨",
    default: "🔧",
  };
  return iconMap[name] || iconMap["default"];
};

const renderMarkdown = (content: string) => {
  if (!content) return "";
  return marked.parse(content) as string;
};

const deleteSkill = async (skill: any) => {
  try {
    if (skill.source === 'marketplace') {
      // 市场技能使用 marketplace uninstall API
      await api.marketplace.uninstall(skill.name);
    } else if (skill.source === 'workspace') {
      // 自建技能也可以删除，使用 marketplace uninstall API（临时解决方案）
      // 后续可以添加专门的自建技能删除 API
      await api.marketplace.uninstall(skill.name);
    } else if (skill.source === 'builtin') {
      // 内置技能不能删除
      alert('内置技能不能删除');
      return;
    }
    
    // 删除成功后刷新技能列表
    await loadSkills();
    selectedSkill.value = null;
  } catch (error) {
    console.error('删除技能失败:', error);
    alert('删除技能失败，请重试');
  }
};

onMounted(() => {
  loadSkills();
});

onActivated(() => {
  loadSkills();
});
</script>

<style scoped lang="scss">
.page-container {
  min-height: 100vh;
  background-color: var(--color-bg-base);
  display: flex;
  flex-direction: column;
}

.content-area {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.page-header {
  padding: 1rem;
  border-bottom: 1px solid var(--color-border);

  h2 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 600;
  }
}

.skills-filter {
  padding: 0.5rem 1rem;
  display: flex;
  gap: 0.5rem;
  border-bottom: 1px solid var(--color-border);
}

.skills-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
  padding: 1rem;
}

.skill-card {
  background-color: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  cursor: pointer;
  transition: all var(--transition-fast);
  display: flex;
  flex-direction: column;
  gap: 1rem;

  &:hover {
    border-color: var(--color-primary);
    box-shadow: var(--shadow-md);
    transform: translateY(-2px);
  }
}

.skill-header {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
}

.skill-icon {
  font-size: 2rem;
  line-height: 1;
  flex-shrink: 0;
}

.skill-info {
  flex: 1;
  min-width: 0;
}

.skill-name {
  margin: 0 0 0.375rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.skill-description {
  margin: 0;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
}

.skill-meta {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: auto;
  padding-top: 0.75rem;
  border-top: 1px solid var(--color-border);
}

.skill-badge {
  display: inline-flex;
  padding: 0.125rem 0.5rem;
  font-size: 0.75rem;
  border-radius: 9999px;

  &.skill-type-builtin {
    background-color: var(--color-info-bg);
    color: var(--color-info);
  }

  &.skill-type-marketplace {
    background-color: var(--color-warning-bg);
    color: var(--color-warning);
  }

  &.skill-type-workspace {
    background-color: var(--color-success-bg);
    color: var(--color-success);
  }

  &.always {
    background-color: var(--color-warning-bg);
    color: var(--color-warning);
  }

  &.on-demand {
    background-color: var(--color-bg-muted);
    color: var(--color-text-secondary);
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: var(--color-text-muted);

  .empty-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
  }
}

.skill-detail-header {
  display: flex;
  gap: 0.875rem;
  align-items: center;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 1rem;
}

.skill-detail-icon {
  font-size: 1.75rem;
  line-height: 1;
  flex-shrink: 0;
  width: 2.75rem;
  height: 2.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(
    135deg,
    var(--color-bg-muted) 0%,
    var(--color-bg-surface) 100%
  );
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
}

.skill-detail-title {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
  line-height: 1.2;
}

.skill-detail-meta {
  margin-bottom: 1rem;
}

.skill-detail-badges {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.75rem;
}

.skill-detail-desc {
  margin: 0;
  font-size: 0.9375rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.skill-detail-section {
  margin-bottom: 1rem;
}

.skill-content {
  font-size: 0.875rem;
  line-height: 1.75;
  color: var(--color-text-primary);

  :deep(h1),
  :deep(h2),
  :deep(h3),
  :deep(h4) {
    margin: 1.75rem 0 0.875rem;
    font-weight: 600;
    color: var(--color-text-primary);
    line-height: 1.4;
  }

  :deep(h1) {
    font-size: 1.375rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--color-border);
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

  :deep(h1:first-child),
  :deep(h2:first-child) {
    margin-top: 0;
  }

  :deep(p) {
    margin: 0 0 1rem;
  }

  :deep(ul),
  :deep(ol) {
    margin: 0 0 1rem;
    padding-left: 1.5rem;
  }

  :deep(li) {
    margin-bottom: 0.5rem;
  }

  :deep(pre) {
    background-color: var(--color-code-bg);
    padding: 1rem;
    border-radius: var(--radius-md);
    overflow-x: auto;
    margin: 0 0 1rem;
    border: 1px solid var(--color-border);
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
    margin: 0 0 1rem;
    padding: 0.875rem 1rem;
    border-left: 3px solid var(--color-primary);
    background-color: var(--color-bg-muted);
    border-radius: 0 var(--radius-md) var(--radius-md) 0;
  }

  :deep(table) {
    width: 100%;
    border-collapse: collapse;
    margin: 0 0 1rem;
    font-size: 0.8125rem;
  }

  :deep(th),
  :deep(td) {
    padding: 0.625rem 0.875rem;
    border: 1px solid var(--color-border);
    text-align: left;
  }

  :deep(th) {
    background-color: var(--color-bg-muted);
    font-weight: 600;
    white-space: nowrap;
  }

  :deep(tr:nth-child(even) td) {
    background-color: var(--color-bg-muted);
  }
}

.modal-footer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.footer-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.skill-source-info {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8125rem;
  color: var(--color-text-secondary);

  .source-label {
    color: var(--color-text-muted);
  }

  .source-value {
    font-weight: 500;
    color: var(--color-text-primary);
  }
}

.btn-danger {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

// Marketplace styles
.skill-marketplace {
  position: relative;

  &:hover {
    .marketplace-actions {
      opacity: 1;
      transform: translateY(0);
    }
  }
}

.market-badge {
  background-color: var(--color-purple-bg, #f3e8ff);
  color: var(--color-purple, #9333ea);
}

.skill-version {
  background-color: var(--color-bg-muted);
  color: var(--color-text-secondary);
}

.skill-update {
  background-color: var(--color-warning-bg, #fef3c7);
  color: var(--color-warning, #d97706);
}

.marketplace-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: auto;
  padding-top: 0.75rem;
  border-top: 1px solid var(--color-border);
  opacity: 1;
  transform: translateY(0);
  transition: all var(--transition-fast);
}

.skill-type-marketplace {
  background-color: var(--color-purple-bg, #f3e8ff);
  color: var(--color-purple, #9333ea);
}

.loading-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: var(--color-text-muted);

  .loading-spinner {
    width: 2rem;
    height: 2rem;
    border: 2px solid var(--color-border);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-bottom: 1rem;
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.btn-success {
  background-color: var(--color-success);
  border-color: var(--color-success);
  color: white;

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}
</style>
