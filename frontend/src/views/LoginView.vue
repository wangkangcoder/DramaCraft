<template>
  <div class="login-page">
    <div class="ambient"></div>
    <div class="login-shell">
      <section class="poster">
        <p class="badge">SCREENPLAY OS</p>
        <h1>欢迎进入智能剧本工作台</h1>
        <p>登录后可使用剧本生成、历史会话、个性化创作空间与指纹留存能力。</p>
        <ul>
          <li>用户身份识别，便于演示完整产品形态</li>
          <li>账号级创作空间，支持后续历史记录扩展</li>
          <li>登录态控制，实现基础权限隔离</li>
        </ul>
      </section>

      <section class="panel">
        <h2>{{ mode === 'login' ? '账号登录' : '注册账号' }}</h2>

        <el-form :model="form" :rules="rules" ref="formRef" label-position="top">
          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" placeholder="请输入用户名" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
          </el-form-item>
          <el-form-item v-if="mode === 'login'">
            <el-checkbox v-model="rememberMe" :title="rememberMeTitle">记住我</el-checkbox>
          </el-form-item>

          <el-button type="primary" :loading="loading" class="submit-btn" :title="submitButtonTitle" @click="submit">
            {{ mode === 'login' ? '登录并进入系统' : '创建账号' }}
          </el-button>
        </el-form>

        <div class="switch-line">
          <span>{{ mode === 'login' ? '没有账号？' : '已有账号？' }}</span>
          <el-button text :title="switchModeButtonTitle" @click="switchMode">{{ mode === 'login' ? '去注册' : '去登录' }}</el-button>
        </div>

        <div class="hint" v-if="mode === 'login'">
          演示账号：<code>admin</code> / <code>123456</code>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElForm, ElFormItem, ElInput, ElCheckbox, ElButton } from 'element-plus'
import { loginAPI, registerAPI } from '../api/auth'
import { loginSuccess, logout } from '../stores/auth'
import { resetProjectWorkspace } from '../stores/project'

const router = useRouter()
const route = useRoute()
const formRef = ref()
const loading = ref(false)
const rememberMe = ref(true)
const mode = ref('login')
const rememberMeTitle = '记住当前登录状态，下次打开时继续保留这个账号会话'

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' }
  ]
}

const switchMode = () => {
  mode.value = mode.value === 'login' ? 'register' : 'login'
}

const submitButtonTitle = computed(() => (
  mode.value === 'login'
    ? '使用当前账号密码登录系统，并进入你要访问的页面'
    : '创建一个新账号；注册成功后会自动切回登录模式'
))

const switchModeButtonTitle = computed(() => (
  mode.value === 'login'
    ? '切换到注册模式，创建新账号'
    : '切换回登录模式，使用已有账号登录系统'
))

onMounted(() => {
  if (route.query.fresh === '1') {
    logout()
    resetProjectWorkspace()
  }
})

const submit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    if (mode.value === 'register') {
      await registerAPI({ username: form.username.trim(), password: form.password })
      ElMessage.success('注册成功，请登录')
      mode.value = 'login'
      return
    }

    const { data } = await loginAPI({ username: form.username.trim(), password: form.password })
    loginSuccess(data.access_token, data.user, rememberMe.value)
    ElMessage.success(`欢迎回来，${data.user.username}`)

    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    router.replace(redirect)
  } catch (error) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || '操作失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  position: relative;
  overflow: hidden;
  background: radial-gradient(circle at 20% 10%, #0f4f89, transparent 45%), #071422;
}

.ambient {
  position: absolute;
  inset: 0;
  background-image: linear-gradient(rgba(80, 158, 255, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(80, 158, 255, 0.08) 1px, transparent 1px);
  background-size: 28px 28px;
  mask-image: radial-gradient(circle at center, black 30%, transparent 90%);
}

.login-shell {
  width: min(1080px, 92vw);
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  border-radius: 24px;
  overflow: hidden;
  border: 1px solid rgba(113, 181, 255, 0.2);
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(8px);
}

.poster {
  padding: 44px;
  color: #e9f3ff;
  background: linear-gradient(135deg, rgba(12, 50, 91, 0.95), rgba(14, 98, 138, 0.88));
}

.badge {
  display: inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  letter-spacing: 0.2em;
  background: rgba(255, 255, 255, 0.16);
}

.poster h1 {
  margin: 18px 0 10px;
  font-size: 40px;
  line-height: 1.15;
}

.poster p {
  line-height: 1.8;
  opacity: 0.95;
}

.poster ul {
  margin: 28px 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 12px;
}

.panel {
  padding: 34px;
  background: rgba(246, 251, 255, 0.96);
}

.panel h2 {
  margin: 0 0 16px;
  font-size: 28px;
  color: #123b63;
}

.submit-btn {
  width: 100%;
}

.switch-line {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 6px;
}

.hint {
  margin-top: 16px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #eaf5ff;
  color: #2a5d8f;
}

@media (max-width: 900px) {
  .login-shell {
    grid-template-columns: 1fr;
  }

  .poster h1 {
    font-size: 30px;
  }
}
</style>
