<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api } from "../api/client";
import { useAppContext } from "../composables/useAppContext";
import AddServerDialog from "../components/AddServerDialog.vue";
import ActionDialog from "../components/ActionDialog.vue";
import LogViewer from "../components/LogViewer.vue";
import SnapshotViewer from "../components/SnapshotViewer.vue";
import EditServerDialog from "../components/EditServerDialog.vue";
import DeveloperResourcesIcon from "@bitrix24/b24icons-vue/outline/DeveloperResourcesIcon";
import PlusLIcon from "@bitrix24/b24icons-vue/outline/PlusLIcon";
import RefreshIcon from "@bitrix24/b24icons-vue/outline/RefreshIcon";
import FileIcon from "@bitrix24/b24icons-vue/outline/FileIcon";
import SearchIcon from "@bitrix24/b24icons-vue/outline/SearchIcon";
import ChevronRightLIcon from "@bitrix24/b24icons-vue/outline/ChevronRightLIcon";
import TrashcanIcon from "@bitrix24/b24icons-vue/outline/TrashcanIcon";
import EditPencilIcon from "@bitrix24/b24icons-vue/main/EditPencilIcon";
import GlobeExtranetIcon from "@bitrix24/b24icons-vue/outline/GlobeExtranetIcon";
import VirtualServerIcon from "@bitrix24/b24icons-vue/outline/VirtualServerIcon";
import DatabaseIcon from "@bitrix24/b24icons-vue/outline/DatabaseIcon";
import ProductsCubeIcon from "@bitrix24/b24icons-vue/outline/ProductsCubeIcon";
import CloudSyncIcon from "@bitrix24/b24icons-vue/outline/CloudSyncIcon";
import ChatsWithCheckIcon from "@bitrix24/b24icons-vue/outline/ChatsWithCheckIcon";
import SettingsIcon from "@bitrix24/b24icons-vue/outline/SettingsIcon";
import ChevronDownSIcon from "@bitrix24/b24icons-vue/outline/ChevronDownSIcon";
import ChevronRightSIcon from "@bitrix24/b24icons-vue/outline/ChevronRightSIcon";
import CrossSIcon from "@bitrix24/b24icons-vue/outline/CrossSIcon";
import FilterFunnelIcon from "@bitrix24/b24icons-vue/outline/FilterFunnelIcon";
import CircleCheckIcon from "@bitrix24/b24icons-vue/outline/CircleCheckIcon";
import { DOMAINS, getActionMeta, groupCapabilities, filterCapabilities } from "../data/capabilitiesMeta";

const route = useRoute();
const router = useRouter();
const toast = useToast();
const { servers, operations, fetchServers, fetchOperations } = useAppContext();

const riskLabels = {
  low: "Низкий",
  medium: "Средний",
  high: "Высокий",
  critical: "Критический",
};

const categoryLabels = {
  pool: "Пул",
  hosts: "Хосты",
  local: "Система",
  runtime: "Платформа",
  mysql: "MySQL",
  memcached: "Memcached",
  tasks: "Задачи",
  sites: "Сайты",
  site: "Сайты",
  sphinx: "Sphinx",
  web: "Web / PHP",
  monitoring: "Мониторинг",
  push: "Push",
  transformer: "Трансформер",
};

const summaryTranslations = {
  "Create the native Bitrix server pool": "Создать пул Bitrix",
  "Remove the native Bitrix server pool": "Удалить пул Bitrix",
  "Reboot the BitrixVM server": "Перезагрузить сервер",
  "Power off the BitrixVM server": "Выключить сервер",
  "Update all EL9 packages": "Обновить системные пакеты",
  "Create memcached instance": "Создать экземпляр Memcached",
  "Stop a Bitrix background task": "Остановить фоновую задачу",
  "Create a Bitrix kernel site": "Создать сайт с ядром Bitrix",
  "Configure Node.js push service": "Настроить Push-сервис",
};

function relativeTime(date) {
  if (!date) return "Не проверялся";
  const minutes = Math.max(0, Math.round((Date.now() - new Date(date).getTime()) / 60000));
  if (minutes < 1) return "только что";
  if (minutes < 60) return `${minutes} мин назад`;
  if (minutes < 1440) return `${Math.round(minutes / 60)} ч назад`;
  return new Date(date).toLocaleDateString("ru-RU");
}

function isServerStale(server) {
  if (!server?.capabilities_checked_at) return true;
  return Date.now() - new Date(server.capabilities_checked_at).getTime() > 7200000;
}

