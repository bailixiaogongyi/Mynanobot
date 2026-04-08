<template>
  <div class="app-layout">
    <AppHeader />
    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <keep-alive>
            <component :is="Component" />
          </keep-alive>
        </transition>
      </router-view>
    </main>
    <ToastContainer />
    <ConfirmModal />
    <ImagePreview />
  </div>
</template>

<script setup lang="ts">
import AppHeader from "./AppHeader.vue";
import ToastContainer from "@/components/ui/ToastContainer.vue";
import ConfirmModal from "@/components/ui/ConfirmModal.vue";
import ImagePreview from "@/components/ui/ImagePreview.vue";
</script>

<style scoped lang="scss">
.app-layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: var(--color-bg-base, #f8fafc);
}

.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow-y: auto;
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
