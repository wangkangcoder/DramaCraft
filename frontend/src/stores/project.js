import { reactive, watch } from 'vue'
import { buildScreenplayTitle, normalizeStoredTitle } from '../utils/screenplayTitle'

const AUTOSAVE_KEY = 'AI_SCREENPLAY_VERSIONS_V2'
const DRAFT_SAVE_KEY = 'AI_SCREENPLAY_DRAFT_V1'
const MANUAL_SAVE_KEY = 'AI_SCREENPLAY_MANUAL_VERSIONS'
const NEXT_SERIES_EPISODE_KEY = 'AI_SCREENPLAY_NEXT_SERIES_EPISODE'
const DRAFT_SAVE_DEBOUNCE_MS = 1200
const AUTOSAVE_DEBOUNCE_MS = 5 * 60 * 1000
const MAX_VERSIONS = 15
const MAX_MANUAL_VERSIONS = 3

function sanitizeStateData(data = {}) {
  if (!data || typeof data !== 'object') return {}
  const next = { ...data }
  delete next.pipelineTotalScenes
  delete next.pipelineCurrentScene
  delete next.pipelineThemeInput
  delete next.pipelineSettingInput
  delete next.pipelineProtagonistInput
  delete next.pipelineConflictInput
  delete next.pipelineStyleInput
  delete next.pipelineEndingInput
  delete next.pipelineExtraInput
  delete next.pipelineGenerationInFlight
  delete next.pipelineGenerationTargetAct
  return next
}

function sanitizeHistoryPayload(history) {
  if (!history || typeof history !== 'object') {
    return { currentVersionId: null, versions: [] }
  }

  return {
    ...history,
    versions: Array.isArray(history.versions)
      ? history.versions.map((version) => ({
          ...version,
          data: sanitizeStateData(version?.data || {}),
        }))
      : [],
  }
}

function loadVersionHistory() {
  try {
    const saved = localStorage.getItem(AUTOSAVE_KEY)
    if (saved) {
      const history = sanitizeHistoryPayload(JSON.parse(saved))
      return history
    }
  } catch (e) {
    console.warn('⚠️ 存档损坏，使用默认值')
  }
  return {
    currentVersionId: null,
    versions: [],
  }
}

function loadDraftState() {
  try {
    const saved = localStorage.getItem(DRAFT_SAVE_KEY)
    if (saved) {
      const payload = JSON.parse(saved)
      return sanitizeStateData(payload?.data || {})
    }
  } catch (e) {
    console.warn('⚠️ 草稿缓存损坏，已忽略本地草稿')
  }
  return {}
}

function extractStateData() {
  return {
    title: globalState.title,
    scriptContent: globalState.scriptContent,
    editorRichContent: globalState.editorRichContent,
    pipelineCharacters: globalState.pipelineCharacters,
    pipelineOutline: globalState.pipelineOutline,
    pipelineRequirements: globalState.pipelineRequirements,
    pipelineScriptFormat: globalState.pipelineScriptFormat,
    pipelineMovieCoreIdea: globalState.pipelineMovieCoreIdea,
    pipelineMovieProtagonist: globalState.pipelineMovieProtagonist,
    pipelineMovieConflict: globalState.pipelineMovieConflict,
    pipelineMovieTone: globalState.pipelineMovieTone,
    pipelineSeriesPreviousEnding: globalState.pipelineSeriesPreviousEnding,
    pipelineSeriesCharacterFocus: globalState.pipelineSeriesCharacterFocus,
    pipelineSeriesToneDirection: globalState.pipelineSeriesToneDirection,
    pipelineSeriesCliffhanger: globalState.pipelineSeriesCliffhanger,
    pipelineMicroHook: globalState.pipelineMicroHook,
    pipelineMicroProtagonist: globalState.pipelineMicroProtagonist,
    pipelineMicroConflict: globalState.pipelineMicroConflict,
    pipelineMicroTone: globalState.pipelineMicroTone,
    pipelineActiveStep: globalState.pipelineActiveStep,
    pipelineLatestActReviewed: globalState.pipelineLatestActReviewed,
    pipelineIsScriptEnd: globalState.pipelineIsScriptEnd,
    pipelineCompletionReason: globalState.pipelineCompletionReason,
    pipelineCompletionSnapshot: globalState.pipelineCompletionSnapshot,
  }
}

function saveDraftState() {
  const currentData = extractStateData()
  localStorage.setItem(DRAFT_SAVE_KEY, JSON.stringify({
    savedAt: Date.now(),
    data: currentData,
  }))
}

