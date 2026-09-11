<script setup>
import { ref, computed, watch } from "vue";
import { api } from "../api/client";
import { getActionMeta } from "../data/capabilitiesMeta";
import AlertIcon from "@bitrix24/b24icons-vue/outline/AlertIcon";
import CircleCheckIcon from "@bitrix24/b24icons-vue/outline/CircleCheckIcon";

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  server: {
    type: Object,
    required: true,
  },
  capability: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits(["update:open", "executed"]);

const toast = useToast();

const values = ref({});
const preview = ref(null);
const loading = ref(false);

const actionMeta = computed(() => getActionMeta(props.capability?.action));

const confirmationRequired = computed(() =>
  ["high", "critical"].includes(props.capability.risk)
);

const properties = computed(() =>
  Object.entries(props.capability.request_schema?.properties || {})
);

const riskBadgeColor = computed(() => {
  switch (props.capability.risk) {
    case "critical":
    case "high":
      return "air-primary-alert";
    case "medium":
      return "air-primary-warning";
    default:
      return "air-primary-success";
  }
});

const riskLabel = computed(() => {
  const map = {
    low: "Низкий риск",
    medium: "Средний риск",
    high: "Высокий риск",
    critical: "Критический риск",
  };
  return map[props.capability.risk] || props.capability.risk;
});

function initValues() {
  const schema = props.capability.request_schema;
  const initial = {};
  if (schema?.properties) {
    for (const [key, definition] of Object.entries(schema.properties)) {
      initial[key] = definition.default ?? (definition.type === "boolean" ? false : "");
    }
  }
  values.value = initial;
  preview.value = null;
}

watch(
  () => props.capability,
  () => {
    initValues();
  },
  { immediate: true }
);

function getFieldOptions(definition) {
  const items = definition.enum || definition["x-options"] || [];
  return items.map((opt) => ({ label: String(opt), value: opt }));
}

function handleValueChange(key, definition, raw) {
  let val = raw;
  if (definition.type === "integer") {
    val = raw === "" ? "" : Number(raw);
  }
  values.value[key] = val;
  preview.value = null;
}

async function runPreview() {
  loading.value = true;
  try {
    preview.value = await api.preview(props.server.id, props.capability.action, values.value);
  } catch (error) {
    toast.add({
      title: "Ошибка предварительной проверки",
      description: error.message,
      color: "air-primary-alert",
    });
  } finally {
    loading.value = false;
  }
}

