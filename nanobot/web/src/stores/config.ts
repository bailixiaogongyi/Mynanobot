import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import api from '@/services/api';

interface ConfigState {
  model: {
    current: string;
    enable_reasoning: boolean;
  };
  providers: any[];
  channels: any[];
  knowledge: any;
  agentDefaults: any;
  gateway: any;
  loading: boolean;
}

export const useConfigStore = defineStore('config', () => {
  const config = ref<ConfigState>({
    model: { current: '', enable_reasoning: true },
    providers: [],
    channels: [],
    knowledge: {},
    agentDefaults: {},
    gateway: {},
    loading: false
  });

  const currentProvider = computed(() => {
    const current = config.value.model.current;
    if (!current || !current.includes('/')) return null;
    const providerName = current.split('/')[0];
    return config.value.providers.find(p => p.name === providerName);
  });

  const currentModel = computed(() => {
    const current = config.value.model.current;
    if (!current || !current.includes('/')) return null;
    const [providerName, modelId] = current.split('/');
    const provider = config.value.providers.find(p => p.name === providerName);
    return provider?.models?.find((m: any) => m.model_id === modelId);
  });

  const enabledChannels = computed(() => 
    config.value.channels.filter((c: any) => c.enabled)
  );

  const loadConfig = async () => {
    config.value.loading = true;
    try {
      if (api?.config) {
        const data = await api.config.get();
        config.value.model = data.model || { current: '', enable_reasoning: true };
        config.value.providers = data.providers || [];
        config.value.channels = data.channels || [];
        config.value.knowledge = data.knowledge || {};
        config.value.agentDefaults = data.agent_defaults || {};
        config.value.gateway = data.gateway || {};
      }
    } catch (e) {
      console.error('[ConfigStore] Failed to load config:', e);
    } finally {
      config.value.loading = false;
    }
  };

  const setModel = async (modelId: string) => {
    try {
      if (api?.config) {
        await api.config.setModel(modelId);
        config.value.model.current = modelId;
      }
    } catch (e) {
      console.error('[ConfigStore] Failed to set model:', e);
      throw e;
    }
  };

  const updateAgentDefaults = async (updates: any) => {
    try {
      if (api?.config) {
        await api.config.updateAgentDefaults(updates);
        Object.assign(config.value.agentDefaults, updates);
      }
    } catch (e) {
      console.error('[ConfigStore] Failed to update agent defaults:', e);
      throw e;
    }
  };

  const toggleChannel = async (channelName: string, enabled: boolean) => {
    try {
      if (api?.config) {
        await api.config.updateChannel(channelName, { enabled });
        const channel = config.value.channels.find((c: any) => c.name === channelName);
        if (channel) {
          channel.enabled = enabled;
        }
      }
    } catch (e) {
      console.error('[ConfigStore] Failed to toggle channel:', e);
      throw e;
    }
  };

  return {
    config,
    currentProvider,
    currentModel,
    enabledChannels,
    loadConfig,
    setModel,
    updateAgentDefaults,
    toggleChannel
  };
});
