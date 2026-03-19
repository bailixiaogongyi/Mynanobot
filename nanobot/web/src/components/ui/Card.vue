<template>
  <div :class="['ui-card', { 'ui-card-hoverable': hoverable, 'ui-card-clickable': clickable }]">
    <div v="$slots.header" class="ui-card-header">
      <slot name="header"></slot>
    </div>
    <div class="ui-card-body" :class="{ 'ui-card-body-nopadding': noPadding }">
      <slot></slot>
    </div>
    <div v="$slots.footer" class="ui-card-footer">
      <slot name="footer"></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  hoverable?: boolean;
  clickable?: boolean;
  noPadding?: boolean;
}

withDefaults(defineProps<Props>(), {
  hoverable: false,
  clickable: false,
  noPadding: false,
});
</script>

<style scoped>
.ui-card {
  background-color: var(--color-bg-surface, #fff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: var(--radius-lg, 12px);
  overflow: hidden;
  transition: all 0.15s ease;
}

.ui-card-hoverable:hover {
  border-color: var(--color-primary, #3b82f6);
  box-shadow: var(--shadow-md, 0 4px 6px rgba(0, 0, 0, 0.1));
}

.ui-card-clickable {
  cursor: pointer;
}

.ui-card-clickable:active {
  transform: scale(0.99);
}

.ui-card-header {
  padding: 1rem;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ui-card-header :deep(h3) {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-text-primary, #1e293b);
}

.ui-card-body {
  padding: 1rem;
}

.ui-card-body-nopadding {
  padding: 0;
}

.ui-card-footer {
  padding: 1rem;
  border-top: 1px solid var(--color-border, #e2e8f0);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>