<template>
  <div class="fingerprint-page">
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Narrative Fingerprint</p>
        <h1>剧本叙事指纹</h1>
        <p>
          在这里查看剧本的结构特征、节奏变化、人物关系、适配方向和历史版本，
          帮你更直观地判断当前内容的风格特点与修改方向。
        </p>
      </div>
      <div class="hero-actions">
        <span class="chip">{{ analysis?.analysis_id || '尚未生成指纹报告' }}</span>
        <el-button type="primary" :loading="loading" :disabled="!hasScript" @click="runFingerprintAnalysis">叙事指纹检测</el-button>
        <el-button plain :disabled="!analysis" @click="exportReport">导出报告</el-button>
        <el-button plain @click="goToEditor">返回编辑器</el-button>
      </div>
    </section>

    <section class="status-row">
      <article class="status-card">
        <span>剧本名称</span>
        <strong>{{ currentTitle }}</strong>
        <p>{{ currentFormatLabel }} · {{ currentScriptLength }} 字</p>
      </article>
      <article class="status-card">
        <span>指纹签名</span>
        <strong>{{ analysis?.fingerprint_signature || '等待检测' }}</strong>
        <p>用于识别当前剧本的结构特征与版本差异</p>
      </article>
      <article class="status-card">
        <span>版本数量</span>
        <strong>{{ history.length }}</strong>
        <p>每次检测都会保存一份分析结果，方便回看和对比</p>
      </article>
    </section>

    <el-empty
      v-if="!analysis"
      class="empty-state"
      description="当前还没有叙事指纹报告。先在编辑器里完成全篇，再点击“叙事指纹检测”。"
    />

    <template v-else>
      <section class="score-grid">
        <article class="score-card primary">
          <span>原创独特分</span>
          <strong>{{ scorePanel.originality_score }}</strong>
          <p>分数越高，说明当前结构辨识度越强</p>
        </article>
        <article class="score-card" :style="{ borderColor: `${scorePanel.risk_color}55` }">
          <span>风险等级</span>
          <strong :style="{ color: scorePanel.risk_color }">{{ scorePanel.risk_label }}</strong>
          <p>当前叙事结构未发现明显撞款风险</p>
        </article>
        <article class="score-card">
          <span>最佳赛道</span>
          <strong>{{ scorePanel.best_track }}</strong>
          <p>当前赛道适配分 {{ scorePanel.track_fit_score }}</p>
        </article>
        <article class="score-card">
          <span>唯一剧本 ID</span>
          <strong>{{ analysis.analysis_id }}</strong>
          <p>{{ generatedAtText }}</p>
        </article>
      </section>

      <div class="layout">
        <div class="main-col">
          <section class="card">
            <header class="card-head">
              <div>
                <p class="section-tag">Radar</p>
                <h2>五维叙事雷达图</h2>
              </div>
              <div class="tag-row">
                <el-tag v-for="tag in analysis.tags?.themes || []" :key="tag" round>{{ tag }}</el-tag>
              </div>
            </header>
            <div ref="radarChartRef" class="chart radar-chart"></div>
          </section>

          <section class="card">
            <header class="card-head">
              <div>
                <p class="section-tag">Rhythm</p>
                <h2>剧情节奏起伏曲线</h2>
              </div>
              <span class="panel-note">按场次估算冲突 / 信息 / 情绪强度</span>
            </header>
            <div ref="tempoChartRef" class="chart tempo-chart"></div>
          </section>

          <section class="card">
            <header class="card-head">
              <div>
                <p class="section-tag">Timeline</p>
                <h2>版本修改时间线</h2>
              </div>
              <div class="history-actions">
                <el-select v-model="compareId" size="small" placeholder="选择对比版本" clearable style="width: 220px;">
                  <el-option
                    v-for="item in compareOptions"
                    :key="item.id"
                    :label="`${item.savedAtReadable} · ${item.analysis?.score_panel?.originality_score || 0} 分`"
                    :value="item.id"
                  />
                </el-select>
              </div>
            </header>

            <div class="history-layout">
              <div class="timeline-list">
                <article v-for="entry in history" :key="entry.id" class="timeline-card" :class="{ active: currentHistoryId === entry.id }">
                  <div class="timeline-head">
                    <div>
                      <strong>{{ entry.savedAtReadable }}</strong>
                      <p>{{ entry.analysis?.analysis_id }}</p>
                    </div>
                    <div class="timeline-buttons">
                      <el-button size="small" plain @click="loadHistoryEntry(entry)">查看</el-button>
                      <el-button size="small" type="primary" plain @click="compareId = entry.id">对比</el-button>
                    </div>
                  </div>
                  <p class="timeline-summary">{{ entry.analysis?.summary }}</p>
                  <div class="timeline-metrics">
                    <span>原创分 {{ entry.analysis?.score_panel?.originality_score }}</span>
                    <span>{{ entry.analysis?.score_panel?.best_track }}</span>
                  </div>
                </article>
              </div>

              <div class="compare-panel">
                <template v-if="comparison">
                  <div class="compare-head">
                    <div>
                      <p class="section-tag">Compare</p>
                      <h3>当前版本 vs 对比版本</h3>
                    </div>
                    <el-tag round>对比对象：{{ comparison.targetTime }}</el-tag>
                  </div>
                  <div class="compare-metrics">
                    <article class="compare-card">
                      <span>原创分变化</span>
                      <strong :class="deltaClass(comparison.originalityDelta)">{{ signedNumber(comparison.originalityDelta) }}</strong>
                    </article>
                    <article class="compare-card">
                      <span>赛道适配变化</span>
                      <strong :class="deltaClass(comparison.trackDelta)">{{ signedNumber(comparison.trackDelta) }}</strong>
                    </article>
                    <article class="compare-card">
                      <span>风险变化</span>
                      <strong>{{ comparison.riskChange }}</strong>
                    </article>
                  </div>
                  <div class="compare-details">
                    <p><strong>当前最佳赛道：</strong>{{ scorePanel.best_track }}</p>
                    <p><strong>对比版本赛道：</strong>{{ comparison.targetTrack }}</p>
                    <p><strong>关键变化：</strong>{{ comparison.summary }}</p>
                  </div>
                  <div class="compare-dimension-list">
                    <div v-for="item in comparison.dimensionChanges" :key="item.name" class="dimension-row">
                      <span>{{ item.name }}</span>
                      <strong :class="deltaClass(item.delta)">{{ signedNumber(item.delta) }}</strong>
                    </div>
                  </div>
                </template>
                <el-empty v-else description="选择一个历史版本后，这里会显示新旧指纹对比。" />
              </div>
            </div>
          </section>
        </div>

        <div class="side-col">
          <section class="card graph-card">
            <header class="card-head">
              <div>
                <p class="section-tag">Relation</p>
                <h2>人物关系与线索图</h2>
              </div>
              <span class="panel-note">角色 / 场景 / 线索 三层结构</span>
            </header>
            <div ref="graphChartRef" class="chart graph-chart"></div>
          </section>

          <section class="card">
            <header class="card-head">
              <div>
                <p class="section-tag">Track Fit</p>
                <h2>自动匹配适合赛道</h2>
              </div>
              <span class="panel-note">分数越高，越适合该投放方向</span>
            </header>
            <div class="track-list">
              <article v-for="item in analysis.track_matches || []" :key="item.track" class="track-card">
                <div class="track-head">
                  <strong>{{ item.track }}</strong>
                  <span>{{ item.score }}</span>
                </div>
                <el-progress :percentage="item.score" :stroke-width="10" />
                <p>{{ item.advice }}</p>
              </article>
            </div>
          </section>

          <section class="card">
            <header class="card-head">
              <div>
                <p class="section-tag">Breakdown</p>
                <h2>结构拆解与建议</h2>
              </div>
              <span class="panel-note">转折点 / 优势 / 风险 / 改写建议</span>
            </header>
            <div class="breakdown-block">
              <h3>转折点</h3>
              <div v-if="analysis.story_breakdown?.turning_points?.length" class="bullet-list">
                <p v-for="item in analysis.story_breakdown.turning_points" :key="`${item.label}-${item.heading}`">
                  {{ item.label }} · {{ item.heading }}：{{ item.reason }}
                </p>
              </div>
              <p v-else class="muted">当前文本还没有足够明显的转折峰值。</p>
            </div>

            <div class="breakdown-block">
              <h3>优势</h3>
              <div class="bullet-list">
                <p v-for="item in analysis.story_breakdown?.strengths || []" :key="item">{{ item }}</p>
              </div>
            </div>

            <div class="breakdown-block">
              <h3>风险提示</h3>
              <div v-if="analysis.story_breakdown?.risks?.length" class="bullet-list">
                <p v-for="item in analysis.story_breakdown?.risks || []" :key="item.title">
                  {{ item.title }}：{{ item.description }}
                </p>
              </div>
              <p v-else class="muted">未发现明显撞款风险，当前叙事结构处于低风险状态。</p>
            </div>

            <div class="breakdown-block">
              <h3>下一轮改写建议</h3>
              <div class="bullet-list">
                <p v-for="item in analysis.story_breakdown?.recommendations || []" :key="item">{{ item }}</p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { analyzeNarrativeFingerprint } from '../api/fingerprint'
