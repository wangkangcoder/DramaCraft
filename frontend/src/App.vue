<template>
  <div class="app-shell">
    <el-container class="app-layout">
      <el-header v-if="showHeader" height="76px" class="app-header">
        <div class="brand-block">
          <div class="brand-mark">AI</div>
          <div>
            <h1 class="app-title">智能剧本工作台</h1>
            <p class="app-subtitle">多阶段生成、编辑联动与叙事状态网络</p>
          </div>
        </div>

        <nav class="nav-menu">
          <router-link
            to="/"
            class="nav-link"
            title="进入自动化工坊，按步骤生成核心设定、人物设定、剧情大纲和分幕正文"
          >
            自动化工坊
          </router-link>
          <router-link
            to="/editor"
            class="nav-link"
            title="进入显性创作轨，继续精修剧本文本并按幕续写"
          >
            显性创作轨
          </router-link>
          <router-link
            to="/fingerprint"
            class="nav-link"
            title="查看剧本叙事指纹、撞款风险、赛道适配和版本时间线"
          >
            剧本叙事指纹
          </router-link>
          <router-link
            to="/settings"
            class="nav-link"
            title="进入设置中心，调整默认模型、采样参数和 API Key"
          >
            设置中心
          </router-link>
        </nav>

        <div class="user-profile">
          <el-avatar size="small">{{ (authState.user?.username || 'U').slice(0, 1).toUpperCase() }}</el-avatar>
          <div>
            <strong>{{ authState.user?.username || '创作会话' }}</strong>
            <span>{{ authState.user?.role || 'workspace_001' }}</span>
          </div>
          <el-button size="small" text title="退出当前账号并返回登录页" @click="handleLogout">退出</el-button>
        </div>
      </el-header>

      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authState, logout } from './stores/auth'

const route = useRoute()
const router = useRouter()

const showHeader = computed(() => route.name !== 'Login')

const handleLogout = () => {
  logout()
  ElMessage.success('已退出登录')
  router.replace({ name: 'Login' })
}
</script>

<style>
body {
  margin: 0;
  padding: 0;
  font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
  background: #f6f8fc;
  color: #10233e;
}

#app {
  min-height: 100vh;
}

* {
  box-sizing: border-box;
}

.app-shell {
  min-height: 100vh;
}

.app-layout {
  min-height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 0 28px;
  color: #f8fbff;
  background:
    linear-gradient(135deg, rgba(5, 36, 88, 0.96), rgba(12, 92, 138, 0.88)),
    linear-gradient(135deg, #0f2d57, #1f7a8c);
  box-shadow: 0 12px 30px rgba(15, 45, 87, 0.16);
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 280px;
}

.brand-mark {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  font-weight: 800;
  letter-spacing: 0.08em;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.16);
}

.app-title {
  margin: 0;
  font-size: 20px;
  line-height: 1.2;
}

.app-subtitle {
  margin: 4px 0 0;
  font-size: 12px;
  color: rgba(248, 251, 255, 0.72);
}

.nav-menu {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex: 1;
}

.nav-link {
  padding: 10px 16px;
  border-radius: 999px;
  color: rgba(248, 251, 255, 0.74);
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
  transition: 0.25s ease;
}

.nav-link:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.router-link-exact-active {
  color: #fff;
  background: rgba(255, 255, 255, 0.14);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12);
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 220px;
  justify-content: flex-end;
}

.user-profile strong,
.user-profile span {
  display: block;
}

.user-profile strong {
  font-size: 13px;
}

.user-profile span {
  font-size: 11px;
  color: rgba(248, 251, 255, 0.72);
}

.user-profile .el-button {
  color: #f6fbff;
}

.app-main {
  padding: 0;
  background: #f6f8fc;
}

@media (max-width: 1080px) {
  .app-header {
    height: auto !important;
    padding: 18px 20px;
    flex-wrap: wrap;
  }

  .brand-block,
  .user-profile {
    min-width: 0;
  }

  .nav-menu {
    order: 3;
    width: 100%;
    justify-content: flex-start;
    overflow-x: auto;
    padding-bottom: 2px;
  }
}
</style>
