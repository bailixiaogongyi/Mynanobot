<template>
  <header class="app-header">
    <div class="header-left">
      <router-link to="/" class="logo">
        <svg class="logo-icon" viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
          <path d="M13.5 2c0 .44-.19.84-.5 1.12V5h5a3 3 0 0 1 3 3v10a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3V8a3 3 0 0 1 3-3h5V3.12A1.5 1.5 0 1 1 13.5 2zM0 10h2v6H0v-6zm24 0h-2v6h2v-6zM9 14.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zm6-1.5a1.5 1.5 0 1 0-3 0 1.5 1.5 0 0 0 3 0z"/>
        </svg>
        <span class="logo-text">AiMate</span>
      </router-link>
    </div>

    <div class="header-spacer"></div>

    <div class="header-right">
      <nav class="header-nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          :class="['nav-link', { active: isActive(item.path) }]"
        >
          <span class="nav-icon" v-html="item.icon"></span>
          <span class="nav-text">{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="theme-toggle">
        <button
          :class="['theme-btn', { active: themeStore.mode === 'light' }]"
          @click="themeStore.setMode('light')"
          title="浅色主题"
        >
          ☀️
        </button>
        <button
          :class="['theme-btn', { active: themeStore.mode === 'dark' }]"
          @click="themeStore.setMode('dark')"
          title="深色主题"
        >
          🌙
        </button>
        <button
          :class="['theme-btn', { active: themeStore.mode === 'system' }]"
          @click="themeStore.setMode('system')"
          title="跟随系统"
        >
          💻
        </button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useRoute } from "vue-router";
import { useThemeStore } from "@/stores/theme";

const route = useRoute();
const themeStore = useThemeStore();

const navItems = [
  { path: "/chat", label: "对话", icon: "💬" },
  { path: "/tasks", label: "任务", icon: "📋" },
  { path: "/notes", label: "笔记", icon: "📝" },
  { path: "/skills", label: "技能", icon: "🛠️" },
  { path: "/marketplace", label: "市场", icon: "🛒" },
  { path: "/config", label: "配置", icon: "⚙️" },
];

const isActive = (path: string) => {
  if (path === "/") {
    return route.path === "/";
  }
  return route.path.startsWith(path);
};
</script>

<style scoped lang="scss">
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 20px;
  background-color: var(--color-bg-surface, #fff);
  border-bottom: 1px solid var(--color-border, #e2e8f0);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left {
  .logo {
    display: flex;
    align-items: center;
    gap: 8px;
    text-decoration: none;
    color: var(--color-text-primary, #1e293b);

    .logo-icon {
      font-size: 24px;
    }

    .logo-text {
      font-size: 18px;
      font-weight: 600;
    }
  }
}

.header-spacer {
  flex: 1;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-nav {
  display: flex;
  gap: 4px;

  .nav-link {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 12px;
    text-decoration: none;
    color: var(--color-text-secondary, #64748b);
    border-radius: 6px;
    transition: all 0.2s ease;
    font-size: 13px;

    &:hover {
      background-color: var(--color-bg-muted, #f1f5f9);
      color: var(--color-text-primary, #1e293b);
    }

    &.active {
      background-color: var(--color-primary-light, #dbeafe);
      color: var(--color-primary, #3b82f6);
    }

    .nav-icon {
      font-size: 14px;
    }
  }
}

.theme-toggle {
  display: flex;
  gap: 4px;
  padding: 4px;
  background-color: var(--color-bg-muted, #f1f5f9);
  border-radius: 8px;

  .theme-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: none;
    background: transparent;
    border-radius: 6px;
    cursor: pointer;
    font-size: 16px;
    transition: all 0.2s ease;

    &:hover {
      background-color: var(--color-bg-surface, #fff);
    }

    &.active {
      background-color: var(--color-bg-surface, #fff);
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
  }
}
</style>
