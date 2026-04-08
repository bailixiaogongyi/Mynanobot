<template>
  <div class="marketplace-page">
    <div class="page-container">
      <div class="content-area">
        <div class="page-header">
          <h2>技能市场</h2>
          <p class="page-description">
            浏览并安装来自 ClawHub、Tencent 等市场的技能
          </p>
        </div>

        <div class="marketplace-filters">
          <div class="marketplace-source-selector">
            <label>选择市场：</label>
            <select
              v-model="selectedSource"
              class="source-select"
              @change="handleSourceChange"
            >
              <option
                v-for="source in marketplaceSources"
                :key="source.value"
                :value="source.value"
              >
                {{ source.label }}
              </option>
            </select>
          </div>
          <div class="marketplace-sort" v-if="currentCapabilities?.sort">
            <label>排序：</label>
            <select
              v-model="selectedSort"
              class="sort-select"
              @change="handleSortChange"
            >
              <option
                v-for="sort in sortOptions"
                :key="sort.value"
                :value="sort.value"
              >
                {{ sort.label }}
              </option>
            </select>
          </div>
          <div class="marketplace-search" v-if="currentCapabilities?.search">
            <input
              v-model="searchQuery"
              type="text"
              class="search-input"
              placeholder="搜索技能..."
              @keyup.enter="handleSearch"
            />
            <button class="btn btn-sm btn-primary" @click="handleSearch">
              搜索
            </button>
          </div>
        </div>

        <div class="skills-grid">
          <div
            v-for="skill in marketplaceSkills"
            :key="skill.slug + skill.source"
            class="skill-card skill-marketplace"
            @click="showSkillDetail(skill)"
          >
            <div class="skill-header">
              <span class="skill-icon">{{
                getSkillIcon(skill.displayName || skill.slug)
              }}</span>
              <div class="skill-info">
                <h3 class="skill-name">
                  {{ skill.displayName || skill.slug }}
                </h3>
                <p class="skill-description">
                  {{ skill.summary || "" }}
                </p>
              </div>
            </div>
            <div class="skill-meta">
              <span class="skill-badge skill-type-marketplace market-badge">
                {{ getSourceLabel(skill.source) }}
              </span>
              <span
                v-if="skill.latestVersion"
                class="skill-badge skill-version"
              >
                v{{ skill.latestVersion }}
              </span>
              <span v-if="skill.category" class="skill-badge">
                {{ skill.category }}
              </span>
              <span v-if="skill.hasUpdate" class="skill-badge skill-update">
                可更新
              </span>
            </div>
            <div class="marketplace-actions">
              <template v-if="skill.installed">
                <button class="btn btn-sm btn-success" disabled>已安装</button>
                <button
                  class="btn btn-sm btn-outline"
                  @click.stop="uninstallSkill(skill)"
                  :disabled="uninstallingSkill === skill.slug"
                >
                  {{ uninstallingSkill === skill.slug ? "卸载中..." : "卸载" }}
                </button>
              </template>
              <template v-else>
                <button
                  class="btn btn-sm btn-primary"
                  @click.stop="installSkill(skill)"
                  :disabled="installingSkill === skill.slug"
                >
                  {{ installingSkill === skill.slug ? "安装中..." : "安装" }}
                </button>
              </template>
            </div>
          </div>

          <div
            v-if="marketplaceSkills.length === 0 && !marketplaceLoading"
            class="empty-state"
          >
            <div class="empty-icon">🛒</div>
            <p>{{ searchQuery ? "未找到匹配的技能" : "暂无技能" }}</p>
            <button
              v-if="searchQuery"
              class="btn btn-secondary"
              @click="clearSearch"
            >
              清除搜索
            </button>
          </div>

          <div v-if="marketplaceLoading" class="loading-state">
            <div class="loading-spinner"></div>
            <p>加载技能中...</p>
          </div>
        </div>

        <div v-if="totalSkills > pageSize" class="pagination">
          <button
            class="btn btn-sm btn-secondary"
            :disabled="currentPage === 1"
            @click="goToPage(currentPage - 1)"
          >
            上一页
          </button>
          <span class="page-info">
            第 {{ currentPage }} 页 / 共
            {{ Math.ceil(totalSkills / pageSize) }} 页 ({{ totalSkills }}
            个技能)
          </span>
          <button
            class="btn btn-sm btn-secondary"
            :disabled="!hasMore"
            @click="goToPage(currentPage + 1)"
          >
            下一页
          </button>
        </div>
      </div>
    </div>

    <!-- 技能详情弹窗 -->
    <Modal
      :show="!!selectedSkill"
      :title="selectedSkill?.displayName || selectedSkill?.slug || '技能详情'"
      size="lg"
      @close="selectedSkill = null"
    >
      <div v-if="selectedSkill" class="skill-detail-content">
        <!-- 直接显示技能详情 -->
        <div class="detail-header">
          <span class="detail-icon">{{
            getSkillIcon(selectedSkill.displayName || selectedSkill.slug)
          }}</span>
          <div class="detail-title">
            <h3>{{ selectedSkill.displayName || selectedSkill.slug }}</h3>
            <p class="detail-summary">{{ selectedSkill.summary }}</p>
          </div>
        </div>

        <div class="detail-meta">
          <span class="detail-badge market-badge">{{
            getSourceLabel(selectedSkill.source)
          }}</span>
          <span v-if="selectedSkill.latestVersion" class="detail-badge"
            >v{{ selectedSkill.latestVersion }}</span
          >
          <span v-if="selectedSkill.category" class="detail-badge">{{
            selectedSkill.category
          }}</span>
          <span v-if="selectedSkill.installed" class="detail-badge installed"
            >已安装</span
          >
          <span v-if="selectedSkill.hasUpdate" class="detail-badge update"
            >可更新</span
          >
        </div>

        <!-- 作者信息 -->
        <div v-if="selectedSkill.author" class="detail-section">
          <h4>作者</h4>
          <div class="detail-author">
            <img
              v-if="selectedSkill.author.image"
              :src="selectedSkill.author.image"
              class="author-avatar"
            />
            <span>{{
              selectedSkill.author.name || selectedSkill.author.handle || "未知"
            }}</span>
          </div>
        </div>

        <!-- 统计信息 -->
        <div class="detail-stats">
          <span v-if="selectedSkill.downloads"
            >📥 下载: {{ selectedSkill.downloads }}</span
          >
          <span v-if="selectedSkill.stars"
            >⭐ 评分: {{ selectedSkill.stars }}</span
          >
          <span v-if="selectedSkill.installs"
            >✅ 安装: {{ selectedSkill.installs }}</span
          >
          <span v-if="selectedSkill.updatedAt"
            >🕐 更新: {{ formatDate(selectedSkill.updatedAt) }}</span
          >
        </div>

        <!-- 安全审核信息 -->
        <div v-if="selectedSkill.moderation" class="detail-section">
          <h4>安全状态</h4>
          <div class="detail-moderation">
            <span
              :class="[
                'status-badge',
                selectedSkill.moderation.verdict === 'clean'
                  ? 'clean'
                  : 'warning',
              ]"
            >
              {{
                selectedSkill.moderation.verdict === "clean"
                  ? "✅ 安全"
                  : "⚠️ 警告"
              }}
            </span>
            <span
              v-if="selectedSkill.moderation.isSuspicious"
              class="status-badge suspicious"
              >可疑</span
            >
            <span
              v-if="selectedSkill.moderation.isMalwareBlocked"
              class="status-badge danger"
              >恶意软件已拦截</span
            >
          </div>
          <p v-if="selectedSkill.moderation.summary" class="moderation-summary">
            {{ selectedSkill.moderation.summary }}
          </p>
        </div>

        <div v-if="selectedSkill.url" class="detail-link">
          <a :href="selectedSkill.url" target="_blank">查看原始页面 →</a>
        </div>

        <div class="detail-actions">
          <template v-if="selectedSkill.installed">
            <button class="btn btn-primary" disabled>已安装</button>
            <button
              class="btn btn-outline"
              @click="handleUninstallFromDetail"
              :disabled="uninstallingSkill === selectedSkill.slug"
            >
              {{
                uninstallingSkill === selectedSkill.slug ? "卸载中..." : "卸载"
              }}
            </button>
          </template>
          <template v-else>
            <button
              class="btn btn-primary"
              @click="handleInstallFromDetail"
              :disabled="installingSkill === selectedSkill.slug"
            >
              {{
                installingSkill === selectedSkill.slug ? "安装中..." : "安装"
              }}
            </button>
          </template>
        </div>
      </div>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import {
  ref,
  computed,
  onMounted,
  onUnmounted,
  onActivated,
  onDeactivated,
  watch,
} from "vue";
import { useRoute, useRouter } from "vue-router";
import { useUIStore } from "@/stores/ui";
import { api } from "@/services/api";
import Modal from "@/components/ui/Modal.vue";

