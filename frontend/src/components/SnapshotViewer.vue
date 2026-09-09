<script setup>
import { ref, computed } from "vue";
import EarthIcon from "@bitrix24/b24icons-vue/outline/EarthIcon";
import StorageIcon from "@bitrix24/b24icons-vue/outline/StorageIcon";
import TaskIcon from "@bitrix24/b24icons-vue/outline/TaskIcon";
import CloudIcon from "@bitrix24/b24icons-vue/outline/CloudIcon";
import DeveloperResourcesIcon from "@bitrix24/b24icons-vue/outline/DeveloperResourcesIcon";
import CopyIcon from "@bitrix24/b24icons-vue/outline/CopyIcon";
import DownloadIcon from "@bitrix24/b24icons-vue/outline/DownloadIcon";
import RefreshIcon from "@bitrix24/b24icons-vue/outline/RefreshIcon";
import SearchIcon from "@bitrix24/b24icons-vue/outline/SearchIcon";
import AlertIcon from "@bitrix24/b24icons-vue/outline/AlertIcon";
import CircleCheckIcon from "@bitrix24/b24icons-vue/outline/CircleCheckIcon";
import CheckLIcon from "@bitrix24/b24icons-vue/outline/CheckLIcon";
import FolderIcon from "@bitrix24/b24icons-vue/outline/FolderIcon";
import FileIcon from "@bitrix24/b24icons-vue/outline/FileIcon";