import { globalState } from '../stores/project'
import { buildScreenplayTitle } from '../utils/screenplayTitle'

const FINGERPRINT_HISTORY_KEY = 'AI_SCREENPLAY_FINGERPRINT_HISTORY_V1'
const MAX_HISTORY = 20

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const analysis = ref(null)
const history = ref([])
const compareId = ref('')
const currentHistoryId = ref('')

const radarChartRef = ref(null)
const tempoChartRef = ref(null)
const graphChartRef = ref(null)

let radarChart = null
let tempoChart = null
let graphChart = null

const hasScript = computed(() => Boolean(String(globalState.scriptContent || '').trim()))
const currentTitle = computed(() => analysis.value?.title || buildScreenplayTitle(globalState.title, globalState.scriptContent))
const currentFormatLabel = computed(() => analysis.value?.script_format_label || '待检测')
const currentScriptLength = computed(() => analysis.value?.script_length || String(globalState.scriptContent || '').trim().length || 0)
const scorePanel = computed(() => analysis.value?.score_panel || {
  originality_score: 0,
  risk_label: '待检测',
  risk_color: '#909399',
  track_fit_score: 0,
  best_track: '待判断',
})
const generatedAtText = computed(() => {
  if (!analysis.value?.generated_at) return '等待生成'
  return new Date(analysis.value.generated_at).toLocaleString('zh-CN')
})
const compareOptions = computed(() => history.value.filter((item) => item.id !== currentHistoryId.value))
const compareTarget = computed(() => history.value.find((item) => item.id === compareId.value) || null)
const comparison = computed(() => {
  if (!analysis.value || !compareTarget.value?.analysis) return null
  const target = compareTarget.value.analysis
  const currentDimensions = Object.fromEntries((analysis.value.dimensions || []).map((item) => [item.name, item.value]))
  const targetDimensions = Object.fromEntries((target.dimensions || []).map((item) => [item.name, item.value]))

  return {
    targetTime: compareTarget.value.savedAtReadable,
    originalityDelta: scorePanel.value.originality_score - (target.score_panel?.originality_score || 0),
    trackDelta: scorePanel.value.track_fit_score - (target.score_panel?.track_fit_score || 0),
    riskChange: `${target.score_panel?.risk_label || '待检测'} → ${scorePanel.value.risk_label}`,
    targetTrack: target.score_panel?.best_track || '待判断',
    summary: buildComparisonSummary(analysis.value, target),
    dimensionChanges: (analysis.value.dimensions || []).map((item) => ({
      name: item.name,
      delta: item.value - (targetDimensions[item.name] || 0),
    })),
  }
})

