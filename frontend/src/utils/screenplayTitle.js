const DEFAULT_TITLE = '剧本正文'
const LEGACY_PLACEHOLDER_TITLE = '白潮回响'
const ACT_SECTION_PATTERN = /^第[一二三四五六七八九十百零\d]+幕[·.、-]?第[一二三四五六七八九十百零\d]+节$/
const SCENE_NUMBER_PATTERN = /^第[一二三四五六七八九十百零\d]+场$/
const SCENE_HEADING_PREFIXES = ['内景', '外景', '内外景', '外内景', '画外音']

export function sanitizeScreenplayText(text) {
  if (!text) return ''

  return String(text)
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .replace(/\t/g, '  ')
    .replace(/[^\S\n]+$/gm, '')
    .replace(/^[ \t]*#{1,6}[ \t]*/gm, '')
    .replace(/^[ \t]*>[ \t]*/gm, '')
    .replace(/^[ \t]*[-*]+[ \t]*/gm, '')
    .replace(/^[ \t]*\d+\.[ \t]*/gm, '')
    .replace(/[`*_~]/g, '')
    .replace(/\bINT\.\s*/gi, '内景 ')
    .replace(/\bEXT\.\s*/gi, '外景 ')
    .replace(/\bO\.S\.\b/gi, '画外音')
    .replace(/\(O\.S\.\)/gi, '画外音')
    .replace(/[ ]{2,}/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function isSceneHeadingLine(line) {
  const trimmed = String(line || '').trim()
  return SCENE_HEADING_PREFIXES.some((prefix) => trimmed.startsWith(prefix))
}

function isStructureLine(line) {
  const trimmed = String(line || '').trim()
  return ACT_SECTION_PATTERN.test(trimmed) || SCENE_NUMBER_PATTERN.test(trimmed) || isSceneHeadingLine(trimmed)
}

export function buildScreenplayTitle(inputTitle, content) {
  const title = String(inputTitle || '').trim()
  if (title && title !== LEGACY_PLACEHOLDER_TITLE) return title

  const candidate = sanitizeScreenplayText(content)
    .split('\n')
    .map((line) => line.trim())
    .find((line) => line && !isStructureLine(line))

  if (!candidate) return DEFAULT_TITLE
  return candidate.replace(/[\\/:*?"<>|]/g, '').slice(0, 24) || DEFAULT_TITLE
}

export function normalizeStoredTitle(title) {
  const normalized = String(title || '').trim()
  if (!normalized || normalized === LEGACY_PLACEHOLDER_TITLE) {
    return ''
  }
  return normalized
}
