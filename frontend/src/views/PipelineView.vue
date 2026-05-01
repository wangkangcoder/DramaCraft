<template>
  <div class="pipeline-page">
    <div class="pipeline-shell">
      <section class="hero-panel">
        <div class="hero-copy">
          <p class="eyebrow">Story Automation Workshop</p>
          <h1>自动化工坊</h1>
          <p>
            把核心故事设定拆成几块来写，系统会自动整理成统一需求，再依次生成人物、大纲和剧本第一幕。第一幕后你可以继续在这里生成下一幕，也可以直接进入显性创作轨细化改写。
          </p>
        </div>
        <div class="hero-summary">
          <div class="summary-item">
            <span>当前步骤</span>
            <strong>{{ stepTitles[activeStep] }}</strong>
          </div>
          <div class="summary-item">
            <span>填写项</span>
            <strong>4 项</strong>
          </div>
          <div class="summary-item">
            <span>生成状态</span>
            <strong :style="activeStep > 0 ? 'color: #67c23a' : ''">{{ workshopStatusText }}</strong>
          </div>
          <div class="summary-item">
            <span>手动保存</span>
            <el-button size="small" @click="handleManualSave" style="margin-left: 8px;">
              💾 手动保存
            </el-button>
          </div>
        </div>
      </section>

      <section class="status-strip">
        <div v-for="card in summaryCards" :key="card.label" class="status-card">
          <span>{{ card.label }}</span>
          <strong>{{ shorten(card.value) || '待填写' }}</strong>
        </div>
      </section>

      <el-card shadow="never" class="main-card">
        <template #header>
          <div class="card-head">
            <div>
              <h2>分步生成流程</h2>
              <p>从核心设定开始，逐步生成角色、剧情和当前幕草稿。</p>
            </div>
            <div class="steps-nav">
              <button
                v-for="(title, index) in stepTitles"
                :key="index"
                type="button"
                class="step-tab"
                :class="{ active: index === activeStep, reached: index <= reachedStep }"
                :disabled="index > reachedStep"
                @click="jumpToStep(index)"
              >
                <span>0{{ index + 1 }}</span>
                <strong>{{ title }}</strong>
              </button>
            </div>
          </div>
        </template>

        <div v-if="loadingData" class="progress-panel">
          <div class="progress-meta">
            <div>
              <p class="progress-label">正在生成</p>
              <h3>{{ progressHeadline }}</h3>
              <p v-if="progressStageText" class="progress-stage">{{ progressStageText }}</p>
            </div>
            <div class="progress-number">{{ progressPercentText }}</div>
          </div>
          <div class="progress-track" role="progressbar" :aria-valuenow="Math.round(progressValue)" aria-valuemin="0" aria-valuemax="100">
            <div class="progress-fill" :style="{ width: `${progressValue}%` }"></div>
          </div>
          <p class="progress-target">{{ progressDisplayText }}</p>
          <div class="act-progress-strip">
            <span
              v-for="label in actStageTitles"
              :key="label"
              class="act-progress-chip"
              :class="{ active: label === progressTargetAct }"
            >
              {{ label }}
            </span>
          </div>
        </div>

        <div v-show="activeStep === 0" class="step-content">
          <div class="section-head">
            <div>
              <p class="section-tag">Step 1</p>
              <h3>填写核心设定</h3>
              <p>先选择剧本形式题材，再在对应卡片里完成 4 项核心信息。旧的输入逻辑已经全部移除，后续人物、大纲和剧本都会严格按这里的题材结构走。</p>
            </div>
            <div class="section-note">
              <el-tag type="danger" effect="dark" round>先选题材，再填写所选题材下的 4 项信息</el-tag>
            </div>
          </div>

          <div class="format-tabs" role="tablist" aria-label="剧本形式题材">
            <button
              v-for="format in scriptFormatOptions"
              :key="format.value"
              type="button"
              class="format-tab"
              :class="{ active: scriptFormat === format.value }"
              @click="scriptFormat = format.value"
            >
              {{ format.label }}
            </button>
          </div>

          <div class="format-grid">
            <section
              v-for="format in scriptFormatOptions"
              :key="format.value"
              class="format-panel"
              :class="{ active: scriptFormat === format.value }"
            >
              <div class="format-panel-head">
                <div>
                  <p class="section-tag">Form {{ format.shortLabel }}</p>
                  <h4>{{ format.label }}</h4>
                </div>
                <el-tag :type="scriptFormat === format.value ? 'primary' : 'info'" effect="plain" round>
                  {{ scriptFormat === format.value ? '当前填写区' : '未选中' }}
                </el-tag>
              </div>
              <p class="format-panel-copy">{{ format.panelHint }}</p>

              <div class="format-field-list">
                <div
                  v-for="field in format.fields"
                  :key="`${format.value}-${field.key}`"
                  class="field-card"
                  :class="{ inactive: scriptFormat !== format.value }"
                >
                  <label>{{ field.label }}</label>
                  <p>{{ field.description }}</p>
                  <el-input
                    :model-value="getFormatFieldValue(format.value, field.key)"
                    type="textarea"
                    :rows="4"
                    :disabled="scriptFormat !== format.value"
                    :placeholder="field.placeholder"
                    @update:model-value="updateFormatField(format.value, field.key, $event)"
                  />
                </div>
              </div>
            </section>
          </div>

          <div class="preview-card">
            <div class="preview-head">
              <div>
                <p class="section-tag">Auto Compiled Brief</p>
                <h4>系统整理后的需求预览</h4>
              </div>
              <span>当前已按“{{ selectedFormatConfig.label }}”结构整理，后端人物、大纲和分幕生成都会读取这套新逻辑。</span>
            </div>
            <el-input :model-value="compiledRequirements" type="textarea" :rows="12" readonly />
          </div>

          <div class="action-bar">
            <el-button
              type="primary"
              size="large"
              @click="generateCharacters"
              :loading="loadingData"
              :disabled="!hasRequiredFields"
            >
              生成人物设定
            </el-button>
          </div>
        </div>

        <div v-show="activeStep === 1" class="step-content">
          <div class="section-head">
            <div>
              <p class="section-tag">Step 2</p>
              <h3>人物设定</h3>
              <p>这里可以继续手改，确认没问题后再生成剧情大纲。</p>
            </div>
            <el-tag type="success" effect="dark" round>可编辑</el-tag>
          </div>
          <el-input
            v-model="characters"
            type="textarea"
            :rows="18"
            placeholder="这里会出现系统生成的人物设定。"
          />
          <div class="action-bar">
            <el-button type="primary" size="large" @click="generateOutline" :loading="loadingData" :disabled="generationBusy && !loadingData">
              生成剧情大纲
            </el-button>
          </div>
        </div>

        <div v-show="activeStep === 2" class="step-content">
          <div class="section-head">
            <div>
              <p class="section-tag">Step 3</p>
              <h3>剧情大纲</h3>
              <p>你可以在这里调整所选题材对应的分幕结构、冲突节奏和每一幕的推进重点，再继续生成当前幕草稿。</p>
            </div>
            <el-tag type="warning" effect="dark" round>建议检查冲突升级</el-tag>
          </div>
          <el-alert
            v-if="globalState.title"
            type="success"
            :closable="false"
            show-icon
            style="margin-bottom: 16px;"
            :title="`剧本名称：${globalState.title}`"
          />
          <el-input
            v-model="outline"
            type="textarea"
            :rows="14"
            placeholder="这里会出现系统生成的剧情大纲。"
          />
          <el-alert
            v-if="isScriptEnd"
            type="success"
            :closable="false"
            show-icon
            style="margin-top: 16px;"
            :title="lockedCompletionNoticeText"
          />

          <div class="action-bar">
            <el-button type="primary" size="large" @click="runScriptGeneration({ forceFirstAct: true })" :loading="loadingData" :disabled="generationBusy && !loadingData">
              {{ firstActButtonText }}
            </el-button>
          </div>
        </div>

        <div v-show="activeStep === 3" class="step-content">
          <div class="section-head">
            <div>
              <p class="section-tag">Step 4</p>
              <h3>当前幕草稿</h3>
              <p>自动化工坊会按当前题材进度一次产出一整幕草稿。接下来你可以继续生成下一幕，或直接进入显性创作轨细化改写。</p>
            </div>
            <el-tag type="info" effect="dark" round>可进入显性创作轨</el-tag>
          </div>
          <el-input
            v-model="script"
            type="textarea"
            :rows="22"
            placeholder="这里会出现系统生成的幕次正文。"
          />

          <el-alert
            v-if="scriptStatusAlertText"
            type="info"
            :closable="false"
            show-icon
            style="margin-top: 16px;"
            :title="scriptStatusAlertText"
          />

          <div class="advisor-panel">
            <div class="advisor-head">
              <div>
                <h4>当前幕 AI 优化建议</h4>
              </div>
              <div class="advisor-actions">
                <el-button size="small" :loading="adviceLoading" title="分析当前幕里还能补强什么、哪些句子或段落还能改得更好" @click="generateCurrentActReview">
                  一键生成AI优化建议
                </el-button>
                <el-button
                  v-if="currentActAnalysis?.has_issues && !currentActRevision"
                  size="small"
                  type="warning"
                  @click="generateCurrentActRevision"
                  :loading="revisionLoading"
                  title="基于当前优化建议生成新的优化版本"
                >
                  一键生成优化版本
                </el-button>
                <el-button
                  v-if="currentActRevision"
                  size="small"
                  type="success"
                  @click="applyCurrentActRevision"
                  :loading="applyingRevision"
                  title="将 AI 优化版本直接应用到当前幕正文"
                >
                  一键应用优化
                </el-button>
              </div>
            </div>

            <div v-if="currentActAnalysis" class="act-review-grid">
              <div class="review-block">
                <div class="review-block-head">
                  <span>建议 1</span>
                  <strong>当前幕还可以补强什么</strong>
                </div>
                <p class="review-block-summary">{{ currentActAnalysis.enhancement?.summary }}</p>
                <div
                  v-for="(item, idx) in currentActAnalysis.enhancement?.items || []"
                  :key="`missing-${idx}`"
                  class="review-item"
                >
                  <strong>补强建议 {{ idx + 1 }}</strong>
                  <p>{{ item.text }}</p>
                </div>
                <p v-if="!(currentActAnalysis.enhancement?.items || []).length" class="review-ok-text">
                  这一方面暂时没有明显补强点。
                </p>
              </div>

              <div class="review-block">
                <div class="review-block-head">
                  <span>建议 2</span>
                  <strong>哪些句子或段落还可以改得更好</strong>
                </div>
                <p class="review-block-summary">{{ currentActAnalysis.polish?.summary }}</p>
                <div
                  v-for="(item, idx) in currentActAnalysis.polish?.items || []"
                  :key="`off-outline-${idx}`"
                  class="review-item"
                >
                  <strong>{{ item.problem }}</strong>
                  <p>{{ item.reason }}</p>
                  <pre v-if="item.snippet">{{ item.snippet }}</pre>
                </div>
                <p v-if="!(currentActAnalysis.polish?.items || []).length" class="review-ok-text">
                  这一方面暂时没有明显可优化句段。
                </p>
              </div>
            </div>

            <div v-if="currentActRevision" class="revision-preview">
              <div class="revision-head">
                <div>
                  <p class="section-tag">AI Polish</p>
                  <h4>当前幕优化版本</h4>
                </div>
              <el-tag type="success" effect="dark" round>
                可直接应用
              </el-tag>
            </div>
            <el-input
              :model-value="currentActRevision.revisedAct"
              type="textarea"
              :rows="14"
              readonly
              placeholder="这里会显示 AI 生成的当前幕优化版本。"
            />
            </div>

            <div v-else-if="!currentActAnalysis && !adviceLoading && !revisionLoading" />
          </div>

          <div class="action-bar">
            <el-button 
              type="primary" 
              size="large" 
              @click="runScriptGeneration"
              :loading="loadingData"
              :disabled="generationLocked || (generationBusy && !loadingData)"
            >
              {{ nextScriptButtonText }}
            </el-button>
            <el-button plain size="large" :disabled="!script.trim()" @click="openNarrativeFingerprint">叙事指纹检测</el-button>
            <el-button type="success" size="large" @click="finishPipeline">进入显性创作轨</el-button>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, toRef, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import {
  generateCharacters as apiGenerateCharacters,
  generateOutline as apiGenerateOutline,
  generatePipelineScript,
} from '../api/ai'
import {
  generateNextAct as generateNextActAPI,
  reviewCurrentAct,
  reviseCurrentAct,
} from '../api/narrative'
import { globalState } from '../stores/project'
import { getRequestErrorMessage } from '../utils/apiError'
import { getLockedCompletionNotice } from '../utils/completionText'
import { formatActProgress, getNextActLabel } from '../utils/actProgress'
import {
  getScriptFormatActSequence,
  getScriptFormatConfig,
  getScriptFormatOptions,
  resolveScriptFormat,
} from '../utils/scriptFormat'
import { normalizeScriptText } from '../utils/scriptText'

