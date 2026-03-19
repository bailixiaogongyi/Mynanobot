import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

type ThemeMode = 'light' | 'dark' | 'system';

const THEME_STORAGE_KEY = 'aimate_theme_mode';

export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>('system');
  const systemTheme = ref<'light' | 'dark'>('light');

  const currentTheme = computed(() => {
    if (mode.value === 'system') {
      return systemTheme.value;
    }
    return mode.value;
  });

  const isDark = computed(() => currentTheme.value === 'dark');

  const init = () => {
    const savedMode = localStorage.getItem(THEME_STORAGE_KEY) as ThemeMode;
    if (savedMode && ['light', 'dark', 'system'].includes(savedMode)) {
      mode.value = savedMode;
    }
    
    detectSystemTheme();
    watchSystemTheme();
    applyTheme();
  };

  const detectSystemTheme = () => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    systemTheme.value = mediaQuery.matches ? 'dark' : 'light';
  };

  const watchSystemTheme = () => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    mediaQuery.addEventListener('change', (e) => {
      systemTheme.value = e.matches ? 'dark' : 'light';
      if (mode.value === 'system') {
        applyTheme();
      }
    });
  };

  const setMode = (newMode: ThemeMode) => {
    mode.value = newMode;
    localStorage.setItem(THEME_STORAGE_KEY, newMode);
    applyTheme();
  };

  const toggleTheme = () => {
    if (mode.value === 'system') {
      setMode(systemTheme.value === 'dark' ? 'light' : 'dark');
    } else {
      setMode(mode.value === 'dark' ? 'light' : 'dark');
    }
  };

  const applyTheme = () => {
    document.documentElement.setAttribute('data-theme', currentTheme.value);
  };

  return {
    mode,
    systemTheme,
    currentTheme,
    isDark,
    init,
    setMode,
    toggleTheme
  };
});
