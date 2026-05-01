<template>
  <div class="editor-page">
    <section class="hero">
      <div>
        <p class="kicker">Visible Writing Track</p>
        <h1>显性创作轨</h1>
        <p class="hero-copy">在这里继续修改和完善当前剧本。你可以按幕续写、查看优化建议、恢复历史版本，也可以直接导出当前成稿。</p>
      </div>
      <div class="hero-actions">
        <span class="chip">{{ statusText }}</span>
        <el-button type="primary" :loading="loading" :disabled="!canGenerateNextAct" title="根据当前剧本文本继续生成下一幕" @click="generateNextAct">{{ nextActButtonText }}</el-button>
        <el-button plain :disabled="!normalizeText(code)" title="基于当前完整剧本文本生成叙事指纹报告" @click="openNarrativeFingerprint">叙事指纹检测</el-button>
        <el-button v-if="!showSeriesCompletionActions" plain title="导出当前剧本文本为 PDF" @click="exportPdf">导出 PDF</el-button>
        <el-button plain title="查看并恢复历史自动存档版本" @click="showVersionHistory = true">时光机（{{ versionHistory.length }}）</el-button>
      </div>
    </section>

    <section class="metrics">
      <article class="metric">
        <span>文本长度</span>
        <strong>{{ contentStats.characters }}</strong>
      </article>
      <article class="metric">
        <span>段落数量</span>
        <strong>{{ contentStats.paragraphs }}</strong>
      </article>
      <article class="metric">
        <span>剧本状态</span>
        <strong>{{ outlineStatusText }}</strong>
      </article>
    </section>

    <section v-if="locked" class="done-banner">
      <div>
        <strong>{{ latestActReviewed ? '剧本已到达当前收口点' : '当前题材已生成到最后一幕' }}</strong>
        <p>{{ completionMessage }}</p>
      </div>
      <div v-if="showSeriesCompletionActions" class="done-actions">
        <el-button plain :loading="preparingNextEpisode" title="导出当前集 PDF，并自动进入下一集创作" @click="exportPdfAndContinueSeries">生成下一集并生成当前集 PDF</el-button>
        <el-button type="success" plain :disabled="preparingNextEpisode" title="当前为最后一集，仅导出本集 PDF" @click="exportPdf">当前是最后一集生成 PDF</el-button>
      </div>
      <el-button v-else type="success" plain title="导出当前剧本文本为 PDF" @click="exportPdf">导出 PDF</el-button>
    </section>

    <div class="layout">
      <div class="main-col">
        <section class="card editor-card">
          <header class="card-head">
            <div>
              <p class="kicker dark">Visible Track</p>
              <h2>显性创作轨</h2>
            </div>
            <span class="pill">{{ editorStatusText }}</span>
          </header>
          <div class="editor-toolbar">
            <div class="toolbar-group">
              <el-button size="small" :type="editorMode === 'rich' ? 'primary' : 'default'" @click="setEditorMode('rich')">可视化排版</el-button>
              <el-button size="small" :type="editorMode === 'plain' ? 'primary' : 'default'" @click="setEditorMode('plain')">纯文本模式</el-button>
              <el-button size="small" plain @click="applyEmphasisMark">强调</el-button>
              <el-button size="small" plain @click="applyHighlightMark">高亮</el-button>
              <el-button size="small" plain @click="clearVisualMark">清除标记</el-button>
            </div>
            <div class="toolbar-group">
              <el-button size="small" plain @click="insertActSection">插入幕节</el-button>
              <el-button size="small" plain @click="insertSceneNumber">插入场次</el-button>
              <el-button size="small" plain @click="insertSceneHeading('内景')">插入内景</el-button>
              <el-button size="small" plain @click="insertSceneHeading('外景')">插入外景</el-button>
              <el-button size="small" plain @click="insertDialogueBlock">插入对白</el-button>
              <el-button size="small" plain @click="normalizeCurrentScript">整理格式</el-button>
            </div>
          </div>

          <div v-show="editorMode === 'rich'" class="rich-shell">
            <div class="rich-shell-head">
              <span>排版视图</span>
              <p>当前内容会按剧本结构展示，方便你直接阅读和修改。</p>
            </div>
            <div
              ref="richEditorRef"
              class="rich-editor"
              contenteditable="true"
              spellcheck="false"
              @focus="handleRichFocus"
              @blur="handleRichBlur"
              @input="handleRichInput"
            ></div>
          </div>

          <textarea
            v-show="editorMode === 'plain'"
            ref="plainTextareaRef"
            v-model="code"
            class="editor-textarea"
            spellcheck="false"
            placeholder="这里是剧本文本正文，支持正常左键选字、滚轮滚动和直接编辑。"
          ></textarea>
        </section>

        <section class="card advice-card">
          <header class="card-head light">
            <div>
              <p class="kicker muted">AI Notes</p>
              <h2>当前幕 AI 优化建议</h2>
            </div>
            <div class="advice-actions">
              <el-button size="small" :loading="adviceLoading" title="分析当前幕里还能补强什么、哪些句子或段落还能改得更好" @click="generateCurrentActReview">一键生成AI优化建议</el-button>
              <el-button
                v-if="currentActAnalysis?.has_issues && !currentActRevision"
                size="small"
                type="warning"
                :loading="revisionLoading"
                title="基于当前优化建议生成新的优化版本"
                @click="generateCurrentActRevision"
              >
                一键生成优化版本
              </el-button>
              <el-button
                v-if="currentActRevision"
                size="small"
                type="success"
                :loading="applyingRevision"
                title="将 AI 优化版本直接应用到当前幕正文"
                @click="applyCurrentActRevision"
              >
                一键应用优化
              </el-button>
            </div>
          </header>

          <div class="advice-body">
            <div v-if="currentActAnalysis" class="review-grid">
              <article class="review-card">
                <div class="review-card-head">
                  <span>建议 1</span>
                  <strong>当前幕还可以补强什么</strong>
                </div>
                <p class="review-summary">{{ currentActAnalysis.enhancement?.summary }}</p>
                <div
                  v-for="(item, idx) in currentActAnalysis.enhancement?.items || []"
                  :key="`editor-missing-${idx}`"
                  class="review-row"
                >
                  <strong>补强建议 {{ idx + 1 }}</strong>
                  <p>{{ item.text }}</p>
                </div>
                <p v-if="!(currentActAnalysis.enhancement?.items || []).length" class="review-ok">
                  这一方面暂时没有明显补强点。
                </p>
              </article>

              <article class="review-card">
                <div class="review-card-head">
                  <span>建议 2</span>
                  <strong>哪些句子或段落还可以改得更好</strong>
                </div>
                <p class="review-summary">{{ currentActAnalysis.polish?.summary }}</p>
                <div
                  v-for="(item, idx) in currentActAnalysis.polish?.items || []"
                  :key="`editor-off-outline-${idx}`"
                  class="review-row"
                >
                  <strong>{{ item.problem }}</strong>
                  <p>{{ item.reason }}</p>
                  <pre v-if="item.snippet">{{ item.snippet }}</pre>
                </div>
                <p v-if="!(currentActAnalysis.polish?.items || []).length" class="review-ok">
                  这一方面暂时没有明显可优化句段。
                </p>
              </article>
            </div>

            <section v-if="currentActRevision" class="revision-box">
              <div class="revision-box-head">
                <div>
                  <p class="kicker muted">AI Polish</p>
                  <h3>当前幕优化版本</h3>
                </div>
                <span class="pill">
                  可直接应用
                </span>
              </div>
              <textarea :value="currentActRevision.revisedAct" class="revision-textarea" readonly />
            </section>

            <div v-else-if="!currentActAnalysis" />
          </div>
        </section>
      </div>

      <section class="card graph-card">
        <header class="card-head">
          <div>
            <p class="kicker dark">Hidden Planning Track</p>
            <h2>隐性规划轨</h2>
          </div>
          <span class="pill blue">叙事状态网络</span>
        </header>
        <div class="legend">
          <span><i class="dot character"></i>角色</span>
          <span><i class="dot scene"></i>场景</span>
          <span><i class="dot foreshadow"></i>伏笔</span>
        </div>
        <div ref="chartRef" class="chart"></div>
      </section>
    </div>

    <el-dialog v-model="showVersionHistory" title="时光机 - 版本历史" width="720px" :close-on-click-modal="false">
      <el-empty v-if="!versionHistory.length" description="还没有可恢复的自动存档。" />
      <div v-else class="version-list">
        <article v-for="(version, idx) in versionHistory" :key="version.id" class="version-card" :class="{ latest: idx === 0 }">
          <div class="version-head">
            <div class="version-meta">
              <el-tag size="small" :type="idx === 0 ? 'success' : 'info'">{{ idx === 0 ? '最新版本' : `#${versionHistory.length - idx}` }}</el-tag>
              <strong>{{ version.savedAtReadable }}</strong>
            </div>
            <el-button size="small" type="primary" plain :loading="restoringVersion === version.id" title="用该历史版本覆盖当前内容" @click="restoreToVersion(version)">恢复到此版本</el-button>
          </div>
          <pre class="version-preview">{{ getVersionPreview(version) }}</pre>
        </article>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import {
  generateNextAct as generateNextActAPI,
  reviewCurrentAct,
  reviseCurrentAct,
  syncNarrativeGraph,
} from '../api/narrative'
import { generateSeriesNextEpisodePrefill } from '../api/ai'
import { globalState, queueNextSeriesEpisode } from '../stores/project'
import { getRequestErrorMessage } from '../utils/apiError'
import { getLockedCompletionNotice } from '../utils/completionText'
import { formatActProgress, getCurrentActLabel, getNextActLabel } from '../utils/actProgress'
import { openScreenplayPdfWindow } from '../utils/pdfExport'
import { resolveScriptFormat } from '../utils/scriptFormat'
import { buildScreenplayTitle } from '../utils/screenplayTitle'
import { normalizeScriptText } from '../utils/scriptText'