function createNewVersion() {
  const history = loadVersionHistory()
  const currentData = extractStateData()

  if (history.versions.length > 0) {
    const lastData = history.versions[0].data
    if (JSON.stringify(currentData) === JSON.stringify(lastData)) {
      return
    }
  }

  const newVersion = {
    id: Date.now(),
    savedAt: Date.now(),
    savedAtReadable: new Date().toLocaleString('zh-CN'),
    data: currentData,
  }

  history.versions.unshift(newVersion)
  history.currentVersionId = newVersion.id

  if (history.versions.length > MAX_VERSIONS) {
    history.versions = history.versions.slice(0, MAX_VERSIONS)
  }

  localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(history))
  console.log(`💾 已自动保存新版本 #${history.versions.length}/${MAX_VERSIONS}，${newVersion.savedAtReadable}（每5分钟自动保存一次）`)
  return newVersion
}

window.restoreVersion = (versionId) => {
  const history = loadVersionHistory()
  const version = history.versions.find(v => v.id === versionId)
  
  if (!version) {
    console.error('❌ 找不到这个版本')
    return
  }

  Object.assign(globalState, version.data)
  history.currentVersionId = versionId
  localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(history))
  
  console.log(`⏰ 已恢复到版本：${version.savedAtReadable}`)
  console.log('👉 页面数据已自动刷新！')
}

window.showVersions = () => {
  const history = loadVersionHistory()
  console.log('\n')
  console.log('%c⏰ 剧本时光机 - 可用历史版本', 'font-size: 16px; font-weight: bold; color: #409eff;')
  console.log('='.repeat(60))
  
  history.versions.forEach((v, i) => {
    const isCurrent = v.id === history.currentVersionId ? '  ← 当前版本' : ''
    const flag = v.id === history.currentVersionId ? '🟢' : '🟡'
    console.log(`%c${flag} [${i}] ${v.savedAtReadable}${isCurrent}`, 
      v.id === history.currentVersionId ? 'color: #67c23a; font-weight: bold' : 'color: #e6a23c')
    console.log(`   恢复命令: restoreVersion(${v.id})`)
  })
  
  console.log('='.repeat(60))
  console.log('%c💡 提示: 输入 showVersions() 查看所有版本', 'color: #909399')
  console.log('%c💡 提示: 输入 restoreVersion(版本号) 回到该版本', 'color: #909399')
  console.log('\n')
}

window.clearAllVersions = () => {
  localStorage.removeItem(AUTOSAVE_KEY)
  console.log('🗑️ 所有版本已清空，刷新页面生效！')
}

const DEFAULT_STATE = {
  title: '',
  track: '主线',
  theme: '悬疑科幻',
  audience: '18-35岁',
  worldTime: '近未来',
  worldRules: '人工智能已经深度参与灾害预警和海上科研',
  worldConflict: '真相调查与失控系统之间的对抗',
  agents: ['主角组', '反派力量', '系统变量'],
  pace: 80,
  taboos: '避免低俗桥段，避免无意义反转',
  chars: [
    { name: '林澈', role: '主角', arc: '从逃避过去到主动面对真相', locked: true },
    { name: '顾南舟', role: '关键线索人物', arc: '从失踪者变成推动真相的核心线索', locked: true },
  ],
  pipelineRequirements: '',
  pipelineScriptFormat: 'movie',
  pipelineMovieCoreIdea: '',
  pipelineMovieProtagonist: '',
  pipelineMovieConflict: '',
  pipelineMovieTone: '',
  pipelineSeriesPreviousEnding: '',
  pipelineSeriesCharacterFocus: '',
  pipelineSeriesToneDirection: '',
  pipelineSeriesCliffhanger: '',
  pipelineMicroHook: '',
  pipelineMicroProtagonist: '',
  pipelineMicroConflict: '',
  pipelineMicroTone: '',
  pipelineCharacters: '',
  pipelineOutline: '',
  pipelineActiveStep: 0,
  pipelineLatestActReviewed: false,
  pipelineIsScriptEnd: false,
  pipelineCompletionReason: '',
  pipelineCompletionSnapshot: null,
  pipelineGenerationInFlight: false,
  pipelineGenerationTargetAct: '',
  editorRichContent: '',
  scriptContent: '',
}

const history = loadVersionHistory()
const latestVersionData = sanitizeStateData(history.versions[0]?.data || {})
const latestDraftData = loadDraftState()

if (history.versions.length > 0) {
  console.log(`✅ 时光机已启动，找到 ${history.versions.length} 个历史版本`)
  console.log('💡 输入 showVersions() 查看所有版本')
}