function loadHistory() {
  try {
    const saved = localStorage.getItem(FINGERPRINT_HISTORY_KEY)
    history.value = saved ? JSON.parse(saved).versions || [] : []
  } catch (error) {
    console.error(error)
    history.value = []
  }
}

function persistHistory() {
  localStorage.setItem(FINGERPRINT_HISTORY_KEY, JSON.stringify({ versions: history.value.slice(0, MAX_HISTORY) }))
}

function saveHistoryEntry(payload) {
  if (!payload?.analysis_id) return

  const last = history.value[0]
  if (last?.analysis?.fingerprint_hash === payload.fingerprint_hash) {
    currentHistoryId.value = last.id
    return
  }

  const entry = {
    id: `${payload.analysis_id}-${Date.now()}`,
    savedAt: Date.now(),
    savedAtReadable: new Date().toLocaleString('zh-CN'),
    analysis: payload,
  }
  history.value.unshift(entry)
  history.value = history.value.slice(0, MAX_HISTORY)
  currentHistoryId.value = entry.id
  persistHistory()
}

function loadHistoryEntry(entry) {
  analysis.value = entry.analysis || null
  currentHistoryId.value = entry.id
}

function buildRequestPayload() {
  return {
    content: String(globalState.scriptContent || '').trim(),
    outline: String(globalState.pipelineOutline || '').trim(),
    characters: String(globalState.pipelineCharacters || '').trim(),
    idea: String(globalState.pipelineRequirements || globalState.theme || '').trim(),
    script_format: globalState.pipelineScriptFormat || 'movie',
    title: buildScreenplayTitle(globalState.title, globalState.scriptContent),
  }
}

