import { createRouter, createWebHashHistory, createWebHistory } from "vue-router";
import { api } from "../api/client";

const isStaticHosting =
  typeof window !== "undefined" &&
  (window.location.hostname.endsWith("github.io") ||
    window.location.hostname.endsWith("gitverse.ru") ||
    window.location.hostname.includes("pages"));

const useHash =
  import.meta.env.VITE_ROUTER_MODE === "hash" ||
  (typeof window !== "undefined" && (window.location.hash.startsWith("#/") || isStaticHosting));

const routes = [
  {
    path: "/login",
    name: "login",
    component: () => import("../views/Login.vue"),
  },
  {
    path: "/",
    redirect: "/servers",
  },
  {
    path: "/overview",
    name: "overview",
    component: () => import("../views/Overview.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/servers",
    name: "servers",
    component: () => import("../views/ServerWorkspace.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/operations",
    name: "operations",
    component: () => import("../views/OperationsView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/users",
    name: "users",
    component: () => import("../views/UsersView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/:pathMatch(.*)*",
    redirect: "/servers",
  },
];

export const router = createRouter({
  history: useHash ? createWebHashHistory() : createWebHistory(import.meta.env.BASE_URL),
  routes,
});

router.beforeEach((to, _from, next) => {
  const isAuth = api.authenticated;
  if (to.meta.requiresAuth && !isAuth) {
    next({ name: "login", query: { redirect: to.fullPath } });
  } else if (to.name === "login" && isAuth) {
    next({ name: "servers" });
  } else {
    next();
  }
});