const AUTOSAVE_KEY = 'AI_SCREENPLAY_VERSIONS_V2'
const router = useRouter()
const chartRef = ref(null)
const richEditorRef = ref(null)
const plainTextareaRef = ref(null)

const ACT_SECTION_PATTERN = /^第[一二三四五六七八九十百零\d]+幕[·.、-]?第[一二三四五六七八九十百零\d]+节$/
const SCENE_NUMBER_PATTERN = /^第[一二三四五六七八九十百零\d]+场$/
const DIALOGUE_SPEAKER_PATTERN = /^[\u4e00-\u9fff]{2,6}$/

const escapeHtml = (text = '') => String(text)
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;')

const normalizeText = (text, trim = true) => normalizeScriptText(text, { trim })
const resolveRequestError = (error, fallbackText) => getRequestErrorMessage(error, fallbackText)
const resolveCurrentTitle = (content = code.value) => buildScreenplayTitle(globalState.title, content)

const code = ref(normalizeText(globalState.scriptContent || '', false))
const editorMode = ref('rich')
const richEditorFocused = ref(false)
const richEditorHtml = ref(String(globalState.editorRichContent || ''))
const codeUpdateSource = ref('init')
const loading = ref(false)
const showVersionHistory = ref(false)
const versionHistory = ref([])
const restoringVersion = ref(null)
const currentActAnalysis = ref(null)
const currentActRevision = ref(null)
const adviceLoading = ref(false)
const revisionLoading = ref(false)
const applyingRevision = ref(false)
const preparingNextEpisode = ref(false)
const completionState = ref(globalState.pipelineCompletionSnapshot || null)
const scriptFormat = computed(() => globalState.pipelineScriptFormat || 'movie')
const isSeriesScript = computed(() => resolveScriptFormat(scriptFormat.value) === 'series')
const latestActReviewed = computed(() => Boolean(globalState.pipelineLatestActReviewed))
const sharedGenerationBusy = computed(() => Boolean(globalState.pipelineGenerationInFlight))
const generationBusy = computed(() => loading.value || sharedGenerationBusy.value)
const generationInOtherView = computed(() => sharedGenerationBusy.value && !loading.value)

