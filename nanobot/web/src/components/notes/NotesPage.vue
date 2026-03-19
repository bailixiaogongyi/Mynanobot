<template>
  <div class="page-container notes-page">
    <!-- 左侧目录树 -->
    <div class="notes-sidebar-panel">
      <div class="sidebar-panel-header">
        <span class="sidebar-title">笔记目录</span>
        <div class="header-actions">
          <button class="btn btn-action" @click="refreshDirectories">
            <span class="btn-icon">🔄</span>
            <span class="btn-text">刷新</span>
          </button>
          <button
            class="btn btn-action"
            :class="{ 'is-loading': isIndexing }"
            @click="handleIndexNotes"
            :disabled="isIndexing"
          >
            <span class="btn-icon">{{ isIndexing ? "⏳" : "📇" }}</span>
            <span class="btn-text">{{ isIndexing ? "索引中" : "索引" }}</span>
          </button>
        </div>
      </div>
      <div class="sidebar-panel-toolbar">
        <input
          class="input search-input"
          v-model="searchQuery"
          @keyup.enter="search"
          placeholder="搜索文件..."
        />
      </div>
      <div class="tree-container">
        <div v-if="directories.length === 0" class="empty-state">
          <p>暂无笔记目录</p>
        </div>
        <TreeNodeComponent
          v-for="item in treeData"
          :key="item.path"
          :node="item"
          :selected-path="currentFile"
          :depth="0"
          @select="handleSelectFile"
          @toggle="handleToggleNode"
        />
      </div>
    </div>

    <!-- 右侧文件编辑区 -->
    <div class="notes-editor-panel">
      <div v-if="!currentFile" class="editor-empty-state">
        <div class="empty-icon">📝</div>
        <p>从左侧选择文件进行查看或编辑</p>
      </div>
      <template v-else>
        <div class="editor-toolbar">
          <div class="editor-info">
            <span class="editor-filename">📄 {{ currentFileName }}</span>
            <span class="editor-status" :class="{ modified: isModified }">
              {{ isModified ? "已修改" : "已保存" }}
            </span>
          </div>
          <div class="editor-actions">
            <button
              class="btn btn-sm btn-secondary"
              @click="deleteNote"
              title="删除文件"
            >
              🗑️
            </button>
            <button
              class="btn btn-sm btn-primary"
              @click="saveNote"
              :disabled="!isModified"
            >
              保存
            </button>
          </div>
        </div>
        <textarea
          v-model="editorContent"
          class="editor-textarea"
          placeholder="开始编写笔记..."
          @input="handleContentChange"
        ></textarea>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import api from "@/services/api";
import TreeNodeComponent from "./TreeNode.vue";
import { useUIStore } from "@/stores/ui";

const uiStore = useUIStore();

interface TreeNode {
  name: string;
  path: string;
  isDirectory: boolean;
  children?: TreeNode[];
  expanded?: boolean;
  loaded?: boolean;
}

const directories = ref<string[]>([]);
const treeData = ref<TreeNode[]>([]);
const currentFile = ref<string | null>(null);
const currentFileName = ref("");
const editorContent = ref("");
const originalContent = ref("");
const isModified = computed(
  () => editorContent.value !== originalContent.value,
);
const searchQuery = ref("");
const isIndexing = ref(false);
const indexStatus = ref<any>(null);

const loadDirectories = async () => {
  try {
    if (api && api.notes) {
      const result = await api.notes.dirs();
      directories.value = Array.isArray(result)
        ? result
        : result.directories || [];
      await loadFullTree();
    } else {
      console.warn("api.notes is not available");
    }
  } catch (e) {
    console.error("Failed to load directories:", e);
  }
};

const loadFullTree = async () => {
  const tree: TreeNode[] = [];
  for (const dir of directories.value) {
    const node: TreeNode = {
      name: dir,
      path: dir,
      isDirectory: true,
      expanded: false,
      loaded: false,
      children: [],
    };
    tree.push(node);
  }
  treeData.value = tree;
};

const loadNodeChildren = async (node: TreeNode) => {
  if (!node.isDirectory || node.loaded) return;
  try {
    if (api.notes) {
      const result = await api.notes.list(node.path);
      node.children = [
        ...(result.directories || []).map((d: any) => ({
          name: d.name,
          path: d.path,
          isDirectory: true,
          expanded: false,
          loaded: false,
          children: [],
        })),
        ...(result.files || []).map((f: any) => ({
          name: f.name,
          path: f.path,
          isDirectory: false,
        })),
      ];
      node.loaded = true;
    }
  } catch (e) {
    console.error("Failed to load node children:", e);
  }
};

const handleToggleNode = async (node: TreeNode) => {
  node.expanded = !node.expanded;
  if (node.expanded && !node.loaded) {
    await loadNodeChildren(node);
  }
  treeData.value = [...treeData.value];
};

const handleSelectFile = async (node: TreeNode) => {
  if (node.isDirectory) {
    await handleToggleNode(node);
    return;
  }

  if (!node.name.toLowerCase().endsWith(".md")) {
    alert("目前只支持 Markdown (.md) 格式文件的编辑");
    return;
  }

  if (isModified.value) {
    const confirmSwitch = await uiStore.showConfirm(
      "未保存的更改",
      "当前文件已修改，是否保存？"
    );
    if (confirmSwitch) {
      await saveNote();
    }
  }

  currentFile.value = node.path;
  currentFileName.value = node.name;
  await loadFile(node.path);
};

const loadFile = async (path: string) => {
  try {
    if (api.notes) {
      const response = await api.notes.read(path);
      let content = "";

      if (typeof response === "string") {
        content = response;
      } else if (response && typeof response === "object") {
        content = response.content || JSON.stringify(response);
      }

      editorContent.value = content;
      originalContent.value = content;
    }
  } catch (e) {
    console.error("Failed to load file:", e);
    editorContent.value = "";
    originalContent.value = "";
  }
};

