<template>
  <div class="settings-page">
    <div class="settings-shell">
      <section class="hero-panel">
        <div>
          <p class="eyebrow">AI Runtime Control Center</p>
          <h1>AI 模型调度与参数配置中心</h1>
          <p class="hero-copy">
            这里的配置会直接影响生成接口、三步流水线和需求生成页面。保存后立即生效，不需要重新填写项目内容。
          </p>
        </div>
        <div class="hero-actions">
          <el-button plain @click="loadSettings" :loading="loading">刷新配置</el-button>
          <el-button type="primary" @click="saveSettings" :loading="saving">保存并立即生效</el-button>
        </div>
      </section>

      <section class="status-grid">
        <article class="status-card">
          <span class="status-label">当前主引擎</span>
          <strong>{{ effectiveProviderLabel }}</strong>
          <span class="status-sub">{{ form.modelBase }}</span>
        </article>
        <article class="status-card">
          <span class="status-label">当前模型</span>
          <strong>{{ activeModel }}</strong>
          <span class="status-sub">后续生成默认使用这一模型</span>
        </article>
        <article class="status-card">
          <span class="status-label">配置状态</span>
          <strong :class="providerReady ? 'good' : 'warn'">{{ providerReady ? '已就绪' : '缺少 Key' }}</strong>
          <span class="status-sub">{{ effectiveSafetyLabel }}</span>
        </article>
      </section>

      <el-row :gutter="24" class="content-grid">
        <el-col :xs="24" :lg="16">
          <el-card shadow="never" class="main-card">
            <template #header>
              <div class="card-head">
                <div>
                  <h2>运行时设置</h2>
                  <p>保存后后端会持久化这些参数，并自动接入生成链路。</p>
                </div>
                <el-tag :type="providerReady ? 'success' : 'warning'" effect="dark">
                  {{ providerReady ? '当前配置可直接调用模型' : '当前主引擎未配置 API Key' }}
                </el-tag>
              </div>
            </template>

            <el-alert
              class="panel-alert"
              type="info"
              :closable="false"
              title="会影响的页面"
              description="设置中心、第一步需求生成、人物设定、大纲生成、剧本生成都会读取这一套运行时配置。"
            />

            <el-form label-position="top" class="settings-form">
              <div class="section-title">模型基座</div>
              <el-form-item label="默认全局调度底座">
                <el-radio-group v-model="form.modelBase" class="provider-group">
                  <el-radio-button
                    v-for="provider in providerCards"
                    :key="provider.value"
                    :label="provider.value"
                  >
                    {{ provider.label }}
                  </el-radio-button>
                </el-radio-group>
              </el-form-item>

              <el-form-item label="当前引擎默认模型">
                <el-select v-model="activeModel" class="full-width">
                  <el-option
                    v-for="model in activeProviderModels"
                    :key="model"
                    :label="model"
                    :value="model"
                  />
                </el-select>
              </el-form-item>

              <div class="section-title">API 密钥</div>
              <el-form-item label="智谱 API Key">
                <el-input
                  v-model="form.zhipuApiKey"
                  type="password"
                  show-password
                  :placeholder="maskedKeys.zhipu_api_key || '未配置时可留空'"
                />
                <div class="field-tip">
                  {{ keyStatus.zhipu_configured ? '已配置，留空则保持不变' : '未配置，建议补上后启用智谱模型' }}
                </div>
              </el-form-item>

              <el-form-item label="OpenAI API Key">
                <el-input
                  v-model="form.openaiApiKey"
                  type="password"
                  show-password
                  :placeholder="maskedKeys.openai_api_key || '未配置时可留空'"
                />
                <div class="field-tip">
                  {{ keyStatus.openai_configured ? '已配置，留空则保持不变' : '未配置，切到 OpenAI 前建议先填写' }}
                </div>
              </el-form-item>

              <el-form-item label="DeepSeek API Key">
                <el-input
                  v-model="form.deepseekApiKey"
                  type="password"
                  show-password
                  :placeholder="maskedKeys.deepseek_api_key || '未配置时可留空'"
                />
                <div class="field-tip">
                  {{ keyStatus.deepseek_configured ? '已配置，留空则保持不变' : '未配置，仅在切换到 DeepSeek 时需要' }}
                </div>
              </el-form-item>

              <div class="section-title">采样参数</div>
              <div class="slider-grid">
                <div class="slider-card">
                  <div class="slider-head">
                    <span>创意发散度</span>
                    <strong>{{ form.temperature.toFixed(2) }}</strong>
                  </div>
                  <p>值越高越大胆，值越低越稳定。</p>
                  <el-slider v-model="form.temperature" :min="0" :max="1" :step="0.05" />
                </div>

                <div class="slider-card">
                  <div class="slider-head">
                    <span>采样控制</span>
                    <strong>{{ form.topP.toFixed(2) }}</strong>
                  </div>
                  <p>控制输出的开放程度，适合和温度一起调节。</p>
                  <el-slider v-model="form.topP" :min="0" :max="1" :step="0.05" />
                </div>
              </div>

              <div class="section-title">安全审核</div>
              <el-form-item label="内容审核策略">
                <el-select v-model="form.safetyProvider" class="full-width">
                  <el-option
                    v-for="option in safetyProviderList"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </el-form-item>

              <div class="button-row">
                <el-button @click="restoreRecommended">恢复推荐值</el-button>
                <el-button @click="clearPendingKeys">清空本次新输入</el-button>
                <el-button type="primary" @click="saveSettings" :loading="saving">保存并立即生效</el-button>
              </div>
            </el-form>
          </el-card>
        </el-col>

        <el-col :xs="24" :lg="8">
          <el-card shadow="never" class="side-card">
            <template #header>
              <div class="side-head">
                <div>
                  <h3>当前生效快照</h3>
                  <p>这是后端当前会真正读取的配置。</p>
                </div>
                <div class="pulse-dot" :class="providerReady ? 'ready' : 'pending'"></div>
              </div>
            </template>

            <div class="snapshot-list">
              <div class="snapshot-item">
                <span>主引擎</span>
                <strong>{{ effectiveProviderLabel }}</strong>
              </div>
              <div class="snapshot-item">
                <span>模型</span>
                <strong>{{ activeModel }}</strong>
              </div>
              <div class="snapshot-item">
                <span>温度</span>
                <strong>{{ form.temperature.toFixed(2) }}</strong>
              </div>
              <div class="snapshot-item">
                <span>Top P</span>
                <strong>{{ form.topP.toFixed(2) }}</strong>
              </div>
              <div class="snapshot-item">
                <span>安全策略</span>
                <strong>{{ effectiveSafetyLabel }}</strong>
              </div>
            </div>

            <div class="effect-panel">
              <h4>保存后会发生什么</h4>
              <ul>
                <li>后端立即持久化到运行时配置文件</li>
                <li>需求生成页不再使用写死模型参数</li>
                <li>人物、大纲、剧本三步流水线直接读取当前设置</li>
                <li>如果当前引擎不可用，系统会自动切换到可用配置，避免生成中断</li>
              </ul>
            </div>

            <el-alert
              v-if="saveMessage"
              class="save-alert"
              type="success"
              :closable="false"
              :title="saveMessage"
            />
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElSwitch, ElSlider, ElButton, ElSelect, ElOption, ElCard } from 'element-plus'
import { getRuntimeAISettings, saveRuntimeAISettings } from '../api/ai'

