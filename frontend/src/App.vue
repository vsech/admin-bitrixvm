<script setup>
import { ref, computed, watch, onMounted } from "vue";
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

const mobileSidebarOpen = ref(false);

onMounted(() => {
  init();
});

watch(
  () => route.fullPath,
  () => {
    mobileSidebarOpen.value = false;
  }
);

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

function isRouteActive(to) {
  if (to === "/overview") {
    return route.path === "/overview";
  }
  if (to === "/servers") {
    return route.path === "/servers" || route.path === "/";
  }
  return route.path === to || route.path.startsWith(to + "/");
}

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
          v-model:open="mobileSidebarOpen"
          collapsible
          resizable
          toggle-side="right"
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
          <template #header>
            <div class="lg:hidden flex items-center justify-between h-14 px-4 border-b border-muted bg-elevated/80 backdrop-blur-md sticky top-0 z-20">
              <div class="flex items-center gap-2.5 min-w-0">
                <B24Button
                  :icon="HamburgerMenuIcon"
                  variant="ghost"
                  color="air-secondary-no-accent"
                  size="sm"
                  class="size-8 shrink-0"
                  aria-label="Открыть меню навигации"
                  @click="mobileSidebarOpen = true"
                />
                <div class="flex items-center gap-2 select-none min-w-0">
                  <div class="w-7 h-7 rounded-md bg-[var(--ui-color-design-filled-blue)] flex items-center justify-center text-white font-bold text-xs shrink-0 shadow-sm">
                    B
                  </div>
                  <span class="font-bold text-label text-sm tracking-tight truncate">BitrixVM Control</span>
                </div>
              </div>

              <div class="flex items-center gap-2 shrink-0">
                <B24ColorModeButton size="sm" />
                <B24Avatar
                  :text="user?.username?.slice(0, 1)?.toUpperCase() || 'A'"
                  size="sm"
                  class="shrink-0 bg-accented font-semibold"
                />
              </div>
            </div>
          </template>

          <template #body>
            <main class="w-full max-w-7xl mx-auto p-4 sm:p-6 lg:p-8 pb-20 sm:pb-24 lg:pb-8">
              <RouterView />
            </main>
          </template>
        </B24DashboardPanel>

        <!-- Mobile Bottom Navigation Bar -->
        <nav
          class="fixed bottom-0 inset-x-0 z-30 lg:hidden border-t border-muted bg-elevated/95 backdrop-blur-md pb-[env(safe-area-inset-bottom,0px)] shadow-lg"
          aria-label="Основная навигация"
        >
          <div class="grid grid-cols-4 h-14 max-w-lg mx-auto">
            <RouterLink
              v-for="item in navigationItems"
              :key="item.to"
              :to="item.to"
              class="flex flex-col items-center justify-center gap-1 transition-colors relative py-1"
              :class="[
                isRouteActive(item.to)
                  ? 'text-[var(--ui-color-design-filled-blue)] font-medium'
                  : 'text-muted hover:text-label'
              ]"
            >
              <div
                v-if="isRouteActive(item.to)"
                class="absolute top-0 inset-x-4 h-0.5 bg-[var(--ui-color-design-filled-blue)] rounded-full"
              />
              <component :is="item.icon" class="size-5 shrink-0" />
              <span class="text-[11px] leading-tight tracking-tight truncate max-w-[72px]">
                {{ item.label }}
              </span>
            </RouterLink>
          </div>
        </nav>
      </B24DashboardGroup>
    </template>
  </B24App>
</template>