const route = useRoute();
const router = useRouter();
const uiStore = useUIStore();

interface MarketplaceSkill {
  slug: string;
  displayName?: string;
  summary?: string;
  source: string;
  latestVersion?: string;
  installed?: boolean;
  installedVersion?: string;
  hasUpdate?: boolean;
  category?: string;
  ownerName?: string;
  url?: string;
  downloads?: number;
  stars?: number;
  installs?: number;
  updatedAt?: string;
  author?: {
    name?: string;
    handle?: string;
    image?: string;
  };
  moderation?: {
    isSuspicious?: boolean;
    isMalwareBlocked?: boolean;
    verdict?: string;
    summary?: string;
  };
}

interface MarketplaceSource {
  id: string;
  label: string;
  value: string;
  capabilities?: {
    search?: boolean;
    list?: boolean;
    detail?: boolean;
    download?: boolean;
    update?: boolean;
  };
}

const marketplaceSources = ref<MarketplaceSource[]>([
  {
    id: "recommended",
    label: "推荐技能",
    value: "recommended",
    capabilities: { search: false, list: true, sort: false },
  },
  {
    id: "tencent",
    label: "Tencent",
    value: "tencent",
    capabilities: { search: true, list: true, sort: true },
  },
]);

const sortOptions = [
  { label: "下载量", value: "downloads" },
  { label: "评分", value: "stars" },
  { label: "安装量", value: "installs" },
  { label: "最新", value: "newest" },
  { label: "更新时间", value: "updated" },
  { label: "名称", value: "name" },
];