async function runFingerprintAnalysis() {
  const payload = buildRequestPayload()
  if (!payload.content) {
    ElMessage.warning('请先准备完整剧本文本，再检测叙事指纹。')
    return
  }

  loading.value = true
  try {
    const response = await analyzeNarrativeFingerprint(payload)
    analysis.value = response.data?.analysis || null
    if (!analysis.value) {
      throw new Error('叙事指纹结果为空')
    }
    saveHistoryEntry(analysis.value)
    ElMessage.success('叙事指纹报告已生成。')
  } catch (error) {
    console.error(error)
    ElMessage.warning(error?.response?.data?.detail || '叙事指纹分析失败，请稍后重试。')
  } finally {
    loading.value = false
  }
}

async function goToEditor() {
  try {
    await router.push({ name: 'Editor' })
  } catch (error) {
    console.error(error)
    window.location.href = `${import.meta.env.BASE_URL || '/'}#/editor`
  }
}

function renderRadarChart() {
  if (!radarChartRef.value || !analysis.value) return
  if (!radarChart) radarChart = echarts.init(radarChartRef.value)

  const data = analysis.value.dimensions || []
  radarChart.setOption(
    {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'item' },
      radar: {
        radius: '62%',
        indicator: data.map((item) => ({ name: item.name, max: 100 })),
        axisName: { color: '#14375f', fontSize: 13 },
        splitLine: { lineStyle: { color: 'rgba(20, 55, 95, 0.14)' } },
        splitArea: { areaStyle: { color: ['rgba(52, 122, 216, 0.04)', 'rgba(52, 122, 216, 0.02)'] } },
      },
      series: [
        {
          type: 'radar',
          data: [
            {
              value: data.map((item) => item.value),
              name: '叙事指纹',
              areaStyle: { color: 'rgba(41, 108, 214, 0.22)' },
              lineStyle: { color: '#165dff', width: 2 },
              itemStyle: { color: '#165dff' },
            },
          ],
        },
      ],
    },
    true,
  )
}

function renderTempoChart() {
  if (!tempoChartRef.value || !analysis.value) return
  if (!tempoChart) tempoChart = echarts.init(tempoChartRef.value)

  const curve = analysis.value.tempo_curve || []
  tempoChart.setOption(
    {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        formatter(params) {
          const item = params?.[0]?.data || {}
          return `${item.heading || item.label}<br/>强度：${item.value}`
        },
      },
      grid: { left: 36, right: 20, top: 28, bottom: 36 },
      xAxis: {
        type: 'category',
        data: curve.map((item) => item.label),
        axisLine: { lineStyle: { color: '#b6c7da' } },
        axisLabel: { color: '#4e637e' },
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        splitLine: { lineStyle: { color: 'rgba(17, 54, 97, 0.08)' } },
        axisLabel: { color: '#4e637e' },
      },
      series: [
        {
          type: 'line',
          smooth: true,
          data: curve,
          symbolSize: 8,
          lineStyle: { width: 3, color: '#ff7a59' },
          itemStyle: { color: '#ff7a59' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(255, 122, 89, 0.32)' },
              { offset: 1, color: 'rgba(255, 122, 89, 0.04)' },
            ]),
          },
        },
      ],
    },
    true,
  )
}

