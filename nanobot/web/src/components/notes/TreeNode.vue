<template>
  <div class="tree-node-wrapper">
    <div
      class="tree-node"
      :class="{ 'is-selected': selectedPath === node.path, 'is-directory': node.isDirectory }"
      :style="{ paddingLeft: (depth * 16 + 8) + 'px' }"
      @click="handleClick"
    >
      <span
        v-if="node.isDirectory"
        class="tree-node-toggle"
        :class="{ 'is-expanded': node.expanded }"
        @click.stop="handleToggle"
      >
        <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
          <path d="M4.5 2L9 6L4.5 10" stroke="currentColor" stroke-width="1.5" fill="none"/>
        </svg>
      </span>
      <span class="tree-node-icon">
        {{ node.isDirectory ? (node.expanded ? '📂' : '📁') : '📄' }}
      </span>
      <span class="tree-node-label">{{ node.name }}</span>
    </div>
    <template v-if="node.isDirectory && node.expanded && node.children && node.children.length > 0">
      <TreeNode
        v-for="child in node.children"
        :key="child.path"
        :node="child"
        :selected-path="selectedPath"
        :depth="depth + 1"
        @select="$emit('select', $event)"
        @toggle="$emit('toggle', $event)"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
interface TreeNodeType {
  name: string;
  path: string;
  isDirectory: boolean;
  children?: TreeNodeType[];
  expanded?: boolean;
  loaded?: boolean;
}

const props = withDefaults(defineProps<{
  node: TreeNodeType;
  selectedPath: string | null;
  depth?: number;
}>(), {
  depth: 0
});

const emit = defineEmits<{
  (e: 'select', node: TreeNodeType): void;
  (e: 'toggle', node: TreeNodeType): void;
}>();

const handleClick = () => {
  emit('select', props.node);
};

const handleToggle = () => {
  emit('toggle', props.node);
};
</script>

<script lang="ts">
export default {
  name: 'TreeNode'
};
</script>

<style scoped lang="scss">
.tree-node-wrapper {
  width: 100%;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  border-radius: var(--radius-sm);
  margin: 0.125rem 0;
  user-select: none;
  transition: background-color 0.15s ease;

  &:hover {
    background-color: var(--color-bg-muted, #f5f5f5);
  }

  &.is-selected {
    background-color: var(--color-primary-light, #e8f4ff);
    color: var(--color-primary, #0066cc);
  }

  &.is-directory {
    font-weight: 500;
  }
}

.tree-node-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  color: var(--color-text-secondary, #666);
  transition: transform 0.15s ease;
  flex-shrink: 0;

  &.is-expanded {
    transform: rotate(90deg);
  }

  svg {
    width: 12px;
    height: 12px;
  }
}

.tree-node-icon {
  font-size: 0.875rem;
  flex-shrink: 0;
}

.tree-node-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