const selectedSort = ref<string>("downloads");
const pageSize = 20;

const goToPage = async (page: number) => {
  if (page < 1) return;
  if (page > currentPage.value && !hasMore.value) return;

  currentPage.value = page;
  await loadMarketplaceSkills();
  window.scrollTo({ top: 0, behavior: "smooth" });
};
const selectedSource = ref<string>("recommended");
const searchQuery = ref<string>("");
const marketplaceSkills = ref<MarketplaceSkill[]>([]);
const marketplaceLoading = ref(false);
const cursor = ref<string | null>(null);
const hasMore = ref(false);
const currentPage = ref(1);
const totalSkills = ref(0);

const currentCapabilities = computed(() => {
  const source = marketplaceSources.value.find(
    (s) => s.value === selectedSource.value,
  );
  return source?.capabilities || {};
});

const getSkillIcon = (name: string): string => {
  const iconMap: Record<string, string> = {
    "web-search": "🔍",
    search: "🔍",
    "file-manager": "📁",
    file: "📁",
    "code-runner": "💻",
    code: "💻",
    image: "🖼️",
    video: "🎬",
    music: "🎵",
    pdf: "📄",
    document: "📝",
    data: "📊",
    api: "🔗",
    browser: "🌐",
    automation: "🤖",
    default: "⚡",
  };
  const key = name.toLowerCase().replace(/[-_\s]/g, "");
  return iconMap[key] || iconMap.default;
};

const getSourceLabel = (source: string): string => {
  const labelMap: Record<string, string> = {
    tencent: "Tencent",
    recommended: "推荐",
    github: "GitHub",
    local: "本地",
  };
  return labelMap[source] || source;
};

const formatDate = (dateStr: string): string => {
  if (!dateStr) return "";
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString("zh-CN", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateStr;
  }
};

const loadMarketplaceSkills = async (append = false) => {
  if (marketplaceLoading.value) return;

  marketplaceLoading.value = true;
  try {
    const params: Record<string, any> = {
      source: selectedSource.value,
      limit: 20,
    };
    if (cursor.value) {
      params.cursor = cursor.value;
    }
    if (searchQuery.value && currentCapabilities.value.search) {
      params.query = searchQuery.value;
    }
    if (selectedSort.value && currentCapabilities.value.sort) {
      params.sort = selectedSort.value;
    }

    const result = await api.marketplace.list(params);
    const newSkills = result.items || result.skills || [];

    if (append) {
      marketplaceSkills.value = [...marketplaceSkills.value, ...newSkills];
    } else {
      marketplaceSkills.value = newSkills;
    }

    cursor.value = result.nextCursor || null;
    hasMore.value = !!result.nextCursor;
  } catch (e: any) {
    console.error("Failed to load marketplace:", e);
    const errorMsg = e?.message || "";
    if (errorMsg.includes("429") || errorMsg.includes("Too Many Requests")) {
      uiStore.showToast(`请求过于频繁，请稍后再试（API 限流）`, "error");
    } else {
      uiStore.showToast(`加载市场技能失败: ${errorMsg}`, "error");
    }
  } finally {
    marketplaceLoading.value = false;
  }
};

