<script setup>
import { ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAppContext } from "../composables/useAppContext";
import ShieldCheckedIcon from "@bitrix24/b24icons-vue/outline/ShieldCheckedIcon";
import KeyIcon from "@bitrix24/b24icons-vue/outline/KeyIcon";
import UserProfileIcon from "@bitrix24/b24icons-vue/outline/UserProfileIcon";

const router = useRouter();
const route = useRoute();
const { login, isDemo } = useAppContext();

const username = ref(isDemo ? "admin" : "");
const password = ref(isDemo ? "demo-password" : "");
const error = ref("");
const loading = ref(false);

async function submit() {
  error.value = "";
  loading.value = true;
  try {
    await login(username.value, password.value);
    const redirect = route.query.redirect || "/servers";
    router.push(redirect);
  } catch (err) {
    error.value = err.message || "Ошибка авторизации";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="min-h-screen grid lg:grid-cols-2 bg-default">
    <!-- Promo / Branding Column -->
    <div class="hidden lg:flex flex-col justify-between p-12 bg-elevated/70 border-r border-muted relative overflow-hidden">
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-lg bg-[var(--ui-color-design-filled-blue)] flex items-center justify-center text-white font-bold text-lg shadow-sm">
          B
        </div>
        <span class="text-xl font-bold text-label tracking-tight">BitrixVM Control</span>
      </div>

      <div class="max-w-md space-y-4">
        <h1 class="text-3xl font-extrabold text-label tracking-tight leading-tight">
          Управление BitrixVM<br />под надёжным контролем
        </h1>
        <p class="text-description text-base leading-relaxed">
          Единая безопасная веб-консоль для администрирования серверов, автоматизации операций и сквозного аудита инфраструктуры BitrixEnv.
        </p>
      </div>

      <div class="flex items-center gap-3 p-4 rounded-xl bg-default/80 border border-muted text-sm text-description">
        <ShieldCheckedIcon class="size-6 text-[var(--ui-color-design-filled-blue)] shrink-0" />
        <span>SSH-ключи и пароли надёжно защищены. Опасные действия требуют предварительного подтверждения.</span>
      </div>
    </div>

    <!-- Form Column -->
    <div class="flex flex-col justify-center items-center p-6 sm:p-12">
      <div class="w-full max-w-md space-y-6">
        <div class="lg:hidden flex items-center gap-2 mb-2">
          <div class="w-8 h-8 rounded-lg bg-[var(--ui-color-design-filled-blue)] flex items-center justify-center text-white font-bold text-base shadow-sm">
            B
          </div>
          <span class="text-lg font-bold text-label tracking-tight">BitrixVM Control</span>
        </div>

        <div>
          <h2 class="text-2xl font-bold text-label tracking-tight">Вход в консоль</h2>
          <p class="text-sm text-muted mt-1">Используйте учётную запись администратора BitrixVM</p>
        </div>

        <B24Alert
          v-if="isDemo"
          title="Демонстрационный режим"
          description="Запросы к серверу не отправляются. Доступен предзаполненный аккаунт."
          color="air-secondary-accent"
        />

        <B24Alert
          v-if="error"
          title="Ошибка входа"
          :description="error"
          color="air-primary-alert"
        />

        <form class="space-y-4" @submit.prevent="submit">
          <B24FormField label="Логин" required>
            <B24Input
              v-model="username"
              :icon="UserProfileIcon"
              placeholder="admin"
              autocomplete="username"
              required
              autofocus
            />
          </B24FormField>

          <B24FormField label="Пароль" required>
            <B24Input
              v-model="password"
              :icon="KeyIcon"
              type="password"
              placeholder="••••••••••••"
              autocomplete="current-password"
              required
            />
          </B24FormField>

          <B24Button
            type="submit"
            label="Войти"
            color="air-primary"
            :loading="loading"
            block
            size="md"
          />

          <p class="text-center text-xs text-muted">
            Сессия защищена короткоживущим access-токеном с автоматическим обновлением.
          </p>
        </form>
      </div>
    </div>
  </div>
</template>