const loading = ref(false)
const saving = ref(false)
const saveMessage = ref('')
const SETTINGS_CACHE_KEY = 'runtime_settings_cache_v1'

const form = reactive({
  modelBase: 'deepseek',
  zhipuModel: 'glm-4-plus',
  openaiModel: 'gpt-4o',
  deepseekModel: 'deepseek-v4-pro',
  temperature: 0.75,
  topP: 0.9,
  safetyProvider: 'tencent',
  zhipuApiKey: '',
  openaiApiKey: '',
  deepseekApiKey: ''
})

const providerOptions = ref({})
const safetyOptions = ref({})

const keyStatus = reactive({
  zhipu_configured: false,
  openai_configured: false,
  deepseek_configured: false
})

const maskedKeys = reactive({
  zhipu_api_key: '',
  openai_api_key: '',
  deepseek_api_key: ''
})

const providerCards = computed(() => {
  return Object.entries(providerOptions.value).map(([value, item]) => ({
    value,
    label: item.label
  }))
})

const activeProvider = computed(() => providerOptions.value[form.modelBase] || { label: form.modelBase, models: [] })

const activeProviderModels = computed(() => activeProvider.value.models || [])

const activeModel = computed({
  get() {
    if (form.modelBase === 'openai') return form.openaiModel
    if (form.modelBase === 'deepseek') return form.deepseekModel
    return form.zhipuModel
  },
  set(value) {
    if (form.modelBase === 'openai') form.openaiModel = value
    else if (form.modelBase === 'deepseek') form.deepseekModel = value
    else form.zhipuModel = value
  }
})

const safetyProviderList = computed(() => {
  return Object.entries(safetyOptions.value).map(([value, label]) => ({ value, label }))
})

