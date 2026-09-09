<script setup>
import { ref, onMounted } from "vue";
import { api } from "../api/client";
import { useAppContext } from "../composables/useAppContext";
import PlusLIcon from "@bitrix24/b24icons-vue/outline/PlusLIcon";
import EditPencilIcon from "@bitrix24/b24icons-vue/main/EditPencilIcon";
import KeyIcon from "@bitrix24/b24icons-vue/outline/KeyIcon";
import TrashcanIcon from "@bitrix24/b24icons-vue/outline/TrashcanIcon";
import ShieldCheckedIcon from "@bitrix24/b24icons-vue/outline/ShieldCheckedIcon";

const toast = useToast();
const { user: currentUser } = useAppContext();

const users = ref([]);
const loading = ref(true);

// Modals state
const createOpen = ref(false);
const newUsername = ref("");
const newPassword = ref("");
const createLoading = ref(false);

const editingUser = ref(null);
const editUsername = ref("");
const editPassword = ref("");
const editLoading = ref(false);

const changingUser = ref(null);
const currentPassword = ref("");
const changeNewPassword = ref("");
const confirmPassword = ref("");
const changeLoading = ref(false);

const disablingUser = ref(null);
const disableConfirmOpen = ref(false);
const disableLoading = ref(false);

async function loadUsers() {
  loading.value = true;
  try {
    users.value = await api.users();
  } catch (err) {
    toast.add({
      title: "Ошибка загрузки пользователей",
      description: err.message,
      color: "air-primary-alert",
    });
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadUsers();
});

async function handleCreate() {
  createLoading.value = true;
  try {
    const created = await api.createUser({
      username: newUsername.value,
      password: newPassword.value,
    });
    users.value.push(created);
    createOpen.value = false;
    newUsername.value = "";
    newPassword.value = "";
    toast.add({
      title: "Пользователь создан",
      description: `Учётная запись ${created.username} успешно добавлена`,
      color: "air-primary-success",
    });
  } catch (err) {
    toast.add({
      title: "Ошибка создания",
      description: err.message,
      color: "air-primary-alert",
    });
  } finally {
    createLoading.value = false;
  }
}

function openEdit(targetUser) {
  editingUser.value = targetUser;
  editUsername.value = targetUser.username;
  editPassword.value = "";
}

async function handleSaveEdit() {
  editLoading.value = true;
  try {
    const updated = await api.updateUser(editingUser.value.id, {
      username: editUsername.value,
      current_password: editPassword.value,
    });
    users.value = users.value.map((u) => (u.id === updated.id ? updated : u));
    editingUser.value = null;
    toast.add({
      title: "Данные обновлены",
      description: `Пользователь ${updated.username} сохранён`,
      color: "air-primary-success",
    });
  } catch (err) {
    toast.add({
      title: "Ошибка обновления",
      description: err.message,
      color: "air-primary-alert",
    });
  } finally {
    editLoading.value = false;
  }
}

function openPasswordChange(targetUser) {
  changingUser.value = targetUser;
  currentPassword.value = "";
  changeNewPassword.value = "";
  confirmPassword.value = "";
}

async function handleSavePassword() {
  if (changeNewPassword.value !== confirmPassword.value) {
    toast.add({
      title: "Пароли не совпадают",
      color: "air-primary-alert",
    });
    return;
  }

  changeLoading.value = true;
  try {
    await api.changePassword(changingUser.value.id, {
      current_password: currentPassword.value,
      new_password: changeNewPassword.value,
      confirm_password: confirmPassword.value,
    });
    changingUser.value = null;
    toast.add({
      title: "Пароль изменён",
      color: "air-primary-success",
    });
  } catch (err) {
    toast.add({
      title: "Ошибка изменения пароля",
      description: err.message,
      color: "air-primary-alert",
    });
  } finally {
    changeLoading.value = false;
  }
}

function promptDisable(targetUser) {
  disablingUser.value = targetUser;
  disableConfirmOpen.value = true;
}

