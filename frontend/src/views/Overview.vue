<script setup>
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useAppContext } from "../composables/useAppContext";
import DeveloperResourcesIcon from "@bitrix24/b24icons-vue/outline/DeveloperResourcesIcon";
import PlayLIcon from "@bitrix24/b24icons-vue/outline/PlayLIcon";
import ShieldCheckedIcon from "@bitrix24/b24icons-vue/outline/ShieldCheckedIcon";
import ChevronRightLIcon from "@bitrix24/b24icons-vue/outline/ChevronRightLIcon";

const router = useRouter();
const { servers, operations } = useAppContext();

const runningOperations = computed(() =>
  operations.value.filter((item) => ["queued", "running"].includes(item.status))
);

function getOperationServerName(serverId) {
  const found = servers.value.find((s) => s.id === serverId);
  return found ? found.name : serverId?.slice(0, 8) || "—";
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-label tracking-tight">Обзор</h1>
        <p class="text-sm text-muted mt-1">Состояние и активность контура управления BitrixVM</p>
      </div>
      <B24Button
        :icon="DeveloperResourcesIcon"
        label="Открыть серверы"
        color="air-primary"
        @click="router.push('/servers')"
      />
    </div>

    <!-- Hero Card -->
    <B24Card
      class="border border-muted bg-elevated/60"
      :b24ui="{ body: 'p-6 sm:p-8' }"
    >
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div class="space-y-2 max-w-xl">
          <B24Badge label="Контроллер активен" color="air-primary-success" size="sm" />
          <h2 class="text-2xl font-bold text-label">
            {{ servers.length ? `${servers.length} ${servers.length === 1 ? 'сервер' : 'сервера'} подключено` : 'Серверы ещё не добавлены' }}
          </h2>
          <p class="text-sm text-description leading-relaxed">
            Опасные действия проходят двухфазную предварительную проверку, все операции и события аудита сохраняются в базе данных.
          </p>
        </div>
        <div class="hidden md:flex items-center justify-center p-4 rounded-2xl bg-default/80 border border-muted shrink-0">
          <ShieldCheckedIcon class="size-16 text-[var(--ui-color-design-filled-blue)]" />
        </div>
      </div>
    </B24Card>

    <!-- Two Column Grid -->
    <div class="grid md:grid-cols-2 gap-6">
      <!-- Infrastructure Card -->
      <B24Card class="border border-muted flex flex-col">
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="font-bold text-label text-base">Инфраструктура</h3>
            <B24Button
              label="Все серверы"
              :trailing-icon="ChevronRightLIcon"
              variant="link"
              color="air-primary"
              size="sm"
              @click="router.push('/servers')"
            />
          </div>
        </template>

        <div v-if="servers.length" class="divide-y divide-muted">
          <div
            v-for="server in servers"
            :key="server.id"
            class="py-3.5 flex items-center justify-between hover:bg-muted/40 transition-colors px-1 rounded-lg cursor-pointer"
            @click="router.push({ path: '/servers', query: { server: server.id } })"
          >
            <div class="flex items-center gap-3 min-w-0">
              <div class="p-2 rounded-lg bg-default border border-muted shrink-0">
                <DeveloperResourcesIcon class="size-4 text-[var(--ui-color-design-filled-blue)]" />
              </div>
              <div class="min-w-0">
                <p class="text-sm font-semibold text-label truncate">{{ server.name }}</p>
                <p class="text-xs text-muted font-mono">{{ server.address }}</p>
              </div>
            </div>
            <B24Badge label="Доступен" color="air-primary-success" size="sm" />
          </div>
        </div>

        <div v-else class="py-8 text-center text-sm text-muted">
          Серверы пока не добавлены в контур
        </div>
      </B24Card>

      <!-- Active Operations Card -->
      <B24Card class="border border-muted flex flex-col">
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="font-bold text-label text-base">Активные операции</h3>
            <B24Button
              label="Журнал"
              :trailing-icon="ChevronRightLIcon"
              variant="link"
              color="air-primary"
              size="sm"
              @click="router.push('/operations')"
            />
          </div>
        </template>

        <div v-if="runningOperations.length" class="divide-y divide-muted">
          <div
            v-for="operation in runningOperations"
            :key="operation.id"
            class="py-3.5 flex items-center justify-between hover:bg-muted/40 transition-colors px-1 rounded-lg cursor-pointer"
            @click="router.push('/operations')"
          >
            <div class="flex items-center gap-3 min-w-0">
              <div class="p-2 rounded-lg bg-default border border-muted shrink-0">
                <PlayLIcon class="size-4 text-[var(--ui-color-design-filled-blue)]" />
              </div>
              <div class="min-w-0">
                <code class="text-xs font-semibold text-label truncate block font-mono">{{ operation.action }}</code>
                <span class="text-xs text-muted truncate block">{{ getOperationServerName(operation.server_id) }}</span>
              </div>
            </div>

            <B24Badge
              :label="operation.status === 'running' ? 'Выполняется' : 'В очереди'"
              :color="operation.status === 'running' ? 'air-primary' : 'air-primary-warning'"
              size="sm"
            />
          </div>
        </div>

        <div v-else class="py-8 text-center text-sm text-muted">
          Нет активных операций в очереди
        </div>
      </B24Card>
    </div>
  </div>
</template>
