import { defineStore } from "pinia";
import { ref } from "vue";

interface Toast {
  id: number;
  message: string;
  type: "info" | "success" | "warning" | "error";
  duration: number;
}

interface ConfirmModal {
  show: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export const useUIStore = defineStore("ui", () => {
  const toasts = ref<Toast[]>([]);
  const confirmModal = ref<ConfirmModal>({
    show: false,
    title: "",
    message: "",
    onConfirm: () => {},
    onCancel: () => {},
  });
  const sidebarCollapsed = ref(false);
  const imagePreviewUrl = ref<string | null>(null);

  const showToast = (
    message: string,
    type: Toast["type"] = "info",
    duration = 3000,
  ) => {
    const id = Date.now();
    toasts.value.push({ id, message, type, duration });

    setTimeout(() => {
      removeToast(id);
    }, duration);
  };

  const removeToast = (id: number) => {
    const index = toasts.value.findIndex((t) => t.id === id);
    if (index > -1) {
      toasts.value.splice(index, 1);
    }
  };

  const showConfirm = (title: string, message: string): Promise<boolean> => {
    return new Promise((resolve) => {
      confirmModal.value = {
        show: true,
        title,
        message,
        onConfirm: () => {
          confirmModal.value.show = false;
          resolve(true);
        },
        onCancel: () => {
          confirmModal.value.show = false;
          resolve(false);
        },
      };
    });
  };

  const toggleSidebar = () => {
    sidebarCollapsed.value = !sidebarCollapsed.value;
  };

  const openImagePreview = (url: string) => {
    imagePreviewUrl.value = url;
  };

  const closeImagePreview = () => {
    imagePreviewUrl.value = null;
  };

  return {
    toasts,
    confirmModal,
    sidebarCollapsed,
    imagePreviewUrl,
    showToast,
    removeToast,
    showConfirm,
    toggleSidebar,
    openImagePreview,
    closeImagePreview,
  };
});