const contentStats = computed(() => ({ characters: (code.value || '').length, paragraphs: (code.value || '').split('\n').map((line) => line.trim()).filter(Boolean).length }))
const hasOutline = computed(() => Boolean(normalizeText(globalState.pipelineOutline || '')))
const completionLockedByState = computed(() => Boolean(
  globalState.pipelineIsScriptEnd ||
  completionState.value?.is_complete ||
  completionState.value?.generation_locked ||
  completionState.value?.can_continue === false
))
const currentActLabel = computed(() => getCurrentActLabel(completionState.value, code.value, scriptFormat.value))
const nextActLabel = computed(() => getNextActLabel(completionState.value, scriptFormat.value, code.value))
const locked = computed(() => completionLockedByState.value)
const showSeriesCompletionActions = computed(() => locked.value && isSeriesScript.value)
const outlineStatusText = computed(() => {
  if (!normalizeText(code.value)) return '尚未生成剧本'
  return formatActProgress(completionState.value, code.value, {
    scriptFormat: scriptFormat.value,
    latestActReviewed: latestActReviewed.value,
  })
})
const lockedCompletionNotice = computed(() => getLockedCompletionNotice(
  completionState.value || globalState.pipelineCompletionSnapshot || null,
  latestActReviewed.value,
))
const completionMessage = computed(() => {
  if (locked.value) return lockedCompletionNotice.value
  return '当前剧本仍在推进中。'
})
const canGenerateNextAct = computed(() => !generationBusy.value && !locked.value && Boolean(normalizeText(code.value)))
const nextActButtonText = computed(() => {
  if (generationBusy.value) return `正在生成${globalState.pipelineGenerationTargetAct || nextActLabel.value || '下一幕'}`
  if (locked.value) return latestActReviewed.value ? '已完结' : '已完结（未修改）'
  return '生成下一幕'
})
const statusText = computed(() => {
  if (loading.value) return `正在生成${nextActLabel.value || '下一幕'}`
  if (generationInOtherView.value) return `正在生成${globalState.pipelineGenerationTargetAct || nextActLabel.value || '下一幕'}`
  if (locked.value) return latestActReviewed.value ? '已完结，可生成 PDF' : '已完结（未修改）'
  return outlineStatusText.value
})
const editorStatusText = computed(() => {
  if (generationBusy.value) return '生成中'
  if (locked.value) return latestActReviewed.value ? '已完结' : '已完结（未修改）'
  return latestActReviewed.value ? '当前幕已确认' : '当前幕待复核'
})

const resetCurrentActAssistant = () => {
  currentActAnalysis.value = null
  currentActRevision.value = null
}

const classifyScriptLine = (line = '') => {
  const trimmed = String(line).trim()
  if (!trimmed) return 'spacer'
  if (ACT_SECTION_PATTERN.test(trimmed)) return 'act'
  if (SCENE_NUMBER_PATTERN.test(trimmed)) return 'scene-number'
  if (trimmed.startsWith('内景') || trimmed.startsWith('外景')) return 'scene-heading'
  if (DIALOGUE_SPEAKER_PATTERN.test(trimmed)) return 'speaker'
  return 'body'
}

const buildRichEditorHtml = (text = '') => {
  const source = normalizeText(text, false)
  const lines = source ? source.split('\n') : ['']
  return lines.map((line) => {
    const type = classifyScriptLine(line)
    if (type === 'spacer') {
      return '<div class="rich-line rich-spacer"><br></div>'
    }
    return `<div class="rich-line rich-${type}">${escapeHtml(line) || '<br>'}</div>`
  }).join('')
}

const getFallbackRichHtml = (text = code.value) => buildRichEditorHtml(text)

const persistRichEditorHtml = () => {
  const currentHtml = String(richEditorRef.value?.innerHTML || '')
  richEditorHtml.value = currentHtml || getFallbackRichHtml(code.value)
  globalState.editorRichContent = richEditorHtml.value
}

const resetRichMarkupFromPlainText = (text = code.value) => {
  richEditorHtml.value = getFallbackRichHtml(text)
  globalState.editorRichContent = richEditorHtml.value
}

const readRichEditorText = () => {
  const raw = String(richEditorRef.value?.innerText || '')
    .replace(/\u00A0/g, ' ')
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
  return normalizeText(raw, false)
}

const syncRichEditorFromCode = () => {
  if (!richEditorRef.value || richEditorFocused.value) return
  const nextHtml = richEditorHtml.value || getFallbackRichHtml(code.value)
  if (richEditorRef.value.innerHTML !== nextHtml) {
    richEditorRef.value.innerHTML = nextHtml
  }
}

const setEditorMode = async (mode) => {
  if (mode === editorMode.value) return
  if (editorMode.value === 'rich') {
    updateCodeValue(readRichEditorText(), { preserveWhitespace: true, source: 'rich' })
    persistRichEditorHtml()
  }
  editorMode.value = mode
  await nextTick()
  if (editorMode.value === 'rich') {
    syncRichEditorFromCode()
  } else {
    plainTextareaRef.value?.focus()
  }
}

