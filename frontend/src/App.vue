<script setup>
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAppContext } from "./composables/useAppContext";
import HomeIcon from "@bitrix24/b24icons-vue/outline/HomeIcon";
import DeveloperResourcesIcon from "@bitrix24/b24icons-vue/outline/DeveloperResourcesIcon";
import PlayLIcon from "@bitrix24/b24icons-vue/outline/PlayLIcon";
import UserGroupIcon from "@bitrix24/b24icons-vue/common-b24/UserGroupIcon";
import LogOutIcon from "@bitrix24/b24icons-vue/outline/LogOutIcon";
import HamburgerMenuIcon from "@bitrix24/b24icons-vue/outline/HamburgerMenuIcon";

const route = useRoute();
const router = useRouter();
const { user, initializing, init, logout } = useAppContext();

onMounted(() => {
  init();
});

const isLoginRoute = computed(() => route.name === "login");

const navigationItems = computed(() => [
  {
    label: "Обзор",
    icon: HomeIcon,
    to: "/overview",
  },
  {
    label: "Серверы",
    icon: DeveloperResourcesIcon,
    to: "/servers",
  },
  {
    label: "Операции",
    icon: PlayLIcon,
    to: "/operations",
  },
  {
    label: "Пользователи",
    icon: UserGroupIcon,
    to: "/users",
  },
]);

async function handleLogout() {
  await logout();
  router.push({ name: "login" });
}
</script>

<template>
  <B24App>
    <div v-if="initializing" class="min-h-screen flex flex-col items-center justify-center gap-3 bg-default">
      <div class="w-10 h-10 rounded-lg bg-[var(--ui-color-design-filled-blue)] flex items-center justify-center text-white font-bold text-lg shadow-sm">
        B
      </div>
      <p class="text-description text-sm">Подключаемся к контроллеру…</p>
    </div>

    <template v-else>
      <RouterView v-if="isLoginRoute" />

      <B24DashboardGroup v-else unit="px" storage="local">
        <B24DashboardSidebar
          id="default"
          collapsible
          resizable
          class="border-r border-muted bg-elevated/40 backdrop-blur-sm"
        >
          <template #header="{ collapsed }">
            <div class="flex items-center gap-2 w-full px-1">
              <B24DashboardSidebarCollapse :icon="HamburgerMenuIcon" class="size-8" />
              <div v-if="!collapsed" class="flex items-center gap-2 select-none overflow-hidden">
                <div class="w-7 h-7 rounded-md bg-[var(--ui-color-design-filled-blue)] flex items-center justify-center text-white font-bold text-sm shrink-0">
                  B
                </div>
                <span class="font-bold text-label text-base tracking-tight whitespace-nowrap">BitrixVM Control</span>
              </div>
            </div>
          </template>

          <template #default="{ collapsed }">
            <B24NavigationMenu
              :collapsed="collapsed"
              :items="navigationItems"
              orientation="vertical"
              tooltip
              class="w-full"
            />
          </template>

          <template #footer="{ collapsed }">
            <div class="w-full flex flex-col gap-2 pt-2 border-t border-muted">
              <div class="flex items-center justify-between px-1" :class="{ 'flex-col gap-2': collapsed }">
                <div v-if="!collapsed" class="flex items-center gap-2 min-w-0">
                  <B24Avatar
                    :text="user?.username?.slice(0, 1)?.toUpperCase() || 'A'"
                    size="sm"
                    class="shrink-0 bg-accented font-semibold"
                  />
                  <div class="min-w-0 flex flex-col">
                    <span class="text-sm font-medium text-label truncate">{{ user?.username || "Администратор" }}</span>
                    <span class="text-xs text-muted">Контроллер</span>
                  </div>
                </div>
                <B24Avatar
                  v-else
                  :text="user?.username?.slice(0, 1)?.toUpperCase() || 'A'"
                  size="sm"
                  class="shrink-0 bg-accented font-semibold"
                />

                <B24ColorModeButton size="sm" />
              </div>

              <B24Button
                :icon="LogOutIcon"
                :label="collapsed ? undefined : 'Выйти'"
                color="air-secondary-no-accent"
                variant="ghost"
                size="sm"
                block
                @click="handleLogout"
              />
            </div>
          </template>
        </B24DashboardSidebar>

        <B24DashboardPanel class="bg-default min-h-screen">
          <template #body>
            <main class="w-full max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
              <RouterView />
            </main>
          </template>
        </B24DashboardPanel>
      </B24DashboardGroup>
    </template>
  </B24App>
</template>