const selectedId = ref(null);
const capabilities = ref([]);
const actionSearch = ref("");
const category = ref("all");
const loadingCapabilities = ref(false);
const addOpen = ref(false);
const editOpen = ref(false);
const activeAction = ref(null);
const actionDialogOpen = ref(false);
const snapshot = ref(null);
const snapshotLoading = ref(false);
const activeTab = ref("capabilities");
const servicesStatus = ref({});
const loadingServices = ref(false);

const keyServices = [
  { key: "mysql", label: "MySQL / MariaDB", desc: "База данных" },
  { key: "nginx", label: "Nginx", desc: "Веб-сервер" },
  { key: "httpd", label: "Apache", desc: "PHP-бэкенд" },
  { key: "php_fpm", label: "PHP-FPM", desc: "FastCGI" },
  { key: "memcached", label: "Memcached", desc: "Кэш RAM" },
  { key: "redis", label: "Redis", desc: "Кэш и очереди" },
  { key: "push_server", label: "Push-сервер", desc: "Bitrix RTC" },
  { key: "cron", label: "Cron", desc: "Задачи" },
];

function getServiceState(key) {
  if (servicesStatus.value && servicesStatus.value[key] !== undefined) {
    return servicesStatus.value[key];
  }
  return selected.value?.capabilities?.services?.[key] || (loadingServices.value ? "loading" : "unknown");
}

function serviceStateInfo(state) {
  if (state === "active") {
    return {
      label: "Работает",
      dotClass: "bg-emerald-500",
      badgeClass: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30",
    };
  }
  if (state === "failed") {
    return {
      label: "Сбой",
      dotClass: "bg-rose-500",
      badgeClass: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/30",
    };
  }
  if (state === "inactive") {
    return {
      label: "Остановлен",
      dotClass: "bg-zinc-400 dark:bg-zinc-500",
      badgeClass: "bg-zinc-500/10 text-zinc-500 dark:text-zinc-400 border-zinc-500/20",
    };
  }
  if (state === "loading") {
    return {
      label: "…",
      dotClass: "bg-amber-400 animate-pulse",
      badgeClass: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
    };
  }
  return {
    label: "Не активен",
    dotClass: "bg-zinc-400/60",
    badgeClass: "bg-zinc-500/10 text-zinc-500 border-zinc-500/20",
  };
}

async function loadServicesStatus() {
  if (!selected.value?.id) {
    servicesStatus.value = {};
    return;
  }
  if (selected.value.capabilities?.services) {
    servicesStatus.value = { ...selected.value.capabilities.services };
  }
  loadingServices.value = true;
  try {
    const res = await api.servicesStatus(selected.value.id);
    if (res && Object.keys(res).length > 0) {
      servicesStatus.value = res;
    }
  } catch {
    // Keep cached
  } finally {
    loadingServices.value = false;
  }
}

const selected = computed(() => {
  return servers.value.find((item) => item.id === selectedId.value) || servers.value[0] || null;
});

const serverOptions = computed(() =>
  servers.value.map((server) => ({
    label: `${server.name} (${server.address})`,
    description: `Порт: ${server.port} · ${relativeTime(server.capabilities_checked_at)}`,
    value: server.id,
  }))
);

onMounted(async () => {
  await fetchServers();
  const queryServerId = route.query.server;
  if (queryServerId && servers.value.some((s) => s.id === queryServerId)) {
    selectedId.value = queryServerId;
  } else if (servers.value.length > 0 && !selectedId.value) {
    selectedId.value = servers.value[0].id;
  }
});

watch(
  () => servers.value,
  (list) => {
    const queryServerId = route.query.server;
    if (queryServerId && list.some((s) => s.id === queryServerId)) {
      selectedId.value = queryServerId;
    } else if (list.length > 0 && (!selectedId.value || !list.some((s) => s.id === selectedId.value))) {
      selectedId.value = list[0].id;
    }
  },
  { immediate: true }
);

watch(
  () => selectedId.value,
  (id) => {
    if (id && route.query.server !== id) {
      router.replace({ query: { ...route.query, server: id } });
    }
  }
);

watch(
  () => route.query.server,
  (newId) => {
    if (newId && newId !== selectedId.value && servers.value.some((s) => s.id === newId)) {
      selectedId.value = newId;
    }
  }
);