async function handleConfirmDisable() {
  if (!disablingUser.value) return;
  disableLoading.value = true;
  try {
    await api.disableUser(disablingUser.value.id);
    users.value = users.value.map((u) =>
      u.id === disablingUser.value.id ? { ...u, is_active: false } : u
    );
    disableConfirmOpen.value = false;
    toast.add({
      title: "Пользователь отключён",
      description: `Учётная запись ${disablingUser.value.username} деактивирована`,
      color: "air-primary-success",
    });
  } catch (err) {
    toast.add({
      title: "Ошибка деактивации",
      description: err.message,
      color: "air-primary-alert",
    });
  } finally {
    disableLoading.value = false;
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-label tracking-tight">Пользователи</h1>
        <p class="text-sm text-muted mt-1">Управление учётными записями администраторов консоли</p>
      </div>

      <B24Button
        label="Добавить пользователя"
        :icon="PlusLIcon"
        color="air-primary"
        @click="createOpen = true"
      />
    </div>

    <!-- Users Table Card -->
    <B24Card class="border border-muted overflow-hidden">
      <div v-if="loading" class="p-8 text-center text-sm text-muted">
        Загрузка списка пользователей…
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead class="bg-elevated/80 border-b border-muted text-xs font-semibold text-muted uppercase tracking-wider">
            <tr>
              <th class="py-3.5 px-4">Пользователь</th>
              <th class="py-3.5 px-4">Статус</th>
              <th class="py-3.5 px-4">Создан</th>
              <th class="py-3.5 px-4 text-right">Действия</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-muted">
            <tr
              v-for="u in users"
              :key="u.id"
              class="hover:bg-muted/30 transition-colors"
            >
              <td class="py-3.5 px-4">
                <div class="flex items-center gap-2">
                  <span class="font-bold text-label">{{ u.username }}</span>
                  <B24Badge
                    v-if="u.id === currentUser?.id"
                    label="Вы"
                    color="air-primary"
                    size="xs"
                  />
                </div>
              </td>
              <td class="py-3.5 px-4">
                <B24Badge
                  :label="u.is_active ? 'Активен' : 'Отключён'"
                  :color="u.is_active ? 'air-primary-success' : 'air-secondary-no-accent'"
                  size="sm"
                />
              </td>
              <td class="py-3.5 px-4 text-xs text-muted font-mono whitespace-nowrap">
                {{ new Date(u.created_at).toLocaleDateString("ru-RU") }}
              </td>
              <td class="py-3.5 px-4 text-right">
                <div class="flex items-center justify-end gap-1">
                  <B24Button
                    :icon="EditPencilIcon"
                    color="air-secondary-no-accent"
                    variant="ghost"
                    size="xs"
                    :disabled="!u.is_active"
                    title="Редактировать логин"
                    @click="openEdit(u)"
                  />
                  <B24Button
                    :icon="KeyIcon"
                    color="air-secondary-no-accent"
                    variant="ghost"
                    size="xs"
                    :disabled="!u.is_active"
                    title="Сменить пароль"
                    @click="openPasswordChange(u)"
                  />
                  <B24Button
                    :icon="TrashcanIcon"
                    color="air-primary-alert"
                    variant="ghost"
                    size="xs"
                    :disabled="u.id === currentUser?.id || !u.is_active"
                    title="Отключить"
                    @click="promptDisable(u)"
                  />
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </B24Card>

    <!-- Create User Modal -->
    <B24Modal
      v-model:open="createOpen"
      title="Новый пользователь"
      description="Доступ к управлению всей инфраструктурой BitrixVM"
    >
      <template #body>
        <form id="create-user-form" class="space-y-4" @submit.prevent="handleCreate">
          <B24FormField label="Логин" required>
            <B24Input
              v-model="newUsername"
              minlength="3"
              maxlength="64"
              pattern="[A-Za-z0-9_.\-]+"
              autocomplete="username"
              required
              autofocus
            />
          </B24FormField>

          <B24FormField label="Пароль" hint="Не менее 12 символов" required>
            <B24Input
              v-model="newPassword"
              type="password"
              minlength="12"
              maxlength="256"
              autocomplete="new-password"
              required
            />
          </B24FormField>

          <B24Alert
            title="Административные права"
            description="Новый пользователь получит полный административный доступ к серверам и операциям."
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
            @click="createOpen = false"
          />
          <B24Button
            form="create-user-form"
            type="submit"
            label="Создать пользователя"
            color="air-primary"
            :loading="createLoading"
          />
        </div>
      </template>
    </B24Modal>

    <!-- Edit User Modal -->
    <B24Modal
      v-if="editingUser"
      :open="Boolean(editingUser)"
      title="Редактирование пользователя"
      :description="editingUser.username"
      @update:open="editingUser = null"
    >
      <template #body>
        <form id="edit-user-form" class="space-y-4" @submit.prevent="handleSaveEdit">
          <B24FormField label="Логин" required>
            <B24Input
              v-model="editUsername"
              minlength="3"
              maxlength="64"
              pattern="[A-Za-z0-9_.\-]+"
              autocomplete="username"
              required
              autofocus
            />
          </B24FormField>

          <B24FormField label="Текущий пароль" hint="Для подтверждения изменения логина" required>
            <B24Input
              v-model="editPassword"
              type="password"
              minlength="12"
              maxlength="256"
              autocomplete="current-password"
              required
            />
          </B24FormField>
        </form>
      </template>

      <template #footer>
        <div class="flex items-center justify-end gap-2 w-full">
          <B24Button
            label="Отмена"
            color="air-secondary-no-accent"
            variant="ghost"
            @click="editingUser = null"
          />
          <B24Button
            form="edit-user-form"
            type="submit"
            label="Сохранить"
            color="air-primary"
            :loading="editLoading"
          />
        </div>
      </template>
    </B24Modal>

    <!-- Change Password Modal -->
    <B24Modal
      v-if="changingUser"
      :open="Boolean(changingUser)"
      title="Смена пароля"
      :description="changingUser.username"
      @update:open="changingUser = null"
    >
      <template #body>
        <form id="change-pass-form" class="space-y-4" @submit.prevent="handleSavePassword">
          <B24FormField label="Текущий пароль" required>
            <B24Input
              v-model="currentPassword"
              type="password"
              minlength="12"
              maxlength="256"
              autocomplete="current-password"
              required
              autofocus
            />
          </B24FormField>

          <B24FormField label="Новый пароль" hint="Не менее 12 символов" required>
            <B24Input
              v-model="changeNewPassword"
              type="password"
              minlength="12"
              maxlength="256"
              autocomplete="new-password"
              required
            />
          </B24FormField>

          <B24FormField label="Подтверждение нового пароля" required>
            <B24Input
              v-model="confirmPassword"
              type="password"
              minlength="12"
              maxlength="256"
              autocomplete="new-password"
              required
            />
          </B24FormField>
        </form>
      </template>

      <template #footer>
        <div class="flex items-center justify-end gap-2 w-full">
          <B24Button
            label="Отмена"
            color="air-secondary-no-accent"
            variant="ghost"
            @click="changingUser = null"
          />
          <B24Button
            form="change-pass-form"
            type="submit"
            label="Изменить пароль"
            color="air-primary"
            :loading="changeLoading"
          />
        </div>
      </template>
    </B24Modal>

    <!-- Confirm Disable Modal -->
    <B24Modal
      v-model:open="disableConfirmOpen"
      title="Отключение пользователя"
      :description="`Вы действительно хотите отключить пользователя ${disablingUser?.username}?`"
    >
      <template #body>
        <p class="text-sm text-description">
          Пользователь больше не сможет входить в консоль управления. Это действие можно отменить только через прямое включение в базе данных или CLI.
        </p>
      </template>

      <template #footer>
        <div class="flex items-center justify-end gap-2 w-full">
          <B24Button
            label="Отмена"
            color="air-secondary-no-accent"
            variant="ghost"
            @click="disableConfirmOpen = false"
          />
          <B24Button
            label="Отключить"
            color="air-primary-alert"
            :loading="disableLoading"
            @click="handleConfirmDisable"
          />
        </div>
      </template>
    </B24Modal>
  </div>
</template>
