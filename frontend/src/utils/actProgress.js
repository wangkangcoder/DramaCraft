import {
  DEFAULT_SCRIPT_FORMAT,
  getActIndex,
  getLastActLabel,
  getScriptFormatActSequence,
  toChineseActCount,
} from './scriptFormat'

const ALL_ACT_LABELS = Array.from(
  new Set(
    Object.values({
      movie: getScriptFormatActSequence('movie'),
      series: getScriptFormatActSequence('series'),
      micro: getScriptFormatActSequence('micro'),
    }).flat()
  )
)

const escapeRegExp = (value = '') => String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

const ACT_LABEL_RE = new RegExp(
  `(${ALL_ACT_LABELS.map(escapeRegExp).join('|')})[·.路]?第[一二三四五六七八九十百零\\d]+节`,
  'g'
)

export const ACT_SEQUENCE = getScriptFormatActSequence(DEFAULT_SCRIPT_FORMAT)

export function normalizeActLabel(label = '', scriptFormat = DEFAULT_SCRIPT_FORMAT) {
  const normalized = String(label || '').trim()
  return getScriptFormatActSequence(scriptFormat).includes(normalized) ? normalized : ''
}

export function extractActLabels(text = '', scriptFormat = DEFAULT_SCRIPT_FORMAT) {
  const labels = []
  const normalized = String(text || '')
  const actSequence = getScriptFormatActSequence(scriptFormat)

  for (const match of normalized.matchAll(ACT_LABEL_RE)) {
    const label = String(match[1] || '').trim()
    if (actSequence.includes(label) && !labels.includes(label)) labels.push(label)
  }

  return labels
}

export function inferLatestActLabel(text = '', scriptFormat = DEFAULT_SCRIPT_FORMAT) {
  const labels = extractActLabels(text, scriptFormat)
  return labels.length ? labels[labels.length - 1] : ''
}

export function getCurrentActLabel(completion = null, text = '', scriptFormat = DEFAULT_SCRIPT_FORMAT) {
  const labelFromCompletion = normalizeActLabel(completion?.current_act_label || '', scriptFormat)
  if (labelFromCompletion) return labelFromCompletion
  return inferLatestActLabel(text, scriptFormat)
}

export function getNextActLabel(completion = null, scriptFormat = DEFAULT_SCRIPT_FORMAT, text = '') {
  const currentLabel = getCurrentActLabel(completion, text, scriptFormat)
  const fromCompletion = normalizeActLabel(completion?.next_act_label || '', scriptFormat)
  if (fromCompletion && fromCompletion !== currentLabel) return fromCompletion

  const currentIndex = getActIndex(currentLabel, scriptFormat)
  const actSequence = getScriptFormatActSequence(scriptFormat)
  if (fromCompletion && !currentLabel) return fromCompletion
  if (!currentIndex) return actSequence[0] || ''
  return actSequence[currentIndex] || ''
}

export function formatActProgress(
  completion = null,
  text = '',
  {
    scriptFormat = DEFAULT_SCRIPT_FORMAT,
    latestActReviewed = false,
  } = {}
) {
  const current = getCurrentActLabel(completion, text, scriptFormat)
  const currentIndex = getActIndex(current, scriptFormat)
  const finalActLabel = getLastActLabel(scriptFormat)
  const isComplete = Boolean(completion?.is_complete) || (
    current === finalActLabel && !getNextActLabel(completion, scriptFormat, text)
  )

  if (!currentIndex) return '尚未生成剧本'

  if (isComplete) {
    return latestActReviewed ? '已完结' : '已完结（未修改）'
  }

  const base = `已完成${toChineseActCount(currentIndex)}幕`
  return latestActReviewed ? base : `${base}（未修改）`
}