const effectiveProviderLabel = computed(() => activeProvider.value.label || form.modelBase)
const effectiveSafetyLabel = computed(() => safetyOptions.value[form.safetyProvider] || form.safetyProvider)
const providerReady = computed(() => {
  if (form.modelBase === 'openai') return keyStatus.openai_configured
  if (form.modelBase === 'deepseek') return keyStatus.deepseek_configured
  return keyStatus.zhipu_configured
})

function applySettings(data) {
  form.modelBase = data.model_base || 'deepseek'
  form.zhipuModel = data.zhipu_model || 'glm-4-plus'
  form.openaiModel = data.openai_model || 'gpt-4o'
  form.deepseekModel = data.deepseek_model || 'deepseek-v4-pro'
  form.temperature = Number(data.temperature ?? 0.75)
  form.topP = Number(data.top_p ?? 0.9)
  form.safetyProvider = data.safety_provider || 'tencent'

  providerOptions.value = data.provider_options || {}
  safetyOptions.value = data.safety_options || {}

  keyStatus.zhipu_configured = !!data.key_status?.zhipu_configured
  keyStatus.openai_configured = !!data.key_status?.openai_configured
  keyStatus.deepseek_configured = !!data.key_status?.deepseek_configured

  maskedKeys.zhipu_api_key = data.masked_keys?.zhipu_api_key || ''
  maskedKeys.openai_api_key = data.masked_keys?.openai_api_key || ''
  maskedKeys.deepseek_api_key = data.masked_keys?.deepseek_api_key || ''

  localStorage.setItem(SETTINGS_CACHE_KEY, JSON.stringify({
    model_base: form.modelBase,
    zhipu_model: form.zhipuModel,
    openai_model: form.openaiModel,
    deepseek_model: form.deepseekModel,
    temperature: form.temperature,
    top_p: form.topP,
    safety_provider: form.safetyProvider,
    provider_options: providerOptions.value,
    safety_options: safetyOptions.value,
    key_status: {
      zhipu_configured: keyStatus.zhipu_configured,
      openai_configured: keyStatus.openai_configured,
      deepseek_configured: keyStatus.deepseek_configured,
    },
    masked_keys: {
      zhipu_api_key: maskedKeys.zhipu_api_key,
      openai_api_key: maskedKeys.openai_api_key,
      deepseek_api_key: maskedKeys.deepseek_api_key,
    },
  }))

  clearPendingKeys()
}

function clearPendingKeys() {
  form.zhipuApiKey = ''
  form.openaiApiKey = ''
  form.deepseekApiKey = ''
}

function restoreRecommended() {
  form.modelBase = 'deepseek'
  form.temperature = 0.75
  form.topP = 0.9
  form.safetyProvider = 'tencent'

  if ((providerOptions.value.zhipu?.models || []).includes('glm-4-plus')) {
    form.zhipuModel = 'glm-4-plus'
  }
  if ((providerOptions.value.openai?.models || []).includes('gpt-4o')) {
    form.openaiModel = 'gpt-4o'
  }
  if ((providerOptions.value.deepseek?.models || []).includes('deepseek-v4-pro')) {
    form.deepseekModel = 'deepseek-v4-pro'
  }
}

