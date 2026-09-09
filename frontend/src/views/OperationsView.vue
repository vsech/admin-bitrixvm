<script setup>
import { ref, computed, onMounted } from "vue";
import { api } from "../api/client";
import { useAppContext } from "../composables/useAppContext";
import RefreshIcon from "@bitrix24/b24icons-vue/outline/RefreshIcon";
import AlertIcon from "@bitrix24/b24icons-vue/outline/AlertIcon";

const toast = useToast();
const { operations, servers, fetchOperations, loadingOperations } = useAppContext();

const filter = ref("all");
const selected = ref(null);
const detailModalOpen = ref(false);
const events = ref([]);
const loadingEvents = ref(false);

onMounted(() => {
  fetchOperations();
});

const filterOptions = computed(() => [
  { id: "all", label: "Все", count: operations.value.length },
  { id: "queued", label: "В очереди", count: operations.value.filter((i) => i.status === "queued").length },
  { id: "running", label: "Выполняются", count: operations.value.filter((i) => i.status === "running").length },
  { id: "succeeded", label: "Завершены", count: operations.value.filter((i) => i.status === "succeeded").length },
  { id: "failed", label: "Ошибки", count: operations.value.filter((i) => i.status === "failed").length },
]);

const visibleOperations = computed(() => {
  if (filter.value === "all") return operations.value;
  return operations.value.filter((item) => item.status === filter.value);
});

function getOperationServerName(serverId) {
  const found = servers.value.find((s) => s.id === serverId);
  return found ? found.name : serverId?.slice(0, 8) || "—";
}

function getStatusBadge(status) {
  switch (status) {
    case "succeeded":
      return { label: "Выполнено", color: "air-primary-success" };
    case "running":
      return { label: "Выполняется", color: "air-primary" };
    case "failed":
      return { label: "Ошибка", color: "air-primary-alert" };
    case "queued":
      return { label: "В очереди", color: "air-primary-warning" };
    case "canceled":
      return { label: "Отменено", color: "air-secondary-no-accent" };
    default:
      return { label: status, color: "air-secondary-no-accent" };
  }
}

function getRiskBadge(risk) {
  switch (risk) {
    case "critical":
    case "high":
      return { label: risk, color: "air-primary-alert" };
    case "medium":
      return { label: risk, color: "air-primary-warning" };
    default:
      return { label: risk, color: "air-primary-success" };
  }
}

async function openDetail(operation) {
  selected.value = operation;
  detailModalOpen.value = true;
  loadingEvents.value = true;
  events.value = [];
  try {
    events.value = await api.events(operation.id);
  } catch (err) {
    toast.add({
      title: "Ошибка загрузки событий аудита",
      description: err.message,
      color: "air-primary-alert",
    });
  } finally {
    loadingEvents.value = false;
  }
}

async function cancelOperation() {
  if (!selected.value) return;
  try {
    const updated = await api.cancelOperation(selected.value.id);
    selected.value = updated;
    await fetchOperations();
    toast.add({
      title: "Операция отменена",
      color: "air-primary-success",
    });
  } catch (err) {
    toast.add({
      title: "Ошибка отмены операции",
      description: err.message,
      color: "air-primary-alert",
    });
  }
}

