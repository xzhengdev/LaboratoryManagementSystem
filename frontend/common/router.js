function encodeQuery(query = {}) {
  const pairs = Object.keys(query)
    .filter((key) => query[key] !== '' && query[key] !== undefined && query[key] !== null)
    .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(query[key])}`)
  return pairs.length ? `?${pairs.join('&')}` : ''
}

export function buildUrl(path, query = {}) {
  return `${path}${encodeQuery(query)}`
}

// ? H5 ?????
// 1. replace ???? redirectTo???? reLaunch ??
// 2. ?????? navigateTo?????? redirectTo/reLaunch
export function openPage(path, options = {}) {
  const { query = {}, replace = false } = options
  const url = buildUrl(path, query)

  if (replace) {
    return uni.redirectTo({
      url,
      fail: () => uni.reLaunch({ url })
    })
  }

  return uni.navigateTo({
    url,
    fail: () =>
      uni.redirectTo({
        url,
        fail: () => uni.reLaunch({ url })
      })
  })
}
