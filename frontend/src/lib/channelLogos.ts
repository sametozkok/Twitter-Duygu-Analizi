const STORAGE_KEY = 'channelLogoMap'

export type ChannelLogoMap = Record<string, string>

function normalizeChannelKey(channel: string): string {
  return channel.trim().replace(/^@/, '').toLowerCase()
}

export function getChannelLogoMap(): ChannelLogoMap {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw) as unknown
    if (!parsed || typeof parsed !== 'object') return {}
    return parsed as ChannelLogoMap
  } catch {
    return {}
  }
}

export function getChannelLogoUrl(channel: string): string | null {
  const key = normalizeChannelKey(channel)
  const map = getChannelLogoMap()
  const url = map[key]
  return typeof url === 'string' && url.trim() ? url.trim() : null
}

export function setChannelLogoUrl(channel: string, url: string | null) {
  const key = normalizeChannelKey(channel)
  const next = { ...getChannelLogoMap() }
  if (!url) {
    delete next[key]
  } else {
    next[key] = url
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    // ignore
  }
}

