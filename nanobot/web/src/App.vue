<template>
  <div id="app" :class="['app-container', themeClass]">
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
    
    <ToastContainer />
    <ConfirmModal />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useThemeStore } from '@/stores/theme';
import ToastContainer from '@/components/ui/ToastContainer.vue';
import ConfirmModal from '@/components/ui/ConfirmModal.vue';

const themeStore = useThemeStore();

const themeClass = computed(() => `theme-${themeStore.currentTheme}`);

onMounted(() => {
  themeStore.init();
});
</script>

<style scoped>
.app-container {
  height: 100vh;
  overflow: hidden;
  background-color: var(--color-bg-base, #f8fafc);
  color: var(--color-text-primary, #1e293b);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
