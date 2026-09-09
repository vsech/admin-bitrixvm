import { ref, computed } from "vue";
import { api } from "../api/client";

const user = ref(null);
const initializing = ref(true);
const servers = ref([]);
const operations = ref([]);
const loadingServers = ref(false);
const loadingOperations = ref(false);

export function useAppContext() {
  const isAuthenticated = computed(() => api.isDemo || Boolean(user.value || api.accessToken));

  async function init() {
    if (!api.authenticated) {
      initializing.value = false;
      return;
    }
    try {
      user.value = await api.me();
      await fetchAll();
    } catch {
      api.clearTokens();
      user.value = null;
    } finally {
      initializing.value = false;
    }
  }

  async function login(username, password) {
    user.value = await api.login(username, password);
    await fetchAll();
    return user.value;
  }

  async function logout() {
    await api.logout();
    user.value = null;
    servers.value = [];
    operations.value = [];
  }

  async function fetchServers() {
    loadingServers.value = true;
    try {
      servers.value = await api.servers();
    } catch (err) {
      console.error("Failed to fetch servers", err);
    } finally {
      loadingServers.value = false;
    }
  }

  async function fetchOperations() {
    loadingOperations.value = true;
    try {
      operations.value = await api.operations();
    } catch (err) {
      console.error("Failed to fetch operations", err);
    } finally {
      loadingOperations.value = false;
    }
  }

  async function fetchAll() {
    await Promise.allSettled([fetchServers(), fetchOperations()]);
  }

  return {
    user,
    initializing,
    isAuthenticated,
    servers,
    operations,
    loadingServers,
    loadingOperations,
    init,
    login,
    logout,
    fetchServers,
    fetchOperations,
    fetchAll,
    isDemo: api.isDemo,
  };
}