function renderGraphChart() {
  if (!graphChartRef.value || !analysis.value) return
  if (!graphChart) graphChart = echarts.init(graphChartRef.value)

  const graph = analysis.value.character_graph || { nodes: [], links: [] }
  graphChart.setOption(
    {
      backgroundColor: 'transparent',
      tooltip: { formatter: '{b}' },
      series: [
        {
          type: 'graph',
          layout: 'force',
          roam: true,
          draggable: true,
          force: { repulsion: 250, edgeLength: 100 },
          data: (graph.nodes || []).map((node) => ({
            ...node,
            itemStyle: {
              color: node.category === 0 ? '#165dff' : node.category === 1 ? '#00a870' : '#ffb302',
            },
          })),
          links: (graph.links || []).map((link) => ({ ...link, value: link.name })),
          categories: [{ name: '角色' }, { name: '场景' }, { name: '线索' }],
          label: { show: true, position: 'right', color: '#0f2d57', fontSize: 12 },
          edgeLabel: { show: true, formatter: '{c}', color: '#6d8098', fontSize: 10 },
          lineStyle: { color: '#9db3c9', curveness: 0.12 },
        },
      ],
    },
    true,
  )
}

async function renderCharts() {
  await nextTick()
  renderRadarChart()
  renderTempoChart()
  renderGraphChart()
}

function signedNumber(value) {
  const num = Number(value || 0)
  return `${num > 0 ? '+' : ''}${num}`
}

function deltaClass(value) {
  const num = Number(value || 0)
  if (num > 0) return 'delta-up'
  if (num < 0) return 'delta-down'
  return 'delta-flat'
}

function buildComparisonSummary(currentAnalysis, targetAnalysis) {
  const currentTrack = currentAnalysis?.score_panel?.best_track || '待判断'
  const targetTrack = targetAnalysis?.score_panel?.best_track || '待判断'
  const originalityDelta = (currentAnalysis?.score_panel?.originality_score || 0) - (targetAnalysis?.score_panel?.originality_score || 0)
  if (currentTrack !== targetTrack) {
    return `当前版本的主要风格从“${targetTrack}”调整到了“${currentTrack}”，整体方向已经发生了变化。`
  }
  if (originalityDelta > 0) {
    return `本轮修改让原创分提高了 ${originalityDelta} 分，整体辨识度更强了。`
  }
  if (originalityDelta < 0) {
    return `本轮修改让原创分下降了 ${Math.abs(originalityDelta)} 分，建议回头检查是否加入了过于常见的桥段。`
  }
  return '新旧版本整体方向比较稳定，变化主要集中在局部桥段和表达细节。'
}