const handleSourceChange = () => {
  searchQuery.value = "";
  cursor.value = null;
  currentPage.value = 1;
  totalSkills.value = 0;
  marketplaceSkills.value = [];
  loadMarketplaceSkills();
};

const handleSortChange = () => {
  cursor.value = null;
  currentPage.value = 1;
  totalSkills.value = 0;
  marketplaceSkills.value = [];
  loadMarketplaceSkills();
};

const handleSearch = () => {
  if (!currentCapabilities.value.search) return;
  cursor.value = null;
  marketplaceSkills.value = [];
  loadMarketplaceSkills();
};

const clearSearch = () => {
  searchQuery.value = "";
  handleSearch();
};

const loadMore = () => {
  loadMarketplaceSkills(true);
};

const installingSkill = ref<string | null>(null);
const uninstallingSkill = ref<string | null>(null);

// 使用简单的 any 类型避免运行时错误
const selectedSkill = ref<any>(null);

const showSkillDetail = async (skill: MarketplaceSkill) => {
  // 直接显示技能信息，暂不调用详情 API
  selectedSkill.value = { ...skill };
};

const handleInstallFromDetail = async () => {
  if (!selectedSkill.value) return;
  await installSkill(selectedSkill.value);
  selectedSkill.value = null;
};

const handleUninstallFromDetail = async () => {
  if (!selectedSkill.value) return;
  await uninstallSkill(selectedSkill.value);
  selectedSkill.value = null;
};

const installSkill = async (skill: MarketplaceSkill) => {
  if (installingSkill.value) return;

  installingSkill.value = skill.slug;
  try {
    // 使用当前选择的市场源，而不是技能对象中的 source
    await api.marketplace.install(skill.slug, selectedSource.value);
    uiStore.showToast(
      `技能 ${skill.displayName || skill.slug} 安装成功，请到技能页面查看`,
      "success",
    );
    marketplaceSkills.value = marketplaceSkills.value.map((s) => {
      if (s.slug === skill.slug) {
        return { ...s, installed: true };
      }
      return s;
    });
  } catch (e: any) {
    console.error("Failed to install skill:", e);
    const errorMsg = e?.message || "";
    if (errorMsg.includes("429") || errorMsg.includes("Too Many Requests")) {
      uiStore.showToast(`API 限流中，请等待 30 秒后重试`, "error");
    } else {
      uiStore.showToast(`技能安装失败: ${errorMsg}`, "error");
    }
  } finally {
    installingSkill.value = null;
  }
};

const uninstallSkill = async (skill: MarketplaceSkill) => {
  if (uninstallingSkill.value) return;

  uninstallingSkill.value = skill.slug;
  try {
    await api.marketplace.uninstall(skill.slug);
    uiStore.showToast(
      `技能 ${skill.displayName || skill.slug} 已卸载`,
      "success",
    );
    marketplaceSkills.value = marketplaceSkills.value.map((s) => {
      if (s.slug === skill.slug) {
        return { ...s, installed: false };
      }
      return s;
    });
  } catch (e: any) {
    console.error("Failed to uninstall skill:", e);
    const errorMsg = e?.message || "";
    if (errorMsg.includes("429") || errorMsg.includes("Too Many Requests")) {
      uiStore.showToast(`请求过于频繁，请稍后再试`, "error");
    } else {
      uiStore.showToast(`技能卸载失败: ${errorMsg}`, "error");
    }
  } finally {
    uninstallingSkill.value = null;
  }
};

// 重置页面所有状态（修复切换页面空白）
const resetPageState = () => {
  selectedSkill.value = null;
  marketplaceLoading.value = false;
  installingSkill.value = null;
  uninstallingSkill.value = null;
};

// 首次挂载加载数据
onMounted(() => {
  loadMarketplaceSkills();
});

