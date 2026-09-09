<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from "vue";
import { api } from "../api/client";
import DownloadIcon from "@bitrix24/b24icons-vue/outline/DownloadIcon";
import RefreshIcon from "@bitrix24/b24icons-vue/outline/RefreshIcon";

const props = defineProps({
  server: {
    type: Object,
    required: true,
  },
});

const toast = useToast();

function toLocalDatetimeString(date) {
  const d = new Date(date);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

const services = ref([]);
const service = ref("");
const source = ref("journal");
const dateFrom = ref(toLocalDatetimeString(Date.now() - 3600000 * 24));
const dateTo = ref(toLocalDatetimeString(Date.now()));
const filePath = ref("");
const grep = ref("");
const limit = ref(5000);
const lines = ref([]);
const total = ref(0);
const truncated = ref(false);
const sourceUsed = ref("");
const loading = ref(false);
const loaded = ref(false);
const autoRefresh = ref(false);
let autoRefreshTimer = null;

const limitOptions = [
  { label: "100 строк", value: 100 },
  { label: "500 строк", value: 500 },
  { label: "1 000 строк", value: 1000 },
  { label: "5 000 строк", value: 5000 },
  { label: "10 000 строк", value: 10000 },
];

async function loadServices() {
  if (!props.server?.id) return;
  try {
    services.value = await api.logServices(props.server.id);
    if (services.value.length > 0) {
      const existing = services.value.find((s) => s.id === service.value);
      if (!existing) {
        service.value = services.value[0].id;
      }
    }
  } catch (err) {
    toast.add({
      title: "Ошибка загрузки сервисов",
      description: err.message,
      color: "air-primary-alert",
    });
  }
}

onMounted(() => {
  loadServices();
});

watch(
  () => props.server?.id,
  () => {
    loadServices();
  }
);

onUnmounted(() => {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer);
  }
});

const selectedService = computed(() =>
  services.value.find((s) => s.id === service.value)
);

const serviceOptions = computed(() =>
  services.value.map((s) => {
    let label = s.name;
    if (s.active === true) {
      label += " (активен)";
    } else if (s.active === false) {
      label += " (неактивен)";
    }
    return { label, value: s.id };
  })
);

const sourceOptions = computed(() => {
  const opts = [];
  if (selectedService.value?.journal_unit) {
    opts.push({ label: "journalctl", value: "journal" });
  }
  if (selectedService.value?.files?.length > 0 || service.value === "custom") {
    opts.push({ label: "Файл лога", value: "file" });
  }
  if (opts.length === 0) {
    opts.push({ label: "Файл лога", value: "file" });
  }
  return opts;
});

const fileOptions = computed(() =>
  (selectedService.value?.files || []).map((f) => ({ label: f, value: f }))
);

watch(selectedService, (s) => {
  if (!s) return;
  if (s.files && s.files.length > 0) {
    filePath.value = s.files[0];
  } else if (s.id !== "custom") {
    filePath.value = "";
  }
  if (s.journal_unit) {
    source.value = "journal";
  } else {
    source.value = "file";
  }
});

watch(autoRefresh, (enabled) => {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer);
    autoRefreshTimer = null;
  }
  if (enabled) {
    autoRefreshTimer = setInterval(() => {
      if (!loading.value && service.value) {
        fetchLogs(true);
      }
    }, 5000);
  }
});

async function fetchLogs(silent = false) {
  if (!service.value) {
    if (!silent) {
      toast.add({
        title: "Выберите сервис",
        color: "air-primary-warning",
      });
    }
    return;
  }

  if (source.value === "file" && service.value === "custom" && !filePath.value) {
    if (!silent) {
      toast.add({
        title: "Укажите путь к файлу лога",
        color: "air-primary-warning",
      });
    }
    return;
  }

  if (!silent) {
    loading.value = true;
  }
  try {
    const result = await api.logs(props.server.id, {
      service: service.value,
      source: source.value,
      date_from: source.value === "journal" ? new Date(dateFrom.value).toISOString() : null,
      date_to: source.value === "journal" ? new Date(dateTo.value).toISOString() : null,
      file_path: source.value === "file" ? filePath.value : null,
      grep: grep.value || null,
      limit: Number(limit.value) || 5000,
    });
    lines.value = result.lines || [];
    total.value = result.total || 0;
    truncated.value = result.truncated || false;
    sourceUsed.value = result.source_used || source.value;
    loaded.value = true;
  } catch (err) {
    if (!silent) {
      toast.add({
        title: "Ошибка получения логов",
        description: err.message,
        color: "air-primary-alert",
      });
    }
  } finally {
    if (!silent) {
      loading.value = false;
    }
  }
}

