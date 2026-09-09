import { createRouter, createWebHistory } from "vue-router";
import { api } from "../api/client";

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
  history: createWebHistory(),
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
