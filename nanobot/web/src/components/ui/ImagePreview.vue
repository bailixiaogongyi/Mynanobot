<template>
  <Teleport to="body">
    <div
      v-if="uiStore.imagePreviewUrl"
      class="image-preview-overlay"
      @click="uiStore.closeImagePreview"
    >
      <div class="image-preview-content" @click.stop>
        <img
          :src="uiStore.imagePreviewUrl"
          alt="预览图片"
          class="preview-image"
        />
        <button class="preview-close" @click="uiStore.closeImagePreview">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useUIStore } from "@/stores/ui";

const uiStore = useUIStore();
</script>

<style scoped lang="scss">
.image-preview-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 2rem;

  .image-preview-content {
    position: relative;
    max-width: 90vw;
    max-height: 90vh;

    .preview-image {
      max-width: 100%;
      max-height: 90vh;
      object-fit: contain;
      border-radius: var(--radius-md);
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }

    .preview-close {
      position: absolute;
      top: -40px;
      right: 0;
      background: none;
      border: none;
      color: white;
      cursor: pointer;
      padding: 8px;
      border-radius: 50%;
      transition: background-color 0.2s;

      &:hover {
        background-color: rgba(255, 255, 255, 0.1);
      }
    }
  }
}
</style>
