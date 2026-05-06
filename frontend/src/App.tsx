import { useEffect, useMemo, useState } from 'react'
import { deleteRun, getRun, listRuns, runMatch, runReplies, runSentimentCompare } from './lib/api'
import type {
  MatchResponse,
  RepliesResponse,
  RunSummary,
  SentimentCompareResponse,
  TweetItem,
} from './types'

/* ========== Helpers ========== */

function renderTweetLabel(tweet: TweetItem, index: number) {
  return tweet.channel ? `@${tweet.channel}` : `Tweet ${index + 1}`
}

function formatCompactNumber(value?: number) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric) || numeric < 0) return '0'
  return new Intl.NumberFormat('tr-TR', { notation: 'compact', maximumFractionDigits: 1 }).format(numeric)
}

function formatMetricValue(value?: number) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric) || numeric <= 0) return '-'
  return formatCompactNumber(numeric)
}

function formatDateLabel(value?: string) {
  if (!value) return '-'
  const parsed = Date.parse(value)
  if (Number.isNaN(parsed)) return value
  // API returns UTC, add 3 hours for Turkey (UTC+3)
  const corrected = new Date(parsed + 3 * 60 * 60 * 1000)
  return new Intl.DateTimeFormat('tr-TR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }).format(corrected)
}

function formatRunTimestamp(value?: string) {
  if (!value) return '-'
  const parsed = Date.parse(value)
  if (Number.isNaN(parsed)) return value
  return new Intl.DateTimeFormat('tr-TR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(parsed))
}

function buildReplyKey(topic: string, tweetIndex: number) {
  return `${topic}::${tweetIndex}`
}

function extractChannelName(url: string): string {
  const trimmed = url.trim()
  const match = trimmed.match(/(?:x\.com|twitter\.com)\/(@?[\w]+)/i)
  if (match) return match[1].replace(/^@/, '')
  const atMatch = trimmed.match(/^@?([\w]+)$/)
  if (atMatch) return atMatch[1]
  return trimmed
}

/* ========== SVG Icons ========== */

function XLogo() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  )
}

/* ========== Doughnut Chart Component ========== */

function DoughnutChart({ positive, negative, neutral }: { positive: number; negative: number; neutral: number }) {
  const total = positive + negative + neutral
  if (total === 0) return null

  const pPct = (positive / total) * 100
  const negPct = (negative / total) * 100
  const neuPct = (neutral / total) * 100

  const radius = 68
  const circumference = 2 * Math.PI * radius

  const pLen = (pPct / 100) * circumference
  const negLen = (negPct / 100) * circumference
  const neuLen = (neuPct / 100) * circumference

  const gap = 4
  const pOffset = 0
  const negOffset = pLen + gap
  const neuOffset = pLen + negLen + gap * 2

  const dominantLabel = pPct >= negPct && pPct >= neuPct ? 'Pozitif' : negPct >= pPct && negPct >= neuPct ? 'Negatif' : 'Nötr'
  const dominantPct = Math.round(Math.max(pPct, negPct, neuPct))

  return (
    <div className="chart-container">
      <div className="doughnut-wrapper">
        <svg className="doughnut-svg" viewBox="0 0 180 180">
          <circle className="doughnut-segment" cx="90" cy="90" r={radius} stroke="var(--positive)" strokeDasharray={`${pLen} ${circumference - pLen}`} strokeDashoffset={-pOffset} />
          <circle className="doughnut-segment" cx="90" cy="90" r={radius} stroke="var(--negative)" strokeDasharray={`${negLen} ${circumference - negLen}`} strokeDashoffset={-negOffset} />
          <circle className="doughnut-segment" cx="90" cy="90" r={radius} stroke="var(--neutral)" strokeDasharray={`${neuLen} ${circumference - neuLen}`} strokeDashoffset={-neuOffset} />
        </svg>
        <div className="doughnut-center">
          <span className="doughnut-center-value">%{dominantPct}</span>
          <span className="doughnut-center-label">{dominantLabel}</span>
        </div>
      </div>
      <div className="chart-legend">
        <div className="legend-item">
          <span className="legend-dot" style={{ background: 'var(--positive)' }} />
          <strong>{Math.round(pPct)}%</strong> Pozitif
        </div>
        <div className="legend-item">
          <span className="legend-dot" style={{ background: 'var(--negative)' }} />
          <strong>{Math.round(negPct)}%</strong> Negatif
        </div>
        <div className="legend-item">
          <span className="legend-dot" style={{ background: 'var(--neutral)' }} />
          <strong>{Math.round(neuPct)}%</strong> Nötr
        </div>
      </div>
    </div>
  )
}

/* ========== Word Cloud Component ========== */