const handleContentChange = () => {
  // 内容变化时自动标记为已修改
};

const saveNote = async () => {
  if (!currentFile.value) return;
  try {
    if (api.notes) {
      await api.notes.write(currentFile.value, editorContent.value);
      originalContent.value = editorContent.value;
    }
  } catch (e) {
    console.error("Failed to save file:", e);
    alert("保存失败");
  }
};

const deleteNote = async () => {
  if (!currentFile.value) return;
  const confirmed = await uiStore.showConfirm(
    "确认删除",
    `确定要删除 "${currentFileName.value}" 吗？此操作不可撤销。`
  );
  if (!confirmed) return;

  try {
    if (api.notes) {
      await api.notes.delete(currentFile.value);
      currentFile.value = null;
      currentFileName.value = "";
      editorContent.value = "";
      originalContent.value = "";
      await loadDirectories();
    }
  } catch (e) {
    console.error("Failed to delete file:", e);
    alert("删除失败");
  }
};

const refreshDirectories = async () => {
  await loadDirectories();
  await loadIndexStatus();
};

const loadIndexStatus = async () => {
  try {
    if (api.notes) {
      const status = await api.notes.indexStatus();
      indexStatus.value = status;
    }
  } catch (e) {
    console.error("Failed to load index status:", e);
    indexStatus.value = null;
  }
};

const handleIndexNotes = async () => {
  if (isIndexing.value) return;

  const hasExistingIndex =
    indexStatus.value && (indexStatus.value.indexed_files || 0) > 0;
  let shouldForce = !hasExistingIndex;

  if (hasExistingIndex) {
    const confirmed = await uiStore.showConfirm(
      "索引选项",
      "检测到已有索引，是否进行全量重建？点击取消将执行增量索引。"
    );
    if (!confirmed) {
      shouldForce = false;
    }
  }

  isIndexing.value = true;
  try {
    if (api.notes) {
      await api.notes.index("notes", shouldForce);
      alert("索引完成！");
      await loadIndexStatus();
    }
  } catch (e) {
    console.error("Failed to index notes:", e);
    alert("索引失败: " + (e as Error).message);
  } finally {
    isIndexing.value = false;
  }
};

const search = async () => {
  if (!searchQuery.value.trim()) return;
  try {
    if (api.notes) {
      const results = await api.notes.search(searchQuery.value);
      if (results.length > 0) {
        await handleSelectFile({
          name: results[0].source,
          path: results[0].source,
          isDirectory: false,
        });
      } else {
        alert("未找到相关内容");
      }
    }
  } catch (e) {
    console.error("Search failed:", e);
  }
};

onMounted(() => {
  loadDirectories();
  loadIndexStatus();
});
</script>

<style scoped lang="scss">
.notes-page {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.notes-sidebar-panel {
  width: 280px;
  min-width: 280px;
  height: 100%;
  background-color: var(--color-sidebar-bg);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
}

.sidebar-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--color-border);
}

.sidebar-title {
  font-weight: 600;
  font-size: 0.9375rem;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-action {
  display: inline-flex;
  align-items: center;
  gap: 0.125rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 500;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.15s ease;
  color: var(--color-text-secondary);

  .btn-icon {
    font-size: 0.75rem;
    line-height: 1;
  }

  .btn-text {
    line-height: 1;
  }

  &:hover:not(:disabled) {
    background: var(--color-bg-muted);
    border-color: var(--color-primary);
    color: var(--color-primary);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  &.is-loading {
    .btn-icon {
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

.sidebar-panel-toolbar {
  padding: 0.5rem;
  border-bottom: 1px solid var(--color-border);
}

.search-input {
  width: 100%;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
}

.tree-container {
  flex: 1;
  height: 100%;
  overflow-y: auto;
  padding: 0.5rem 0;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  border-radius: var(--radius-sm);
  margin: 0.125rem 0.25rem;

  &:hover {
    background-color: var(--color-bg-muted);
  }

  &.is-selected {
    background-color: var(--color-primary-light);
    color: var(--color-primary);
  }
}

.tree-node-toggle {
  flex-shrink: 0;
  font-size: 0.875rem;
}

.tree-node-icon {
  flex-shrink: 0;
  font-size: 0.875rem;
}

.tree-node-label {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.notes-editor-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%;
  background-color: var(--color-bg-base);
}

.editor-empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  color: var(--color-text-muted);

  .empty-icon {
    font-size: 3rem;
  }
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--color-border);
  background-color: var(--color-bg-card);
}

.editor-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.editor-filename {
  font-weight: 500;
  font-size: 0.9375rem;
}

.editor-status {
  font-size: 0.75rem;
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-sm);
  background-color: var(--color-success);
  color: white;

  &.modified {
    background-color: var(--color-warning);
  }
}

.editor-actions {
  display: flex;
  gap: 0.5rem;
}

.editor-textarea {
  flex: 1;
  width: 100%;
  padding: 1rem;
  font-family: "Consolas", "Monaco", monospace;
  font-size: 0.9375rem;
  line-height: 1.6;
  border: none;
  outline: none;
  resize: none;
  background-color: var(--color-bg-card);
  color: var(--color-text-primary);

  &::placeholder {
    color: var(--color-text-muted);
  }

  &:focus {
    background-color: var(--color-bg-base);
  }
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  color: var(--color-text-muted);
  font-size: 0.875rem;
}

@media (max-width: 768px) {
  .notes-sidebar-panel {
    width: 200px;
    min-width: 200px;
  }
}
</style>
