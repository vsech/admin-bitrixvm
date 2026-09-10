<script setup>
import { ref, watch } from "vue";
import { api } from "../api/client";

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  server: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(["update:open", "updated"]);

const toast = useToast();

const name = ref("");
const address = ref("");
const port = ref(22);
const loading = ref(false);

watch(
  () => props.server,
  (srv) => {
    if (srv) {
      name.value = srv.name || "";
      address.value = srv.address || "";
      port.value = srv.port || 22;
    }
  },
  { immediate: true }
);

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen && props.server) {
      name.value = props.server.name || "";
      address.value = props.server.address || "";
      port.value = props.server.port || 22;
      loading.value = false;
    }
  }
);

function handleClose() {
  emit("update:open", false);
}

async function handleSave() {
  if (!props.server) return;
  loading.value = true;

  const payload = {
    name: name.value.trim(),
    address: address.value.trim(),
    port: Number(port.value),
  };

  try {
    const updated = await api.updateServer(props.server.id, payload);
    toast.add({
      title: "Сервер обновлён",
      description: `Параметры сервера «${updated.name}» успешно сохранены`,
      color: "air-primary-success",
    });
    emit("updated", updated);
    handleClose();
  } catch (error) {
    toast.add({
      title: "Ошибка обновления сервера",
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
    title="Редактирование сервера"
    :description="`Изменение параметров подключения для ${server?.name || ''}`"
    @update:open="handleClose"
  >
    <template #body>
      <form id="edit-server-form" class="space-y-4" @submit.prevent="handleSave">
        <B24FormField label="Имя сервера" required hint="Идентификатор в панели (латиница, цифры, дефис, точка)">
          <B24Input
            v-model="name"
            placeholder="bx-prod-01"
            pattern="[A-Za-z0-9_.\-]+"
            required
            autofocus
          />
        </B24FormField>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div class="sm:col-span-2">
            <B24FormField label="Адрес сервера (IP или домен)" required>
              <B24Input
                v-model="address"
                placeholder="10.20.0.42 или host.internal"
                required
              />
            </B24FormField>
          </div>
          <div>
            <B24FormField label="SSH-порт" required>
              <B24Input
                v-model.number="port"
                type="number"
                min="1"
                max="65535"
                required
              />
            </B24FormField>
          </div>
        </div>

        <B24Alert
          title="Смена сетевых параметров"
          description="При изменении IP-адреса или порта контроллер автоматически свяжется с новым хостом, обновит публичный SSH host key и проверит совместимость окружения BitrixVM."
          color="air-secondary-accent"
        />
      </form>
    </template>

    <template #footer>
      <div class="flex items-center justify-end gap-2 w-full">
        <B24Button
          label="Отмена"
          color="air-secondary-no-accent"
          variant="ghost"
          :disabled="loading"
          @click="handleClose"
        />
        <B24Button
          form="edit-server-form"
          type="submit"
          label="Сохранить изменения"
          color="air-primary"
          :loading="loading"
        />
      </div>
    </template>
  </B24Modal>
</template>