async function loadSettings() {
  loading.value = true
  try {
    const { data } = await getRuntimeAISettings()
    applySettings(data)
  } catch (error) {
    console.error(error)
    const cached = localStorage.getItem(SETTINGS_CACHE_KEY)
    if (cached) {
      try {
        applySettings(JSON.parse(cached))
        ElMessage.warning('后端暂时不可达，已显示上次缓存配置。')
      } catch {
        ElMessage.error('读取运行时配置失败')
      }
    } else {
      ElMessage.error('读取运行时配置失败')
    }
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  saveMessage.value = ''
  try {
    const payload = {
      model_base: form.modelBase,
      zhipu_model: form.zhipuModel,
      openai_model: form.openaiModel,
      deepseek_model: form.deepseekModel,
      temperature: Number(form.temperature),
      top_p: Number(form.topP),
      safety_provider: form.safetyProvider
    }

    if (form.zhipuApiKey.trim()) payload.zhipu_api_key = form.zhipuApiKey.trim()
    if (form.openaiApiKey.trim()) payload.openai_api_key = form.openaiApiKey.trim()
    if (form.deepseekApiKey.trim()) payload.deepseek_api_key = form.deepseekApiKey.trim()

    const { data } = await saveRuntimeAISettings(payload)
    applySettings(data)
    saveMessage.value = `已保存，当前默认使用 ${effectiveProviderLabel.value} / ${activeModel.value}`
    ElMessage.success('配置已保存并立即生效')
  } catch (error) {
    console.error(error)
    ElMessage.error('保存设置失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
.settings-page {
  min-height: 100vh;
  padding: 28px;
  background:
    radial-gradient(circle at top left, rgba(34, 115, 255, 0.16), transparent 28%),
    radial-gradient(circle at top right, rgba(10, 181, 134, 0.14), transparent 24%),
    linear-gradient(180deg, #eef3fb 0%, #f6f8fc 100%);
}

.settings-shell {
  max-width: 1320px;
  margin: 0 auto;
}

.hero-panel {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 24px;
  margin-bottom: 22px;
  padding: 28px 32px;
  border-radius: 24px;
  color: #f8fbff;
  background:
    linear-gradient(135deg, rgba(5, 36, 88, 0.95), rgba(12, 92, 138, 0.88)),
    linear-gradient(135deg, #0f2d57, #1f7a8c);
  box-shadow: 0 18px 50px rgba(15, 45, 87, 0.18);
}

.eyebrow {
  margin: 0 0 10px;
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  opacity: 0.72;
}

.hero-panel h1 {
  margin: 0;
  font-size: 34px;
  line-height: 1.2;
}

.hero-copy {
  max-width: 760px;
  margin: 12px 0 0;
  font-size: 15px;
  line-height: 1.75;
  opacity: 0.9;
}

.hero-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
  margin-bottom: 24px;
}

.status-card {
  padding: 20px 22px;
  border: 1px solid rgba(16, 51, 92, 0.08);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 10px 30px rgba(37, 70, 120, 0.08);
  backdrop-filter: blur(8px);
}

.status-label {
  display: block;
  margin-bottom: 8px;
  font-size: 12px;
  color: #6b7890;
}

.status-card strong {
  display: block;
  font-size: 22px;
  color: #12263f;
}

.status-sub {
  display: block;
  margin-top: 8px;
  color: #71829a;
  font-size: 13px;
}

.good {
  color: #108a57 !important;
}

.warn {
  color: #d97706 !important;
}

.content-grid {
  margin-top: 0;
}

.main-card,
.side-card {
  border: none;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 18px 50px rgba(37, 70, 120, 0.08);
}

.card-head,
.side-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.card-head h2,
.side-head h3 {
  margin: 0;
  font-size: 20px;
  color: #10233e;
}

.card-head p,
.side-head p {
  margin: 6px 0 0;
  font-size: 13px;
  color: #7a879b;
}

.panel-alert {
  margin-bottom: 24px;
  border-radius: 16px;
}

.settings-form {
  padding-top: 4px;
}

.section-title {
  margin: 10px 0 14px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: #6d7c92;
  text-transform: uppercase;
}

.provider-group {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.full-width {
  width: 100%;
}

.field-tip {
  margin-top: 8px;
  font-size: 12px;
  color: #7d8796;
}

.slider-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 8px;
}

.slider-card {
  padding: 18px;
  border-radius: 18px;
  background: linear-gradient(180deg, #f8fbff 0%, #f1f6ff 100%);
  border: 1px solid rgba(46, 103, 181, 0.12);
}

.slider-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.slider-head span {
  color: #3b4b63;
  font-weight: 600;
}

.slider-head strong {
  font-size: 18px;
  color: #0a4db3;
}

.slider-card p {
  margin: 0 0 16px;
  color: #70809a;
  font-size: 13px;
}

.button-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 28px;
}

.snapshot-list {
  display: grid;
  gap: 14px;
  margin-bottom: 22px;
}

.snapshot-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-radius: 16px;
  background: #f5f8fc;
}

.snapshot-item span {
  color: #6f7f95;
  font-size: 13px;
}

.snapshot-item strong {
  color: #10233e;
}

.effect-panel {
  padding: 18px;
  border-radius: 18px;
  background: linear-gradient(180deg, #132c52, #0d5e84);
  color: #f7fbff;
}

.effect-panel h4 {
  margin: 0 0 14px;
  font-size: 16px;
}

.effect-panel ul {
  margin: 0;
  padding-left: 18px;
  line-height: 1.8;
  font-size: 13px;
}

.save-alert {
  margin-top: 18px;
  border-radius: 14px;
}

.pulse-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  box-shadow: 0 0 0 8px rgba(36, 99, 235, 0.08);
}

.pulse-dot.ready {
  background: #16a34a;
}

.pulse-dot.pending {
  background: #f59e0b;
}

@media (max-width: 1080px) {
  .status-grid {
    grid-template-columns: 1fr;
  }

  .slider-grid {
    grid-template-columns: 1fr;
  }

  .hero-panel {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 768px) {
  .settings-page {
    padding: 16px;
  }

  .hero-panel {
    padding: 24px 20px;
  }

  .hero-panel h1 {
    font-size: 28px;
  }
}
</style>