// 监听路由变化，切换离开时重置状态
watch(
  () => route.path,
  (newPath) => {
    if (!newPath.includes("marketplace")) {
      resetPageState();
    }
  },
);

// 缓存页面激活时不再重复加载（避免频繁调用 API）
// 数据变化时已在 install/uninstall 函数中更新 UI
onActivated(() => {
  // 可选：如果需要刷新数据，可以添加一个"刷新"按钮让用户手动触发
  // loadMarketplaceSkills();
});

// 页面失活/销毁时：关闭弹窗+重置所有状态
onDeactivated(() => {
  resetPageState();
});
onUnmounted(() => {
  resetPageState();
});
</script>

<style scoped>
/* 修复样式：min-height:100vh，避免高度失效 */
.page-container {
  padding: 1.5rem;
  min-height: 100vh;
  overflow-y: auto;
}

.page-header {
  margin-bottom: 1.5rem;
}

.page-header h2 {
  margin: 0 0 0.5rem 0;
  font-size: 1.5rem;
  font-weight: 600;
}

.page-description {
  margin: 0;
  color: var(--color-text-secondary);
}

.marketplace-filters {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.marketplace-source-selector {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.marketplace-source-selector label {
  font-weight: 500;
}

.source-select {
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 0.875rem;
  min-width: 150px;
}

.marketplace-sort {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.marketplace-sort label {
  font-weight: 500;
}

.sort-select {
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 0.875rem;
  min-width: 100px;
}

.marketplace-search {
  display: flex;
  gap: 0.5rem;
}

.search-input {
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 0.875rem;
  width: 250px;
}

.search-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.skills-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}

.skill-card {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  transition: all var(--transition-fast);
}

.skill-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-md);
}

.skill-header {
  display: flex;
  gap: 0.75rem;
}

.skill-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.skill-info {
  flex: 1;
  min-width: 0;
}

.skill-name {
  margin: 0 0 0.25rem 0;
  font-size: 1rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.skill-description {
  margin: 0;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.skill-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.skill-badge {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  font-size: 0.75rem;
  border-radius: var(--radius-sm);
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
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
}

.btn-success {
  background: var(--color-success);
  color: white;
  border: none;
  cursor: default;
}

.btn-outline {
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text);
}

.btn-outline:hover {
  background: var(--color-bg-muted);
}

.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 3rem;
  color: var(--color-text-secondary);
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.loading-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 3rem;
  color: var(--color-text-secondary);
}

.loading-spinner {
  width: 2rem;
  height: 2rem;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 1.5rem;
  padding: 1rem;
}

.page-info {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

/* 技能详情弹窗样式 */
.skill-detail-content {
  padding: 0.5rem;
}

.detail-header {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.detail-icon {
  font-size: 2.5rem;
  flex-shrink: 0;
}

.detail-title h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.25rem;
}

.detail-summary {
  margin: 0;
  color: var(--color-text-secondary);
}

.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.detail-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  border-radius: var(--radius-sm);
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
}

.detail-badge.installed {
  background: var(--color-success-bg, #dcfce7);
  color: var(--color-success, #16a34a);
}

.detail-badge.update {
  background: var(--color-warning-bg, #fef3c7);
  color: var(--color-warning, #d97706);
}

.detail-stats {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.detail-link {
  margin-bottom: 1rem;
}

.detail-link a {
  color: var(--color-primary);
  text-decoration: none;
}

.detail-link a:hover {
  text-decoration: underline;
}

.detail-loading {
  text-align: center;
  padding: 2rem;
  color: var(--color-text-secondary);
}

.detail-section {
  margin-bottom: 1rem;
}

.detail-section h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.detail-author {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.author-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
}

.detail-moderation {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  border-radius: var(--radius-sm);
}

.status-badge.clean {
  background: var(--color-success-bg, #dcfce7);
  color: var(--color-success, #16a34a);
}

.status-badge.warning {
  background: var(--color-warning-bg, #fef3c7);
  color: var(--color-warning, #d97706);
}

.status-badge.suspicious {
  background: var(--color-warning-bg, #fef3c7);
  color: var(--color-warning, #d97706);
}

.status-badge.danger {
  background: var(--color-error-bg, #fee2e2);
  color: var(--color-error, #dc2626);
}

.moderation-summary {
  margin: 0.5rem 0 0 0;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.detail-actions {
  display: flex;
  gap: 0.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
}
</style>