async function executeAction() {
  if (confirmationRequired.value && !preview.value) {
    await runPreview();
    return;
  }

  loading.value = true;
  try {
    const operation = await api.execute(
      props.server.id,
      props.capability.action,
      values.value,
      preview.value?.confirmation_token
    );
    toast.add({
      title: "Операция в очереди",
      description: `Действие ${props.capability.action} запущено`,
      color: "air-primary-success",
    });
    emit("executed", operation);
    emit("update:open", false);
  } catch (error) {
    toast.add({
      title: "Ошибка запуска",
      description: error.message,
      color: "air-primary-alert",
    });
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <B24Modal
    :open="open"
    :title="actionMeta.title || capability.summary || capability.action"
    :description="`${server.name} · ${capability.action}`"
    :b24ui="{ content: 'max-w-2xl' }"
    @update:open="emit('update:open', $event)"
  >
    <template #body>
      <div class="space-y-6">
        <!-- Action Description & Risk Notice -->
        <div class="space-y-2">
          <p v-if="actionMeta.description" class="text-sm text-description">
            {{ actionMeta.description }}
          </p>
          <div class="flex items-center justify-between p-3.5 rounded-xl bg-elevated/80 border border-muted">
            <div class="flex items-center gap-2.5">
              <B24Badge :label="riskLabel" :color="riskBadgeColor" size="sm" />
              <span class="text-xs text-description">
                {{ confirmationRequired ? 'Требуется предварительное подтверждение параметров' : 'Можно поставить в очередь сразу' }}
              </span>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <!-- Form parameters column -->
          <div class="lg:col-span-3 space-y-4">
            <h4 class="text-xs font-semibold uppercase tracking-wider text-muted">Параметры действия</h4>

            <div v-if="properties.length === 0" class="p-4 rounded-xl bg-muted/20 text-center text-sm text-muted">
              У действия нет настраиваемых параметров
            </div>

            <div v-else class="space-y-4">
              <div v-for="[key, definition] in properties" :key="key">
                <!-- Boolean field -->
                <div v-if="definition.type === 'boolean'" class="flex items-center justify-between p-3 rounded-lg bg-elevated/40 border border-muted">
                  <div>
                    <label class="text-sm font-medium text-label block">{{ definition.description || key }}</label>
                    <code class="text-xs text-muted font-mono">{{ key }}</code>
                  </div>
                  <B24Switch
                    :model-value="Boolean(values[key])"
                    @update:model-value="handleValueChange(key, definition, $event)"
                  />
                </div>

                <!-- Select field -->
                <div v-else-if="getFieldOptions(definition).length > 0">
                  <B24FormField
                    :label="definition.description || key"
                    :required="capability.request_schema.required?.includes(key)"
                  >
                    <B24Select
                      :model-value="values[key]"
                      :items="getFieldOptions(definition)"
                      placeholder="Выберите значение"
                      class="w-full"
                      @update:model-value="handleValueChange(key, definition, $event)"
                    />
                    <template #hint>
                      <code class="text-xs text-muted font-mono">{{ key }}</code>
                    </template>
                  </B24FormField>
                </div>

                <!-- Number or Password or Text input -->
                <div v-else>
                  <B24FormField
                    :label="definition.description || key"
                    :required="capability.request_schema.required?.includes(key)"
                  >
                    <B24Input
                      :model-value="values[key]"
                      :type="definition.format === 'password' ? 'password' : definition.type === 'integer' ? 'number' : 'text'"
                      :min="definition.minimum"
                      :max="definition.maximum"
                      :pattern="definition.pattern"
                      class="w-full"
                      @update:model-value="handleValueChange(key, definition, $event)"
                    />
                    <template #hint>
                      <code class="text-xs text-muted font-mono">{{ key }}</code>
                    </template>
                  </B24FormField>
                </div>
              </div>
            </div>
          </div>

          <!-- Preview & Warnings column -->
          <div class="lg:col-span-2 p-4 rounded-xl bg-elevated/50 border border-muted flex flex-col justify-between space-y-4">
            <div class="space-y-3">
              <h4 class="text-xs font-semibold uppercase tracking-wider text-muted">Проверка запуска</h4>

              <div v-if="preview" class="space-y-3">
                <div class="flex items-center gap-2 text-xs font-medium text-[var(--ui-color-design-filled-green)]">
                  <CircleCheckIcon class="size-4" />
                  <span>Параметры проверены API</span>
                </div>

                <p class="text-xs text-description leading-relaxed">{{ preview.summary }}</p>

                <div v-if="preview.warnings?.length" class="space-y-1.5">
                  <div
                    v-for="warning in preview.warnings"
                    :key="warning"
                    class="p-2.5 rounded-lg bg-primary-alert/10 border border-primary-alert/20 text-xs text-label flex items-start gap-2"
                  >
                    <AlertIcon class="size-4 text-[var(--ui-color-design-filled-red)] shrink-0 mt-0.5" />
                    <span>{{ warning }}</span>
                  </div>
                </div>

                <div class="text-xs text-muted pt-2 border-t border-muted">
                  Токен подтверждения действителен до:
                  <span class="font-mono text-label block mt-0.5">
                    {{ new Date(preview.expires_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) }}
                  </span>
                </div>
              </div>

              <p v-else class="text-xs text-muted leading-relaxed">
                {{ confirmationRequired ? 'Для выполнения действия высокого риска требуется предварительная проверка и генерация токена.' : 'Проверьте заполненные параметры перед запуском.' }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </template>

    <template #footer>
      <div class="flex items-center justify-end gap-2 w-full">
        <B24Button
          label="Отмена"
          color="air-secondary-no-accent"
          variant="ghost"
          :disabled="loading"
          @click="emit('update:open', false)"
        />

        <B24Button
          v-if="confirmationRequired && !preview"
          label="Предварительный просмотр"
          color="air-primary"
          :loading="loading"
          @click="runPreview"
        />

        <B24Button
          v-else
          :label="capability.risk === 'critical' ? 'Подтвердить и запустить' : 'Запустить операцию'"
          :color="capability.risk === 'critical' ? 'air-primary-alert' : 'air-primary'"
          :loading="loading"
          @click="executeAction"
        />
      </div>
    </template>
  </B24Modal>
</template>