function cloneDefaultState() {
  return JSON.parse(JSON.stringify(DEFAULT_STATE))
}

const initialState = { ...cloneDefaultState(), ...latestVersionData, ...latestDraftData }
initialState.title = normalizeStoredTitle(initialState.title)
export const globalState = reactive(initialState)

export function resetProjectWorkspace() {
  if (saveTimer) {
    clearTimeout(saveTimer)
    saveTimer = null
  }
  if (draftSaveTimer) {
    clearTimeout(draftSaveTimer)
    draftSaveTimer = null
  }

  localStorage.removeItem(DRAFT_SAVE_KEY)
  localStorage.removeItem(AUTOSAVE_KEY)
  localStorage.removeItem(MANUAL_SAVE_KEY)
  if (typeof window !== 'undefined') {
    sessionStorage.removeItem(NEXT_SERIES_EPISODE_KEY)
  }
  Object.assign(globalState, cloneDefaultState())
}

function normalizeNextSeriesEpisodePrefill(prefill = '') {
  if (prefill && typeof prefill === 'object') {
    return {
      previousEnding: String(prefill.previousEnding ?? '').trim(),
      characterFocus: String(prefill.characterFocus ?? '').trim(),
      toneDirection: String(prefill.toneDirection ?? '').trim(),
      cliffhanger: String(prefill.cliffhanger ?? '').trim(),
    }
  }

  return {
    previousEnding: String(prefill || '').trim(),
    characterFocus: '',
    toneDirection: '',
    cliffhanger: '',
  }
}

function buildNextSeriesEpisodeState(prefill = '') {
  const normalizedPrefill = normalizeNextSeriesEpisodePrefill(prefill)
  return {
    pipelineScriptFormat: 'series',
    pipelineSeriesPreviousEnding: normalizedPrefill.previousEnding,
    pipelineSeriesCharacterFocus: normalizedPrefill.characterFocus,
    pipelineSeriesToneDirection: normalizedPrefill.toneDirection,
    pipelineSeriesCliffhanger: normalizedPrefill.cliffhanger,
    pipelineRequirements: '',
    pipelineCharacters: '',
    pipelineOutline: '',
    pipelineActiveStep: 0,
    pipelineLatestActReviewed: false,
    pipelineIsScriptEnd: false,
    pipelineCompletionReason: '',
    pipelineCompletionSnapshot: null,
    pipelineGenerationInFlight: false,
    pipelineGenerationTargetAct: '',
    editorRichContent: '',
    scriptContent: '',
  }
}

export function prepareNextSeriesEpisode(prefill = '') {
  Object.assign(globalState, buildNextSeriesEpisodeState(prefill))
}

export function queueNextSeriesEpisode(prefill = '') {
  if (typeof window === 'undefined') return false

  try {
    const normalizedPrefill = normalizeNextSeriesEpisodePrefill(prefill)
    sessionStorage.setItem(NEXT_SERIES_EPISODE_KEY, JSON.stringify(normalizedPrefill))
    return true
  } catch (error) {
    console.warn('缓存下一集电视剧续写信息失败。', error)
    return false
  }
}

export function consumeQueuedNextSeriesEpisode() {
  if (typeof window === 'undefined') return false

  const saved = sessionStorage.getItem(NEXT_SERIES_EPISODE_KEY)
  if (!saved) return false

  sessionStorage.removeItem(NEXT_SERIES_EPISODE_KEY)

  try {
    const payload = JSON.parse(saved)
    prepareNextSeriesEpisode(payload || '')
    return true
  } catch (error) {
    console.warn('恢复下一集电视剧续写信息失败。', error)
    return false
  }
}

const fieldsToWatch = [
  () => globalState.scriptContent,
  () => globalState.editorRichContent,
  () => globalState.pipelineRequirements,
  () => globalState.pipelineCharacters,
  () => globalState.pipelineOutline,
  () => globalState.pipelineScriptFormat,
  () => globalState.pipelineMovieCoreIdea,
  () => globalState.pipelineMovieProtagonist,
  () => globalState.pipelineMovieConflict,
  () => globalState.pipelineMovieTone,
  () => globalState.pipelineSeriesPreviousEnding,
  () => globalState.pipelineSeriesCharacterFocus,
  () => globalState.pipelineSeriesToneDirection,
  () => globalState.pipelineSeriesCliffhanger,
  () => globalState.pipelineMicroHook,
  () => globalState.pipelineMicroProtagonist,
  () => globalState.pipelineMicroConflict,
  () => globalState.pipelineMicroTone,
  () => globalState.pipelineActiveStep,
  () => globalState.pipelineLatestActReviewed,
  () => globalState.pipelineIsScriptEnd,
  () => globalState.pipelineCompletionReason,
  () => globalState.pipelineCompletionSnapshot,
]