const router = useRouter()
const activeStep = toRef(globalState, 'pipelineActiveStep')
const loadingData = ref(false)

const progressValue = ref(0)
const progressText = ref('')
const progressPhase = ref('idle')
const progressElapsedSeconds = ref(0)
const progressCap = ref(0)
const progressTargetAct = ref('')
const lastRuleValidation = ref(null)
const adviceLoading = ref(false)
const revisionLoading = ref(false)
const applyingRevision = ref(false)
const scriptCompletion = ref(null)
const currentActAnalysis = ref(null)
const currentActRevision = ref(null)
let progressTimer = null
let progressRampTimer = null

const stepTitles = ['核心设定', '人物设定', '剧情大纲', '当前幕草稿']
const scriptFormatOptions = getScriptFormatOptions()
const scriptFormat = toRef(globalState, 'pipelineScriptFormat')
const latestActReviewed = toRef(globalState, 'pipelineLatestActReviewed')
const actStageTitles = computed(() => getScriptFormatActSequence(scriptFormat.value))
const sharedGenerationBusy = computed(() => Boolean(globalState.pipelineGenerationInFlight))
const generationBusy = computed(() => loadingData.value || sharedGenerationBusy.value)
const generationInOtherView = computed(() => sharedGenerationBusy.value && !loadingData.value)

