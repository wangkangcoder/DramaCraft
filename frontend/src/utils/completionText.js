export const REVIEWED_COMPLETE_MESSAGE = '当前题材的全部幕次已经完成并完成复核，可以导出 PDF。'
export const UNREVIEWED_COMPLETE_MESSAGE = '当前题材的全部幕次已经生成完成，请先完成最后一幕修改，确认无误后再导出 PDF。'

export function getLockedCompletionNotice(completion = null, latestActReviewed = false) {
  if (latestActReviewed) return REVIEWED_COMPLETE_MESSAGE

  const reason = String(completion?.reason || '').trim()
  return reason || UNREVIEWED_COMPLETE_MESSAGE
}
