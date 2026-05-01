const INTERNAL_SCAFFOLD_PREFIXES = [
  '上一场位于：',
  '当前目标：',
  '校验备注：',
  '推进说明：',
  '关键对白：',
  '动作描述：',
  '承接上节：',
  '承接上场：',
]

const INTERNAL_SCAFFOLD_HEADINGS = new Set([
  '承接上场',
  '承接上节',
  '动作描述',
  '推进说明',
  '关键对白',
])

const INTERNAL_SCAFFOLD_FRAGMENTS = [
  '没有停留在上一场的情绪里',
  '局势因此发生了不可逆的变化',
  '埋下了更具体的后果',
  '没有真正推进当前应写的大纲节点',
  '这一次，我们不能再原地打转了。',
]

const DIALOGUE_SPEAKER_PATTERN = /^[\u4e00-\u9fff]{2,6}$/

const isInternalScaffoldLine = (line = '') => {
  const stripped = String(line).trim()
  if (!stripped) return false
  if (INTERNAL_SCAFFOLD_HEADINGS.has(stripped)) return true
  if (INTERNAL_SCAFFOLD_PREFIXES.some((prefix) => stripped.startsWith(prefix))) return true
  return INTERNAL_SCAFFOLD_FRAGMENTS.some((fragment) => stripped.includes(fragment))
}

export const stripInternalScaffolding = (text = '') => {
  const lines = String(text).split('\n')
  const kept = []

  lines.forEach((rawLine) => {
    const line = rawLine.trim()
    if (isInternalScaffoldLine(line)) {
      if (kept.length && DIALOGUE_SPEAKER_PATTERN.test(String(kept[kept.length - 1]).trim())) {
        kept.pop()
      }
      return
    }
    kept.push(rawLine)
  })

  return kept.join('\n')
}

export const normalizeScriptText = (text, { trim = true } = {}) => {
  if (!text) return ''

  const normalized = stripInternalScaffolding(
    String(text)
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n')
      .replace(/[#*_`]/g, '')
      .replace(/\bEXT\.\s*/gi, '外景 ')
      .replace(/\bINT\.\s*/gi, '内景 ')
  ).replace(/\n{3,}/g, '\n\n')

  return trim ? normalized.trim() : normalized
}