const movieCoreIdea = toRef(globalState, 'pipelineMovieCoreIdea')
const movieProtagonist = toRef(globalState, 'pipelineMovieProtagonist')
const movieConflict = toRef(globalState, 'pipelineMovieConflict')
const movieTone = toRef(globalState, 'pipelineMovieTone')
const seriesPreviousEnding = toRef(globalState, 'pipelineSeriesPreviousEnding')
const seriesCharacterFocus = toRef(globalState, 'pipelineSeriesCharacterFocus')
const seriesToneDirection = toRef(globalState, 'pipelineSeriesToneDirection')
const seriesCliffhanger = toRef(globalState, 'pipelineSeriesCliffhanger')
const microHook = toRef(globalState, 'pipelineMicroHook')
const microProtagonist = toRef(globalState, 'pipelineMicroProtagonist')
const microConflict = toRef(globalState, 'pipelineMicroConflict')
const microTone = toRef(globalState, 'pipelineMicroTone')
const isScriptEnd = ref(false) // 是否剧本结束

const requirements = toRef(globalState, 'pipelineRequirements')
const characters = toRef(globalState, 'pipelineCharacters')
const outline = toRef(globalState, 'pipelineOutline')
const script = toRef(globalState, 'scriptContent')
const completionReason = toRef(globalState, 'pipelineCompletionReason')

const formatFieldRefs = {
  movie: {
    coreIdea: movieCoreIdea,
    protagonist: movieProtagonist,
    conflict: movieConflict,
    tone: movieTone,
  },
  series: {
    previousEnding: seriesPreviousEnding,
    characterFocus: seriesCharacterFocus,
    toneDirection: seriesToneDirection,
    cliffhanger: seriesCliffhanger,
  },
  micro: {
    hook: microHook,
    protagonist: microProtagonist,
    conflict: microConflict,
    tone: microTone,
  },
}

const selectedFormatConfig = computed(() => getScriptFormatConfig(scriptFormat.value))
const selectedFormatFields = computed(() => selectedFormatConfig.value.fields || [])
const summaryCards = computed(() =>
  selectedFormatFields.value.map((field) => ({
    label: field.summaryLabel || field.label,
    value: getFormatFieldValue(scriptFormat.value, field.key),
  }))
)
const reachedStep = computed(() => {
  let step = 0
  if (characters.value.trim()) step = 1
  if (outline.value.trim()) step = 2
  if (script.value.trim()) step = 3
  return Math.max(step, activeStep.value || 0)
})

const workshopStatusText = computed(() => {
  if (loadingData.value) return '正在处理...'
  if (generationInOtherView.value) {
    return `正在生成${globalState.pipelineGenerationTargetAct || '下一幕'}`
  }
  if (activeStep.value === 0) return '准备就绪'
  if (activeStep.value === 1) return '人物设定已完成'
  if (activeStep.value === 2) return '剧情大纲已完成'
  if (script.value.trim()) {
    return formatActProgress(scriptCompletion.value, script.value, {
      scriptFormat: scriptFormat.value,
      latestActReviewed: latestActReviewed.value,
    })
  }
  return '待开始'
})

const firstActButtonText = computed(() => (script.value.trim() ? '重新生成第一幕' : '生成第一幕'))

const cleanGeneratedText = (text) => {
  return normalizeScriptText(text)
}

const resetCurrentActAssistant = () => {
  currentActAnalysis.value = null
  currentActRevision.value = null
}

const markLatestActNeedsReview = () => {
  latestActReviewed.value = false
}

const markLatestActReviewed = () => {
  latestActReviewed.value = true
}

const resetScriptProgress = (clearScript = false) => {
  syncScriptCompletion(null)
  markLatestActNeedsReview()
  resetCurrentActAssistant()
  if (clearScript) {
    script.value = ''
  }
}

const shorten = (text) => {
  const value = (text || '').trim()
  if (!value) return ''
  return value.length > 16 ? `${value.slice(0, 16)}...` : value
}

const getFormatFieldRef = (formatKey, fieldKey) => formatFieldRefs[resolveScriptFormat(formatKey)]?.[fieldKey] || null

