export const DEFAULT_SCRIPT_FORMAT = 'movie'

export const SCRIPT_FORMATS = {
  movie: {
    value: 'movie',
    label: '电影',
    shortLabel: '电影',
    acts: ['第一幕', '第二幕', '第三幕'],
    outlineSections: [
      { label: '第一幕', description: '开端（建置、触发事件）' },
      { label: '第二幕', description: '发展（对抗、冲突升级）' },
      { label: '第三幕', description: '结局（高潮、解决）' },
    ],
    fields: [
      {
        key: 'coreIdea',
        label: '核心立意',
        summaryLabel: '核心立意',
        description: '写核心情感、价值观或观点',
        placeholder: '例如：失序世界里，救人的不是技术，而是愿不愿为彼此付代价。',
      },
      {
        key: 'protagonist',
        label: '主角人物设定',
        summaryLabel: '主角设定',
        description: '写主角是谁、有什么能力、被什么困住',
        placeholder: '例如：沈岚是海上机器人工程师，擅长故障推演，却困在当年事故的愧疚里。',
      },
      {
        key: 'conflict',
        label: '核心冲突',
        summaryLabel: '核心冲突',
        description: '写主冲突如何推进',
        placeholder: '例如：她要在隐瞒真相和公开证据、撕开旧秩序之间做选择。',
      },
      {
        key: 'tone',
        label: '调性与风格',
        summaryLabel: '调性风格',
        description: '写类型和整体感觉',
        placeholder: '例如：工业感悬疑科幻，冷硬压迫，节奏由慢转快。',
      },
    ],
    panelHint: '适合长片，强调主题、主角弧光和三幕推进。',
  },
  series: {
    value: 'series',
    label: '电视/连续剧',
    shortLabel: '连续剧',
    acts: ['第一幕', '第二幕', '第三幕', '第四幕'],
    outlineSections: [
      { label: '第一幕', description: '交代情况 + 抛出问题' },
      { label: '第二幕', description: '开始行动 + 遇到麻烦' },
      { label: '第三幕', description: '矛盾激化 + 陷入绝境' },
      { label: '第四幕', description: '解决危机 + 留下新悬念' },
    ],
    fields: [
      {
        key: 'previousEnding',
        label: '上集结尾剧情',
        summaryLabel: '上集结尾',
        description: '写上集结尾；第一集填当前背景',
        placeholder: '例如：上集末尾，女主收到匿名快递，里面是失踪父亲的旧图纸。',
      },
      {
        key: 'characterFocus',
        label: '本集人物重心',
        summaryLabel: '人物重心',
        description: '写本集主角和核心困境',
        placeholder: '例如：本集主角林雾，要在保护弟弟和追查组织间做选择。',
      },
      {
        key: 'toneDirection',
        label: '本集调性与走向',
        summaryLabel: '调性走向',
        description: '写本集基调和剧情走向',
        placeholder: '例如：前半压抑试探，后半升级冲突，整体从怀疑走向爆发。',
      },
      {
        key: 'cliffhanger',
        label: '本集结尾悬念',
        summaryLabel: '结尾悬念',
        description: '写本集悬念；最后一集填未来走向',
        placeholder: '例如：结尾发现真正的操盘者，其实就在主角团队内部。',
      },
    ],
    panelHint: '适合单集推进，强调承上启下和连续悬念。',
  },
  micro: {
    value: 'micro',
    label: '短/微短剧',
    shortLabel: '微短剧',
    acts: ['第一幕', '第二幕'],
    outlineSections: [
      { label: '第一幕', description: '危机开局、强冲突' },
      { label: '第二幕', description: '解决打脸、爽点爆发' },
    ],
    fields: [
      {
        key: 'hook',
        label: '钩子',
        summaryLabel: '开篇钩子',
        description: '写开篇最抓人的悬念点',
        placeholder: '例如：婚礼前，新郎当众播放女主三年前的“背叛证据”。',
      },
      {
        key: 'protagonist',
        label: '主角',
        summaryLabel: '主角',
        description: '写身份和核心欲望',
        placeholder: '例如：女主是被雪藏的天才律师，最想当众翻案、拿回名声。',
      },
      {
        key: 'conflict',
        label: '冲突',
        summaryLabel: '核心冲突',
        description: '写核心矛盾往哪边发展',
        placeholder: '例如：她要在众人认定自己有罪时，反手揭穿真正操盘者。',
      },
      {
        key: 'tone',
        label: '调性',
        summaryLabel: '调性',
        description: '写风格和节奏',
        placeholder: '例如：节奏极快，情绪高压，反击干脆，爽点密集。',
      },
    ],
    panelHint: '适合强钩子和快节奏，重点是迅速抓人、快速给爽点。',
  },
}

const SCRIPT_FORMAT_ALIASES = {
  movie: 'movie',
  film: 'movie',
  电影: 'movie',
  series: 'series',
  tv: 'series',
  '电视/连续剧': 'series',
  '电视/连续句': 'series',
  电视: 'series',
  连续剧: 'series',
  电视剧: 'series',
  micro: 'micro',
  short: 'micro',
  微短剧: 'micro',
  短剧: 'micro',
  '短/微短剧': 'micro',
}

export function resolveScriptFormat(value = '') {
  const normalized = String(value || '').trim()
  return SCRIPT_FORMAT_ALIASES[normalized] || DEFAULT_SCRIPT_FORMAT
}

export function getScriptFormatConfig(value = '') {
  const resolved = resolveScriptFormat(value)
  return SCRIPT_FORMATS[resolved] || SCRIPT_FORMATS[DEFAULT_SCRIPT_FORMAT]
}

export function getScriptFormatOptions() {
  return Object.values(SCRIPT_FORMATS)
}

export function getScriptFormatActSequence(value = '') {
  return [...getScriptFormatConfig(value).acts]
}

export function getActIndex(label = '', scriptFormat = '') {
  const acts = getScriptFormatActSequence(scriptFormat)
  const index = acts.indexOf(String(label || '').trim())
  return index >= 0 ? index + 1 : 0
}

export function getLastActLabel(scriptFormat = '') {
  const acts = getScriptFormatActSequence(scriptFormat)
  return acts[acts.length - 1] || ''
}

export function toChineseActCount(count = 0) {
  const map = ['', '一', '两', '三', '四', '五', '六']
  return map[count] || String(count)
}