function exportReport() {
  if (!analysis.value) return

  const reportTitle = `${currentTitle.value}-叙事指纹报告`
  const comparisonHtml = comparison.value
    ? `
      <section class="card">
        <h2>版本对比</h2>
        <p>${comparison.value.summary}</p>
        <ul>
          <li>原创分变化：${signedNumber(comparison.value.originalityDelta)}</li>
          <li>赛道适配变化：${signedNumber(comparison.value.trackDelta)}</li>
          <li>风险变化：${comparison.value.riskChange}</li>
        </ul>
      </section>
    `
    : ''

  const html = `
    <!doctype html>
    <html lang="zh-CN">
      <head>
        <meta charset="utf-8" />
        <title>${reportTitle}</title>
        <style>
          body { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; margin: 32px; color: #17304f; background: #f7f9fc; }
          h1, h2 { margin: 0 0 12px; }
          p, li { line-height: 1.8; }
          .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
          .card { margin-top: 16px; padding: 18px 20px; border-radius: 18px; background: #fff; border: 1px solid rgba(23, 48, 79, 0.08); }
          .tag { display: inline-block; margin-right: 8px; padding: 4px 10px; border-radius: 999px; background: #edf4ff; color: #165dff; font-size: 12px; }
          ul { margin: 10px 0 0; padding-left: 18px; }
        </style>
      </head>
      <body>
        <h1>${reportTitle}</h1>
        <p>报告时间：${generatedAtText.value}</p>
        <div class="grid">
          <div class="card">
            <h2>核心分数</h2>
            <ul>
              <li>原创独特分：${scorePanel.value.originality_score}</li>
              <li>风险等级：${scorePanel.value.risk_label}</li>
              <li>最佳赛道：${scorePanel.value.best_track}</li>
              <li>赛道适配分：${scorePanel.value.track_fit_score}</li>
            </ul>
          </div>
          <div class="card">
            <h2>标签</h2>
            ${(analysis.value.tags?.themes || []).map((tag) => `<span class="tag">${tag}</span>`).join('')}
            ${(analysis.value.tags?.styles || []).map((tag) => `<span class="tag">${tag}</span>`).join('')}
          </div>
        </div>
        <section class="card">
          <h2>摘要</h2>
          <p>${analysis.value.summary}</p>
        </section>
        <section class="card">
          <h2>改写建议</h2>
          <ul>
            ${(analysis.value.story_breakdown?.recommendations || []).map((item) => `<li>${item}</li>`).join('')}
          </ul>
        </section>
        ${comparisonHtml}
      </body>
    </html>
  `

  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `${reportTitle}-${Date.now()}.html`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(link.href)
}

function handleResize() {
  radarChart?.resize()
  tempoChart?.resize()
  graphChart?.resize()
}

watch(analysis, () => {
  if (analysis.value) renderCharts()
}, { deep: true })

onMounted(async () => {
  loadHistory()
  if (history.value.length) {
    analysis.value = history.value[0].analysis || null
    currentHistoryId.value = history.value[0].id
  }
  window.addEventListener('resize', handleResize)

  if (route.query.autorun === '1' && hasScript.value) {
    await runFingerprintAnalysis()
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  radarChart?.dispose()
  tempoChart?.dispose()
  graphChart?.dispose()
  radarChart = null
  tempoChart = null
  graphChart = null
})
</script>

<style scoped>
.fingerprint-page {
  min-height: 100vh;
  padding: 28px;
  background:
    radial-gradient(circle at top left, rgba(25, 111, 212, 0.14), transparent 28%),
    radial-gradient(circle at top right, rgba(14, 167, 118, 0.12), transparent 24%),
    linear-gradient(180deg, #eef4fb 0%, #f8fafc 100%);
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(320px, 0.95fr);
  gap: 20px;
  padding: 30px 32px;
  border-radius: 28px;
  color: #f6fbff;
  background:
    radial-gradient(circle at top right, rgba(146, 217, 255, 0.18), transparent 32%),
    linear-gradient(135deg, rgba(8, 36, 82, 0.96), rgba(15, 94, 146, 0.92));
  box-shadow: 0 20px 48px rgba(15, 45, 87, 0.16);
}

.hero-copy h1 {
  margin: 0 0 12px;
  font-size: 34px;
}

.hero-copy p:last-child {
  margin: 0;
  line-height: 1.85;
  font-size: 15px;
  color: rgba(246, 251, 255, 0.92);
}

.eyebrow,
.section-tag {
  margin: 0 0 10px;
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(246, 251, 255, 0.72);
}

.section-tag {
  color: #7a879b;
}

.hero-actions,
.history-actions,
.tag-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-content: flex-start;
}

.chip {
  display: inline-flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 999px;
  font-size: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.1);
}

.status-row,
.score-grid {
  display: grid;
  gap: 16px;
  margin-top: 22px;
}