const getFormatFieldValue = (formatKey, fieldKey) => getFormatFieldRef(formatKey, fieldKey)?.value || ''

const updateFormatField = (formatKey, fieldKey, value) => {
  const fieldRef = getFormatFieldRef(formatKey, fieldKey)
  if (fieldRef) fieldRef.value = value
}

const hasRequiredFields = computed(() =>
  selectedFormatFields.value.every((field) => getFormatFieldValue(scriptFormat.value, field.key).trim())
)

const buildRequirementsText = () => {
  const config = selectedFormatConfig.value
  const sections = [
    ['剧本形式题材', config.label],
    ['结构要求', config.outlineSections.map((item) => `${item.label}：${item.description}`).join('\n')],
    ...config.fields.map((field) => [field.label, getFormatFieldValue(scriptFormat.value, field.key)]),
  ]

  return sections
    .filter(([, value]) => value && String(value).trim())
    .map(([title, value]) => `${title}\n${value.trim()}`)
    .join('\n\n')
}

const compiledRequirements = computed(() => buildRequirementsText())
const generationLocked = computed(() => {
  if (!script.value.trim()) return false
  if (isScriptEnd.value) return true
  if (scriptCompletion.value?.generation_locked) return true
  if (scriptCompletion.value?.can_continue === false) return true
  return false
})
const lockedCompletionNoticeText = computed(() => getLockedCompletionNotice(
  scriptCompletion.value || globalState.pipelineCompletionSnapshot || null,
  latestActReviewed.value,
))
const scriptCompletionStatusText = computed(() => {
  if (!script.value.trim()) return ''
  if (loadingData.value && progressPhase.value === 'finishing') return '正在核对当前已写到哪一幕...'
  return formatActProgress(scriptCompletion.value, script.value, {
    scriptFormat: scriptFormat.value,
    latestActReviewed: latestActReviewed.value,
  })
})
const scriptStatusAlertText = computed(() => {
  if (generationLocked.value) return lockedCompletionNoticeText.value
  return scriptCompletionStatusText.value
})
const nextScriptButtonText = computed(() => {
  if (generationLocked.value) return latestActReviewed.value ? '已完结' : '已完结（未修改）'
  if (!script.value.trim()) return '生成第一幕'
  return '生成下一幕'
})

const progressHeadline = computed(() => progressText.value)

const progressStageText = computed(() => {
  if (!loadingData.value) return ''

  const phaseTextMap = {
    queued: '请求已提交',
    waiting: '大模型生成中',
    validating: '结果整理与规则检查中',
    finishing: '当前幕次核对中',
    complete: '生成完成',
  }

  const phaseText = phaseTextMap[progressPhase.value] || '处理中'
  return `${phaseText} · 已用时 ${progressElapsedSeconds.value}s`
})

const progressPercentText = computed(() => `${Math.round(progressValue.value)}%`)
const progressDisplayText = computed(() => (progressTargetAct.value ? `当前目标：${progressTargetAct.value}` : '当前目标：处理中'))

const clearProgressTimer = () => {
  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
  if (progressRampTimer) {
    clearInterval(progressRampTimer)
    progressRampTimer = null
  }
}

const startProgress = (text, targetAct = '') => {
  clearProgressTimer()
  progressValue.value = 6
  progressCap.value = 18
  progressText.value = text
  progressTargetAct.value = targetAct
  progressPhase.value = 'queued'
  progressElapsedSeconds.value = 0
  progressTimer = setInterval(() => {
    progressElapsedSeconds.value += 1
  }, 1000)
  progressRampTimer = setInterval(() => {
    if (progressValue.value >= progressCap.value) return
    const remaining = progressCap.value - progressValue.value
    const step = remaining > 16 ? 2 : remaining > 7 ? 1 : 0.4
    progressValue.value = Math.min(progressCap.value, Math.round((progressValue.value + step) * 10) / 10)
  }, 240)
}

const setProgressCheckpoint = (phase, text, percentage, cap = null) => {
  if (text) progressText.value = text
  if (phase) progressPhase.value = phase
  if (typeof percentage === 'number') {
    progressValue.value = Math.max(progressValue.value, Math.min(percentage, 99))
  }
  const fallbackCapMap = {
    queued: 18,
    waiting: 72,
    validating: 94,
    finishing: 97,
    complete: 100,
  }
  const resolvedCap =
    typeof cap === 'number'
      ? cap
      : Math.max(percentage ?? progressValue.value, fallbackCapMap[phase] ?? progressValue.value)
  progressCap.value = Math.max(progressValue.value, Math.min(resolvedCap, 99))
}

const completeProgress = async (text = '生成完成') => {
  if (text) progressText.value = text
  progressPhase.value = 'complete'
  progressCap.value = 100
  if (progressRampTimer) {
    clearInterval(progressRampTimer)
    progressRampTimer = null
  }
  await new Promise((resolve) => {
    const finalRamp = setInterval(() => {
      const remaining = 100 - progressValue.value
      if (remaining <= 0.4) {
        progressValue.value = 100
        clearInterval(finalRamp)
        resolve()
        return
      }
      const step = remaining > 18 ? 4.8 : remaining > 9 ? 2.4 : remaining > 4 ? 1.2 : 0.5
      progressValue.value = Math.min(100, Math.round((progressValue.value + step) * 10) / 10)
    }, 45)
  })
  await new Promise((resolve) => setTimeout(resolve, 180))
  clearProgressTimer()
  progressPhase.value = 'complete'
  progressValue.value = 100
}

const resetProgress = () => {
  clearProgressTimer()
  progressPhase.value = 'idle'
  progressElapsedSeconds.value = 0
  progressCap.value = 0
  progressValue.value = 0
  progressText.value = ''
  progressTargetAct.value = ''
}

const ensureRequirements = () => {
  const text = buildRequirementsText()
  requirements.value = text
  return text
}

const resolveRequestError = (error, fallbackText) => getRequestErrorMessage(error, fallbackText)

const syncRuleValidation = (result) => {
  lastRuleValidation.value = result?.data?.meta?.rule_validation || result?.data?.validation || null
}