const updateCodeValue = (nextText, { preserveWhitespace = false, source = 'plain' } = {}) => {
  codeUpdateSource.value = source
  code.value = normalizeText(nextText, !preserveWhitespace)
  globalState.scriptContent = normalizeText(code.value)
}

const handleRichInput = () => {
  persistRichEditorHtml()
  updateCodeValue(readRichEditorText(), { preserveWhitespace: true, source: 'rich' })
}

const handleRichFocus = () => {
  richEditorFocused.value = true
}

const handleRichBlur = () => {
  richEditorFocused.value = false
  persistRichEditorHtml()
  updateCodeValue(readRichEditorText(), { preserveWhitespace: true, source: 'rich' })
}

const ensureRichSelection = () => {
  if (editorMode.value !== 'rich') {
    ElMessage.info('强调和高亮仅在可视化排版模式下可用。')
    return false
  }

  richEditorRef.value?.focus()
  const selection = window.getSelection()
  const hasText = Boolean(selection && selection.rangeCount > 0 && String(selection.toString() || '').trim())
  if (!hasText) {
    ElMessage.info('请先在可视化排版区域选中需要标记的文字。')
    return false
  }
  return true
}

const refreshRichMarkupAfterCommand = () => {
  persistRichEditorHtml()
  updateCodeValue(readRichEditorText(), { preserveWhitespace: true, source: 'rich' })
}

const applyEmphasisMark = () => {
  if (!ensureRichSelection()) return
  document.execCommand('bold', false)
  refreshRichMarkupAfterCommand()
}

const applyHighlightMark = () => {
  if (!ensureRichSelection()) return
  document.execCommand('styleWithCSS', false, true)
  document.execCommand('foreColor', false, '#7ee7ff')
  refreshRichMarkupAfterCommand()
}

const clearVisualMark = () => {
  if (!ensureRichSelection()) return
  document.execCommand('removeFormat', false)
  refreshRichMarkupAfterCommand()
}

const insertTextAtCursor = (text) => {
  if (!text) return

  if (editorMode.value === 'plain') {
    const textarea = plainTextareaRef.value
    const source = code.value || ''
    const start = textarea?.selectionStart ?? source.length
    const end = textarea?.selectionEnd ?? source.length
    const nextValue = `${source.slice(0, start)}${text}${source.slice(end)}`
    richEditorHtml.value = ''
    globalState.editorRichContent = ''
    updateCodeValue(nextValue, { preserveWhitespace: true, source: 'plain' })
    nextTick(() => {
      if (!textarea) return
      textarea.focus()
      const position = start + text.length
      textarea.setSelectionRange(position, position)
    })
    return
  }

  richEditorRef.value?.focus()
  if (document.queryCommandSupported?.('insertText')) {
    document.execCommand('insertText', false, text)
  } else {
    const selection = window.getSelection()
    if (!selection?.rangeCount) {
      richEditorRef.value?.append(document.createTextNode(text))
    } else {
      const range = selection.getRangeAt(0)
      range.deleteContents()
      range.insertNode(document.createTextNode(text))
      range.collapse(false)
      selection.removeAllRanges()
      selection.addRange(range)
    }
  }
  persistRichEditorHtml()
  updateCodeValue(readRichEditorText(), { preserveWhitespace: true, source: 'rich' })
}

const extractNextSceneNumber = () => {
  const matches = [...String(code.value || '').matchAll(/第([一二三四五六七八九十百零\d]+)场/g)]
  return matches.length + 1
}

const insertActSection = () => {
  const actLabel = currentActLabel.value || '第一幕'
  insertTextAtCursor(`${actLabel}·第1节\n`)
}

const insertSceneNumber = () => {
  insertTextAtCursor(`第${extractNextSceneNumber()}场\n`)
}

const insertSceneHeading = (type) => {
  insertTextAtCursor(`${type} 场所 时间\n`)
}

const insertDialogueBlock = () => {
  insertTextAtCursor('角色名\n对话内容\n')
}

const normalizeCurrentScript = () => {
  const normalizedScript = normalizeText(code.value, false)
  resetRichMarkupFromPlainText(normalizedScript)
  updateCodeValue(normalizedScript, { preserveWhitespace: true, source: 'plain' })
  nextTick(() => syncRichEditorFromCode())
  ElMessage.success('剧本文本已按当前规则重新整理。')
}

let myChart = null
let syncTimer = null
let lastSyncedContent = ''
const getVersionPreview = (version) => normalizeText(version?.data?.scriptContent || version?.data?.pipelineRequirements || '暂无内容').slice(0, 180) || '暂无内容'

const refreshVersionHistory = () => {
  try {
    const saved = localStorage.getItem(AUTOSAVE_KEY)
    versionHistory.value = saved ? JSON.parse(saved).versions || [] : []
  } catch (error) {
    console.error(error)
    versionHistory.value = []
  }
}

const syncProgress = (completion = null) => {
  const snapshot = completion ? { ...completion } : null
  completionState.value = snapshot
  globalState.pipelineCompletionSnapshot = snapshot
  const generationLocked = Boolean(snapshot?.generation_locked || snapshot?.can_continue === false)
  const completed = Boolean(snapshot?.is_complete || generationLocked)
  globalState.pipelineIsScriptEnd = completed
  globalState.pipelineCompletionReason = String(snapshot?.reason || '')
}

const refreshCompletionStatus = async (sourceText = code.value) => {
  const normalized = normalizeText(sourceText)
  if (!normalized) {
    syncProgress(null)
    return null
  }
  const completion = globalState.pipelineCompletionSnapshot || completionState.value || null
  syncProgress(completion)
  return completion
}

