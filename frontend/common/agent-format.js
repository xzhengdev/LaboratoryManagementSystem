const TERM_MAP = {
  pending: '\u5f85\u5ba1\u6279',
  approved: '\u5df2\u901a\u8fc7',
  rejected: '\u5df2\u9a73\u56de',
  reject: '\u9a73\u56de',
  cancelled: '\u5df2\u53d6\u6d88',
  canceled: '\u5df2\u53d6\u6d88',
  reservation: '\u9884\u7ea6',
  reservations: '\u9884\u7ea6',
  approval: '\u5ba1\u6279',
  approvals: '\u5ba1\u6279',
  create: '\u521b\u5efa',
  update: '\u66f4\u65b0',
  cancel: '\u53d6\u6d88',
  active: '\u542f\u7528',
  disabled: '\u505c\u7528',
  not_found: '\u672a\u627e\u5230',
  query_failed: '\u67e5\u8be2\u5931\u8d25',
  time_conflict: '\u65f6\u95f4\u51b2\u7a81',
  missing_fields: '\u7f3a\u5c11\u5b57\u6bb5'
}

const PATH_MAP = {
  '/pages/my-reservations/my-reservations': '/pages/my-reservations/index',
  '/pages/agent/chat': '/pages/agent/index',
  '/pages/agent/index': '/pages/agent/index'
}

function replaceMappedTerms(content) {
  const keys = Object.keys(TERM_MAP).sort((a, b) => b.length - a.length)
  return keys.reduce((text, key) => {
    const pattern = new RegExp(`\\b${key}\\b`, 'gi')
    return text.replace(pattern, TERM_MAP[key])
  }, String(content || ''))
}

export function formatAgentReply(content) {
  const text = String(content || '')
  return replaceMappedTerms(
    text
      .replace(/```[\s\S]*?```/g, (block) => block.replace(/```/g, '').trim())
      .replace(/^#{1,6}\s*/gm, '')
      .replace(/^\s*>\s?/gm, '')
      .replace(/\*\*(.*?)\*\*/g, '$1')
      .replace(/\*(.*?)\*/g, '$1')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/^\s*[-*+]\s+/gm, '- ')
      .replace(/\n{3,}/g, '\n\n')
      .trim()
  )
}

export function normalizeAgentPath(path) {
  const raw = String(path || '')
  return PATH_MAP[raw] || raw
}

export function normalizeAgentActions(actions) {
  if (!Array.isArray(actions)) return []
  return actions.map((item) => ({
    ...item,
    label: formatAgentReply(item?.label || ''),
    path: normalizeAgentPath(item?.path)
  }))
}