async function handleRefresh() {
  await fetchOperations();
  toast.add({
    title: "Журнал операций обновлен",
    color: "air-primary-success",
  });
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-label tracking-tight">Операции</h1>
        <p class="text-sm text-muted mt-1">Очередь задач, статус выполнения и журнал аудита</p>
      </div>

      <B24Button
        label="Обновить"
        :icon="RefreshIcon"
        color="air-secondary-no-accent"
        variant="outline"
        :loading="loadingOperations"
        @click="handleRefresh"
      />
    </div>

    <!-- Filter Tabs -->
    <div class="flex items-center gap-2 overflow-x-auto pb-3 border-b border-muted">
      <B24Button
        v-for="tab in filterOptions"
        :key="tab.id"
        :label="`${tab.label} (${tab.count})`"
        :variant="filter === tab.id ? 'solid' : 'ghost'"
        :color="filter === tab.id ? 'air-primary' : 'air-secondary-no-accent'"
        size="sm"
        @click="filter = tab.id"
      />
    </div>

    <!-- Operations Table Card -->
    <B24Card class="border border-muted overflow-hidden" :b24ui="{ body: '!p-0' }">
      <div v-if="visibleOperations.length" class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead class="bg-elevated/80 border-b border-muted text-xs font-semibold text-muted uppercase tracking-wider">
            <tr>
              <th class="py-3.5 px-4">Операция</th>
              <th class="py-3.5 px-4">Сервер</th>
              <th class="py-3.5 px-4">Риск</th>
              <th class="py-3.5 px-4">Статус</th>
              <th class="py-3.5 px-4 text-right">Создана</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-muted">
            <tr
              v-for="op in visibleOperations"
              :key="op.id"
              class="hover:bg-muted/30 transition-colors cursor-pointer"
              @click="openDetail(op)"
            >
              <td class="py-3.5 px-4">
                <div class="min-w-0">
                  <code class="font-bold text-xs text-label font-mono block truncate">{{ op.action }}</code>
                  <span class="text-[11px] text-muted font-mono">{{ op.id.slice(0, 12) }}…</span>
                </div>
              </td>
              <td class="py-3.5 px-4 font-medium text-label">
                {{ getOperationServerName(op.server_id) }}
              </td>
              <td class="py-3.5 px-4">
                <B24Badge
                  :label="getRiskBadge(op.risk).label"
                  :color="getRiskBadge(op.risk).color"
                  size="xs"
                />
              </td>
              <td class="py-3.5 px-4">
                <B24Badge
                  :label="getStatusBadge(op.status).label"
                  :color="getStatusBadge(op.status).color"
                  size="sm"
                />
              </td>
              <td class="py-3.5 px-4 text-right text-xs text-muted font-mono whitespace-nowrap">
                {{ new Date(op.created_at).toLocaleString("ru-RU", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else class="p-12 text-center text-sm text-muted">
        Операции в этой категории отсутствуют
      </div>
    </B24Card>

    <!-- Operation Detail Modal -->
    <B24Modal
      v-if="selected"
      v-model:open="detailModalOpen"
      :title="selected.action"
      :description="`Операция ${selected.id}`"
      :b24ui="{ content: 'max-w-2xl' }"
    >
      <template #body>
        <div class="space-y-6">
          <!-- Summary attributes -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 rounded-xl bg-elevated/50 border border-muted text-xs">
            <div>
              <span class="text-muted block">Статус</span>
              <div class="mt-1">
                <B24Badge
                  :label="getStatusBadge(selected.status).label"
                  :color="getStatusBadge(selected.status).color"
                  size="sm"
                />
              </div>
            </div>
            <div>
              <span class="text-muted block">Сервер</span>
              <span class="font-medium text-label block mt-1">{{ getOperationServerName(selected.server_id) }}</span>
            </div>
            <div>
              <span class="text-muted block">Риск</span>
              <div class="mt-1">
                <B24Badge
                  :label="getRiskBadge(selected.risk).label"
                  :color="getRiskBadge(selected.risk).color"
                  size="xs"
                />
              </div>
            </div>
            <div>
              <span class="text-muted block">Создана</span>
              <span class="text-label block mt-1 font-mono">
                {{ new Date(selected.created_at).toLocaleString("ru-RU") }}
              </span>
            </div>
          </div>

          <!-- Error Alert if failed -->
          <B24Alert
            v-if="selected.error_message"
            title="Ошибка выполнения операции"
            :description="selected.error_message"
            color="air-primary-alert"
          />

          <!-- Parameters Block -->
          <div class="space-y-2">
            <h4 class="text-xs font-semibold uppercase tracking-wider text-muted">Параметры выполнения</h4>
            <div class="p-3 rounded-lg bg-elevated/80 border border-muted overflow-auto max-h-40">
              <pre class="terminal-output text-xs font-mono text-description whitespace-pre-wrap">{{ JSON.stringify(selected.args_redacted, null, 2) }}</pre>
            </div>
          </div>

          <!-- Timeline of Audit Events -->
          <div class="space-y-3">
            <h4 class="text-xs font-semibold uppercase tracking-wider text-muted">События аудита</h4>

            <div v-if="loadingEvents" class="p-6 text-center text-xs text-muted">
              Загрузка журнала событий…
            </div>

            <div v-else-if="events.length" class="space-y-3 relative pl-6 before:content-[''] before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-muted">
              <div
                v-for="ev in events"
                :key="ev.id"
                class="relative space-y-1"
              >
                <div class="absolute -left-[21px] top-1 size-2 rounded-full bg-[var(--ui-color-design-filled-blue)] ring-4 ring-default" />
                <p class="text-xs font-semibold text-label">{{ ev.message }}</p>
                <p class="text-[11px] text-muted">
                  {{ ev.event }} · {{ new Date(ev.created_at).toLocaleTimeString('ru-RU') }}
                </p>
              </div>
            </div>

            <div v-else class="p-4 text-center text-xs text-muted">
              События для этой операции пока не зарегистрированы
            </div>
          </div>
        </div>
      </template>

      <template #footer>
        <div class="flex items-center justify-between w-full">
          <div>
            <B24Button
              v-if="selected.status === 'queued'"
              label="Отменить операцию"
              color="air-primary-alert"
              variant="outline"
              size="sm"
              @click="cancelOperation"
            />
          </div>

          <B24Button
            label="Закрыть"
            color="air-primary"
            size="sm"
            @click="detailModalOpen = false"
          />
        </div>
      </template>
    </B24Modal>
  </div>
</template>
