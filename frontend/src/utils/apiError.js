export const getRequestErrorMessage = (error, fallbackText) => {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail.trim()
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((item) => item?.msg || item?.message || String(item || ''))
      .filter(Boolean)
      .join('；') || fallbackText
  }

  const code = error?.code
  const message = error?.message
  if (code === 'ERR_NETWORK' || /network error/i.test(message || '')) {
    return '无法连接本地服务。可能是本地后端已自动关闭，请重新启动系统后再试。'
  }
  if (code === 'ECONNABORTED' || /timeout/i.test(message || '')) {
    return '请求超时，模型生成时间较长，请稍后再试。'
  }
  if (typeof message === 'string' && message.trim()) return message.trim()
  return fallbackText
}