const renderGraph = (graphData) => {
  if (!myChart) return
  const fallbackGraph = {
    nodes: [
      { id: 'scene:当前场景', name: '当前场景', category: 1 },
      { id: 'char:主角', name: '主角', category: 0 },
    ],
    links: [{ source: 'char:主角', target: 'scene:当前场景', name: '出现在' }],
  }
  const safeGraph = graphData?.nodes?.length ? graphData : fallbackGraph
  myChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { formatter: '{b}' },
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      draggable: true,
      force: { repulsion: 260, edgeLength: 110 },
      label: { show: true, position: 'right', formatter: '{b}', color: '#eef4ff' },
      edgeSymbol: ['circle', 'arrow'],
      edgeSymbolSize: [4, 10],
      edgeLabel: { show: true, fontSize: 10, formatter: '{c}', color: '#9eb0c8' },
      data: (safeGraph.nodes || []).map((node) => ({ ...node, symbolSize: node.category === 0 ? 54 : node.category === 2 ? 34 : 42 })),
      links: (safeGraph.links || []).map((link) => ({ ...link, value: link.name })),
      categories: [{ name: '角色' }, { name: '场景' }, { name: '伏笔' }],
      lineStyle: { color: '#7f8da3', curveness: 0.12 },
    }],
  }, true)
}

const syncGraph = async (content) => {
  if (!myChart) return
  const normalized = normalizeText(content)
  if (!normalized) {
    renderGraph(null)
    return
  }
  try {
    const response = await syncNarrativeGraph(normalized)
    renderGraph(response.data?.data)
  } catch (error) {
    console.error(error)
  }
}

const queueGraphSync = (content) => {
  if (syncTimer) clearTimeout(syncTimer)
  syncTimer = setTimeout(() => {
    const normalized = normalizeText(content)
    if (!normalized || normalized === lastSyncedContent) return
    lastSyncedContent = normalized
    syncGraph(normalized)
  }, 1200)
}

const initChart = async () => {
  if (!chartRef.value) return
  myChart = echarts.init(chartRef.value)
  myChart.showLoading({ text: '正在同步剧情状态网络...', color: '#4f8cff', textColor: '#d7e6ff', maskColor: 'rgba(9, 21, 40, 0.24)' })
  try {
    await syncGraph(globalState.scriptContent || code.value)
  } finally {
    myChart.hideLoading()
  }
}

const restoreToVersion = async (version) => {
  restoringVersion.value = version.id
  try {
    const saved = localStorage.getItem(AUTOSAVE_KEY)
    const data = JSON.parse(saved)
    data.currentVersionId = version.id
    localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(data))
    if (version.data) Object.assign(globalState, version.data)
    const restoredText = normalizeText(globalState.scriptContent || version.data?.scriptContent || '', false)
    richEditorHtml.value = String(globalState.editorRichContent || version.data?.editorRichContent || '')
    if (!richEditorHtml.value) {
      resetRichMarkupFromPlainText(restoredText)
    }
    updateCodeValue(restoredText, { preserveWhitespace: true, source: 'external' })
    resetCurrentActAssistant()
    syncProgress(globalState.pipelineCompletionSnapshot || version.data?.pipelineCompletionSnapshot || null)
    showVersionHistory.value = false
    ElMessage.success(`已恢复到 ${version.savedAtReadable}`)
  } catch (error) {
    console.error(error)
    ElMessage.error('恢复失败，请重试。')
  } finally {
    restoringVersion.value = null
  }
}

const generateCurrentActReview = async () => {
  const sourceText = normalizeText(code.value)
  if (!sourceText) {
    ElMessage.warning('请先准备当前幕正文，再生成 AI 优化建议。')
    return
  }

  adviceLoading.value = true
  currentActAnalysis.value = null
  currentActRevision.value = null
  try {
    const response = await reviewCurrentAct(
      sourceText,
      globalState.pipelineOutline || '',
      globalState.pipelineCharacters || '',
      globalState.pipelineRequirements || '',
      scriptFormat.value,
    )
    currentActAnalysis.value = response?.data?.analysis || null
    if (!currentActAnalysis.value) {
      throw new Error('当前幕优化建议结果为空')
    }
    if (currentActAnalysis.value.has_issues) {
      globalState.pipelineLatestActReviewed = false
      ElMessage.warning('已生成当前幕优化建议，可以继续一键生成优化版本。')
    } else {
      globalState.pipelineLatestActReviewed = true
      ElMessage.success(locked.value ? lockedCompletionNotice.value : '当前幕暂时没有明显需要优化的地方。')
    }
  } catch (error) {
    console.error(error)
    ElMessage.warning(resolveRequestError(error, '当前幕优化建议生成失败，请稍后重试。'))
  } finally {
    adviceLoading.value = false
  }
}