watch(
  () => selected.value?.id,
  async (id) => {
    snapshot.value = null;
    if (!id) {
      capabilities.value = [];
      return;
    }
    loadingCapabilities.value = true;
    try {
      capabilities.value = await api.capabilities(id);
    } catch (err) {
      toast.add({
        title: "Ошибка загрузки возможностей",
        description: err.message,
        color: "air-primary-alert",
      });
    } finally {
      loadingCapabilities.value = false;
    }
    loadServicesStatus();
    if (activeTab.value === "snapshot") {
      await loadSnapshot();
    }
  },
  { immediate: true }
);

const selectedDomain = ref("all");
const onlyAvailable = ref(false);
const selectedRisk = ref("all");
const collapsedSubgroups = ref(new Set());

const riskFilterOptions = [
  { label: "Все уровни риска", value: "all" },
  { label: "Низкий риск", value: "low" },
  { label: "Средний риск", value: "medium" },
  { label: "Высокий / Критический", value: "danger" },
];

const domainIcons = {
  sites: GlobeExtranetIcon,
  pool: VirtualServerIcon,
  runtime: ProductsCubeIcon,
  mysql: DatabaseIcon,
  cache: CloudSyncIcon,
  services: ChatsWithCheckIcon,
  system: SettingsIcon,
};

const domainStats = computed(() => {
  const stats = {
    all: {
      id: "all",
      label: "Все возможности",
      shortLabel: "Все",
      total: capabilities.value.length,
      available: capabilities.value.filter((c) => c.available).length,
    },
  };

  for (const [key, domain] of Object.entries(DOMAINS)) {
    stats[key] = {
      id: key,
      label: domain.label,
      shortLabel: domain.shortLabel,
      total: 0,
      available: 0,
    };
  }

  for (const cap of capabilities.value) {
    const meta = getActionMeta(cap.action);
    const dKey = meta.domain || "system";
    if (stats[dKey]) {
      stats[dKey].total += 1;
      if (cap.available) stats[dKey].available += 1;
    }
  }

  return stats;
});

const structuredDomains = computed(() => {
  const filtered = filterCapabilities(capabilities.value, {
    search: actionSearch.value,
    domain: selectedDomain.value,
    onlyAvailable: onlyAvailable.value,
    risk: selectedRisk.value,
  });
  return groupCapabilities(filtered);
});

const totalVisibleActions = computed(() => {
  return structuredDomains.value.reduce((acc, domain) => {
    return acc + domain.subgroups.reduce((subAcc, sg) => subAcc + sg.actions.length, 0);
  }, 0);
});

function toggleSubgroup(domainId, sgId) {
  const key = `${domainId}:${sgId}`;
  if (collapsedSubgroups.value.has(key)) {
    collapsedSubgroups.value.delete(key);
  } else {
    collapsedSubgroups.value.add(key);
  }
}

function isSubgroupCollapsed(domainId, sgId) {
  return collapsedSubgroups.value.has(`${domainId}:${sgId}`);
}

function resetFilters() {
  actionSearch.value = "";
  selectedDomain.value = "all";
  onlyAvailable.value = false;
  selectedRisk.value = "all";
}

async function refreshCapabilities() {
  if (!selected.value) return;
  loadingCapabilities.value = true;
  try {
    capabilities.value = await api.refreshCapabilities(selected.value.id);
    await loadServicesStatus();
    toast.add({
      title: "Возможности обновлены",
      color: "air-primary-success",
    });
    await fetchServers();
  } catch (err) {
    toast.add({
      title: "Ошибка обновления возможностей",
      description: err.message,
      color: "air-primary-alert",
    });
  } finally {
    loadingCapabilities.value = false;
  }
}

async function loadSnapshot() {
  if (!selected.value) return;
  snapshotLoading.value = true;
  try {
    snapshot.value = await api.snapshot(selected.value.id);
  } catch (err) {
    toast.add({
      title: "Ошибка получения снимка",
      description: err.message,
      color: "air-primary-alert",
    });
  } finally {
    snapshotLoading.value = false;
  }
}

function openAction(item) {
  const meta = getActionMeta(item.action);
  activeAction.value = {
    ...item,
    summary: meta.title || summaryTranslations[item.summary] || item.summary || item.action,
    description: meta.description || "",
  };
  actionDialogOpen.value = true;
}

function handleServerCreated(newServer) {
  fetchServers();
  selectedId.value = newServer.id;
}

function handleActionExecuted(operation) {
  fetchOperations();
}

const confirmDeleteOpen = ref(false);
const deleteLoading = ref(false);