const syncScriptCompletion = (completion = null) => {
  const snapshot = completion ? { ...completion } : null
  scriptCompletion.value = snapshot
  globalState.pipelineCompletionSnapshot = snapshot
  const generationStopped = Boolean(
    snapshot?.is_complete ||
    snapshot?.generation_locked ||
    snapshot?.can_continue === false
  )
  isScriptEnd.value = generationStopped
  completionReason.value = String(snapshot?.reason || '')
}

const ensureScriptCompletion = async (completion = null, sourceText = script.value) => {
  const normalized = cleanGeneratedText(sourceText)
  if (!normalized) {
    syncScriptCompletion(null, '')
    return null
  }

  const resolvedCompletion = completion || globalState.pipelineCompletionSnapshot || scriptCompletion.value || null
  syncScriptCompletion(resolvedCompletion)
  return resolvedCompletion
}

const generateCharacters = async () => {
  const compiled = ensureRequirements()
  if (!hasRequiredFields.value) {
    ElMessage.warning(`请先完成“${selectedFormatConfig.value.label}”下的 4 项必填信息。`)
    return
  }

  loadingData.value = true
  startProgress('正在根据核心设定生成人物设定...')
  try {
    setProgressCheckpoint('waiting', '已提交请求，正在等待模型生成人物设定...', 20)
    const result = await apiGenerateCharacters(compiled, scriptFormat.value)
    setProgressCheckpoint('validating', '模型已返回，正在整理人物设定...', 78)
    syncRuleValidation(result)
    characters.value = cleanGeneratedText(result.data.characters)
    await completeProgress('人物设定生成完成，正在写入结果...')
    activeStep.value = 1
    await forceSyncSteps()
  } catch (error) {
    console.error(error)
    ElMessage.warning(resolveRequestError(error, '人物设定生成失败，请稍后重试。'))
  } finally {
    loadingData.value = false
    if (progressPhase.value !== 'complete') resetProgress()
  }
}

const generateOutline = async () => {
  const compiled = ensureRequirements()
  loadingData.value = true
  startProgress('正在根据人物设定生成剧情大纲...')
  try {
    setProgressCheckpoint('waiting', '已提交请求，正在等待模型生成剧情大纲...', 20)
    const result = await apiGenerateOutline(compiled, characters.value, scriptFormat.value)
    setProgressCheckpoint('validating', '模型已返回，正在整理剧情大纲...', 78)
    syncRuleValidation(result)
    outline.value = cleanGeneratedText(result.data.outline)
    const generatedTitle = cleanGeneratedText(result.data.title || '')
    if (generatedTitle) {
      globalState.title = generatedTitle
    }
    resetScriptProgress(true)
    await completeProgress('剧情大纲生成完成，正在写入结果...')
    activeStep.value = 2
    await forceSyncSteps()
  } catch (error) {
    console.error(error)
    ElMessage.warning(resolveRequestError(error, '剧情大纲生成失败，请稍后重试。'))
  } finally {
    loadingData.value = false
    if (progressPhase.value !== 'complete') resetProgress()
  }
}

const runScriptGeneration = async (options = {}) => {
  const forceFirstAct = typeof options === 'boolean' ? options : Boolean(options?.forceFirstAct)
  const currentScript = cleanGeneratedText(script.value)
  const generatingFirstAct = forceFirstAct || !currentScript

  if (!generatingFirstAct && generationLocked.value) {
    ElMessage.info(lockedCompletionNoticeText.value)
    return
  }
  if (generationBusy.value && !loadingData.value) {
    ElMessage.info(`当前正在生成${globalState.pipelineGenerationTargetAct || '下一幕'}，请稍等。`)
    return
  }

  const compiled = ensureRequirements()
  resetCurrentActAssistant()
  markLatestActNeedsReview()
  lastRuleValidation.value = null

  const progressAct = generatingFirstAct
    ? '第一幕'
    : (getNextActLabel(scriptCompletion.value, scriptFormat.value, currentScript) || '下一幕')

  loadingData.value = true
  globalState.pipelineGenerationInFlight = true
  globalState.pipelineGenerationTargetAct = progressAct
  startProgress(
    generatingFirstAct
      ? '正在根据剧情大纲生成第一幕...'
      : `正在根据剧情大纲生成${progressAct}...`,
    progressAct
  )

  try {
    if (generatingFirstAct) {
      setProgressCheckpoint('waiting', '请求已提交，正在等待模型生成第一幕...', 20)
      const result = await generatePipelineScript(
        compiled,
        characters.value,
        outline.value,
        scriptFormat.value,
      )
      setProgressCheckpoint('validating', '模型已返回，正在整理第一幕正文...', 72)
      syncRuleValidation(result)
      script.value = cleanGeneratedText(result.data?.script || '')
      globalState.scriptContent = script.value
      setProgressCheckpoint('finishing', '正在同步当前幕状态...', 88)
      await ensureScriptCompletion(result.data?.completion || null, script.value)
    } else {
      setProgressCheckpoint('waiting', `请求已提交，正在等待模型生成${progressAct}...`, 20)
      const result = await generateNextActAPI(
        currentScript,
        outline.value,
        characters.value,
        compiled,
        scriptFormat.value,
      )
      syncRuleValidation(result)
      setProgressCheckpoint('validating', '模型已返回，正在整理新一幕正文...', 72)
      const nextText = cleanGeneratedText(result.data?.text || '')
      if (!nextText) {
        await ensureScriptCompletion(result.data?.completion || scriptCompletion.value || null, currentScript)
        await completeProgress('当前题材已经写到可结束的位置')
        ElMessage.info(lockedCompletionNoticeText.value)
        return
      }
      script.value = cleanGeneratedText(`${currentScript}\n\n${nextText}`)
      globalState.scriptContent = script.value
      setProgressCheckpoint('finishing', '正在同步当前幕状态...', 88)
      await ensureScriptCompletion(result.data?.completion || null, script.value)
    }

    await completeProgress('本轮生成完成，正在整理幕次结果...')
    activeStep.value = 3
    await forceSyncSteps()
    const acceptedWithIssues = Boolean(lastRuleValidation.value && !lastRuleValidation.value.is_valid)
    const progressText = formatActProgress(scriptCompletion.value, script.value, {
      scriptFormat: scriptFormat.value,
      latestActReviewed: latestActReviewed.value,
    })

    if (acceptedWithIssues) {
      ElMessage.warning(
        isScriptEnd.value
          ? '本轮剧本已生成并到达结尾，但当前幕还有待优化的细节，建议先看下方建议，再决定是否生成 AI 优化建议。'
          : `${progressText}，但当前幕还有待优化的细节，建议先看下方建议，再决定是否生成 AI 优化建议。`
      )
    } else if (isScriptEnd.value) {
      ElMessage.success(lockedCompletionNoticeText.value)
    } else {
      ElMessage.success(progressText)
    }
  } catch (error) {
    console.error(error)
    ElMessage.warning(resolveRequestError(error, '剧本幕次生成失败，请稍后重试。'))
  } finally {
    loadingData.value = false
    globalState.pipelineGenerationInFlight = false
    globalState.pipelineGenerationTargetAct = ''
    if (progressPhase.value !== 'complete') resetProgress()
  }
}

