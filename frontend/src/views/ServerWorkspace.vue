<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api } from "../api/client";
import { useAppContext } from "../composables/useAppContext";
import AddServerDialog from "../components/AddServerDialog.vue";
import ActionDialog from "../components/ActionDialog.vue";
import LogViewer from "../components/LogViewer.vue";
import SnapshotViewer from "../components/SnapshotViewer.vue";
import DeveloperResourcesIcon from "@bitrix24/b24icons-vue/outline/DeveloperResourcesIcon";
import PlusLIcon from "@bitrix24/b24icons-vue/outline/PlusLIcon";
import RefreshIcon from "@bitrix24/b24icons-vue/outline/RefreshIcon";
import FileIcon from "@bitrix24/b24icons-vue/outline/FileIcon";
import SearchIcon from "@bitrix24/b24icons-vue/outline/SearchIcon";
import ChevronRightLIcon from "@bitrix24/b24icons-vue/outline/ChevronRightLIcon";

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

const categories = computed(() => [
  ...new Set(capabilities.value.map((item) => item.category)),
]);

const categoryOptions = computed(() => [
  { label: "Все категории", value: "all" },
  ...categories.value.map((cat) => ({
    label: categoryLabels[cat] || cat,
    value: cat,
  })),
]);

const visibleCapabilities = computed(() =>
  capabilities.value.filter(
    (item) =>
      (category.value === "all" || item.category === category.value) &&
      `${item.action} ${item.summary || ""}`.toLowerCase().includes(actionSearch.value.toLowerCase())
  )
);

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
  activeAction.value = {
    ...item,
    summary: summaryTranslations[item.summary] || item.summary || item.action,
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
        <div v-if="activeTab === 'capabilities'" class="space-y-4">
          <!-- Filters -->
          <div class="flex flex-col sm:flex-row items-center gap-3">
            <div class="flex-1 w-full">
              <B24Input
                v-model="actionSearch"
                :icon="SearchIcon"
                placeholder="Найти действие (например reboot, site, mysql)…"
                class="w-full"
              />
            </div>
            <div class="w-full sm:w-48">
              <B24Select
                v-model="category"
                :items="categoryOptions"
                class="w-full"
              />
            </div>
          </div>

          <!-- Actions Table -->
          <div class="rounded-xl border border-muted overflow-hidden">
            <div v-if="loadingCapabilities" class="p-8 text-center text-sm text-muted">
              Загрузка доступных действий…
            </div>

            <div v-else-if="visibleCapabilities.length" class="divide-y divide-muted">
              <div
                v-for="item in visibleCapabilities"
                :key="item.action"
                class="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-muted/30 transition-colors"
                :class="{ 'opacity-60': !item.available }"
              >
                <div class="min-w-0 space-y-1">
                  <div class="flex items-center gap-2">
                    <code class="text-xs font-bold text-label font-mono">{{ item.action }}</code>
                    <B24Badge
                      :label="riskLabels[item.risk] || item.risk"
                      :color="item.risk === 'high' || item.risk === 'critical' ? 'air-primary-alert' : item.risk === 'medium' ? 'air-primary-warning' : 'air-primary-success'"
                      size="xs"
                    />
                  </div>
                  <p class="text-xs text-description">
                    {{ summaryTranslations[item.summary] || item.summary || categoryLabels[item.category] || "Системное действие" }}
                  </p>
                  <p v-if="item.reason" class="text-[11px] text-[var(--ui-color-design-filled-amber)]">
                    Недоступно: {{ item.reason }}
                  </p>
                </div>

                <div class="flex items-center gap-3 shrink-0 self-end sm:self-center">
                  <B24Badge
                    :label="item.available ? 'Доступно' : 'Недоступно'"
                    :color="item.available ? 'air-primary-success' : 'air-secondary-no-accent'"
                    size="xs"
                  />
                  <B24Button
                    label="Открыть"
                    color="air-primary"
                    variant="outline"
                    size="xs"
                    :disabled="!item.available"
                    @click="openAction(item)"
                  />
                </div>
              </div>
            </div>

            <div v-else class="p-8 text-center text-sm text-muted">
              Действия по указанным критериям не найдены
            </div>
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
  </div>
</template>