let saveTimer = null
let draftSaveTimer = null
fieldsToWatch.forEach(getter => {
  watch(getter, () => {
    if (draftSaveTimer) clearTimeout(draftSaveTimer)
    draftSaveTimer = setTimeout(saveDraftState, DRAFT_SAVE_DEBOUNCE_MS)
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = setTimeout(createNewVersion, AUTOSAVE_DEBOUNCE_MS)
  }, { deep: true })
})

watch(() => globalState.scriptContent, (value) => {
  globalState.title = buildScreenplayTitle(normalizeStoredTitle(globalState.title), value || '')
}, { immediate: true })

// 手动保存功能
function loadManualVersions() {
  try {
    const saved = localStorage.getItem(MANUAL_SAVE_KEY)
    if (saved) {
      const history = sanitizeHistoryPayload(JSON.parse(saved))
      return history
    }
  } catch (e) {
    console.warn('⚠️ 手动存档损坏，使用默认值')
  }
  return {
    currentVersionId: null,
    versions: [],
  }
}

function createManualVersion(description = '') {
  const history = loadManualVersions()
  const currentData = extractStateData()

  if (history.versions.length > 0) {
    const lastData = history.versions[0].data
    if (JSON.stringify(currentData) === JSON.stringify(lastData)) {
      console.log('⚠️ 内容未变化，无需手动保存')
      return
    }
  }

  const newVersion = {
    id: Date.now(),
    savedAt: Date.now(),
    savedAtReadable: new Date().toLocaleString('zh-CN'),
    description: description || '手动保存',
    data: currentData,
  }

  history.versions.unshift(newVersion)
  history.currentVersionId = newVersion.id

  if (history.versions.length > MAX_MANUAL_VERSIONS) {
    history.versions = history.versions.slice(0, MAX_MANUAL_VERSIONS)
  }

  localStorage.setItem(MANUAL_SAVE_KEY, JSON.stringify(history))
  console.log(`💾 已手动保存版本 #${history.versions.length}/${MAX_MANUAL_VERSIONS}，${newVersion.savedAtReadable}`)
  console.log(`📝 描述：${newVersion.description}`)
  return newVersion
}

function restoreManualVersion(versionId) {
  const history = loadManualVersions()
  const version = history.versions.find(v => v.id === versionId)
  
  if (!version) {
    console.error('❌ 找不到这个手动保存版本')
    return
  }

  Object.assign(globalState, version.data)
  history.currentVersionId = versionId
  localStorage.setItem(MANUAL_SAVE_KEY, JSON.stringify(history))
  
  console.log(`⏰ 已恢复到手动保存版本：${version.savedAtReadable}`)
  console.log(`📝 描述：${version.description}`)
  console.log('👉 页面数据已自动刷新！')
}

function showManualVersions() {
  const history = loadManualVersions()
  console.log('\n')
  console.log('%c⏰ 手动保存版本', 'font-size: 16px; font-weight: bold; color: #67c23a;')
  console.log('='.repeat(60))
  
  if (history.versions.length === 0) {
    console.log('📭 暂无手动保存版本')
  } else {
    history.versions.forEach((v, i) => {
      const isCurrent = v.id === history.currentVersionId ? '  ← 当前版本' : ''
      const flag = v.id === history.currentVersionId ? '🟢' : '🟡'
      console.log(`%c${flag} [${i}] ${v.savedAtReadable}${isCurrent}`, 
        v.id === history.currentVersionId ? 'color: #67c23a; font-weight: bold' : 'color: #e6a23c')
      console.log(`   📝 描述: ${v.description}`)
      console.log(`   恢复命令: restoreManualVersion(${v.id})`)
    })
  }
  
  console.log('='.repeat(60))
  console.log('%c💡 提示: 输入 saveManually("描述") 手动保存', 'color: #909399')
  console.log('%c💡 提示: 输入 showManualVersions() 查看手动版本', 'color: #909399')
  console.log('%c💡 提示: 输入 restoreManualVersion(版本号) 恢复手动版本', 'color: #909399')
  console.log('\n')
}

function clearManualVersions() {
  localStorage.removeItem(MANUAL_SAVE_KEY)
  console.log('🗑️ 所有手动保存版本已清空，刷新页面生效！')
}

// 导出手动保存相关函数
window.saveManually = createManualVersion
window.showManualVersions = showManualVersions
window.restoreManualVersion = restoreManualVersion
window.clearManualVersions = clearManualVersions