const generateCurrentActReview = async () => {
  const sourceText = cleanGeneratedText(script.value)
  if (!sourceText) {
    ElMessage.warning('请先生成当前幕正文，再生成 AI 优化建议。')
    return
  }

  adviceLoading.value = true
  currentActAnalysis.value = null
  currentActRevision.value = null
  try {
    const compiled = ensureRequirements()
    const response = await reviewCurrentAct(
      sourceText,
      outline.value || '',
      characters.value || '',
      compiled,
      scriptFormat.value,
    )
    currentActAnalysis.value = response?.data?.analysis || null
    if (!currentActAnalysis.value) {
      throw new Error('当前幕优化建议结果为空')
    }
    if (currentActAnalysis.value.has_issues) {
      markLatestActNeedsReview()
      ElMessage.warning('已生成当前幕优化建议，可以继续一键生成优化版本。')
    } else {
      markLatestActReviewed()
      ElMessage.success(generationLocked.value ? lockedCompletionNoticeText.value : '当前幕暂时没有明显需要优化的地方。')
    }
  } catch (error) {
    console.error(error)
    ElMessage.warning(resolveRequestError(error, '当前幕优化建议生成失败，请稍后重试。'))
  } finally {
    adviceLoading.value = false
  }
}

const generateCurrentActRevision = async () => {
  const sourceText = cleanGeneratedText(script.value)
  if (!sourceText) {
    ElMessage.warning('请先生成当前幕正文，再生成优化版本。')
    return
  }

  if (!currentActAnalysis.value) {
    ElMessage.warning('请先点击“一键生成AI优化建议”，确认当前幕优化方向后再生成优化版本。')
    return
  }

  revisionLoading.value = true
  currentActRevision.value = null
  try {
    const compiled = ensureRequirements()
    const analysis = currentActAnalysis.value
    if (!analysis) {
      throw new Error('当前幕优化建议结果为空')
    }

    const response = await reviseCurrentAct(
      sourceText,
      outline.value || '',
      characters.value || '',
      compiled,
      analysis,
      scriptFormat.value,
    )
    currentActAnalysis.value = response?.data?.analysis || analysis
    if (response?.data?.generated === false) {
      currentActRevision.value = null
      markLatestActReviewed()
      ElMessage.success('当前幕暂时不需要生成优化版本。')
      return
    }
    const revisedAct = cleanGeneratedText(response?.data?.revised_act || '')
    const revisedContent = cleanGeneratedText(response?.data?.revised_content || '')
    if (!revisedAct || !revisedContent) {
      throw new Error('AI 没有返回可应用的优化版本')
    }

    currentActRevision.value = {
      revisedAct,
      revisedContent,
      sourceText,
      completion: response?.data?.completion || null,
      warning: response?.data?.warning || '',
      acceptedWithIssues: Boolean(response?.data?.accepted_with_issues),
      generated: Boolean(response?.data?.generated),
    }

    ElMessage.success(
      currentActRevision.value.acceptedWithIssues
        ? 'AI 优化版本已生成，你可以先查看下面的版本，再决定是否替换当前正文。'
        : 'AI 优化版本已生成，确认后可直接应用。'
    )
  } catch (error) {
    console.error(error)
    ElMessage.warning(resolveRequestError(error, '当前幕优化版本生成失败，请稍后重试。'))
  } finally {
    revisionLoading.value = false
  }
}

const applyCurrentActRevision = async () => {
  if (!currentActRevision.value?.revisedContent) return
  if (cleanGeneratedText(script.value) !== currentActRevision.value.sourceText) {
    ElMessage.warning('当前幕正文已经变化，请重新生成优化版本，避免覆盖你刚刚的新改动。')
    return
  }

  applyingRevision.value = true
  try {
    const revision = currentActRevision.value
    if (!revision) return
    script.value = cleanGeneratedText(revision.revisedContent)
    lastRuleValidation.value = null
    await ensureScriptCompletion(revision.completion || null, script.value)
    currentActAnalysis.value = null
    currentActRevision.value = null
    if (revision.acceptedWithIssues) {
      markLatestActNeedsReview()
    } else {
      markLatestActReviewed()
    }
    ElMessage.success(
      latestActReviewed.value && generationLocked.value
        ? lockedCompletionNoticeText.value
        : 'AI 优化版本已应用到当前幕。'
    )
  } catch (error) {
    console.error(error)
    ElMessage.warning('应用 AI 优化版本失败，请稍后重试。')
  } finally {
    applyingRevision.value = false
  }
}

const handleManualSave = async () => {
  if (typeof window.saveManually === 'function') {
    const description = `自动化工坊 - 第${stepTitles[activeStep.value]}步骤`
    const result = window.saveManually(description)
    if (result) {
      ElMessage.success(`✅ 手动保存成功！最多保留 ${3} 个版本`)
    } else {
      ElMessage.info('⚠️ 内容未变化，无需保存')
    }
  } else {
    ElMessage.warning('⚠️ 手动保存功能暂不可用')
  }
}

const finishPipeline = async () => {
  globalState.scriptContent = cleanGeneratedText(script.value)
  globalState.editorRichContent = ''
  ElMessage.success('剧本草稿已整理完成，正在进入显性创作轨。')

  try {
    await router.push({ name: 'Editor' })
  } catch (error) {
    console.error(error)
    const base = import.meta.env.BASE_URL || '/'
    window.location.href = `${base}#/editor`
  }
}

