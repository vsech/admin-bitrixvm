<script setup>
import { ref } from "vue";
import { api } from "../api/client";
import ShieldCheckedIcon from "@bitrix24/b24icons-vue/outline/ShieldCheckedIcon";

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["update:open", "created"]);

const toast = useToast();

const step = ref(1);
const address = ref("");
const port = ref(22);
const probe = ref(null);
const name = ref("");
const nameManuallyEdited = ref(false);
const credentialType = ref("private_key");
const secret = ref("");
const passphrase = ref("");
const confirmed = ref(false);
const loading = ref(false);

function reset() {
  step.value = 1;
  address.value = "";
  port.value = 22;
  probe.value = null;
  name.value = "";
  nameManuallyEdited.value = false;
  credentialType.value = "private_key";
  secret.value = "";
  passphrase.value = "";
  confirmed.value = false;
  loading.value = false;
}

function handleClose() {
  emit("update:open", false);
  reset();
}

function onAddressInput() {
  if (!nameManuallyEdited.value) {
    name.value = address.value.trim().replace(/[^A-Za-z0-9_.-]/g, "-");
  }
}

async function runProbe() {
  loading.value = true;
  try {
    const result = await api.probe({ address: address.value, port: Number(port.value) });
    probe.value = result;
    if (!name.value.trim()) {
      name.value = address.value.trim().replace(/[^A-Za-z0-9_.-]/g, "-");
    }
    step.value = 2;
  } catch (error) {
    toast.add({
      title: "Ошибка проверки хоста",
      description: error.message,
      color: "air-primary-alert",
    });
  } finally {
    loading.value = false;
  }
}

async function createServer() {
  loading.value = true;
  const credential =
    credentialType.value === "password"
      ? { type: "password", password: secret.value }
      : {
          type: "private_key",
          private_key: secret.value,
          ...(passphrase.value ? { passphrase: passphrase.value } : {}),
        };

  try {
    const server = await api.createServer({
      name: name.value,
      probe_id: probe.value.id,
      confirmed_fingerprint: probe.value.fingerprint,
      username: "root",
      credential,
    });
    toast.add({
      title: "Сервер добавлен",
      description: `Сервер ${server.name} успешно подключён к контуру`,
      color: "air-primary-success",
    });
    emit("created", server);
    handleClose();
  } catch (error) {
    toast.add({
      title: "Ошибка добавления сервера",
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
    :title="step === 1 ? 'Добавить сервер (Шаг 1 из 2)' : 'Подтверждение и доступ (Шаг 2 из 2)'"
    :description="step === 1 ? 'Проверка SSH host key перед сохранением' : 'Сверка fingerprint и учетные данные root'"
    @update:open="handleClose"
  >
    <template #body>
      <!-- Step 1: Name, Address & Port Probe -->
      <form v-if="step === 1" id="add-server-form" class="space-y-4" @submit.prevent="runProbe">
        <B24FormField label="Имя сервера" hint="Идентификатор сервера в панели (латиница, цифры, дефис, точка)">
          <B24Input
            v-model="name"
            placeholder="bx-prod-01 (опционально, по умолчанию из адреса)"
            pattern="[A-Za-z0-9_.\-]+"
            @input="nameManuallyEdited = true"
          />
        </B24FormField>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div class="sm:col-span-2">
            <B24FormField label="Адрес сервера (IP или домен)" required>
              <B24Input
                v-model="address"
                placeholder="10.20.0.42 или host.internal"
                required
                autofocus
                @input="onAddressInput"
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
          title="Проверка безопасности"
          description="Контроллер сначала установит безопасный пробный контакт и получит публичный SSH fingerprint хоста. Сверьте его перед передачей реквизитов доступа."
          color="air-secondary-accent"
        />
      </form>

      <!-- Step 2: Fingerprint verification & Credentials -->
      <form v-else id="create-server-form" class="space-y-4" @submit.prevent="createServer">
        <!-- Fingerprint verification box -->
        <div class="p-4 rounded-xl bg-elevated/70 border border-muted space-y-3">
          <div class="flex items-center justify-between text-xs text-muted">
            <span>SSH host key fingerprint</span>
            <span class="font-mono">{{ probe?.host_key_algorithm }}</span>
          </div>
          <code class="text-xs font-mono break-all block p-2.5 rounded-lg bg-default border border-muted text-label select-all">
            {{ probe?.fingerprint }}
          </code>
          <div class="pt-1">
            <B24Checkbox
              v-model="confirmed"
              label="Fingerprint сверен по доверенному каналу вне контроллера"
            />
          </div>
        </div>

        <B24FormField label="Имя сервера" required>
          <B24Input
            v-model="name"
            placeholder="bx-prod-01"
            pattern="[A-Za-z0-9_.\-]+"
            required
          />
        </B24FormField>

        <div class="space-y-2">
          <label class="text-sm font-medium text-label block">Способ подключения</label>
          <div class="grid grid-cols-2 gap-2">
            <B24Button
              type="button"
              label="Приватный ключ"
              :variant="credentialType === 'private_key' ? 'solid' : 'outline'"
              :color="credentialType === 'private_key' ? 'air-primary' : 'air-secondary-no-accent'"
              size="sm"
              block
              @click="credentialType = 'private_key'"
            />
            <B24Button
              type="button"
              label="Пароль root"
              :variant="credentialType === 'password' ? 'solid' : 'outline'"
              :color="credentialType === 'password' ? 'air-primary' : 'air-secondary-no-accent'"
              size="sm"
              block
              @click="credentialType = 'password'"
            />
          </div>
        </div>

        <B24Alert
          v-if="credentialType === 'password'"
          title="Автоматическая настройка SSH-ключа"
          description="Контроллер подключится по паролю один раз, автоматически сгенерирует закрытый ключ Ed25519, добавит открытый ключ в ~/.ssh/authorized_keys на сервере и в дальнейшем будет использовать только ключ. Пароль в системе не сохраняется."
          color="air-primary-success"
        />

        <B24FormField
          :label="credentialType === 'password' ? 'Пароль root' : 'Приватный SSH-ключ'"
          required
        >
          <B24Input
            v-if="credentialType === 'password'"
            v-model="secret"
            type="password"
            placeholder="••••••••••••"
            autocomplete="new-password"
            required
          />
          <B24Textarea
            v-else
            v-model="secret"
            placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"
            rows="4"
            class="font-mono text-xs"
            required
          />
        </B24FormField>

        <B24FormField
          v-if="credentialType === 'private_key'"
          label="Passphrase (если ключ зашифрован)"
        >
          <B24Input
            v-model="passphrase"
            type="password"
            placeholder="Опционально"
            autocomplete="new-password"
          />
        </B24FormField>
      </form>
    </template>

    <template #footer>
      <div class="flex items-center justify-between w-full">
        <B24Button
          v-if="step === 2"
          label="Назад"
          color="air-secondary-no-accent"
          variant="outline"
          :disabled="loading"
          @click="step = 1"
        />
        <div v-else />

        <div class="flex items-center gap-2">
          <B24Button
            label="Отмена"
            color="air-secondary-no-accent"
            variant="ghost"
            :disabled="loading"
            @click="handleClose"
          />
          <B24Button
            v-if="step === 1"
            form="add-server-form"
            type="submit"
            label="Получить fingerprint"
            color="air-primary"
            :loading="loading"
          />
          <B24Button
            v-else
            form="create-server-form"
            type="submit"
            label="Добавить сервер"
            color="air-primary"
            :loading="loading"
            :disabled="!confirmed"
          />
        </div>
      </div>
    </template>
  </B24Modal>
</template>