const props = defineProps({
  snapshot: {
    type: Object,
    default: null,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  server: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(["refresh"]);
const toast = useToast();

const viewMode = ref("visual"); // 'visual' | 'json'
const activeCategory = ref("all");
const searchQuery = ref("");
const expandedSites = ref({});
const copied = ref(false);
let copyTimer = null;

const actionTitles = {
  "site.create": "Создание сайта",
  "site.create_kernel": "Создание сайта с ядром",
  "site.create_external_kernel": "Создание сайта с внешним ядром",
  "site.create_link": "Создание сайта-ссылки",
  "site.delete": "Удаление сайта",
  "site.backup": "Резервное копирование сайта",
  "site.backup_enable": "Включение автобэкапа",
  "site.backup_disable": "Отключение автобэкапа",
  "site.email": "Настройка SMTP почты",
  "site.https_enable": "Включение HTTPS",
  "site.https_disable": "Отключение HTTPS",
  "site.cron_enable": "Включение Cron",
  "site.cron_disable": "Отключение Cron",
  "site.composite_enable": "Включение Композита",
  "site.composite_disable": "Отключение Композита",
  "pool.create": "Создание пула хостов",
  "pool.delete": "Удаление пула хостов",
  "host.add": "Добавление хоста в пул",
  "host.delete": "Удаление хоста из пула",
  "web.php.configure": "Настройка версии PHP",
  "mysql.root_password": "Смена пароля root MySQL",
  "mysql.slave": "Настройка репликации MySQL",
};

const roleLabels = {
  web: "Веб-сервер",
  mysql: "База данных",
  push: "Push-сервер",
  sphinx: "Sphinx поиск",
  memcached: "Memcached",
  monitoring: "Мониторинг",
};

// Normalize Sites
const normalizedSites = computed(() => {
  if (!props.snapshot) return [];
  const raw =
    props.snapshot.sites?.data?.params ??
    props.snapshot.sites?.data ??
    props.snapshot.sites?.params ??
    props.snapshot.sites;

  if (Array.isArray(raw)) {
    return raw.map((item, idx) => ({
      SiteName: item.SiteName || item.site || item.name || `site_${idx + 1}`,
      ServerName: item.ServerName || item.server_name || item.domain || "",
      DocumentRoot: item.DocumentRoot || item.document_root || item.root || "",
      DBType: item.DBType || item.db_type || "mysql",
      DBName: item.DBName || item.db_name || "",
      DBLogin: item.DBLogin || item.db_login || item.db_user || "",
      HTTPS: item.HTTPS === "enable" || item.https === true || item.HTTPS === true,
      Charset: item.Charset || item.charset || "utf-8",
      CronTask: item.CronTask === "enable" || item.cron === true || item.CronTask === true,
      CompositeStatus: item.CompositeStatus === "enable" || item.composite === true || item.CompositeStatus === true,
      SiteStatus: item.SiteStatus || item.status || "finished",
      NginxHTTPConfig: item.NginxHTTPConfig || item.nginx_conf || "",
      ApacheConf: item.ApacheConf || item.apache_conf || "",
      error: item.error || 0,
      message: item.message || "",
      raw: item,
    }));
  }

  if (raw && typeof raw === "object") {
    return Object.entries(raw).map(([key, val]) => {
      const item = typeof val === "object" ? val : { value: val };
      return {
        SiteName: item.SiteName || key,
        ServerName: item.ServerName || item.domain || "",
        DocumentRoot: item.DocumentRoot || item.root || "",
        DBType: item.DBType || "mysql",
        DBName: item.DBName || "",
        DBLogin: item.DBLogin || "",
        HTTPS: item.HTTPS === "enable" || item.https === true,
        Charset: item.Charset || "utf-8",
        CronTask: item.CronTask === "enable" || item.cron === true,
        CompositeStatus: item.CompositeStatus === "enable" || item.composite === true,
        SiteStatus: item.SiteStatus || item.status || "finished",
        NginxHTTPConfig: item.NginxHTTPConfig || "",
        ApacheConf: item.ApacheConf || "",
        error: item.error || 0,
        message: item.message || "",
        raw: item,
      };
    });
  }

  return [];
});

// Normalize Pool
const normalizedPool = computed(() => {
  if (!props.snapshot) return { configured: false, hosts: [], status: "none", error: null };
  const poolSec = props.snapshot.pool;
  if (!poolSec) return { configured: false, hosts: [], status: "none", error: null };

  if (poolSec.error) {
    return { configured: false, hosts: [], status: "error", error: poolSec.error };
  }

  const raw =
    poolSec.data?.params ??
    poolSec.data?.hosts ??
    poolSec.data ??
    poolSec.params ??
    poolSec;

  let hosts = [];
  if (Array.isArray(raw)) {
    hosts = raw.map((h) => {
      if (typeof h === "string") {
        return { hostname: h, ip: "", roles: ["web"], status: "online", raw: h };
      }
      return {
        hostname: h.hostname || h.host || h.name || "unknown",
        ip: h.ip || h.address || "",
        roles: Array.isArray(h.roles) ? h.roles : (h.roles ? [h.roles] : []),
        status: h.status || "online",
        raw: h,
      };
    });
  } else if (raw && typeof raw === "object") {
    if (Array.isArray(raw.hosts)) {
      hosts = raw.hosts.map((h) => ({
        hostname: typeof h === "string" ? h : (h.hostname || h.host || "unknown"),
        ip: h.ip || "",
        roles: Array.isArray(h.roles) ? h.roles : [],
        status: h.status || "online",
        raw: h,
      }));
    } else if (Object.keys(raw).length > 0 && !raw.status) {
      hosts = Object.entries(raw).map(([k, v]) => ({
        hostname: k,
        ip: v?.ip || "",
        roles: Array.isArray(v?.roles) ? v.roles : [],
        status: v?.status || "online",
        raw: v,
      }));
    }
  }

  const status = poolSec.data?.status || (hosts.length > 0 ? "finished" : "not_configured");
  const configured = hosts.length > 0 && status !== "error";
  return {
    configured,
    status,
    hosts,
    error: poolSec.exit_status && poolSec.exit_status !== 0 ? (poolSec.stderr || poolSec.data?.message) : null,
    raw: poolSec,
  };
});

// Normalize Tasks
const normalizedTasks = computed(() => {
  if (!props.snapshot) return [];
  const raw =
    props.snapshot.tasks?.data?.params ??
    props.snapshot.tasks?.data ??
    props.snapshot.tasks?.params ??
    props.snapshot.tasks;

  if (Array.isArray(raw)) {
    return raw.map((item, idx) => ({
      id: item.id || item.task_id || `task_${idx + 1}`,
      pid: item.pid || null,
      action: item.action || item.cmd || item.name || "Фоновая задача",
      actionDisplay: actionTitles[item.action] || item.action || "Фоновая задача",
      status: item.status || "finished",
      percent: typeof item.percent === "number" ? item.percent : (item.status === "finished" ? 100 : null),
      errors: item.errors || item.error || 0,
      message: item.message || "",
      raw: item,
    }));
  }
  return [];
});

// Normalize MySQL
const normalizedMysql = computed(() => {
  if (!props.snapshot) return null;
  const mysqlSec = props.snapshot.mysql;
  if (!mysqlSec) return null;

  if (mysqlSec.error || (mysqlSec.exit_status && mysqlSec.exit_status !== 0)) {
    return {
      available: false,
      error: mysqlSec.error || mysqlSec.stderr || "Служба MySQL недоступна",
      raw: mysqlSec,
    };
  }

  const raw =
    mysqlSec.data?.params ??
    mysqlSec.data ??
    mysqlSec.params ??
    mysqlSec;

  if (raw && typeof raw === "object") {
    return {
      available: true,
      version: raw.version || raw.ServerVersion || "MySQL / Percona",
      role: raw.role || (raw.slave ? "Slave" : "Master"),
      replication: raw.replication || (raw.slave_status ? "Активна" : "Одиночный сервер"),
      databases: Array.isArray(raw.databases) ? raw.databases : (raw.dbs || []),
      connections: raw.connections ?? null,
      max_connections: raw.max_connections ?? null,
      status: raw.status || "active",
      raw,
    };
  }
  return null;
});

// Normalize Services (Memcached, Sphinx, Monitoring, Network, etc.)
const normalizedServices = computed(() => {
  if (!props.snapshot) return [];
  const list = [];

  // Memcached
  if (props.snapshot.memcached) {
    const data = props.snapshot.memcached.data?.params ?? props.snapshot.memcached.data;
    const items = Array.isArray(data) ? data : (data ? [data] : []);
    list.push({
      id: "memcached",
      title: "Memcached",
      type: "Кэширование данных",
      status: props.snapshot.memcached.exit_status === 0 ? "active" : "inactive",
      items,
      raw: props.snapshot.memcached,
      error: props.snapshot.memcached.error || (props.snapshot.memcached.exit_status !== 0 ? props.snapshot.memcached.stderr : null),
    });
  }

  // Sphinx
  if (props.snapshot.sphinx) {
    const data = props.snapshot.sphinx.data?.params ?? props.snapshot.sphinx.data;
    list.push({
      id: "sphinx",
      title: "Sphinx Search",
      type: "Полнотекстовый поиск",
      status: props.snapshot.sphinx.exit_status === 0 ? "active" : "inactive",
      data: typeof data === "object" ? data : null,
      raw: props.snapshot.sphinx,
      error: props.snapshot.sphinx.error || (props.snapshot.sphinx.exit_status !== 0 ? props.snapshot.sphinx.stderr : null),
    });
  }

  // Monitoring
  if (props.snapshot.monitoring) {
    const data = props.snapshot.monitoring.data?.params ?? props.snapshot.monitoring.data;
    list.push({
      id: "monitoring",
      title: "Мониторинг BitrixVM",
      type: "Телеметрия и метрики",
      status: props.snapshot.monitoring.exit_status === 0 ? "active" : "inactive",
      data: typeof data === "object" ? data : null,
      raw: props.snapshot.monitoring,
      error: props.snapshot.monitoring.error || (props.snapshot.monitoring.exit_status !== 0 ? props.snapshot.monitoring.stderr : null),
    });
  }

  // Network
  if (props.snapshot.network) {
    const data = props.snapshot.network.data?.params ?? props.snapshot.network.data;
    const items = Array.isArray(data) ? data : (data ? [data] : []);
    list.push({
      id: "network",
      title: "Сетевые интерфейсы",
      type: "Сеть и маршрутизация",
      status: props.snapshot.network.exit_status === 0 ? "active" : "inactive",
      items,
      raw: props.snapshot.network,
      error: props.snapshot.network.error || (props.snapshot.network.exit_status !== 0 ? props.snapshot.network.stderr : null),
    });
  }

  // Generic services (if present at top level)
  if (props.snapshot.services && typeof props.snapshot.services === "object") {
    list.push({
      id: "services_map",
      title: "Системные демоны",
      type: "Службы сервера",
      status: "active",
      data: props.snapshot.services,
      raw: props.snapshot.services,
      error: null,
    });
  }

  return list;
});

// Environment / Host info
const serverInfo = computed(() => {
  return {
    hostname: props.snapshot?.hostname || props.server?.name || "Сервер",
    platform: props.snapshot?.platform || "Linux",
    bitrixenv: props.snapshot?.bitrixenv || "BitrixEnv 9.x",
    address: props.server?.address || "",
    port: props.server?.port || 22,
  };
});

// Filters
const query = computed(() => searchQuery.value.trim().toLowerCase());

const filteredSites = computed(() => {
  if (!query.value) return normalizedSites.value;
  return normalizedSites.value.filter((s) => {
    return (
      s.SiteName.toLowerCase().includes(query.value) ||
      s.ServerName.toLowerCase().includes(query.value) ||
      s.DocumentRoot.toLowerCase().includes(query.value) ||
      s.DBName.toLowerCase().includes(query.value)
    );
  });
});

const filteredHosts = computed(() => {
  if (!query.value) return normalizedPool.value.hosts;
  return normalizedPool.value.hosts.filter((h) => {
    return (
      h.hostname.toLowerCase().includes(query.value) ||
      h.ip.toLowerCase().includes(query.value) ||
      h.roles.some((r) => r.toLowerCase().includes(query.value))
    );
  });
});

const filteredTasks = computed(() => {
  if (!query.value) return normalizedTasks.value;
  return normalizedTasks.value.filter((t) => {
    return (
      t.id.toLowerCase().includes(query.value) ||
      t.action.toLowerCase().includes(query.value) ||
      t.actionDisplay.toLowerCase().includes(query.value) ||
      t.message.toLowerCase().includes(query.value)
    );
  });
});

const filteredServices = computed(() => {
  if (!query.value) return normalizedServices.value;
  return normalizedServices.value.filter((srv) => {
    return (
      srv.title.toLowerCase().includes(query.value) ||
      srv.type.toLowerCase().includes(query.value)
    );
  });
});

const formattedJson = computed(() => {
  if (!props.snapshot) return "";
  return JSON.stringify(props.snapshot, null, 2);
});

const jsonSizeKb = computed(() => {
  if (!formattedJson.value) return "0 KB";
  const bytes = new Blob([formattedJson.value]).size;
  return `${(bytes / 1024).toFixed(1)} KB`;
});

function toggleSiteJson(siteName) {
  expandedSites.value[siteName] = !expandedSites.value[siteName];
}

async function copyJson() {
  if (!formattedJson.value) return;
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(formattedJson.value);
    } else {
      const ta = document.createElement("textarea");
      ta.value = formattedJson.value;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    copied.value = true;
    if (copyTimer) clearTimeout(copyTimer);
    copyTimer = setTimeout(() => {
      copied.value = false;
    }, 2000);
    toast.add({
      title: "JSON скопирован в буфер обмена",
      color: "air-primary-success",
    });
  } catch (err) {
    toast.add({
      title: "Ошибка копирования",
      description: err.message,
      color: "air-primary-alert",
    });
  }
}

function downloadJson() {
  if (!formattedJson.value) return;
  const blob = new Blob([formattedJson.value], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const sName = props.server?.name || "bitrixvm";
  const dateStr = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
  a.download = `${sName}_snapshot_${dateStr}.json`;
  a.click();
  URL.revokeObjectURL(url);
}
</script>

<template>
  <div class="space-y-5">
    <!-- Loading State -->
    <div
      v-if="loading"
      class="p-12 rounded-xl bg-elevated/40 border border-muted flex flex-col items-center justify-center text-center space-y-4"
    >
      <div class="w-10 h-10 border-2 border-air-primary border-t-transparent rounded-full animate-spin" />
      <div>
        <h4 class="font-bold text-label text-base">Сбор диагностического снимка…</h4>
        <p class="text-xs text-muted mt-1 max-w-md">
          Опрос системных компонентов BitrixVM: сайты, процессы, пул серверов, MySQL, кэш и сеть.
        </p>
      </div>
    </div>

    <!-- Empty State -->
    <div
      v-else-if="!snapshot"
      class="p-12 rounded-xl bg-elevated/40 border border-muted flex flex-col items-center justify-center text-center space-y-4"
    >
      <div class="p-4 rounded-2xl bg-muted/20 text-muted">
        <FileIcon class="w-10 h-10" />
      </div>
      <div>
        <h4 class="font-bold text-label text-base">Диагностический снимок не загружен</h4>
        <p class="text-xs text-muted mt-1 max-w-md">
          Снимок собирает актуальное состояние пула хостов, сайтов Bitrix, фоновых задач и системных сервисов.
        </p>
      </div>
      <B24Button
        label="Собрать снимок состояния"
        color="air-primary"
        variant="solid"
        size="md"
        :icon="RefreshIcon"
        @click="$emit('refresh')"
      />
    </div>

    <!-- Snapshot Loaded State -->
    <div v-else class="space-y-5">
      <!-- Top KPIs Bar -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <!-- KPI 1: Sites -->
        <div
          class="p-4 rounded-xl bg-elevated/60 border border-muted hover:border-air-primary/40 transition-colors cursor-pointer"
          @click="activeCategory = 'sites'"
        >
          <div class="flex items-center justify-between text-xs text-muted mb-1">
            <span class="flex items-center gap-1.5 font-medium">
              <EarthIcon class="w-4 h-4 text-air-primary" />
              Сайты Bitrix
            </span>
            <B24Badge
              :label="normalizedSites.length ? `${normalizedSites.length} шт` : 'Нет'"
              :color="normalizedSites.length ? 'air-primary-success' : 'neutral'"
              size="xs"
            />
          </div>
          <div class="text-xl font-bold text-label">
            {{ normalizedSites.length }}
          </div>
          <div class="text-xs text-description mt-0.5 truncate">
            {{ normalizedSites.filter(s => s.SiteStatus === 'finished').length }} активны
          </div>
        </div>

        <!-- KPI 2: Pool -->
        <div
          class="p-4 rounded-xl bg-elevated/60 border border-muted hover:border-air-primary/40 transition-colors cursor-pointer"
          @click="activeCategory = 'pool'"
        >
          <div class="flex items-center justify-between text-xs text-muted mb-1">
            <span class="flex items-center gap-1.5 font-medium">
              <CloudIcon class="w-4 h-4 text-air-primary" />
              Пул хостов
            </span>
            <B24Badge
              :label="normalizedPool.configured ? 'Активен' : 'Одиночный'"
              :color="normalizedPool.configured ? 'air-primary-success' : 'neutral'"
              size="xs"
            />
          </div>
          <div class="text-xl font-bold text-label">
            {{ normalizedPool.hosts.length || 1 }}
          </div>
          <div class="text-xs text-description mt-0.5 truncate">
            {{ normalizedPool.configured ? 'Кластер настроен' : 'Локальный режим' }}
          </div>
        </div>

        <!-- KPI 3: Tasks -->
        <div
          class="p-4 rounded-xl bg-elevated/60 border border-muted hover:border-air-primary/40 transition-colors cursor-pointer"
          @click="activeCategory = 'tasks'"
        >
          <div class="flex items-center justify-between text-xs text-muted mb-1">
            <span class="flex items-center gap-1.5 font-medium">
              <TaskIcon class="w-4 h-4 text-air-primary" />
              Фоновые задачи
            </span>
            <B24Badge
              :label="normalizedTasks.filter(t => t.status === 'running').length ? 'В работе' : 'Спокойно'"
              :color="normalizedTasks.filter(t => t.status === 'running').length ? 'air-primary-warning' : 'air-primary-success'"
              size="xs"
            />
          </div>
          <div class="text-xl font-bold text-label">
            {{ normalizedTasks.length }}
          </div>
          <div class="text-xs text-description mt-0.5 truncate">
            {{ normalizedTasks.filter(t => t.status === 'running').length ? 'Есть активные операции' : 'Все задачи завершены' }}
          </div>
        </div>

        <!-- KPI 4: MySQL -->
        <div
          class="p-4 rounded-xl bg-elevated/60 border border-muted hover:border-air-primary/40 transition-colors cursor-pointer"
          @click="activeCategory = 'mysql'"
        >
          <div class="flex items-center justify-between text-xs text-muted mb-1">
            <span class="flex items-center gap-1.5 font-medium">
              <StorageIcon class="w-4 h-4 text-air-primary" />
              База данных
            </span>
            <B24Badge
              :label="normalizedMysql?.available ? (normalizedMysql.role || 'MySQL') : 'Проверка'"
              :color="normalizedMysql?.available ? 'air-primary-success' : 'neutral'"
              size="xs"
            />
          </div>
          <div class="text-xl font-bold text-label truncate">
            {{ normalizedMysql?.role || 'Master' }}
          </div>
          <div class="text-xs text-description mt-0.5 truncate">
            {{ normalizedMysql?.databases?.length ? `${normalizedMysql.databases.length} БД` : 'Активна' }}
          </div>
        </div>
      </div>

      <!-- Controls Toolbar -->
      <div class="p-4 rounded-xl bg-elevated/40 border border-muted flex flex-col md:flex-row md:items-center justify-between gap-3">
        <!-- View Toggle & Search -->
        <div class="flex flex-wrap items-center gap-2 flex-1">
          <!-- View switcher segmented buttons -->
          <div class="inline-flex rounded-lg border border-muted p-0.5 bg-elevated">
            <button
              type="button"
              class="px-3 py-1.5 text-xs font-medium rounded-md transition-colors flex items-center gap-1.5"
              :class="viewMode === 'visual' ? 'bg-air-primary text-white shadow-sm' : 'text-muted hover:text-label'"
              @click="viewMode = 'visual'"
            >
              <DeveloperResourcesIcon class="w-3.5 h-3.5" />
              Наглядный вид
            </button>
            <button
              type="button"
              class="px-3 py-1.5 text-xs font-medium rounded-md transition-colors flex items-center gap-1.5"
              :class="viewMode === 'json' ? 'bg-air-primary text-white shadow-sm' : 'text-muted hover:text-label'"
              @click="viewMode = 'json'"
            >
              <FileIcon class="w-3.5 h-3.5" />
              JSON (сырой)
            </button>
          </div>

          <!-- Search Input -->
          <div class="w-full sm:w-64">
            <B24Input
              v-model="searchQuery"
              :icon="SearchIcon"
              placeholder="Фильтр по сайтам, хостам, БД..."
              size="sm"
            />
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex items-center gap-2 self-end md:self-center">
          <B24Button
            :label="copied ? 'Скопировано!' : 'Копировать JSON'"
            :icon="copied ? CheckLIcon : CopyIcon"
            :color="copied ? 'air-primary-success' : 'air-secondary-no-accent'"
            variant="outline"
            size="sm"
            @click="copyJson"
          />
          <B24Button
            label="Скачать"
            :icon="DownloadIcon"
            color="air-secondary-no-accent"
            variant="outline"
            size="sm"
            @click="downloadJson"
          />
          <B24Button
            label="Обновить"
            :icon="RefreshIcon"
            color="air-primary"
            variant="soft"
            size="sm"
            :loading="loading"
            @click="$emit('refresh')"
          />
        </div>
      </div>

      <!-- VISUAL MODE -->
      <div v-if="viewMode === 'visual'" class="space-y-6">
        <!-- Category Navigation Pills -->
        <div class="flex items-center gap-2 border-b border-muted pb-3 overflow-x-auto text-xs">
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg font-medium transition-colors whitespace-nowrap"
            :class="activeCategory === 'all' ? 'bg-air-primary text-white' : 'text-muted hover:text-label hover:bg-elevated'"
            @click="activeCategory = 'all'"
          >
            Все компоненты
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap"
            :class="activeCategory === 'sites' ? 'bg-air-primary text-white' : 'text-muted hover:text-label hover:bg-elevated'"
            @click="activeCategory = 'sites'"
          >
            Сайты Bitrix
            <span class="px-1.5 py-0.2 rounded-full text-[10px] bg-black/20">{{ normalizedSites.length }}</span>
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap"
            :class="activeCategory === 'pool' ? 'bg-air-primary text-white' : 'text-muted hover:text-label hover:bg-elevated'"
            @click="activeCategory = 'pool'"
          >
            Пул хостов
            <span class="px-1.5 py-0.2 rounded-full text-[10px] bg-black/20">{{ normalizedPool.hosts.length || 1 }}</span>
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap"
            :class="activeCategory === 'tasks' ? 'bg-air-primary text-white' : 'text-muted hover:text-label hover:bg-elevated'"
            @click="activeCategory = 'tasks'"
          >
            Фоновые задачи
            <span class="px-1.5 py-0.2 rounded-full text-[10px] bg-black/20">{{ normalizedTasks.length }}</span>
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg font-medium transition-colors whitespace-nowrap"
            :class="activeCategory === 'mysql' ? 'bg-air-primary text-white' : 'text-muted hover:text-label hover:bg-elevated'"
            @click="activeCategory = 'mysql'"
          >
            База данных
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap"
            :class="activeCategory === 'services' ? 'bg-air-primary text-white' : 'text-muted hover:text-label hover:bg-elevated'"
            @click="activeCategory = 'services'"
          >
            Службы и сервисы
            <span class="px-1.5 py-0.2 rounded-full text-[10px] bg-black/20">{{ normalizedServices.length }}</span>
          </button>
        </div>

        <!-- 1. SITES SECTION -->
        <div v-if="activeCategory === 'all' || activeCategory === 'sites'" class="space-y-4">
          <div class="flex items-center justify-between">
            <h3 class="font-bold text-label text-base flex items-center gap-2">
              <EarthIcon class="w-5 h-5 text-air-primary" />
              Сайты Bitrix
              <span class="text-xs font-normal text-muted">({{ filteredSites.length }})</span>
            </h3>
          </div>

          <div v-if="filteredSites.length > 0" class="grid grid-cols-1 gap-4">
            <div
              v-for="site in filteredSites"
              :key="site.SiteName"
              class="rounded-xl border border-muted bg-elevated/40 p-5 space-y-4 hover:border-air-primary/40 transition-colors"
            >
              <!-- Site Card Header -->
              <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-muted">
                <div class="flex items-center gap-3">
                  <div class="p-2 rounded-lg bg-air-primary/10 text-air-primary">
                    <EarthIcon class="w-5 h-5" />
                  </div>
                  <div>
                    <div class="flex items-center gap-2">
                      <span class="font-bold text-label text-base">{{ site.SiteName }}</span>
                      <a
                        v-if="site.ServerName"
                        :href="`http://${site.ServerName}`"
                        target="_blank"
                        rel="noopener"
                        class="text-xs text-air-primary hover:underline font-mono"
                      >
                        {{ site.ServerName }} ↗
                      </a>
                    </div>
                    <div class="text-xs text-muted flex items-center gap-2 mt-0.5">
                      <FolderIcon class="w-3.5 h-3.5" />
                      <span class="font-mono truncate max-w-md">{{ site.DocumentRoot }}</span>
                    </div>
                  </div>
                </div>

                <div class="flex items-center gap-2 self-start sm:self-center">
                  <B24Badge
                    :label="site.SiteStatus === 'finished' ? 'Активен' : (site.SiteStatus === 'error' ? 'Ошибка' : site.SiteStatus)"
                    :color="site.SiteStatus === 'finished' ? 'air-primary-success' : (site.SiteStatus === 'error' ? 'air-primary-alert' : 'air-primary-warning')"
                    size="sm"
                  />
                  <B24Button
                    label="JSON"
                    color="air-secondary-no-accent"
                    variant="ghost"
                    size="xs"
                    @click="toggleSiteJson(site.SiteName)"
                  />
                </div>
              </div>

              <!-- Site Feature Badges -->
              <div class="flex flex-wrap items-center gap-2">
                <B24Badge
                  :label="site.HTTPS ? 'HTTPS: Вкл' : 'HTTPS: Выкл'"
                  :color="site.HTTPS ? 'air-primary-success' : 'neutral'"
                  size="xs"
                />
                <B24Badge
                  :label="site.CronTask ? 'Cron: Вкл' : 'Cron: Выкл'"
                  :color="site.CronTask ? 'air-primary' : 'neutral'"
                  size="xs"
                />
                <B24Badge
                  :label="site.CompositeStatus ? 'Композит: Вкл' : 'Композит: Выкл'"
                  :color="site.CompositeStatus ? 'air-primary' : 'neutral'"
                  size="xs"
                />
                <B24Badge
                  :label="`Кодировка: ${site.Charset}`"
                  color="neutral"
                  size="xs"
                />
                <B24Badge
                  :label="`БД: ${site.DBType}`"
                  color="neutral"
                  size="xs"
                />
              </div>

              <!-- Site Details Grid -->
              <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 p-3 rounded-lg bg-black/10 border border-muted/50 text-xs">
                <div>
                  <span class="text-muted block text-[11px]">База данных</span>
                  <span class="font-mono text-label font-medium block truncate mt-0.5" :title="site.DBName">
                    {{ site.DBName || '—' }}
                  </span>
                  <span class="text-muted text-[10px] block truncate">
                    логин: {{ site.DBLogin || '—' }}
                  </span>
                </div>

                <div>
                  <span class="text-muted block text-[11px]">Домен (ServerName)</span>
                  <span class="font-mono text-label block truncate mt-0.5" :title="site.ServerName">
                    {{ site.ServerName || 'Не указан' }}
                  </span>
                </div>

                <div>
                  <span class="text-muted block text-[11px]">Конфигурация Nginx</span>
                  <span class="font-mono text-label block truncate mt-0.5" :title="site.NginxHTTPConfig">
                    {{ site.NginxHTTPConfig ? site.NginxHTTPConfig.split('/').pop() : '—' }}
                  </span>
                </div>

                <div>
                  <span class="text-muted block text-[11px]">Конфигурация Apache</span>
                  <span class="font-mono text-label block truncate mt-0.5" :title="site.ApacheConf">
                    {{ site.ApacheConf ? site.ApacheConf.split('/').pop() : '—' }}
                  </span>
                </div>
              </div>

              <!-- Site Error / Alert if any -->
              <div
                v-if="site.message && site.error"
                class="p-3 rounded-lg bg-air-primary-alert/10 border border-air-primary-alert/30 text-xs flex items-start gap-2 text-air-primary-alert"
              >
                <AlertIcon class="w-4 h-4 mt-0.5 shrink-0" />
                <span>{{ site.message }}</span>
              </div>

              <!-- Collapsible Site Raw JSON -->
              <div v-if="expandedSites[site.SiteName]" class="mt-3">
                <div class="p-3 rounded-lg bg-black/40 border border-muted overflow-auto max-h-60">
                  <pre class="text-xs font-mono text-description whitespace-pre-wrap">{{ JSON.stringify(site.raw, null, 2) }}</pre>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="p-8 rounded-xl bg-elevated/30 border border-muted text-center text-xs text-muted">
            {{ searchQuery ? 'Сайты, соответствующие условиям поиска, не найдены' : 'Сайты Bitrix на данном сервере не сконфигурированы' }}
          </div>
        </div>

        <!-- 2. POOL HOSTS SECTION -->
        <div v-if="activeCategory === 'all' || activeCategory === 'pool'" class="space-y-4">
          <div class="flex items-center justify-between">
            <h3 class="font-bold text-label text-base flex items-center gap-2">
              <CloudIcon class="w-5 h-5 text-air-primary" />
              Пул серверов Bitrix
              <span class="text-xs font-normal text-muted">({{ filteredHosts.length }})</span>
            </h3>
            <B24Badge
              :label="normalizedPool.configured ? 'Кластер активен' : 'Одиночный сервер'"
              :color="normalizedPool.configured ? 'air-primary-success' : 'neutral'"
              size="sm"
            />
          </div>

          <div v-if="filteredHosts.length > 0" class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div
              v-for="host in filteredHosts"
              :key="host.hostname"
              class="rounded-xl border border-muted bg-elevated/40 p-4 space-y-3 hover:border-air-primary/40 transition-colors"
            >
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2.5">
                  <div class="p-2 rounded-lg bg-air-primary/10 text-air-primary">
                    <DeveloperResourcesIcon class="w-4 h-4" />
                  </div>
                  <div>
                    <span class="font-bold text-label text-sm block">{{ host.hostname }}</span>
                    <span class="font-mono text-xs text-muted block">{{ host.ip || 'Локальный IP' }}</span>
                  </div>
                </div>
                <B24Badge
                  :label="host.status === 'online' ? 'В сети' : host.status"
                  :color="host.status === 'online' ? 'air-primary-success' : 'neutral'"
                  size="xs"
                />
              </div>

              <!-- Roles Badges -->
              <div class="flex flex-wrap items-center gap-1.5 pt-1">
                <span class="text-[11px] text-muted mr-1">Роли хоста:</span>
                <B24Badge
                  v-for="role in host.roles"
                  :key="role"
                  :label="roleLabels[role] || role"
                  color="air-primary"
                  variant="subtle"
                  size="xs"
                />
                <span v-if="!host.roles?.length" class="text-xs text-muted">—</span>
              </div>
            </div>
          </div>

          <div
            v-else-if="!normalizedPool.configured"
            class="p-6 rounded-xl bg-elevated/30 border border-muted text-xs text-muted flex items-start gap-3"
          >
            <div class="p-2 rounded-lg bg-muted/20 text-muted shrink-0">
              <DeveloperResourcesIcon class="w-5 h-5" />
            </div>
            <div>
              <p class="font-medium text-label">Одиночный сервер (Stand-alone BitrixVM)</p>
              <p class="text-muted mt-0.5">
                Кластерный пул серверов не создан. Сервер выполняет все роли (веб-сервер, база данных, кэш) локально.
              </p>
            </div>
          </div>

          <div
            v-if="normalizedPool.error"
            class="p-4 rounded-xl bg-air-primary-alert/10 border border-air-primary-alert/30 text-xs text-air-primary-alert flex items-start gap-2"
          >
            <AlertIcon class="w-4 h-4 mt-0.5 shrink-0" />
            <span>{{ normalizedPool.error }}</span>
          </div>
        </div>

        <!-- 3. TASKS SECTION -->
        <div v-if="activeCategory === 'all' || activeCategory === 'tasks'" class="space-y-4">
          <div class="flex items-center justify-between">
            <h3 class="font-bold text-label text-base flex items-center gap-2">
              <TaskIcon class="w-5 h-5 text-air-primary" />
              Фоновые задачи BitrixVM
              <span class="text-xs font-normal text-muted">({{ filteredTasks.length }})</span>
            </h3>
          </div>

          <div v-if="filteredTasks.length > 0" class="space-y-3">
            <div
              v-for="task in filteredTasks"
              :key="task.id"
              class="rounded-xl border border-muted bg-elevated/40 p-4 space-y-3"
            >
              <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div class="flex items-center gap-2.5">
                  <div
                    class="w-2.5 h-2.5 rounded-full"
                    :class="task.status === 'running' ? 'bg-air-primary-warning animate-pulse' : (task.status === 'finished' ? 'bg-air-primary-success' : 'bg-air-primary-alert')"
                  />
                  <div>
                    <span class="font-bold text-label text-sm">{{ task.actionDisplay }}</span>
                    <span class="text-xs font-mono text-muted ml-2">ID: {{ task.id }}</span>
                    <span v-if="task.pid" class="text-xs font-mono text-muted ml-2">PID: {{ task.pid }}</span>
                  </div>
                </div>

                <B24Badge
                  :label="task.status === 'running' ? 'Выполняется' : (task.status === 'finished' ? 'Завершена' : task.status)"
                  :color="task.status === 'running' ? 'air-primary-warning' : (task.status === 'finished' ? 'air-primary-success' : 'air-primary-alert')"
                  size="xs"
                />
              </div>

              <!-- Progress bar if percentage available -->
              <div v-if="task.percent !== null" class="space-y-1">
                <div class="flex justify-between text-[11px] text-muted font-mono">
                  <span>Прогресс выполнения</span>
                  <span>{{ task.percent }}%</span>
                </div>
                <div class="w-full h-1.5 rounded-full bg-muted/20 overflow-hidden">
                  <div
                    class="h-full rounded-full transition-all duration-300"
                    :class="task.status === 'error' ? 'bg-air-primary-alert' : 'bg-air-primary'"
                    :style="{ width: `${task.percent}%` }"
                  />
                </div>
              </div>

              <div v-if="task.message" class="text-xs text-description bg-black/10 p-2.5 rounded-lg font-mono">
                {{ task.message }}
              </div>
            </div>
          </div>

          <div
            v-else
            class="p-6 rounded-xl bg-elevated/30 border border-muted text-xs text-muted flex items-center justify-center gap-2"
          >
            <CircleCheckIcon class="w-4 h-4 text-air-primary-success" />
            <span>Нет активных фоновых задач (все процессы завершены штатно)</span>
          </div>
        </div>

        <!-- 4. MYSQL SECTION -->
        <div v-if="activeCategory === 'all' || activeCategory === 'mysql'" class="space-y-4">
          <div class="flex items-center justify-between">
            <h3 class="font-bold text-label text-base flex items-center gap-2">
              <StorageIcon class="w-5 h-5 text-air-primary" />
              База данных MySQL
            </h3>
            <B24Badge
              v-if="normalizedMysql"
              :label="normalizedMysql.available ? 'Работает' : 'Ошибка'"
              :color="normalizedMysql.available ? 'air-primary-success' : 'air-primary-alert'"
              size="sm"
            />
          </div>

          <div
            v-if="normalizedMysql?.available"
            class="rounded-xl border border-muted bg-elevated/40 p-5 space-y-4"
          >
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
              <div>
                <span class="text-muted block text-[11px]">Версия сервера</span>
                <span class="font-mono text-label font-bold block mt-0.5 truncate" :title="normalizedMysql.version">
                  {{ normalizedMysql.version }}
                </span>
              </div>
              <div>
                <span class="text-muted block text-[11px]">Роль сервера</span>
                <span class="font-medium text-label block mt-0.5">
                  {{ normalizedMysql.role }}
                </span>
              </div>
              <div>
                <span class="text-muted block text-[11px]">Репликация</span>
                <span class="font-medium text-label block mt-0.5">
                  {{ normalizedMysql.replication }}
                </span>
              </div>
              <div>
                <span class="text-muted block text-[11px]">Активные соединения</span>
                <span class="font-mono text-label block mt-0.5">
                  {{ normalizedMysql.connections ?? '—' }} {{ normalizedMysql.max_connections ? `/ ${normalizedMysql.max_connections}` : '' }}
                </span>
              </div>
            </div>

            <!-- Databases List -->
            <div v-if="normalizedMysql.databases?.length" class="pt-3 border-t border-muted space-y-2">
              <span class="text-xs font-medium text-muted block">Обнаруженные базы данных ({{ normalizedMysql.databases.length }}):</span>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="db in normalizedMysql.databases"
                  :key="db"
                  class="px-2.5 py-1 rounded-md bg-black/20 border border-muted text-xs font-mono text-label"
                >
                  {{ db }}
                </span>
              </div>
            </div>
          </div>

          <div
            v-else-if="normalizedMysql?.error"
            class="p-4 rounded-xl bg-air-primary-alert/10 border border-air-primary-alert/30 text-xs text-air-primary-alert flex items-start gap-2"
          >
            <AlertIcon class="w-4 h-4 mt-0.5 shrink-0" />
            <span>{{ normalizedMysql.error }}</span>
          </div>

          <div v-else class="p-6 rounded-xl bg-elevated/30 border border-muted text-xs text-muted text-center">
            Информация о MySQL отсутствует в текущем снимке.
          </div>
        </div>

        <!-- 5. SERVICES & CACHE SECTION -->
        <div v-if="activeCategory === 'all' || activeCategory === 'services'" class="space-y-4">
          <div class="flex items-center justify-between">
            <h3 class="font-bold text-label text-base flex items-center gap-2">
              <DeveloperResourcesIcon class="w-5 h-5 text-air-primary" />
              Службы кэша, поиска и сети
              <span class="text-xs font-normal text-muted">({{ filteredServices.length }})</span>
            </h3>
          </div>

          <div v-if="filteredServices.length > 0" class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div
              v-for="srv in filteredServices"
              :key="srv.id"
              class="rounded-xl border border-muted bg-elevated/40 p-4 space-y-3"
            >
              <div class="flex items-center justify-between">
                <div>
                  <span class="font-bold text-label text-sm block">{{ srv.title }}</span>
                  <span class="text-xs text-muted block">{{ srv.type }}</span>
                </div>
                <B24Badge
                  :label="srv.status === 'active' ? 'Активна' : 'Неактивна'"
                  :color="srv.status === 'active' ? 'air-primary-success' : 'neutral'"
                  size="xs"
                />
              </div>

              <!-- Service Details List or Data -->
              <div v-if="srv.items?.length" class="space-y-1.5 text-xs font-mono bg-black/10 p-2.5 rounded-lg">
                <div v-for="(it, i) in srv.items" :key="i" class="truncate text-description">
                  <template v-if="typeof it === 'object'">
                    <span v-for="(val, key) in it" :key="key" class="mr-3">
                      <span class="text-muted">{{ key }}:</span> {{ val }}
                    </span>
                  </template>
                  <template v-else>
                    {{ it }}
                  </template>
                </div>
              </div>

              <div v-else-if="srv.data" class="text-xs font-mono bg-black/10 p-2.5 rounded-lg space-y-1 text-description">
                <div v-for="(val, key) in srv.data" :key="key" class="truncate">
                  <span class="text-muted">{{ key }}:</span> {{ val }}
                </div>
              </div>

              <div v-if="srv.error" class="text-xs text-air-primary-alert bg-air-primary-alert/10 p-2.5 rounded-lg">
                {{ srv.error }}
              </div>
            </div>
          </div>

          <div v-else class="p-6 rounded-xl bg-elevated/30 border border-muted text-xs text-muted text-center">
            Дополнительные службы не обнаружены в снимке.
          </div>
        </div>
      </div>

      <!-- JSON MODE (RAW) -->
      <div v-else-if="viewMode === 'json'" class="space-y-3">
        <div class="flex items-center justify-between text-xs text-muted px-1">
          <span class="font-mono">Размер данных: {{ jsonSizeKb }}</span>
          <span class="font-mono">JSON валиден</span>
        </div>

        <div class="p-4 rounded-xl bg-elevated border border-muted overflow-auto max-h-[600px] relative group">
          <pre class="terminal-output text-xs font-mono text-description whitespace-pre-wrap selection:bg-air-primary/30">{{ formattedJson }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>