.status-row {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.score-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.status-card,
.score-card,
.card {
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(16, 51, 92, 0.08);
  box-shadow: 0 14px 36px rgba(34, 61, 101, 0.08);
}

.status-card,
.score-card {
  padding: 18px 20px;
}

.status-card span,
.score-card span,
.compare-card span {
  display: block;
  margin-bottom: 8px;
  font-size: 12px;
  color: #71819a;
}

.status-card strong,
.score-card strong,
.compare-card strong {
  display: block;
  font-size: 24px;
  color: #10233e;
}

.status-card p,
.score-card p,
.track-card p,
.timeline-summary,
.compare-details p,
.bullet-list p,
.panel-note {
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.75;
  color: #5f7291;
}

.score-card.primary {
  background: linear-gradient(135deg, rgba(21, 93, 255, 0.95), rgba(33, 176, 115, 0.9));
  border-color: transparent;
}

.score-card.primary span,
.score-card.primary p,
.score-card.primary strong {
  color: #f7fbff;
}

.empty-state {
  margin-top: 26px;
  padding: 36px 0;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.86);
}

.layout {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(360px, 0.86fr);
  gap: 20px;
  margin-top: 22px;
  align-items: start;
}

.main-col,
.side-col {
  display: grid;
  gap: 20px;
}

.card {
  overflow: hidden;
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 18px 22px;
  border-bottom: 1px solid rgba(16, 51, 92, 0.08);
}

.card-head h2,
.compare-head h3,
.breakdown-block h3 {
  margin: 0;
  color: #10233e;
}

.chart {
  width: 100%;
}

.radar-chart,
.tempo-chart {
  min-height: 360px;
  padding: 12px 16px 22px;
}

.graph-card {
  background: linear-gradient(180deg, #0f2034 0%, #132a44 100%);
}

.graph-card .card-head {
  border-bottom-color: rgba(255, 255, 255, 0.08);
}

.graph-card .card-head h2,
.graph-card .panel-note,
.graph-card .section-tag {
  color: #edf4ff;
}

.graph-chart {
  min-height: 520px;
  padding: 6px 8px 16px;
}

.track-list,
.timeline-list {
  display: grid;
  gap: 14px;
  padding: 18px 20px 22px;
}

.track-card,
.timeline-card,
.compare-panel,
.compare-card {
  border-radius: 18px;
  border: 1px solid rgba(16, 51, 92, 0.08);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(245, 248, 252, 0.96));
}

.track-card,
.timeline-card {
  padding: 16px;
}

.track-head,
.timeline-head,
.compare-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.track-head strong,
.timeline-head strong {
  color: #10233e;
}

.compare-details strong {
  color: #10305b;
}

.history-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
  gap: 18px;
  padding: 18px 20px 22px;
}

.timeline-list {
  padding: 0;
  max-height: 620px;
  overflow-y: auto;
}

.timeline-card.active {
  border-color: rgba(22, 93, 255, 0.34);
  box-shadow: 0 18px 40px rgba(22, 93, 255, 0.08);
}

.timeline-buttons,
.timeline-metrics,
.compare-metrics {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.timeline-metrics span {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(16, 51, 92, 0.06);
  color: #445974;
  font-size: 12px;
}

.compare-panel {
  padding: 18px;
  min-height: 360px;
}

.compare-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 16px;
}

.compare-card {
  padding: 14px;
}

.compare-details,
.compare-dimension-list {
  margin-top: 16px;
}

.dimension-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(16, 51, 92, 0.08);
  color: #425870;
}

.dimension-row:last-child {
  border-bottom: 0;
}

.breakdown-block {
  padding: 0 22px 18px;
}

.breakdown-block:first-of-type {
  padding-top: 18px;
}

.bullet-list {
  display: grid;
  gap: 10px;
}

.muted {
  padding: 0 22px 18px;
  color: #7b889c;
}

.delta-up {
  color: #1f8f72 !important;
}

.delta-down {
  color: #f56c6c !important;
}

.delta-flat {
  color: #7b889c !important;
}

@media (max-width: 1240px) {
  .hero,
  .status-row,
  .score-grid,
  .layout,
  .history-layout,
  .compare-metrics {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .fingerprint-page {
    padding: 16px;
  }

  .hero,
  .card-head,
  .sample-head,
  .track-head,
  .timeline-head,
  .compare-head {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
  }

  .graph-chart {
    min-height: 380px;
  }
}
</style>