const openNarrativeFingerprint = async () => {
  const scriptText = cleanGeneratedText(script.value)
  if (!scriptText) {
    ElMessage.warning('请先生成完整剧本文本，再检测叙事指纹。')
    return
  }

  globalState.scriptContent = scriptText
  try {
    await router.push({ name: 'Fingerprint', query: { autorun: '1' } })
  } catch (error) {
    console.error(error)
    const base = import.meta.env.BASE_URL || '/'
    window.location.href = `${base}#/fingerprint?autorun=1`
  }
}

const forceSyncSteps = async () => {
  await nextTick()
  await nextTick()
}

const jumpToStep = async (target) => {
  if (target < 0 || target > reachedStep.value) return
  activeStep.value = target
  await forceSyncSteps()
}

watch(
  isScriptEnd,
  (value) => {
    globalState.pipelineIsScriptEnd = Boolean(value)
  },
  { immediate: true }
)

onMounted(async () => {
  scriptFormat.value = resolveScriptFormat(scriptFormat.value)
  isScriptEnd.value = Boolean(globalState.pipelineIsScriptEnd)

  const expectedStep = Math.max(0, Math.min(3, activeStep.value || 0))
  if (globalState.pipelineActiveStep !== expectedStep) {
    globalState.pipelineActiveStep = expectedStep
  }
  syncScriptCompletion(globalState.pipelineCompletionSnapshot || null)
  await forceSyncSteps()
})

watch(
  () => globalState.pipelineCompletionSnapshot,
  (value) => {
    scriptCompletion.value = value ? { ...value } : null
    isScriptEnd.value = Boolean(
      value?.is_complete ||
      value?.generation_locked ||
      value?.can_continue === false ||
      globalState.pipelineIsScriptEnd
    )
    completionReason.value = String(value?.reason || globalState.pipelineCompletionReason || '')
  },
  { immediate: true, deep: true }
)

// 实时监控 activeStep 变化，确保步骤条100%同步
watch(activeStep, async (newVal, oldVal) => {
  if (newVal !== oldVal) {
    await nextTick()
    await nextTick()
  }
}, { immediate: true })
</script>

<style scoped>
.pipeline-page {
  min-height: 100vh;
  padding: 28px;
  background:
    radial-gradient(circle at top left, rgba(34, 115, 255, 0.16), transparent 28%),
    radial-gradient(circle at top right, rgba(10, 181, 134, 0.12), transparent 24%),
    linear-gradient(180deg, #eef3fb 0%, #f7f9fd 100%);
}

.pipeline-shell {
  max-width: 1320px;
  margin: 0 auto;
}

.hero-panel {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 20px;
  padding: 28px 32px;
  border-radius: 24px;
  color: #f8fbff;
  background:
    linear-gradient(135deg, rgba(5, 36, 88, 0.95), rgba(12, 92, 138, 0.88)),
    linear-gradient(135deg, #0f2d57, #1f7a8c);
  box-shadow: 0 18px 50px rgba(15, 45, 87, 0.18);
}

.eyebrow,
.section-tag {
  margin: 0 0 10px;
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #7a879b;
}

.hero-copy .eyebrow {
  color: rgba(248, 251, 255, 0.74);
}

.hero-copy h1 {
  margin: 0 0 10px;
  font-size: 34px;
}

.hero-copy p:last-child {
  margin: 0;
  max-width: 760px;
  line-height: 1.75;
  font-size: 15px;
  color: rgba(248, 251, 255, 0.9);
}

.hero-summary {
  display: grid;
  gap: 14px;
}

.summary-item {
  padding: 18px 20px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(10px);
}

.summary-item span,
.status-card span {
  display: block;
  margin-bottom: 8px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.72);
}

.summary-item strong {
  font-size: 19px;
}

.status-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin: 22px 0;
}

.status-card {
  padding: 18px 20px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.84);
  box-shadow: 0 10px 30px rgba(37, 70, 120, 0.08);
  border: 1px solid rgba(16, 51, 92, 0.08);
}

.status-card span {
  color: #748297;
}

.status-card strong {
  display: block;
  font-size: 16px;
  color: #10233e;
}

.main-card {
  border: none;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 18px 50px rgba(37, 70, 120, 0.08);
}

.card-head {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: center;
}

.card-head h2 {
  margin: 0;
  font-size: 22px;
  color: #10233e;
}

.card-head p {
  margin: 8px 0 0;
  color: #7a879b;
  font-size: 13px;
}

.steps-nav {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
  min-width: 420px;
}