function WordCloud({ words }: { words: { text: string; weight: number }[] }) {
  if (!words.length) return null

  const maxWeight = Math.max(...words.map((w) => w.weight))
  const colors = ['var(--accent)', 'var(--positive)', 'var(--neutral)', '#d291ff', '#ff6b9d', '#79e2f2', '#ffad5c']

  return (
    <div className="word-cloud-section">
      <div className="word-cloud-title">
        <span className="icon">cloud</span>
        Kelime Bulutu
      </div>
      <div className="word-cloud">
        {words.map((w, i) => {
          const normalizedWeight = w.weight / maxWeight
          const fontSize = 11 + normalizedWeight * 14
          const color = colors[i % colors.length]
          return (
            <span key={w.text} className="word-tag" style={{ fontSize: `${fontSize}px`, color, background: `${color}15`, border: `1px solid ${color}30` }}>
              {w.text}
            </span>
          )
        })}
      </div>
    </div>
  )
}

const ALGORITHM_ORDER = [
  { key: 'bert', title: 'BERT', fallbackEngine: 'bert-model' },
  { key: 'api', title: 'Gemini API', fallbackEngine: 'gemini-api' },
]

/* ========== Main App ========== */

export default function App() {
  /* --- State --- */
  const [channels, setChannels] = useState<string[]>(['haber', 'bpthaber', 'pusholder'])
  const [tweetsPerChannel, setTweetsPerChannel] = useState<number | ''>(10)
  const [minChannelsForMatch, setMinChannelsForMatch] = useState<number | ''>(2)
  const [replyCount, setReplyCount] = useState<number | ''>(20)
  const [twitterAuthToken, setTwitterAuthToken] = useState('')
  const [twitterCt0, setTwitterCt0] = useState('')
  const [twitterBearerToken, setTwitterBearerToken] = useState('')

  const [isMatching, setIsMatching] = useState(false)
  const [isFetchingReplies, setIsFetchingReplies] = useState(false)
  const [isComparingSentiment, setIsComparingSentiment] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [matchResult, setMatchResult] = useState<MatchResponse | null>(null)
  const [repliesResult, setRepliesResult] = useState<RepliesResponse | null>(null)
  const [compareResult, setCompareResult] = useState<SentimentCompareResponse | null>(null)
  const [selectedGroupIndex, setSelectedGroupIndex] = useState(0)
  const [editingChannelIndex, setEditingChannelIndex] = useState<number | null>(null)
  const [expandedReplies, setExpandedReplies] = useState<Record<string, boolean>>({})

  const [currentView, setCurrentView] = useState<'dashboard' | 'archive'>('dashboard')
  const [currentRunId, setCurrentRunId] = useState<string | null>(null)
  const [archiveRuns, setArchiveRuns] = useState<RunSummary[]>([])
  const [archiveLoading, setArchiveLoading] = useState(false)
  const [archiveError, setArchiveError] = useState<string | null>(null)
  const [archiveOpeningId, setArchiveOpeningId] = useState<string | null>(null)
  const [archiveDeletingId, setArchiveDeletingId] = useState<string | null>(null)

  const activeChannels = useMemo(
    () => channels.map((item) => item.trim()).filter((item) => item.length > 0),
    [channels],
  )

  const shownGroups = repliesResult?.matched_groups ?? matchResult?.matched_groups ?? []
  const isRepliesReady = Boolean(repliesResult)
  const selectedGroupIndexSafe = selectedGroupIndex < shownGroups.length ? selectedGroupIndex : 0
  const selectedGroup = shownGroups[selectedGroupIndexSafe] ?? null
  const selectedCompareGroup = compareResult?.compared_groups.find((g) => g.topic === selectedGroup?.topic) ?? null

  const algorithmTotals = useMemo(() => {
    if (!selectedCompareGroup) return null
    const totals: Record<string, { positive: number; negative: number; neutral: number; total: number; engine?: string }> = {}

    ALGORITHM_ORDER.forEach((algo) => {
      totals[algo.key] = { positive: 0, negative: 0, neutral: 0, total: 0 }
    })

    Object.values(selectedCompareGroup.channel_results).forEach((cr) => {
      Object.entries(cr.algorithms).forEach(([name, algo]) => {
        if (!totals[name]) return
        totals[name].positive += algo.summary.positive
        totals[name].negative += algo.summary.negative
        totals[name].neutral += algo.summary.neutral
        totals[name].total += algo.summary.total
        if (!totals[name].engine && algo.engine) {
          totals[name].engine = algo.engine
        }
      })
    })

    return totals
  }, [selectedCompareGroup])

  const algorithmItems = useMemo(() => {
    if (!selectedCompareGroup) return null
    const itemsByAlgo: Record<string, Array<{ text?: string }>> = {}
    Object.values(selectedCompareGroup.channel_results).forEach((cr) => {
      Object.entries(cr.algorithms).forEach(([name, algo]) => {
        if (!itemsByAlgo[name]) itemsByAlgo[name] = []
        itemsByAlgo[name].push(...(algo.items ?? []))
      })
    })
    return itemsByAlgo
  }, [selectedCompareGroup])

  const wordCloudByAlgorithm = useMemo(() => {
    if (!algorithmItems) return null
    const buildCloud = (items: Array<{ text?: string }>) => {
      const wordCounts: Record<string, number> = {}
      items.forEach((item) => {
        if (!item.text) return
        const words = item.text.split(/\s+/).filter((w) => w.length > 3)
        words.forEach((w) => {
          const lower = w.toLowerCase().replace(/[^a-zçğıöşü0-9]/gi, '')
          if (lower.length > 3) {
            wordCounts[lower] = (wordCounts[lower] || 0) + 1
          }
        })
      })
      return Object.entries(wordCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 20)
        .map(([text, weight]) => ({ text, weight }))
    }

    const cloud: Record<string, { text: string; weight: number }[]> = {}
    Object.entries(algorithmItems).forEach(([name, items]) => {
      cloud[name] = buildCloud(items)
    })
    return cloud
  }, [algorithmItems])

  /* --- Handlers --- */
  function updateChannel(index: number, value: string) {
    setChannels((prev) => prev.map((item, i) => (i === index ? value : item)))
  }

  function addChannel() {
    setChannels((prev) => {
      setEditingChannelIndex(prev.length)
      return [...prev, '']
    })
  }

  function removeChannel(index: number) {
    setEditingChannelIndex(null)
    setChannels((prev) => {
      if (prev.length <= 2) return prev
      return prev.filter((_, i) => i !== index)
    })
  }

  function toggleReplies(topic: string, tweetIndex: number) {
    const key = buildReplyKey(topic, tweetIndex)
    setExpandedReplies((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  async function handleFetchMatches() {
    setError(null)
    if (activeChannels.length < 2) {
      setError('En az 2 kanal girmen gerekiyor.')
      return
    }
    setIsMatching(true)
    setRepliesResult(null)
    setCompareResult(null)
    setCurrentRunId(null)
    try {
      const response = await runMatch({ channels: activeChannels, tweets_per_channel: Number(tweetsPerChannel) || 10, min_channels_for_match: Number(minChannelsForMatch) || 2 })
      setMatchResult(response)
      setCurrentRunId(response.run_id ?? null)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Eşleştirme sırasında beklenmeyen hata oldu.')
    } finally {
      setIsMatching(false)
    }
  }

  async function handleFetchReplies() {
    setError(null)
    if (!matchResult?.matched_groups?.length) {
      setError('Önce tweetleri çekip eşleşmeleri bulman gerekiyor.')
      return
    }
    setIsFetchingReplies(true)
    try {
      const response = await runReplies({
        matched_groups: matchResult.matched_groups,
        reply_count: Number(replyCount) || 20,
        twitter_auth_token: twitterAuthToken.trim(),
        twitter_ct0: twitterCt0.trim(),
        twitter_bearer_token: twitterBearerToken.trim(),
        run_id: currentRunId,
      })
      setRepliesResult(response)
      setCompareResult(null)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Yorum çekme sırasında beklenmeyen hata oldu.')
    } finally {
      setIsFetchingReplies(false)
    }
  }

  async function handleCompareSentiment() {
    setError(null)
    if (!repliesResult?.matched_groups?.length) {
      setError('Duygu karşılaştırması için önce yorumları çekmelisin.')
      return
    }
    setIsComparingSentiment(true)
    try {
      const response = await runSentimentCompare({
        matched_groups: repliesResult.matched_groups,
        algorithms: ['bert', 'api'],
        save_to_json: true,
        run_id: currentRunId,
      })
      setCompareResult(response)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Duygu karşılaştırması sırasında beklenmeyen hata oldu.')
    } finally {
      setIsComparingSentiment(false)
    }
  }

  async function refreshArchiveList() {
    setArchiveLoading(true)
    setArchiveError(null)
    try {
      const response = await listRuns()
      setArchiveRuns(response.runs)
    } catch (e) {
      setArchiveError(e instanceof Error ? e.message : 'Arşiv listesi alınamadı.')
    } finally {
      setArchiveLoading(false)
    }
  }

  function showDashboardView() {
    setCurrentView('dashboard')
  }

  async function showArchiveView() {
    setCurrentView('archive')
    await refreshArchiveList()
  }

  async function openArchiveRun(runId: string) {
    setArchiveOpeningId(runId)
    setArchiveError(null)
    try {
      const detail = await getRun(runId)
      const matched = detail.matched_groups
      setMatchResult({
        matched_groups: matched,
        total_groups: detail.total_groups,
        status: 'archived',
        run_id: detail.run_id,
      })
      if (detail.has_replies) {
        setRepliesResult({
          matched_groups: matched,
          total_groups: detail.total_groups,
          total_replies: detail.total_replies,
          status: 'archived',
          run_id: detail.run_id,
        })
      } else {
        setRepliesResult(null)
      }
      if (detail.has_sentiment && detail.sentiment_compare) {
        setCompareResult({
          compared_groups: detail.sentiment_compare.compared_groups,
          total_groups: detail.sentiment_compare.compared_groups.length,
          status: 'archived',
          saved_file: null,
          run_id: detail.run_id,
        })
      } else {
        setCompareResult(null)
      }
      setCurrentRunId(detail.run_id)
      setSelectedGroupIndex(0)
      setExpandedReplies({})
      setError(null)
      setCurrentView('dashboard')
    } catch (e) {
      setArchiveError(e instanceof Error ? e.message : 'Arşiv kaydı yüklenemedi.')
    } finally {
      setArchiveOpeningId(null)
    }
  }

  async function removeArchiveRun(runId: string) {
    if (!window.confirm('Bu arşiv kaydını silmek istediğine emin misin?')) return
    setArchiveDeletingId(runId)
    setArchiveError(null)
    try {
      await deleteRun(runId)
      setArchiveRuns((prev) => prev.filter((r) => r.run_id !== runId))
      if (currentRunId === runId) {
        setMatchResult(null)
        setRepliesResult(null)
        setCompareResult(null)
        setCurrentRunId(null)
      }
    } catch (e) {
      setArchiveError(e instanceof Error ? e.message : 'Arşiv kaydı silinemedi.')
    } finally {
      setArchiveDeletingId(null)
    }
  }

  useEffect(() => {
    if (currentView === 'archive' && archiveRuns.length === 0 && !archiveLoading) {
      refreshArchiveList()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentView])

  /* ========== RENDER ========== */

  return (
    <div className="app-shell">
      {/* ===== 1. Nav Sidebar (Narrow Icon Bar) ===== */}
      <nav className="nav-sidebar" id="nav-sidebar">
        <button className="nav-logo" title="X Haber Analiz Pro" id="nav-logo">
          <XLogo />
        </button>

        <button
          className={`nav-item${currentView === 'dashboard' ? ' active' : ''}`}
          title="Dashboard"
          id="nav-dashboard"
          type="button"
          onClick={showDashboardView}
        >
          <span className="icon">dashboard</span>
        </button>
        <button
          className={`nav-item${currentView === 'archive' ? ' active' : ''}`}
          title="Arşiv"
          id="nav-archive"
          type="button"
          onClick={showArchiveView}
        >
          <span className="icon">history</span>
        </button>
        <button className="nav-item" title="Raporlar" id="nav-reports">
          <span className="icon">assessment</span>
        </button>
        <button className="nav-item" title="Arama" id="nav-search">
          <span className="icon">search</span>
        </button>
        <button className="nav-item" title="Bildirimler" id="nav-notifications">
          <span className="icon">notifications</span>
        </button>

        <div className="nav-spacer" />

        <button className="nav-item" title="Ayarlar" id="nav-settings">
          <span className="icon">settings</span>
        </button>
      </nav>

      {/* ===== 2. Left Panel (Settings + Channels) ===== */}
      <aside className="left-panel" id="left-panel">
        <div className="left-panel-header">
          <h1>Haber Analiz</h1>
        </div>

        {/* API Settings */}
        <section className="left-panel-section" id="api-settings">
          <div className="section-label">
            <span className="icon">key</span>
            API Ayarları
          </div>
          <div className="settings-grid">
            <div className="setting-field">
              <label htmlFor="auth-token-input">Auth Token</label>
              <input id="auth-token-input" type="password" value={twitterAuthToken} onChange={(e) => setTwitterAuthToken(e.target.value)} placeholder="auth_token" />
            </div>
            <div className="setting-field">
              <label htmlFor="ct0-input">ct0</label>
              <input id="ct0-input" type="password" value={twitterCt0} onChange={(e) => setTwitterCt0(e.target.value)} placeholder="ct0" />
            </div>
            <div className="setting-field">
              <label htmlFor="bearer-input">Bearer Token</label>
              <input id="bearer-input" type="password" value={twitterBearerToken} onChange={(e) => setTwitterBearerToken(e.target.value)} placeholder="Bearer ..." />
            </div>
          </div>
        </section>

        {/* Numeric Settings */}
        <section className="left-panel-section" id="numeric-settings">
          <div className="section-label">
            <span className="icon">tune</span>
            Parametreler
          </div>
          <div className="numeric-settings">
            <div className="numeric-field">
              <label>Tweet / Kanal</label>
              <input type="number" min={1} max={50} value={tweetsPerChannel} onChange={(e) => setTweetsPerChannel(e.target.value === '' ? '' : Number(e.target.value))} />
            </div>
            <div className="numeric-field">
              <label>Ortak Eşik</label>
              <input type="number" min={2} max={10} value={minChannelsForMatch} onChange={(e) => setMinChannelsForMatch(e.target.value === '' ? '' : Number(e.target.value))} />
            </div>
            <div className="numeric-field">
              <label>Yorum / Tweet</label>
              <input type="number" min={1} max={100} value={replyCount} onChange={(e) => setReplyCount(e.target.value === '' ? '' : Number(e.target.value))} />
            </div>
          </div>
        </section>

        {/* Channel Management */}
        <section className="left-panel-section" id="channel-management">
          <div className="section-label">
            <span className="icon">group</span>
            Kanal Yönetimi
          </div>
          <div className="channel-list">
            {channels.map((channel, index) => {
              const displayName = extractChannelName(channel)
              const hasValue = channel.trim().length > 0
              const isEditing = editingChannelIndex === index
              const showBadge = hasValue && displayName && !isEditing
              return (
                <div className="channel-badge" key={`channel-${index}`}>
                  <div className="channel-avatar">
                    {hasValue && displayName ? displayName.slice(0, 1).toUpperCase() : '?'}
                  </div>
                  {showBadge ? (
                    <div
                      className="channel-info"
                      onClick={() => setEditingChannelIndex(index)}
                      style={{ cursor: 'pointer' }}
                      title="Düzenlemek için tıklayın"
                    >
                      <span className="channel-name">{displayName}</span>
                      <span className="channel-handle">@{displayName}</span>
                    </div>
                  ) : (
                    <input
                      className="channel-input-inline"
                      type="text"
                      value={channel}
                      onChange={(e) => updateChannel(index, e.target.value)}
                      onBlur={() => setEditingChannelIndex(null)}
                      autoFocus={isEditing}
                      placeholder="kullanıcı adı veya link"
                      aria-label={`Kanal ${index + 1}`}
                    />
                  )}
                  <button
                    className="channel-remove-btn"
                    type="button"
                    onClick={() => removeChannel(index)}
                    disabled={channels.length <= 2}
                    title={channels.length <= 2 ? 'En az 2 kanal gerekli' : 'Kanalı sil'}
                    aria-label={`Kanal ${index + 1} sil`}
                  >
                    <span className="icon">close</span>
                  </button>
                </div>
              )
            })}
            <button className="add-channel-btn" type="button" onClick={addChannel} id="add-channel-btn">
              <span className="icon">add</span>
              Kanal Ekle
            </button>
          </div>
        </section>
      </aside>

      {/* ===== 3. Center Feed (Grouped News or Archive) ===== */}
      <main className="center-feed" id="center-feed">
        {currentView === 'archive' ? (
          <>
            <div className="feed-header">
              <h2>
                Arşiv
                {archiveRuns.length > 0 && <span className="feed-header-count">({archiveRuns.length})</span>}
              </h2>
              <button
                className="fetch-btn"
                type="button"
                onClick={refreshArchiveList}
                disabled={archiveLoading}
                id="archive-refresh-btn"
              >
                {archiveLoading ? (
                  <>
                    <span className="spinner" />
                    Yükleniyor...
                  </>
                ) : (
                  <>
                    <span className="icon">refresh</span>
                    Yenile
                  </>
                )}
              </button>
            </div>

            <div className="feed-content">
              {archiveError && (
                <div className="error-banner" role="alert">
                  <span className="icon">error</span>
                  <span>{archiveError}</span>
                </div>
              )}

              {!archiveLoading && archiveRuns.length === 0 && !archiveError ? (
                <div className="feed-empty">
                  <span className="icon">inventory_2</span>
                  <h3>Arşiv boş</h3>
                  <p>Henüz kayıtlı analiz yok. Dashboard'dan tweet çekince otomatik olarak buraya kaydedilir.</p>
                </div>
              ) : (
                archiveRuns.map((run) => {
                  const isOpening = archiveOpeningId === run.run_id
                  const isDeleting = archiveDeletingId === run.run_id
                  return (
                    <article className="archive-card" key={run.run_id} id={`archive-card-${run.run_id}`}>
                      <div className="archive-card-header">
                        <div className="archive-card-title">
                          <span className="icon">schedule</span>
                          <span>{formatRunTimestamp(run.created_at)}</span>
                        </div>
                        <div className="archive-card-flags">
                          {run.has_replies ? (
                            <span className="archive-flag flag-on">
                              <span className="icon">forum</span>
                              Yorumlar
                            </span>
                          ) : (
                            <span className="archive-flag flag-off">
                              <span className="icon">forum</span>
                              Yorum yok
                            </span>
                          )}
                          {run.has_sentiment ? (
                            <span className="archive-flag flag-on">
                              <span className="icon">insights</span>
                              Duygu analizli
                            </span>
                          ) : (
                            <span className="archive-flag flag-off">
                              <span className="icon">insights</span>
                              Analiz yapılmamış
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="archive-card-channels">
                        {run.channels.map((ch) => (
                          <span className="source-badge" key={`${run.run_id}-${ch}`}>
                            <span className="source-badge-avatar">{ch.replace('@', '').slice(0, 1).toUpperCase()}</span>
                            @{ch}
                          </span>
                        ))}
                      </div>

                      <div className="archive-card-stats">
                        <span className="group-stat">
                          <span className="icon">group_work</span>
                          {run.total_groups} grup
                        </span>
                        <span className="group-stat">
                          <span className="icon">forum</span>
                          {run.total_replies} yorum
                        </span>
                        <span className="archive-card-id">ID: {run.run_id}</span>
                      </div>

                      <div className="archive-card-actions">
                        <button
                          className="fetch-btn"
                          type="button"
                          onClick={() => openArchiveRun(run.run_id)}
                          disabled={isOpening}
                        >
                          {isOpening ? (
                            <>
                              <span className="spinner" />
                              Açılıyor...
                            </>
                          ) : (
                            <>
                              <span className="icon">open_in_new</span>
                              Aç
                            </>
                          )}
                        </button>
                        <button
                          className="archive-delete-btn"
                          type="button"
                          onClick={() => removeArchiveRun(run.run_id)}
                          disabled={isDeleting}
                          title="Bu kaydı sil"
                        >
                          {isDeleting ? <span className="spinner" /> : <span className="icon">delete</span>}
                        </button>
                      </div>
                    </article>
                  )
                })
              )}
            </div>
          </>
        ) : (
          <>
        <div className="feed-header">
          <h2>
            Gruplanmış Haberler
            {shownGroups.length > 0 && <span className="feed-header-count">({shownGroups.length})</span>}
          </h2>
          <button
            className={`fetch-btn${isMatching ? ' fetch-btn-loading' : ''}`}
            type="button"
            onClick={handleFetchMatches}
            disabled={isMatching}
            id="fetch-tweets-btn"
          >
            {isMatching ? (
              <>
                <span className="spinner" />
                Çekiliyor...
              </>
            ) : (
              <>
                <span className="icon">download</span>
                Tweetleri Çek
              </>
            )}
          </button>
        </div>

        <div className="feed-content">
          {error && (
            <div className="error-banner" role="alert" id="error-banner">
              <span className="icon">error</span>
              <span>{error}</span>
            </div>
          )}

          {isRepliesReady && (repliesResult?.total_replies ?? 0) === 0 && (
            <div className="info-notice" id="no-replies-notice">
              <span className="icon">info</span>
              <span>Yorum bulunamadı. Tweetlerde yorumlar kapalı olabilir veya auth bilgileri eksik/geçersiz olabilir.</span>
            </div>
          )}

          {shownGroups.length === 0 ? (
            <div className="feed-empty" id="feed-empty">
              <span className="icon">newspaper</span>
              <h3>Henüz eşleşme yok</h3>
              <p>Kanalları ayarlayın ve "Tweetleri Çek" butonuna tıklayarak haber gruplarını oluşturun.</p>
            </div>
          ) : (
            shownGroups.map((group, groupIndex) => {
              const isActive = groupIndex === selectedGroupIndexSafe
              return (
                <div key={group.topic}>
                  <article
                    className={`news-group-card${isActive ? ' active' : ''}`}
                    role="button"
                    tabIndex={0}
                    onClick={() => setSelectedGroupIndex(groupIndex)}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setSelectedGroupIndex(groupIndex) }}
                    id={`group-card-${groupIndex}`}
                  >
                    <div className="group-card-header">
                      <span className="group-number">{groupIndex + 1}</span>
                      <span className="group-headline">{group.topic}</span>
                    </div>

                    <div className="group-meta">
                      <div className="group-source-badges">
                        {group.channels.map((ch) => (
                          <span className="source-badge" key={ch}>
                            <span className="source-badge-avatar">{ch.replace('@', '').slice(0, 1).toUpperCase()}</span>
                            @{ch}
                          </span>
                        ))}
                      </div>
                      <div className="group-stats">
                        <span className="group-stat">
                          <span className="icon">forum</span>
                          {group.total_reply_count} yorum
                        </span>
                        <span className="group-stat">
                          <span className="icon">people</span>
                          {group.channel_count} kanal
                        </span>
                      </div>
                    </div>
                  </article>

                  {/* Split View — expanded when active */}
                  {isActive && (
                    <div className={`split-view${group.tweets.length === 1 ? ' split-view-single' : ''}`} id="split-view">
                      {group.tweets.map((tweet, idx) => (
                        <article className="split-tweet" key={`${group.topic}-${idx}`}>
                          <div className="tweet-author">
                            <div className="tweet-author-avatar">
                              {renderTweetLabel(tweet, idx).replace('@', '').slice(0, 1).toUpperCase()}
                            </div>
                            <div className="tweet-author-info">
                              <span className="tweet-author-name">{renderTweetLabel(tweet, idx)}</span>
                              <span className="tweet-author-handle">
                                {tweet.channel ? `@${tweet.channel}` : ''}
                              </span>
                            </div>
                            <span className="tweet-author-time">{tweet.date_formatted || '-'}</span>
                          </div>
                          <p className="tweet-text">{tweet.text ?? '-'}</p>
                          <div className="tweet-engagement">
                            <span className="tweet-metric">
                              <span className="icon">favorite</span>
                              <strong>{formatMetricValue(tweet.likes)}</strong>
                            </span>
                            <span className="tweet-metric">
                              <span className="icon">chat_bubble_outline</span>
                              <strong>{formatMetricValue(tweet.replies)}</strong>
                            </span>
                            <span className="tweet-metric">
                              <span className="icon">repeat</span>
                              <strong>{formatMetricValue(tweet.retweets)}</strong>
                            </span>
                          </div>
                          {tweet.url && (
                            <a className="tweet-link-external" href={tweet.url} target="_blank" rel="noreferrer">
                              <span className="icon">open_in_new</span>
                              X'te aç
                            </a>
                          )}

                          {(() => {
                            const channelKey = String(tweet.channel ?? '')
                            const repliesForChannel = group.replies_by_channel?.[channelKey] ?? []
                            const repliesKey = buildReplyKey(group.topic, idx)
                            const isOpen = expandedReplies[repliesKey]
                            const replyCount = repliesForChannel.length

                            return (
                              <div className="tweet-replies" id={`tweet-replies-${groupIndex}-${idx}`}>
                                <button
                                  className="tweet-replies-toggle"
                                  type="button"
                                  onClick={() => toggleReplies(group.topic, idx)}
                                  disabled={replyCount === 0}
                                >
                                  <span className="icon">forum</span>
                                  {replyCount === 0 ? 'Yorum yok' : isOpen ? `Yorumlari gizle (${replyCount})` : `Yorumlari goster (${replyCount})`}
                                  <span className={`icon reply-caret${isOpen ? ' open' : ''}`}>expand_more</span>
                                </button>

                                {isOpen && replyCount > 0 && (
                                  <div className="tweet-replies-list">
                                    {repliesForChannel.map((reply, replyIndex) => (
                                      <article className="reply-card" key={`${group.topic}-${idx}-${replyIndex}`}>
                                        <div className="reply-header">
                                          <div className="reply-avatar">{(reply.user || reply.name || '?').slice(0, 1).toUpperCase()}</div>
                                          <div className="reply-user">
                                            <span className="reply-name">{reply.name || 'Kullanici'}</span>
                                            <span className="reply-handle">@{reply.user || '-'}</span>
                                          </div>
                                          <span className="reply-time">{formatDateLabel(reply.date)}</span>
                                        </div>
                                        <p className="reply-text">{reply.text || '-'}</p>
                                        <div className="reply-metrics">
                                          <span className="reply-metric">
                                            <span className="icon">favorite</span>
                                            {formatMetricValue(reply.likes)}
                                          </span>
                                          <span className="reply-metric">
                                            <span className="icon">chat_bubble_outline</span>
                                            {formatMetricValue(reply.replies)}
                                          </span>
                                          <span className="reply-metric">
                                            <span className="icon">repeat</span>
                                            {formatMetricValue(reply.retweets)}
                                          </span>
                                        </div>
                                      </article>
                                    ))}
                                  </div>
                                )}
                              </div>
                            )
                          })()}
                        </article>
                      ))}
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
          </>
        )}
      </main>

      {/* ===== 4. Right Panel (Dynamic Analysis) ===== */}
      <aside className="right-panel" id="right-panel">
        <div className="right-panel-header">
          <h2>Analiz Paneli</h2>
        </div>

        {!selectedGroup ? (
          /* No group selected */
          <div className="analysis-empty" id="analysis-empty">
            <span className="icon">analytics</span>
            <h3>Grup Seçin</h3>
            <p>Analiz sonuçlarını görmek için sol panelden bir haber grubu seçin.</p>
          </div>
        ) : (
          <>
            {/* Summary of selected group */}
            <section className="analysis-summary" id="analysis-summary">
              <h3 className="summary-title">{selectedGroup.topic}</h3>
              <div className="summary-channels">
                {selectedGroup.channels.map((ch) => (
                  <span className="source-badge" key={ch}>
                    <span className="source-badge-avatar">{ch.replace('@', '').slice(0, 1).toUpperCase()}</span>
                    @{ch}
                  </span>
                ))}
              </div>
              <div className="summary-stat-row">
                <div className="summary-stat-card">
                  <span className="stat-value">{selectedGroup.channel_count}</span>
                  <span className="stat-label">Kanal</span>
                </div>
                <div className="summary-stat-card">
                  <span className="stat-value">{selectedGroup.total_reply_count}</span>
                  <span className="stat-label">Yorum</span>
                </div>
              </div>
            </section>

            {/* State 1: Locked Sentiment — Before comments pulled */}
            {!isRepliesReady && !compareResult && (
              <section className="sentiment-locked" id="sentiment-locked">
                <div className="locked-overlay">
                  <div className="locked-header">
                    <span className="icon">lock</span>
                    <h3>Duygu Analizi</h3>
                  </div>
                  <div className="locked-placeholder">
                    <div className="locked-bar" />
                    <div className="locked-bar" />
                    <div className="locked-bar" />
                  </div>
                  <div className="locked-chart-placeholder" />
                </div>
              </section>
            )}

            {/* Pull Comments Button */}
            <section className="pull-comments-section" id="pull-comments-section">
              <button
                className={`pull-comments-btn${isFetchingReplies ? ' pull-comments-btn-loading' : ''}`}
                type="button"
                onClick={handleFetchReplies}
                disabled={isFetchingReplies || isMatching || !matchResult?.matched_groups?.length}
                id="pull-comments-btn"
              >
                {isFetchingReplies ? (
                  <>
                    <span className="spinner" />
                    Yorumlar Çekiliyor...
                  </>
                ) : (
                  <>
                    <span className="icon">cloud_download</span>
                    Analiz İçin Yorumları Çek
                  </>
                )}
              </button>
            </section>

            {/* State 2: Sentiment Dashboard — After comments loaded */}
            {isRepliesReady && (
              <>
                {/* Compare button */}
                <section className="compare-section" id="compare-section">
                  <button
                    className="compare-btn"
                    type="button"
                    onClick={handleCompareSentiment}
                    disabled={isComparingSentiment || !repliesResult?.matched_groups?.length}
                    id="compare-sentiment-btn"
                  >
                    {isComparingSentiment ? (
                      <>
                        <span className="spinner" />
                        Karşılaştırılıyor...
                      </>
                    ) : (
                      <>
                        <span className="icon">compare_arrows</span>
                        Duygu Karşılaştır
                      </>
                    )}
                  </button>
                </section>

                {compareResult && selectedCompareGroup && algorithmTotals && (
                  <section className="sentiment-dashboard" id="sentiment-dashboard">
                    <div className="sentiment-header">
                      <span className="icon">insights</span>
                      <h3>Duygu Analizi Sonuçları</h3>
                    </div>

                    <div className="sentiment-grid">
                      {ALGORITHM_ORDER.map((algo) => {
                        const totals = algorithmTotals[algo.key]
                        const words = wordCloudByAlgorithm?.[algo.key] ?? []
                        const engineLabel = totals?.engine ?? algo.fallbackEngine
                        if (!totals || totals.total === 0) {
                          return (
                            <div className="sentiment-panel" key={`sentiment-${algo.key}`}>
                              <div className="sentiment-panel-header">
                                <div className="sentiment-panel-title">
                                  <span className="icon">psychology</span>
                                  <h4>{algo.title}</h4>
                                </div>
                                <span className="sentiment-engine">{engineLabel}</span>
                              </div>
                              <div className="sentiment-empty">Bu algoritma icin sonuc bulunamadi.</div>
                            </div>
                          )
                        }

                        return (
                          <div className="sentiment-panel" key={`sentiment-${algo.key}`}>
                            <div className="sentiment-panel-header">
                              <div className="sentiment-panel-title">
                                <span className="icon">psychology</span>
                                <h4>{algo.title}</h4>
                              </div>
                              <span className="sentiment-engine">{engineLabel}</span>
                            </div>

                            <DoughnutChart positive={totals.positive} negative={totals.negative} neutral={totals.neutral} />

                            <div className="sentiment-bars">
                              <div className="sentiment-bar-row">
                                <div className="sentiment-bar-label">
                                  <span>Pozitif</span>
                                  <span>{totals.positive} ({totals.total > 0 ? Math.round((totals.positive / totals.total) * 100) : 0}%)</span>
                                </div>
                                <div className="sentiment-bar-track">
                                  <div className="sentiment-bar-fill" style={{ width: `${totals.total > 0 ? (totals.positive / totals.total) * 100 : 0}%`, background: 'var(--positive)' }} />
                                </div>
                              </div>
                              <div className="sentiment-bar-row">
                                <div className="sentiment-bar-label">
                                  <span>Negatif</span>
                                  <span>{totals.negative} ({totals.total > 0 ? Math.round((totals.negative / totals.total) * 100) : 0}%)</span>
                                </div>
                                <div className="sentiment-bar-track">
                                  <div className="sentiment-bar-fill" style={{ width: `${totals.total > 0 ? (totals.negative / totals.total) * 100 : 0}%`, background: 'var(--negative)' }} />
                                </div>
                              </div>
                              <div className="sentiment-bar-row">
                                <div className="sentiment-bar-label">
                                  <span>Nötr</span>
                                  <span>{totals.neutral} ({totals.total > 0 ? Math.round((totals.neutral / totals.total) * 100) : 0}%)</span>
                                </div>
                                <div className="sentiment-bar-track">
                                  <div className="sentiment-bar-fill" style={{ width: `${totals.total > 0 ? (totals.neutral / totals.total) * 100 : 0}%`, background: 'var(--neutral)' }} />
                                </div>
                              </div>
                            </div>

                            <WordCloud words={words} />
                          </div>
                        )
                      })}
                    </div>

                    {/* Channel Comparison */}
                    <div className="channel-comparison" id="channel-comparison">
                      <div className="comparison-title">
                        <span className="icon">compare</span>
                        Kanal Karşılaştırma
                      </div>
                      <div className="comparison-cards">
                        {Object.entries(selectedCompareGroup.channel_results).map(([channel, result]) => (
                          <div className="comparison-card" key={`${selectedCompareGroup.topic}-${channel}`}>
                            <div className="comparison-card-header">
                              <span className="comparison-channel-name">
                                <span className="icon">person</span>
                                @{channel}
                              </span>
                              <span className="comparison-best-algo">🏆 {result.best_algorithm}</span>
                            </div>
                            <div className="comparison-algo-row">
                              {Object.entries(result.algorithms).map(([name, algo]) => (
                                <span className="algo-chip" key={`${channel}-${name}`}>
                                  <span className="algo-chip-name">{name}</span>
                                  <span className="algo-chip-dominant">{algo.summary.dominant}</span>
                                  <span className="algo-chip-total">({algo.summary.total})</span>
                                </span>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Save notice */}
                    {compareResult.saved_file && (
                      <div className="save-notice" id="save-notice">
                        <span className="icon">check_circle</span>
                        JSON kaydı: {compareResult.saved_file}
                      </div>
                    )}
                  </section>
                )}
              </>
            )}
          </>
        )}
      </aside>
    </div>
  )
}