async function deleteSelectedServer() {
  if (!selected.value) return;
  const serverToDelete = selected.value;
  deleteLoading.value = true;
  try {
    await api.deleteServer(serverToDelete.id);
    toast.add({
      title: "Сервер удален",
      description: `Сервер «${serverToDelete.name}» успешно исключён из контура`,
      color: "air-primary-success",
    });
    confirmDeleteOpen.value = false;
    await fetchServers();
    selectedId.value = servers.value.length > 0 ? servers.value[0].id : null;
  } catch (err) {
    toast.add({
      title: "Ошибка удаления сервера",
      description: err.message,
      color: "air-primary-alert",
    });
  } finally {
    deleteLoading.value = false;
  }
}

const tabItems = computed(() => [
  {
    value: "capabilities",
    label: `Возможности (${capabilities.value.filter((i) => i.available).length})`,
  },
  {
    value: "snapshot",
    label: "Состояние",
  },
  {
    value: "logs",
    label: "Логи",
  },
  {
    value: "history",
    label: "История",
  },
]);

function handleTabChange(tab) {
  activeTab.value = tab;
  if (tab === "snapshot" && !snapshot.value) {
    loadSnapshot();
  } else if (tab === "history") {
    router.push("/operations");
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-label tracking-tight">Серверы</h1>
        <p class="text-sm text-muted mt-1">Управление инфраструктурой и действиями BitrixEnv</p>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <div v-if="servers.length" class="w-full sm:w-72 md:w-80">
          <B24Select
            v-model="selectedId"
            :items="serverOptions"
            :icon="DeveloperResourcesIcon"
            placeholder="Выберите сервер"
            class="w-full"
          />
        </div>
        <B24Button
          :icon="PlusLIcon"
          label="Добавить сервер"
          color="air-primary"
          @click="addOpen = true"
        />
      </div>
    </div>

    <!-- If no servers exist -->
    <B24Card v-if="!servers.length" class="p-12 text-center border border-muted">
      <div class="max-w-md mx-auto space-y-4">
        <div class="p-4 rounded-2xl bg-elevated border border-muted inline-block">
          <DeveloperResourcesIcon class="size-12 text-[var(--ui-color-design-filled-blue)]" />
        </div>
        <h2 class="text-xl font-bold text-label">Добавьте первый сервер</h2>
        <p class="text-sm text-description">
          Контроллер проверит SSH fingerprint и совместимость BitrixEnv перед сохранением в контур.
        </p>
        <B24Button
          label="Добавить сервер"
          :icon="PlusLIcon"
          color="air-primary"
          @click="addOpen = true"
        />
      </div>
    </B24Card>

    <!-- Full-width Server Workspace -->
    <B24Card v-else-if="selected" class="border border-muted" :b24ui="{ header: 'border-b border-muted' }">
      <template #header>
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 w-full">
          <div class="flex items-center gap-3 min-w-0">
            <div class="p-2.5 rounded-xl bg-default border border-muted shrink-0">
              <DeveloperResourcesIcon class="size-5 text-[var(--ui-color-design-filled-blue)]" />
            </div>
            <div class="min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <h2 class="text-xl font-bold text-label truncate">{{ selected.name }}</h2>
                <B24Badge
                  :label="isServerStale(selected) ? 'Проверить' : 'Доступен'"
                  :color="isServerStale(selected) ? 'air-primary-warning' : 'air-primary-success'"
                  size="sm"
                />
              </div>
              <p class="text-xs text-muted font-mono truncate">{{ selected.address }}:{{ selected.port }}</p>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <B24Button
              label="Обновить"
              :icon="RefreshIcon"
              color="air-secondary-no-accent"
              variant="outline"
              size="sm"
              :loading="loadingCapabilities"
              @click="refreshCapabilities"
            />
            <B24Button
              label="Снимок"
              :icon="FileIcon"
              color="air-secondary-no-accent"
              variant="outline"
              size="sm"
              :loading="snapshotLoading"
              @click="loadSnapshot"
            />
            <B24Button
              label="Изменить"
              :icon="EditPencilIcon"
              color="air-secondary-no-accent"
              variant="outline"
              size="sm"
              @click="editOpen = true"
            />
            <B24Button
              label="Удалить"
              :icon="TrashcanIcon"
              color="air-primary-alert"
              variant="outline"
              size="sm"
              @click="confirmDeleteOpen = true"
            />
          </div>
        </div>
      </template>

      <div class="space-y-6">
        <!-- Meta list with Server Info & Service Statuses -->
        <div class="p-4 rounded-xl bg-elevated/50 border border-muted text-xs space-y-4">
          <!-- Top Row: Server Connection & Host Info -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <span class="text-muted block">Адрес</span>
              <span class="font-mono text-label block mt-0.5">{{ selected.address }}:{{ selected.port }}</span>
            </div>
            <div>
              <span class="text-muted block">Пользователь</span>
              <span class="font-medium text-label block mt-0.5">{{ selected.username }}</span>
            </div>
            <div>
              <span class="text-muted block">SSH fingerprint</span>
              <span class="font-mono text-label block mt-0.5 truncate" :title="selected.host_key_fingerprint">
                {{ selected.host_key_fingerprint?.slice(0, 20) }}…
              </span>
            </div>
            <div>
              <span class="text-muted block">Проверен</span>
              <span class="text-label block mt-0.5">{{ relativeTime(selected.capabilities_checked_at) }}</span>
            </div>
          </div>

          <!-- Bottom Row: Key Services Status -->
          <div class="pt-3 border-t border-muted/70">
            <div class="flex items-center justify-between gap-2 mb-2.5">
              <div class="flex items-center gap-2">
                <span class="text-label font-semibold text-xs tracking-tight">Статусы ключевых служб</span>
                <span v-if="loadingServices" class="text-[11px] text-muted animate-pulse">обновление…</span>
              </div>
              <span class="text-[11px] text-muted hidden sm:inline">systemd статус</span>
            </div>

            <div class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
              <div
                v-for="svc in keyServices"
                :key="svc.key"
                class="flex flex-col p-2 rounded-lg border transition-colors"
                :class="serviceStateInfo(getServiceState(svc.key)).badgeClass"
                :title="`${svc.label} (${svc.desc}): ${serviceStateInfo(getServiceState(svc.key)).label}`"
              >
                <div class="flex items-center justify-between gap-1 mb-1">
                  <span class="font-bold text-[11px] truncate">{{ svc.label }}</span>
                  <span
                    class="w-2 h-2 rounded-full shrink-0"
                    :class="serviceStateInfo(getServiceState(svc.key)).dotClass"
                  />
                </div>
                <div class="flex items-center justify-between text-[10px]">
                  <span class="opacity-70 truncate">{{ svc.desc }}</span>
                  <span class="font-medium shrink-0 ml-1">
                    {{ serviceStateInfo(getServiceState(svc.key)).label }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Custom Tabs Switcher -->
        <div class="flex items-center gap-2 border-b border-muted pb-3 overflow-x-auto">
          <B24Button
            v-for="tab in tabItems"
            :key="tab.value"
            :label="tab.label"
            :variant="activeTab === tab.value ? 'solid' : 'ghost'"
            :color="activeTab === tab.value ? 'air-primary' : 'air-secondary-no-accent'"
            size="sm"
            @click="handleTabChange(tab.value)"
          />
        </div>

        <!-- Tab 1: Capabilities -->
        <div v-if="activeTab === 'capabilities'" class="space-y-5">
          <!-- Domain Navigation Pills / Cards -->
          <div class="space-y-2">
            <div class="flex items-center justify-between text-xs text-muted px-0.5">
              <span class="font-medium">Разделы возможностей BitrixVM</span>
              <span>Доступно: <b class="text-label">{{ capabilities.filter(c => c.available).length }}</b> из {{ capabilities.length }}</span>
            </div>

            <div class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
              <!-- All Domains Pill -->
              <button
                type="button"
                class="flex flex-col p-2.5 rounded-xl border text-left transition-all cursor-pointer select-none"
                :class="selectedDomain === 'all'
                  ? 'bg-[var(--ui-color-design-filled-blue)]/10 border-[var(--ui-color-design-filled-blue)] ring-1 ring-[var(--ui-color-design-filled-blue)]/30'
                  : 'bg-elevated/40 border-muted hover:border-muted-foreground/30 hover:bg-elevated'"
                @click="selectedDomain = 'all'"
              >
                <div class="flex items-center justify-between gap-1 mb-1">
                  <div class="p-1 rounded-lg bg-default border border-muted/60 shrink-0">
                    <DeveloperResourcesIcon class="size-3.5 text-[var(--ui-color-design-filled-blue)]" />
                  </div>
                  <span
                    class="text-[11px] font-bold px-1.5 py-0.5 rounded-full"
                    :class="selectedDomain === 'all' ? 'bg-[var(--ui-color-design-filled-blue)] text-white' : 'bg-muted/60 text-muted'"
                  >
                    {{ domainStats.all?.available }}/{{ domainStats.all?.total }}
                  </span>
                </div>
                <span class="text-xs font-semibold text-label truncate">Все разделы</span>
                <span class="text-[10px] text-muted truncate">Полный перечень</span>
              </button>

              <!-- Specific Domain Pills -->
              <button
                v-for="(domDef, domKey) in DOMAINS"
                :key="domKey"
                type="button"
                class="flex flex-col p-2.5 rounded-xl border text-left transition-all cursor-pointer select-none"
                :class="selectedDomain === domKey
                  ? 'bg-[var(--ui-color-design-filled-blue)]/10 border-[var(--ui-color-design-filled-blue)] ring-1 ring-[var(--ui-color-design-filled-blue)]/30'
                  : 'bg-elevated/40 border-muted hover:border-muted-foreground/30 hover:bg-elevated'"
                @click="selectedDomain = domKey"
              >
                <div class="flex items-center justify-between gap-1 mb-1">
                  <div class="p-1 rounded-lg bg-default border border-muted/60 shrink-0">
                    <component :is="domainIcons[domKey] || SettingsIcon" class="size-3.5 text-[var(--ui-color-design-filled-blue)]" />
                  </div>
                  <span
                    class="text-[11px] font-bold px-1.5 py-0.5 rounded-full"
                    :class="selectedDomain === domKey ? 'bg-[var(--ui-color-design-filled-blue)] text-white' : 'bg-muted/60 text-muted'"
                  >
                    {{ domainStats[domKey]?.available }}/{{ domainStats[domKey]?.total }}
                  </span>
                </div>
                <span class="text-xs font-semibold text-label truncate">{{ domDef.shortLabel }}</span>
                <span class="text-[10px] text-muted truncate">{{ domDef.subgroups?.length || 0 }} подгрупп</span>
              </button>
            </div>
          </div>

          <!-- Toolbar: Search, Filters, Counters -->
          <div class="p-3.5 rounded-xl bg-elevated/50 border border-muted flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
            <div class="flex-1 flex flex-col sm:flex-row items-center gap-2.5">
              <!-- Search Input -->
              <div class="relative w-full sm:w-80">
                <B24Input
                  v-model="actionSearch"
                  :icon="SearchIcon"
                  placeholder="Поиск действий, описаний или ключей…"
                  class="w-full"
                />
                <button
                  v-if="actionSearch"
                  type="button"
                  class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-label p-0.5"
                  @click="actionSearch = ''"
                >
                  <CrossSIcon class="size-3.5" />
                </button>
              </div>

              <!-- Risk Filter -->
              <div class="w-full sm:w-52">
                <B24Select
                  v-model="selectedRisk"
                  :items="riskFilterOptions"
                  class="w-full"
                />
              </div>

              <!-- Only Available Toggle Button -->
              <B24Button
                :label="onlyAvailable ? 'Только доступные' : 'Все действия'"
                :icon="onlyAvailable ? CircleCheckIcon : FilterFunnelIcon"
                :variant="onlyAvailable ? 'solid' : 'outline'"
                :color="onlyAvailable ? 'air-primary' : 'air-secondary-no-accent'"
                size="sm"
                class="shrink-0 w-full sm:w-auto"
                @click="onlyAvailable = !onlyAvailable"
              />
            </div>

            <!-- Stats & Reset Button -->
            <div class="flex items-center justify-between md:justify-end gap-3 text-xs text-muted border-t md:border-t-0 pt-2 md:pt-0 border-muted/60">
              <span>Найдено: <b class="text-label font-mono">{{ totalVisibleActions }}</b></span>
              <B24Button
                v-if="actionSearch || selectedDomain !== 'all' || onlyAvailable || selectedRisk !== 'all'"
                label="Сбросить"
                variant="link"
                color="air-secondary-no-accent"
                size="xs"
                @click="resetFilters"
              />
            </div>
          </div>

          <!-- Structured Domains and Subgroups -->
          <div v-if="loadingCapabilities" class="p-12 text-center text-sm text-muted rounded-xl border border-muted">
            Загрузка доступных действий…
          </div>

          <div v-else-if="structuredDomains.length" class="space-y-6">
            <div
              v-for="domain in structuredDomains"
              :key="domain.id"
              class="space-y-3"
            >
              <!-- Domain Header -->
              <div class="flex items-center justify-between gap-3 pb-1 border-b border-muted">
                <div class="flex items-center gap-2 min-w-0">
                  <div class="p-1.5 rounded-lg bg-default border border-muted shrink-0">
                    <component :is="domainIcons[domain.id] || SettingsIcon" class="size-4 text-[var(--ui-color-design-filled-blue)]" />
                  </div>
                  <div>
                    <div class="flex items-center gap-2">
                      <h3 class="text-sm font-bold text-label">{{ domain.label }}</h3>
                      <B24Badge
                        :label="`${domain.availableCount}/${domain.totalCount} доступно`"
                        :color="domain.availableCount > 0 ? 'air-primary-success' : 'air-secondary-no-accent'"
                        size="xs"
                      />
                    </div>
                    <p class="text-xs text-muted truncate">{{ domain.description }}</p>
                  </div>
                </div>
              </div>

              <!-- Subgroups in Domain -->
              <div class="space-y-3">
                <div
                  v-for="subgroup in domain.subgroups"
                  :key="subgroup.id"
                  class="rounded-xl border border-muted overflow-hidden bg-elevated/20"
                >
                  <!-- Subgroup Header -->
                  <div
                    class="p-3 bg-elevated/60 flex items-center justify-between gap-3 cursor-pointer select-none hover:bg-elevated/90 transition-colors border-b border-muted/50"
                    @click="toggleSubgroup(domain.id, subgroup.id)"
                  >
                    <div class="flex items-center gap-2.5 min-w-0">
                      <component
                        :is="isSubgroupCollapsed(domain.id, subgroup.id) ? ChevronRightSIcon : ChevronDownSIcon"
                        class="size-3.5 text-muted shrink-0 transition-transform"
                      />
                      <span class="text-xs font-bold text-label tracking-tight">{{ subgroup.label }}</span>
                      <span v-if="subgroup.description" class="text-xs text-muted hidden sm:inline truncate">
                        · {{ subgroup.description }}
                      </span>
                    </div>

                    <div class="flex items-center gap-2 shrink-0">
                      <span class="text-[11px] font-mono px-2 py-0.5 rounded-full bg-default border border-muted text-muted font-medium">
                        {{ subgroup.actions.length }} {{ subgroup.actions.length === 1 ? 'действие' : subgroup.actions.length < 5 ? 'действия' : 'действий' }}
                      </span>
                    </div>
                  </div>

                  <!-- Actions in Subgroup -->
                  <div v-show="!isSubgroupCollapsed(domain.id, subgroup.id)" class="divide-y divide-muted/60">
                    <div
                      v-for="item in subgroup.actions"
                      :key="item.action"
                      class="p-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3 hover:bg-muted/20 transition-colors"
                      :class="{ 'opacity-65': !item.available }"
                    >
                      <!-- Action Info -->
                      <div class="min-w-0 space-y-1.5 flex-1">
                        <div class="flex items-center gap-2 flex-wrap">
                          <span class="text-xs font-bold text-label">{{ item.displayTitle }}</span>
                          <code class="text-[11px] font-mono font-bold px-1.5 py-0.5 rounded bg-default border border-muted text-label">{{ item.action }}</code>
                          <B24Badge
                            :label="riskLabels[item.risk] || item.risk"
                            :color="item.risk === 'high' || item.risk === 'critical' ? 'air-primary-alert' : item.risk === 'medium' ? 'air-primary-warning' : 'air-primary-success'"
                            size="xs"
                          />
                          <B24Badge
                            v-if="item.meta?.pairWith"
                            :label="item.meta?.pairType === 'enable' ? 'Включение' : item.meta?.pairType === 'disable' ? 'Отключение' : item.meta?.pairType === 'upgrade' ? 'Обновление' : item.meta?.pairType === 'rollback' ? 'Откат' : 'Связанная операция'"
                            color="air-secondary-no-accent"
                            size="xs"
                          />
                        </div>

                        <p class="text-xs text-description leading-relaxed">
                          {{ item.displayDescription }}
                        </p>

                        <p v-if="item.reason" class="text-[11px] text-[var(--ui-color-design-filled-amber)] flex items-center gap-1 font-medium">
                          <span>⚠ Недоступно:</span>
                          <span>{{ item.reason }}</span>
                        </p>
                      </div>

                      <!-- Action Buttons & Status -->
                      <div class="flex items-center gap-3 shrink-0 self-end md:self-center">
                        <B24Badge
                          :label="item.available ? 'Доступно' : 'Недоступно'"
                          :color="item.available ? 'air-primary-success' : 'air-secondary-no-accent'"
                          size="xs"
                        />
                        <B24Button
                          :label="item.available ? 'Настроить' : 'Недоступно'"
                          :color="item.available ? 'air-primary' : 'air-secondary-no-accent'"
                          :variant="item.available ? 'outline' : 'ghost'"
                          size="xs"
                          :disabled="!item.available"
                          @click="openAction(item)"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Empty State -->
          <div v-else class="p-12 text-center space-y-3 rounded-xl border border-muted bg-elevated/20">
            <div class="p-3 rounded-2xl bg-default border border-muted inline-block">
              <SearchIcon class="size-6 text-muted" />
            </div>
            <h4 class="text-sm font-bold text-label">Действия не найдены</h4>
            <p class="text-xs text-muted max-w-sm mx-auto">
              По заданным критериям фильтрации ничего не найдено. Попробуйте изменить поисковый запрос или сбросить фильтры.
            </p>
            <B24Button
              label="Сбросить все фильтры"
              color="air-primary"
              variant="outline"
              size="sm"
              @click="resetFilters"
            />
          </div>
        </div>

        <!-- Tab 2: Snapshot -->
        <div v-else-if="activeTab === 'snapshot'">
          <SnapshotViewer
            :snapshot="snapshot"
            :loading="snapshotLoading"
            :server="selected"
            @refresh="loadSnapshot"
          />
        </div>

        <!-- Tab 3: Logs -->
        <div v-else-if="activeTab === 'logs'">
          <LogViewer :server="selected" />
        </div>
      </div>
    </B24Card>

    <!-- Recent Operations Strip -->
    <B24Card class="border border-muted" :b24ui="{ header: 'border-b border-muted' }">
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="font-bold text-label text-base">Последние операции</h3>
          <B24Button
            label="Все операции"
            :trailing-icon="ChevronRightLIcon"
            variant="link"
            color="air-primary"
            size="sm"
            @click="router.push('/operations')"
          />
        </div>
      </template>

      <div v-if="operations.length" class="divide-y divide-muted">
        <div
          v-for="op in operations.slice(0, 3)"
          :key="op.id"
          class="py-3 flex items-center justify-between text-sm"
        >
          <div class="flex items-center gap-3 min-w-0">
            <code class="text-xs font-bold text-label font-mono">{{ op.action }}</code>
            <span class="text-xs text-muted truncate">
              {{ servers.find(s => s.id === op.server_id)?.name || op.server_id }}
            </span>
          </div>

          <div class="flex items-center gap-3">
            <B24Badge
              :label="op.status === 'succeeded' ? 'Выполнено' : op.status === 'running' ? 'Выполняется' : op.status === 'failed' ? 'Ошибка' : 'В очереди'"
              :color="op.status === 'succeeded' ? 'air-primary-success' : op.status === 'running' ? 'air-primary' : op.status === 'failed' ? 'air-primary-alert' : 'air-primary-warning'"
              size="sm"
            />
            <span class="text-xs text-muted">
              {{ new Date(op.created_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) }}
            </span>
          </div>
        </div>
      </div>
      <div v-else class="py-4 text-center text-sm text-muted">
        Операций пока нет
      </div>
    </B24Card>

    <!-- Dialogs -->
    <AddServerDialog
      v-model:open="addOpen"
      @created="handleServerCreated"
    />

    <ActionDialog
      v-if="selected && activeAction"
      v-model:open="actionDialogOpen"
      :server="selected"
      :capability="activeAction"
      @executed="handleActionExecuted"
    />

    <!-- Confirm Delete Modal -->
    <B24Modal
      v-model:open="confirmDeleteOpen"
      title="Удаление сервера"
      :description="`Исключение сервера «${selected?.name}» из контура управления`"
    >
      <template #body>
        <div class="space-y-3">
          <p class="text-sm text-description">
            Вы действительно хотите удалить сервер <strong class="text-label">{{ selected?.name }}</strong> ({{ selected?.address }})?
          </p>
          <B24Alert
            title="Внимание"
            description="Сервер и сохранённые учётные данные будут удалены из базы контроллера. Сам удалённый сервер и его работающие службы затронуты не будут."
            color="air-secondary-alert"
          />
        </div>
      </template>

      <template #footer>
        <div class="flex items-center justify-end gap-2 w-full">
          <B24Button
            label="Отмена"
            color="air-secondary-no-accent"
            variant="ghost"
            :disabled="deleteLoading"
            @click="confirmDeleteOpen = false"
          />
          <B24Button
            label="Удалить сервер"
            color="air-primary-alert"
            :loading="deleteLoading"
            @click="deleteSelectedServer"
          />
        </div>
      </template>
    </B24Modal>

    <!-- Edit Server Dialog -->
    <EditServerDialog
      v-if="selected"
      v-model:open="editOpen"
      :server="selected"
      @updated="fetchServers"
    />
  </div>
</template>