.step-tab {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border: 1px solid rgba(16, 51, 92, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  color: #6f7f95;
  cursor: pointer;
  transition: all 0.2s ease;
}

.step-tab span {
  font-size: 12px;
  color: #7a879b;
}

.step-tab strong {
  font-size: 13px;
  color: inherit;
}

.step-tab.reached {
  color: #113661;
}

.step-tab.active {
  border-color: transparent;
  background: linear-gradient(135deg, #0f67d8, #1f8f72);
  color: #f8fbff;
  box-shadow: 0 12px 24px rgba(15, 103, 216, 0.18);
}

.step-tab.active span {
  color: rgba(248, 251, 255, 0.78);
}

.step-tab:disabled {
  opacity: 0.48;
  cursor: not-allowed;
}

.progress-panel {
  margin-bottom: 24px;
  padding: 22px;
  border-radius: 20px;
  background: linear-gradient(180deg, #f8fbff 0%, #eef5ff 100%);
  border: 1px solid rgba(59, 93, 159, 0.12);
}

.progress-track {
  position: relative;
  height: 12px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(17, 54, 97, 0.1);
  box-shadow: inset 0 1px 2px rgba(17, 54, 97, 0.08);
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #0f67d8 0%, #1d86d7 48%, #1f8f72 100%);
  box-shadow: 0 10px 20px rgba(15, 103, 216, 0.2);
  transition: width 0.18s ease-out;
}

.progress-target {
  margin: 12px 0 0;
  font-size: 13px;
  color: #4f6582;
}

.act-progress-strip {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 16px;
}

.act-progress-chip {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(16, 51, 92, 0.06);
  color: #6f7f95;
  font-size: 12px;
  font-weight: 600;
}

.act-progress-chip.active {
  background: linear-gradient(135deg, #0f67d8, #1f8f72);
  color: #f6fbff;
}

.progress-meta {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 12px;
}

.progress-label {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #6d7c92;
}

.progress-meta h3 {
  margin: 8px 0 0;
  font-size: 22px;
  color: #12305c;
}

.progress-stage {
  margin: 8px 0 0;
  font-size: 13px;
  color: #5f7291;
}

.progress-number {
  font-size: 28px;
  font-weight: 700;
  color: #0a4db3;
}

.step-content {
  padding-top: 4px;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
  margin-bottom: 20px;
}

.section-head h3 {
  margin: 0 0 8px;
  font-size: 24px;
  color: #10233e;
}

.section-head p:last-child {
  margin: 0;
  color: #70809a;
  line-height: 1.7;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.format-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 20px;
}

.format-tab {
  padding: 12px 20px;
  border: 1px solid rgba(16, 51, 92, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: #23456d;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}

.format-tab.active {
  color: #f6fbff;
  border-color: transparent;
  background: linear-gradient(135deg, #0f67d8, #1f8f72);
  box-shadow: 0 14px 26px rgba(15, 103, 216, 0.18);
}

.format-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.format-panel,
.field-card,
.wide-card,
.preview-card {
  padding: 20px;
  border-radius: 20px;
  border: 1px solid rgba(16, 51, 92, 0.08);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92) 0%, rgba(247, 250, 255, 0.9) 100%);
}

.format-panel {
  position: relative;
  border-color: rgba(16, 51, 92, 0.1);
  box-shadow: inset 0 0 0 1px rgba(16, 51, 92, 0.04);
}

.format-panel.active {
  border-color: rgba(15, 103, 216, 0.28);
  box-shadow: 0 18px 38px rgba(15, 103, 216, 0.08), inset 0 0 0 1px rgba(15, 103, 216, 0.12);
}

.format-panel-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.format-panel-head h4 {
  margin: 0;
  font-size: 22px;
  color: #10233e;
}

.format-panel-copy {
  margin: 0 0 16px;
  color: #6f8199;
  line-height: 1.7;
  font-size: 14px;
}

.format-field-list {
  display: grid;
  gap: 14px;
}

.field-card.inactive {
  opacity: 0.64;
}

.wide-card {
  box-shadow: inset 0 0 0 1px rgba(26, 100, 155, 0.06);
}

.field-card label,
.wide-card label {
  display: block;
  margin-bottom: 8px;
  font-size: 16px;
  font-weight: 700;
  color: #12263f;
}

.field-card label span,
.wide-card label span {
  margin-left: 8px;
  color: #6e7d92;
  font-size: 12px;
  font-weight: 500;
}

.field-card p,
.wide-card p {
  margin: 0 0 14px;
  color: #71829a;
  line-height: 1.7;
  font-size: 14px;
}

.wide-card,
.preview-card {
  margin-top: 18px;
}

.preview-card {
  background: linear-gradient(135deg, #f0f6ff 0%, #f8fbff 100%);
}

.advisor-panel {
  margin-top: 18px;
  padding: 16px;
  border-radius: 14px;
  background: #f7fbff;
  border: 1px solid rgba(33, 104, 173, 0.18);
}

.advisor-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 10px;
}

.advisor-head h4 {
  margin: 0;
  font-size: 15px;
  color: #12406c;
}

.advisor-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.advisor-placeholder {
  margin: 16px 0 0;
  color: #6c809d;
  font-size: 13px;
  line-height: 1.7;
}

.act-review-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-top: 16px;
}

.review-block,
.revision-preview {
  padding: 16px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(18, 64, 108, 0.1);
}

.review-block-head,
.revision-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 10px;
}

.review-block-head span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 60px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(18, 64, 108, 0.08);
  color: #12406c;
  font-size: 12px;
  font-weight: 700;
}

.review-block-head strong {
  color: #10305b;
  font-size: 15px;
  line-height: 1.5;
}

.review-block-summary {
  margin: 0 0 12px;
  color: #566b87;
  line-height: 1.7;
  font-size: 13px;
}

.review-item {
  margin-top: 10px;
  padding: 12px;
  border-radius: 10px;
  background: #f5f9ff;
}

.review-item strong {
  display: block;
  color: #10305b;
  font-size: 13px;
}

.review-item p {
  margin: 8px 0 0;
  color: #52677f;
  line-height: 1.7;
  font-size: 13px;
}

.review-item pre {
  margin: 10px 0 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: #eef4fb;
  color: #3d5570;
  white-space: pre-wrap;
  font-size: 12px;
  line-height: 1.6;
}

.review-ok-text,
.revision-warning {
  margin: 8px 0 0;
  color: #6c809d;
  font-size: 13px;
  line-height: 1.6;
}

.suggestion-applied-row {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 10px;
}

.applied-flag {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  color: #2f7d32;
  background: #e8f5e9;
  border: 1px solid rgba(47, 125, 50, 0.18);
}

.preview-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 14px;
}

.preview-head h4 {
  margin: 0;
  font-size: 20px;
  color: #10305b;
}

.preview-head span {
  max-width: 380px;
  color: #6d7c92;
  line-height: 1.6;
  font-size: 13px;
}

.action-bar {
  display: flex;
  justify-content: flex-end;
  gap: 14px;
  margin-top: 26px;
}

@media (max-width: 1100px) {
  .hero-panel,
  .status-strip {
    grid-template-columns: 1fr;
  }

  .card-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .steps-nav {
    min-width: 0;
    width: 100%;
    justify-content: flex-start;
  }
}

@media (max-width: 900px) {
  .pipeline-page {
    padding: 16px;
  }

  .field-grid {
    grid-template-columns: 1fr;
  }

  .format-grid {
    grid-template-columns: 1fr;
  }

  .act-review-grid {
    grid-template-columns: 1fr;
  }

  .preview-head,
  .section-head,
  .advisor-head {
    flex-direction: column;
  }

  .advisor-actions {
    justify-content: flex-start;
  }

  .action-bar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