function downloadLogs() {
  if (!lines.value.length) return;
  const blob = new Blob([lines.value.join("\n")], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${props.server?.name || "server"}_${service.value}_${new Date().toISOString().slice(0, 10)}.log`;
  a.click();
  URL.revokeObjectURL(url);
}
</script>

<template>
  <div class="space-y-4">
    <!-- Controls Bar -->
    <div class="p-4 rounded-xl bg-elevated/50 border border-muted space-y-4">
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- Service -->
        <B24FormField label="Сервис / Источник" required>
          <B24Select
            v-model="service"
            :items="serviceOptions"
            placeholder="Выберите сервис"
            class="w-full"
          />
        </B24FormField>

        <!-- Source -->
        <B24FormField label="Режим">
          <B24Select
            v-model="source"
            :items="sourceOptions"
            class="w-full"
          />
        </B24FormField>

        <!-- Date From -->
        <B24FormField label="С даты" :description="source === 'file' ? 'Только для journalctl' : undefined">
          <B24Input
            v-model="dateFrom"
            type="datetime-local"
            :disabled="source === 'file'"
            class="w-full"
          />
        </B24FormField>

        <!-- Date To -->
        <B24FormField label="По дату" :description="source === 'file' ? 'Только для journalctl' : undefined">
          <B24Input
            v-model="dateTo"
            type="datetime-local"
            :disabled="source === 'file'"
            class="w-full"
          />
        </B24FormField>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-12 gap-4 items-end">
        <!-- Log File (if file source) -->
        <div v-if="source === 'file'" class="sm:col-span-5">
          <B24FormField label="Файл лога" required>
            <B24Input
              v-if="service === 'custom'"
              v-model="filePath"
              placeholder="/var/log/... или /opt/webdir/logs/..."
              class="w-full font-mono text-xs"
              @keyup.enter="fetchLogs(false)"
            />
            <B24Select
              v-else-if="fileOptions.length > 0"
              v-model="filePath"
              :items="fileOptions"
              class="w-full font-mono text-xs"
            />
            <div v-else class="text-xs text-muted py-2">
              У сервиса нет стандартных файлов логов
            </div>
          </B24FormField>
        </div>

        <!-- Grep Pattern -->
        <div :class="source === 'file' ? 'sm:col-span-4' : 'sm:col-span-8'">
          <B24FormField label="Grep фильтр (regex / подстрока)">
            <B24Input
              v-model="grep"
              placeholder="Например: error, 404, bxcv.ru..."
              class="w-full font-mono text-xs"
              @keyup.enter="fetchLogs(false)"
            />
          </B24FormField>
        </div>

        <!-- Limit -->
        <div class="sm:col-span-3">
          <B24FormField label="Количество строк">
            <B24Select
              v-model="limit"
              :items="limitOptions"
              class="w-full text-xs"
            />
          </B24FormField>
        </div>

        <!-- Action Buttons & Auto refresh -->
        <div class="sm:col-span-12 flex items-center justify-between pt-2 border-t border-muted/30 flex-wrap gap-3">
          <div class="flex items-center gap-3">
            <label class="flex items-center gap-2 cursor-pointer text-xs select-none">
              <input
                v-model="autoRefresh"
                type="checkbox"
                class="rounded border-muted text-primary focus:ring-primary h-4 w-4"
              />
              <span :class="autoRefresh ? 'text-primary font-medium' : 'text-muted'">Авто-обновление (каждые 5 сек)</span>
            </label>
          </div>

          <div class="flex items-center gap-2 flex-wrap">
            <B24Button
              label="Загрузить логи"
              :icon="RefreshIcon"
              color="air-primary"
              :loading="loading"
              @click="fetchLogs(false)"
            />
            <B24Button
              v-if="loaded && lines.length > 0"
              label="Скачать"
              :icon="DownloadIcon"
              color="air-secondary-no-accent"
              variant="outline"
              @click="downloadLogs"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Info bar -->
    <div v-if="loaded" class="flex items-center justify-between px-2 text-xs text-muted">
      <span>Найдено строк: <b class="text-label">{{ total }}</b></span>
      <span v-if="truncated" class="text-[var(--ui-color-design-filled-amber)]">
        (Вывод ограничен последними {{ limit }} строками)
      </span>
      <span>Источник: <code class="font-mono text-xs">{{ sourceUsed }}</code></span>
    </div>

    <!-- Terminal Output -->
    <div class="rounded-xl border border-muted bg-elevated/80 overflow-hidden shadow-inner min-h-[320px]">
      <div v-if="loading" class="p-8 text-center text-sm text-muted">
        Загрузка журнала событий…
      </div>

      <div v-else-if="loaded && lines.length > 0" class="p-4 max-h-[560px] overflow-auto">
        <pre class="terminal-output text-xs font-mono text-description leading-relaxed whitespace-pre-wrap break-all select-all">{{ lines.join('\n') }}</pre>
      </div>

      <div v-else-if="loaded" class="p-12 text-center text-sm text-muted">
        Записи в журнале за указанный период или по фильтру не найдены
      </div>

      <div v-else class="p-12 text-center text-sm text-muted">
        Выберите сервис, режим и нажмите «Загрузить логи»
      </div>
    </div>
  </div>
</template>