const generateCurrentActRevision = async () => {
  const sourceText = normalizeText(code.value)
  if (!sourceText) {
    ElMessage.warning('请先准备当前幕正文，再生成优化版本。')
    return
  }

  if (!currentActAnalysis.value) {
    ElMessage.warning('请先点击“一键生成AI优化建议”，确认当前幕优化方向后再生成优化版本。')
    return
  }

  revisionLoading.value = true
  currentActRevision.value = null
  try {
    const analysis = currentActAnalysis.value
    if (!analysis) {
      throw new Error('当前幕优化建议结果为空')
    }

    const response = await reviseCurrentAct(
      sourceText,
      globalState.pipelineOutline || '',
      globalState.pipelineCharacters || '',
      globalState.pipelineRequirements || '',
      analysis,
      scriptFormat.value,
    )
    currentActAnalysis.value = response?.data?.analysis || analysis
    if (response?.data?.generated === false) {
      currentActRevision.value = null
      globalState.pipelineLatestActReviewed = true
      ElMessage.success('当前幕暂时不需要生成优化版本。')
      return
    }
    const revisedAct = normalizeText(response?.data?.revised_act || '')
    const revisedContent = normalizeText(response?.data?.revised_content || '')
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
  if (normalizeText(code.value) !== currentActRevision.value.sourceText) {
    ElMessage.warning('当前幕正文已经变化，请重新生成优化版本，避免覆盖你刚刚的新改动。')
    return
  }

  applyingRevision.value = true
  try {
    const revision = currentActRevision.value
    if (!revision) return
    resetRichMarkupFromPlainText(revision.revisedContent)
    updateCodeValue(revision.revisedContent, { preserveWhitespace: true, source: 'external' })
    globalState.pipelineLatestActReviewed = !revision.acceptedWithIssues
    syncProgress(revision.completion || completionState.value || null)
    resetCurrentActAssistant()
    ElMessage.success(
      globalState.pipelineLatestActReviewed && locked.value
        ? lockedCompletionNotice.value
        : 'AI 优化版本已应用到当前幕。'
    )
  } catch (error) {
    console.error(error)
    ElMessage.warning('应用 AI 优化版本失败，请稍后重试。')
  } finally {
    applyingRevision.value = false
  }
}

const generateNextAct = async () => {
  const normalized = normalizeText(code.value)
  if (!normalized) {
    ElMessage.warning('请先准备剧本文本，再生成下一幕。')
    return
  }
  if (locked.value) {
    ElMessage.info(completionMessage.value)
    return
  }
  if (generationBusy.value && !loading.value) {
    ElMessage.info(`当前正在生成${globalState.pipelineGenerationTargetAct || nextActLabel.value || '下一幕'}，请稍等。`)
    return
  }
  loading.value = true
  globalState.pipelineGenerationInFlight = true
  globalState.pipelineGenerationTargetAct = nextActLabel.value || '下一幕'
  resetCurrentActAssistant()
  try {
    const response = await generateNextActAPI(
      normalized,
      globalState.pipelineOutline || '',
      globalState.pipelineCharacters || '',
      globalState.pipelineRequirements || '',
      scriptFormat.value,
    )
    const nextText = normalizeText(response.data?.text || '')
    if (!nextText) {
      syncProgress(response.data?.completion || completionState.value || null)
      ElMessage.info(completionMessage.value)
      return
    }
    const mergedContent = normalizeText(`${normalized}\n\n${nextText}`, false)
    resetRichMarkupFromPlainText(mergedContent)
    updateCodeValue(mergedContent, { preserveWhitespace: true, source: 'external' })
    if (nextText) globalState.pipelineLatestActReviewed = false
    const mergedText = nextText ? code.value : normalized
    syncProgress(response.data?.completion || null)
    if (response.data?.data) {
      renderGraph(response.data.data)
    } else {
      await syncGraph(mergedText)
    }
    if (response.data?.accepted_with_issues && nextText) {
      ElMessage.warning('下一幕已生成，但当前幕还有可继续优化的细节。可以先生成 AI 优化建议，再决定是否生成优化版本。')
    } else if (locked.value) {
      ElMessage.success(completionMessage.value)
    } else if (nextText) {
      ElMessage.success(`下一幕已生成，当前状态：${outlineStatusText.value}。`)
    } else {
      ElMessage.warning('本次没有生成新的幕内容，请稍后重试。')
    }
  } catch (error) {
    console.error(error)
    ElMessage.warning(resolveRequestError(error, '生成下一幕失败，请稍后重试。'))
  } finally {
    loading.value = false
    globalState.pipelineGenerationInFlight = false
    globalState.pipelineGenerationTargetAct = ''
  }
}

const exportPdf = () => {
  const exported = openScreenplayPdfWindow({ title: resolveCurrentTitle(), content: normalizeText(code.value) })
  if (!exported) ElMessage.warning('请先准备剧本文本，并允许浏览器弹出导出窗口。')
}

const openNarrativeFingerprint = async () => {
  const scriptText = normalizeText(code.value)
  if (!scriptText) {
    ElMessage.warning('请先准备完整剧本文本，再检测叙事指纹。')
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

const saveManualCheckpoint = (description) => {
  if (typeof window === 'undefined' || typeof window.saveManually !== 'function') return
  try {
    window.saveManually(description)
  } catch (error) {
    console.error(error)
  }
}

const exportPdfAndContinueSeries = async () => {
  const currentEpisode = normalizeText(code.value)
  if (!currentEpisode) {
    ElMessage.warning('请先准备当前集剧本文本，再继续生成下一集。')
    return
  }

  const exported = openScreenplayPdfWindow({ title: resolveCurrentTitle(currentEpisode), content: currentEpisode })
  if (!exported) {
    ElMessage.warning('请先准备剧本文本，并允许浏览器弹出导出窗口。')
    return
  }

  preparingNextEpisode.value = true
  saveManualCheckpoint('电视剧当前集导出后进入下一集')
  let nextEpisodePrefill = {
    previousEnding: currentEpisode,
    characterFocus: '',
    toneDirection: '',
    cliffhanger: '',
  }

  try {
    const response = await generateSeriesNextEpisodePrefill(currentEpisode)
    const fields = response?.data?.fields || {}
    nextEpisodePrefill = {
      previousEnding: normalizeText(fields.previous_ending || currentEpisode),
      characterFocus: normalizeText(fields.character_focus || ''),
      toneDirection: normalizeText(fields.tone_direction || ''),
      cliffhanger: normalizeText(fields.cliffhanger || ''),
    }
  } catch (error) {
    console.error(error)
    ElMessage.warning('下一集预填建议生成失败，先保留上一集承接内容；你仍可手动调整其余字段。')
  }

  const queued = queueNextSeriesEpisode(nextEpisodePrefill)
  if (!queued) {
    preparingNextEpisode.value = false
    ElMessage.warning('当前集 PDF 导出窗口已打开，但暂时无法自动带入下一集信息，请稍后重试。')
    return
  }

  try {
    await router.push({ name: 'Pipeline' })
  } catch (error) {
    console.error(error)
    const base = import.meta.env.BASE_URL || '/'
    window.location.href = `${base}#/`
    return
  } finally {
    preparingNextEpisode.value = false
  }
}

const handleResize = () => {
  if (myChart) myChart.resize()
}

watch(() => code.value, (newValue) => {
  const normalized = normalizeText(newValue)
  globalState.scriptContent = normalized
  if (codeUpdateSource.value === 'rich') {
    persistRichEditorHtml()
  } else if (codeUpdateSource.value !== 'init') {
    resetRichMarkupFromPlainText(normalized)
  }
  queueGraphSync(normalized)
  if (!richEditorFocused.value || codeUpdateSource.value !== 'rich') {
    syncRichEditorFromCode()
  }
  codeUpdateSource.value = ''
})

watch(() => globalState.scriptContent, (newValue) => {
  const normalized = normalizeText(newValue || '', false)
  if (normalized !== normalizeText(code.value, false)) {
    resetRichMarkupFromPlainText(normalized)
    updateCodeValue(normalized, { preserveWhitespace: true, source: 'external' })
  }
})

watch(() => globalState.pipelineCompletionSnapshot, (value) => {
  completionState.value = value ? { ...value } : null
})

watch(showVersionHistory, (open) => {
  if (open) refreshVersionHistory()
})

onMounted(async () => {
  if (!richEditorHtml.value) {
    resetRichMarkupFromPlainText(code.value)
  } else {
    globalState.editorRichContent = richEditorHtml.value
  }
  globalState.scriptContent = normalizeText(code.value)
  syncProgress(globalState.pipelineCompletionSnapshot || null)
  await initChart()
  refreshVersionHistory()
  await nextTick()
  syncRichEditorFromCode()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (syncTimer) clearTimeout(syncTimer)
  window.removeEventListener('resize', handleResize)
  if (myChart) {
    myChart.dispose()
    myChart = null
  }
})
</script>
<style scoped>
.editor-page { min-height: 100vh; padding: 28px; background: radial-gradient(circle at top left, rgba(27, 89, 188, 0.18), transparent 28%), radial-gradient(circle at top right, rgba(9, 161, 138, 0.1), transparent 24%), linear-gradient(180deg, #eaf0fa 0%, #f7f9fd 100%); }
.hero { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.95fr); gap: 22px; padding: 30px 32px; border-radius: 28px; color: #f8fbff; background: radial-gradient(circle at top right, rgba(120, 220, 204, 0.16), transparent 34%), linear-gradient(135deg, rgba(6, 38, 84, 0.96), rgba(8, 95, 133, 0.92)); box-shadow: 0 20px 48px rgba(15, 45, 87, 0.16); }
.hero-copy { margin: 0; max-width: 760px; font-size: 15px; line-height: 1.8; color: rgba(244, 248, 255, 0.92); }
.kicker { margin: 0 0 10px; font-size: 12px; letter-spacing: 0.18em; text-transform: uppercase; color: rgba(248, 251, 255, 0.72); }
.kicker.dark { color: rgba(238, 244, 255, 0.72); }
.kicker.muted { color: #758399; }
.hero h1, .card-head h2 { margin: 0 0 10px; }
.hero-actions, .advice-actions { display: flex; gap: 12px; flex-wrap: wrap; align-content: flex-start; }
.chip, .pill { padding: 8px 12px; border-radius: 999px; font-size: 12px; }
.chip { border: 1px solid rgba(255, 255, 255, 0.12); background: rgba(255, 255, 255, 0.1); }
.pill { background: rgba(255, 255, 255, 0.08); color: #e8f2ff; }
.pill.blue { background: rgba(79, 140, 255, 0.14); color: #bcd5ff; }
.metrics { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin: 22px 0; }
.metric, .card { border-radius: 22px; box-shadow: 0 16px 40px rgba(37, 70, 120, 0.08); }
.metric { padding: 18px 20px; border: 1px solid rgba(16, 51, 92, 0.08); background: rgba(255, 255, 255, 0.88); }
.metric span { display: block; margin-bottom: 8px; font-size: 12px; color: #758399; }
.metric strong { font-size: 24px; color: #10233e; }
.done-banner { display: flex; justify-content: space-between; align-items: center; gap: 20px; margin-bottom: 22px; padding: 18px 20px; border-radius: 20px; border: 1px solid rgba(52, 168, 83, 0.14); background: linear-gradient(135deg, #effaf2, #f8fffa); color: #275a31; }
.done-banner p { margin: 6px 0 0; color: #4b6f55; line-height: 1.7; }
.done-actions { display: flex; justify-content: flex-end; gap: 12px; flex-wrap: wrap; }
.layout { display: grid; grid-template-columns: minmax(0, 1.45fr) minmax(360px, 0.95fr); gap: 20px; align-items: start; }
.main-col { display: grid; gap: 20px; }
.card { overflow: hidden; background: #fff; }
.editor-card { background: linear-gradient(180deg, #0d1626 0%, #101d30 100%); border: 1px solid rgba(39, 66, 107, 0.38); }
.advice-card { border: 1px solid rgba(184, 198, 219, 0.55); background: linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(248, 250, 255, 0.96)); }
.graph-card { position: sticky; top: 20px; min-height: 1100px; border: 1px solid rgba(52, 92, 146, 0.26); background: linear-gradient(180deg, #15253a 0%, #182c46 100%); }
.card-head { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding: 18px 22px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); }
.card-head.light { border-bottom-color: rgba(16, 51, 92, 0.08); }
.editor-card .card-head h2, .graph-card .card-head h2 { color: #eef4ff; }
.advice-card .card-head h2 { color: #10233e; }
.editor-toolbar { display: flex; justify-content: space-between; gap: 12px; padding: 14px 18px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); background: rgba(255, 255, 255, 0.03); flex-wrap: wrap; }
.toolbar-group { display: flex; gap: 10px; flex-wrap: wrap; }
.rich-shell { min-height: 720px; background: linear-gradient(180deg, rgba(255, 255, 255, 0.02), transparent 18%), linear-gradient(180deg, #0f1827, #101a2a); }
.rich-shell-head { padding: 16px 24px 0; color: #8fa5c2; }
.rich-shell-head span { display: block; font-size: 12px; letter-spacing: 0.12em; text-transform: uppercase; color: #cfe0f8; }
.rich-shell-head p { margin: 8px 0 0; font-size: 13px; line-height: 1.7; }
.rich-editor,
.editor-textarea { width: 100%; min-height: 720px; border: 0; padding: 24px; outline: none; color: #f7f9ff; background: transparent; font-size: 15px; line-height: 1.95; font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif; overflow: auto; white-space: pre-wrap; word-break: break-word; user-select: text; cursor: text; }
.editor-textarea { resize: none; }
.rich-editor { caret-color: #f7f9ff; }
.rich-editor:focus { box-shadow: inset 0 0 0 1px rgba(79, 140, 255, 0.12); }
.rich-editor :deep(strong),
.rich-editor :deep(b) { color: #ffd479; font-weight: 800; }
.rich-editor :deep(mark) { padding: 0; border-radius: 0; background: transparent !important; color: #7ee7ff !important; font-weight: 700; }
.rich-editor :deep(span[style*="background-color"]) { padding: 0; border-radius: 0; background: transparent !important; color: #7ee7ff !important; font-weight: 700; }
.rich-editor :deep(font[color="#7ee7ff"]),
.rich-editor :deep(span[style*="color: rgb(126, 231, 255)"]),
.rich-editor :deep(span[style*="color:#7ee7ff"]),
.rich-editor :deep(span[style*="color: #7ee7ff"]) { color: #7ee7ff !important; font-weight: 700; }
.rich-line { min-height: 1.95em; white-space: pre-wrap; word-break: break-word; }
.rich-spacer { height: 0.9em; }
.rich-act { margin-top: 0.5em; color: #89d3ff; font-weight: 700; letter-spacing: 0.02em; }
.rich-scene-number { margin-top: 0.2em; color: #ffc670; font-weight: 700; }
.rich-scene-heading { color: #88f1be; font-weight: 600; }
.rich-speaker { margin-top: 0.4em; color: #f7f0ad; font-weight: 700; }
.rich-body { color: #f7f9ff; }
.editor-textarea::placeholder { color: rgba(222, 232, 246, 0.42); }
.advice-body { padding: 18px 20px 22px; }
.review-grid, .version-list { display: grid; gap: 14px; margin-top: 16px; }
.review-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.review-card, .version-card, .revision-box { padding: 16px; border-radius: 16px; border: 1px solid rgba(16, 51, 92, 0.08); background: #fff; }
.review-card-head, .version-head, .revision-box-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.review-card-head span { flex-shrink: 0; padding: 6px 12px; border-radius: 999px; background: rgba(16, 51, 92, 0.06); color: #12406c; font-size: 12px; font-weight: 700; }
.review-card-head strong { color: #10233e; font-size: 16px; line-height: 1.6; }
.review-summary { margin: 12px 0 0; color: #4b5870; line-height: 1.8; font-size: 14px; }
.review-row { margin-top: 12px; padding: 12px; border-radius: 14px; background: #f5f8fd; }
.review-row strong { display: block; color: #10233e; font-size: 13px; }
.review-row p { margin: 8px 0 0; color: #526178; line-height: 1.7; font-size: 13px; }
.review-row pre, .version-preview { margin: 10px 0 0; white-space: pre-wrap; word-break: break-word; font-family: inherit; color: #1b2c42; }
.review-ok, .revision-tip { margin: 12px 0 0; color: #6c7c91; line-height: 1.7; font-size: 13px; }
.revision-box { margin-top: 16px; background: linear-gradient(180deg, rgba(245, 249, 255, 0.96), rgba(255, 255, 255, 0.96)); }
.revision-box h3 { margin: 6px 0 0; color: #10233e; }
.revision-textarea { width: 100%; min-height: 280px; margin-top: 14px; padding: 16px; border: 1px solid rgba(16, 51, 92, 0.1); border-radius: 16px; background: #fff; color: #1b2c42; resize: vertical; line-height: 1.8; font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif; }
.pill.warning { background: rgba(230, 162, 60, 0.14); color: #b36a0b; }
.legend { display: flex; gap: 16px; padding: 14px 22px 0; color: #d0dbed; font-size: 13px; flex-wrap: wrap; }
.dot { display: inline-block; width: 10px; height: 10px; margin-right: 8px; border-radius: 999px; }
.dot.character { background: #4f8cff; }
.dot.scene { background: #70f0a8; }
.dot.foreshadow { background: #f1d45a; }
.chart { width: 100%; min-height: 1020px; padding: 10px 16px 18px; box-sizing: border-box; }
.version-list { max-height: 520px; overflow-y: auto; }
.version-card.latest { border-color: #67c23a; box-shadow: inset 0 0 0 1px rgba(103, 194, 58, 0.12); }
.version-meta { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
@media (max-width: 1280px) { .hero, .metrics, .layout, .review-grid { grid-template-columns: 1fr; } .graph-card { position: static; min-height: 760px; } .chart { min-height: 700px; } }
@media (max-width: 900px) { .editor-page { padding: 16px; } .hero, .done-banner, .card-head, .version-head, .review-card-head, .revision-box-head { display: flex; flex-direction: column; align-items: flex-start; } .editor-toolbar { flex-direction: column; align-items: flex-start; } .rich-editor, .editor-textarea { min-height: 560px; padding: 18px; } .chart { min-height: 420px; } }
</style>
