import { createRouter, createWebHashHistory } from "vue-router"
import { isAuthenticated, logout } from "./stores/auth"
import { resetProjectWorkspace } from "./stores/project"

const routes = [
  { path: "/login", name: "Login", component: () => import("./views/LoginView.vue") },
  { path: "/", name: "Pipeline", component: () => import("./views/PipelineView.vue"), meta: { requiresAuth: true } },
  { path: "/editor", name: "Editor", component: () => import("./views/EditorView.vue"), meta: { requiresAuth: true } },
  { path: "/fingerprint", name: "Fingerprint", component: () => import("./views/FingerprintView.vue"), meta: { requiresAuth: true } },
  { path: "/settings", name: "Settings", component: () => import("./views/SettingsView.vue"), meta: { requiresAuth: true } },
]

const router = createRouter({ history: createWebHashHistory(), routes })

router.beforeEach((to) => {
  if (to.query.fresh === '1') {
    logout()
    resetProjectWorkspace()
    if (to.name !== 'Login') {
      return { name: 'Login' }
    }
  }

  if (to.meta.requiresAuth && !isAuthenticated()) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }

  return true
})

export default router
