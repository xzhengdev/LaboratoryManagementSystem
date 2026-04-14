import { isTabRoute } from '../config/navigation'

function encodeQuery(query = {}) {
  const pairs = Object.keys(query)
    .filter((key) => query[key] !== '' && query[key] !== undefined && query[key] !== null)
    .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(query[key])}`)
  return pairs.length ? `?${pairs.join('&')}` : ''
}

export function buildUrl(path, query = {}) {
  return `${path}${encodeQuery(query)}`
}

// 统一处理三种跳转语义：
// 1. Tab 页优先走 switchTab
// 2. replace 场景走 redirectTo
// 3. 其余默认使用 navigateTo
export function openPage(path, options = {}) {
  const { query = {}, replace = false } = options
  const url = buildUrl(path, query)

  if (isTabRoute(path) && typeof uni.switchTab === 'function' && !query && !replace) {
    return uni.switchTab({ url: path })
  }

  if (isTabRoute(path) && typeof uni.switchTab === 'function' && Object.keys(query).length === 0 && !replace) {
    return uni.switchTab({ url: path })
  }

  if (replace) {
    return uni.redirectTo({ url })
  }

  return uni.navigateTo({ url })
}
