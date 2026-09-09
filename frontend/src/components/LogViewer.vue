<script setup>
import { ref, computed, watch, onMounted } from "vue";
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
const dateFrom = ref(toLocalDatetimeString(Date.now() - 3600000));
const dateTo = ref(toLocalDatetimeString(Date.now()));
const filePath = ref("");
const grep = ref("");
const lines = ref([]);
const total = ref(0);
const truncated = ref(false);
const loading = ref(false);
const loaded = ref(false);

onMounted(async () => {
  try {
    services.value = await api.logServices();
    if (services.value.length > 0 && !service.value) {
      service.value = services.value[0].id;
    }
  } catch (err) {
    toast.add({
      title: "Ошибка загрузки сервисов",
      description: err.message,
      color: "air-primary-alert",
    });
  }
});

const selectedService = computed(() =>
  services.value.find((s) => s.id === service.value)
);

const serviceOptions = computed(() =>
  services.value.map((s) => ({ label: s.name, value: s.id }))
);

const sourceOptions = computed(() => {
  const opts = [];
  if (selectedService.value?.journal_unit) {
    opts.push({ label: "journalctl", value: "journal" });
  }
  opts.push({ label: "Файл лога", value: "file" });
  return opts;
});

const fileOptions = computed(() =>
  (selectedService.value?.files || []).map((f) => ({ label: f, value: f }))
);

watch(selectedService, (s) => {
  if (s && s.files.length > 0) {
    filePath.value = s.files[0];
  } else {
    filePath.value = "";
  }
  if (s) {
    source.value = s.journal_unit ? "journal" : "file";
  }
});

async function fetchLogs() {
  if (!service.value) {
    toast.add({
      title: "Выберите сервис",
      color: "air-primary-warning",
    });
    return;
  }

  loading.value = true;
  loaded.value = false;
  try {
    const result = await api.logs(props.server.id, {
      service: service.value,
      source: source.value,
      date_from: new Date(dateFrom.value).toISOString(),
      date_to: new Date(dateTo.value).toISOString(),
      file_path: source.value === "file" ? filePath.value : null,
      grep: grep.value || null,
      limit: 5000,
    });
    lines.value = result.lines || [];
    total.value = result.total || 0;
    truncated.value = result.truncated || false;
    loaded.value = true;
  } catch (err) {
    toast.add({
      title: "Ошибка получения логов",
      description: err.message,
      color: "air-primary-alert",
    });
  } finally {
    loading.value = false;
  }
}

function downloadLogs() {
  if (!lines.value.length) return;
  const blob = new Blob([lines.value.join("\n")], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${props.server.name}_${service.value}_${new Date().toISOString().slice(0, 10)}.log`;
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
        <B24FormField label="Сервис" required>
          <B24Select
            v-model="service"
            :items="serviceOptions"
            placeholder="Выберите сервис"
            class="w-full"
          />
        </B24FormField>

        <!-- Source -->
        <B24FormField label="Источник">
          <B24Select
            v-model="source"
            :items="sourceOptions"
            class="w-full"
          />
        </B24FormField>

        <!-- Date From -->
        <B24FormField label="С даты">
          <B24Input
            v-model="dateFrom"
            type="datetime-local"
            class="w-full"
          />
        </B24FormField>

        <!-- Date To -->
        <B24FormField label="По дату">
          <B24Input
            v-model="dateTo"
            type="datetime-local"
            class="w-full"
          />
        </B24FormField>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
        <!-- Log File (if file source) -->
        <div v-if="source === 'file' && fileOptions.length > 0" class="sm:col-span-1">
          <B24FormField label="Файл">
            <B24Select
              v-model="filePath"
              :items="fileOptions"
              class="w-full font-mono text-xs"
            />
          </B24FormField>
        </div>

        <!-- Grep Pattern -->
        <div :class="source === 'file' && fileOptions.length > 0 ? 'sm:col-span-1' : 'sm:col-span-2'">
          <B24FormField label="Grep фильтр">
            <B24Input
              v-model="grep"
              placeholder="Шаблон регулярного выражения или подстрока"
              class="w-full font-mono text-xs"
            />
          </B24FormField>
        </div>

        <!-- Action Buttons -->
        <div class="flex items-center gap-2 justify-end flex-wrap">
          <B24Button
            label="Загрузить логи"
            :icon="RefreshIcon"
            color="air-primary"
            :loading="loading"
            @click="fetchLogs"
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

    <!-- Info bar -->
    <div v-if="loaded" class="flex items-center justify-between px-2 text-xs text-muted">
      <span>Найдено строк: <b class="text-label">{{ total }}</b></span>
      <span v-if="truncated" class="text-[var(--ui-color-design-filled-amber)]">
        (Вывод ограничен первыми 5000 строками)
      </span>
      <span>Источник: <code class="font-mono text-xs">{{ lines[0]?.includes("journalctl") ? "journalctl" : source }}</code></span>
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
        Записи в журнале за указанный период не найдены
      </div>

      <div v-else class="p-12 text-center text-sm text-muted">
        Выберите сервис, временной интервал и нажмите «Загрузить логи»
      </div>
    </div>
  </div>
</template>
