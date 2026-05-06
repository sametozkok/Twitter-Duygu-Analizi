import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { deleteRun, getRun, listRuns, runMatch, runReplies, runSentimentCompare } from './lib/api'
import { SegmentedControl } from './components/SegmentedControl'
import { ChannelAvatar } from './components/ChannelAvatar'
import { EmptyState } from './components/EmptyState'
import { Metric } from './components/Metric'
import { Skeleton, SkeletonText } from './components/Skeleton'
import { OnboardingCard } from './features/dashboard/OnboardingCard'
import { AppearanceSettings } from './features/settings/AppearanceSettings'
import { SentimentDashboard } from './features/analysis/SentimentDashboard'
import i18n, { getIntlLocaleTag } from './i18n'
import type { SupportedLocale } from './i18n'
import { useTheme } from './theme/ThemeProvider'
import { AvatarGroup } from './components/ui/avatar-group'
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
  const locale = getIntlLocaleTag((i18n.language as any) || 'tr')
  return new Intl.NumberFormat(locale, { notation: 'compact', maximumFractionDigits: 1 }).format(numeric)
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
  const locale = getIntlLocaleTag((i18n.language as any) || 'tr')
  // Date already resolves UTC strings into local time; avoid double-shifting.
  return new Intl.DateTimeFormat(locale, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(parsed))
}

function formatRunTimestamp(value?: string) {
  if (!value) return '-'
  const parsed = Date.parse(value)
  if (Number.isNaN(parsed)) return value
  const locale = getIntlLocaleTag((i18n.language as any) || 'tr')
  return new Intl.DateTimeFormat(locale, {
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

function buildLetterAvatarDataUrl(letter: string, seed: string) {
  const safeLetter = (letter || '?').slice(0, 1).toUpperCase()
  const colors = [
    ['#1d9bf0', '#1a73c7'],
    ['#00ba7c', '#028a5d'],
    ['#ffad5c', '#f97316'],
    ['#d291ff', '#7c3aed'],
    ['#79e2f2', '#06b6d4'],
    ['#ff6b9d', '#db2777'],
  ]
  let hash = 0
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) >>> 0
  const [c1, c2] = colors[hash % colors.length]

  const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="${c1}"/>
      <stop offset="1" stop-color="${c2}"/>
    </linearGradient>
  </defs>
  <circle cx="50" cy="50" r="50" fill="url(#g)"/>
  <text x="50" y="56" text-anchor="middle" font-family="Inter, system-ui, -apple-system, Segoe UI, sans-serif"
        font-size="44" font-weight="900" fill="#ffffff">${safeLetter}</text>
</svg>`

  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
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
  const { t } = useTranslation('analysis')
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

  const dominantLabel =
    pPct >= negPct && pPct >= neuPct
      ? t('sentiments.positive')
      : negPct >= pPct && negPct >= neuPct
        ? t('sentiments.negative')
        : t('sentiments.neutral')
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
          <strong>{Math.round(pPct)}%</strong> {t('sentiments.positive')}
        </div>
        <div className="legend-item">
          <span className="legend-dot" style={{ background: 'var(--negative)' }} />
          <strong>{Math.round(negPct)}%</strong> {t('sentiments.negative')}
        </div>
        <div className="legend-item">
          <span className="legend-dot" style={{ background: 'var(--neutral)' }} />
          <strong>{Math.round(neuPct)}%</strong> {t('sentiments.neutral')}
        </div>
      </div>
    </div>
  )
}

/* ========== Word Cloud Component ========== */

function WordCloud({ words }: { words: { text: string; weight: number }[] }) {
  const { t } = useTranslation('analysis')
  if (!words.length) return null

  const maxWeight = Math.max(...words.map((w) => w.weight))
  const colors = ['var(--accent)', 'var(--positive)', 'var(--neutral)', '#d291ff', '#ff6b9d', '#79e2f2', '#ffad5c']

  return (
    <div className="word-cloud-section">
      <div className="word-cloud-title">
        <span className="icon">cloud</span>
        {t('wordCloud')}
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

function ArchiveListSkeleton() {
  return (
    <div className="feed-content" aria-label={i18n.t('common:loading')}>
      {Array.from({ length: 6 }).map((_, i) => (
        <article className="archive-card" key={`archive-skel-${i}`}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
            <div style={{ display: 'grid', gap: 10, minWidth: 220, flex: 1 }}>
              <Skeleton height={14} radius={999} style={{ width: '44%' }} />
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <Skeleton height={22} radius={999} style={{ width: 92 }} />
                <Skeleton height={22} radius={999} style={{ width: 84 }} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <Skeleton height={22} radius={999} style={{ width: 96 }} />
              <Skeleton height={22} radius={999} style={{ width: 84 }} />
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <Skeleton height={26} radius={999} style={{ width: 120 }} />
            <Skeleton height={26} radius={999} style={{ width: 110 }} />
            <Skeleton height={26} radius={999} style={{ width: 130 }} />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <Skeleton height={14} radius={999} style={{ width: 110 }} />
              <Skeleton height={14} radius={999} style={{ width: 110 }} />
              <Skeleton height={14} radius={999} style={{ width: 180 }} />
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <Skeleton height={36} radius={12} style={{ width: 120 }} />
              <Skeleton height={36} radius={12} style={{ width: 44 }} />
            </div>
          </div>
        </article>
      ))}
    </div>
  )
}

function AnalyticsSkeleton() {
  return (
    <div className="feed-content" aria-label={i18n.t('common:loading')}>
      <div className="analytics-overview">
        <div className="summary-stat-row" style={{ marginBottom: '20px' }}>
          {Array.from({ length: 3 }).map((_, i) => (
            <div className="summary-stat-card" key={`summary-skel-${i}`}>
              <Skeleton height={22} radius={12} style={{ width: 64 }} />
              <Skeleton height={12} radius={999} style={{ width: 120, marginTop: 10 }} />
            </div>
          ))}
        </div>
        <Skeleton height={16} radius={999} style={{ width: 140, marginBottom: 12 }} />
        <div className="archive-card-channels" style={{ marginBottom: '20px' }}>
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={`ch-skel-${i}`} height={26} radius={999} style={{ width: 120 }} />
          ))}
        </div>
        <Skeleton height={16} radius={999} style={{ width: 160, marginBottom: 12 }} />
        <div className="analytics-table">
          <div className="analytics-table-header">
            <div>Tarih</div>
            <div>Kanallar</div>
            <div>Grup</div>
            <div>Yorum</div>
            <div>Durum</div>
          </div>
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={`row-skel-${i}`} className="analytics-table-row" style={{ cursor: 'default' }}>
              <Skeleton height={12} radius={999} style={{ width: 120 }} />
              <Skeleton height={12} radius={999} />
              <Skeleton height={12} radius={999} style={{ width: 44 }} />
              <Skeleton height={12} radius={999} style={{ width: 52 }} />
              <Skeleton height={22} radius={999} style={{ width: 120, justifySelf: 'end' }} />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function AlertsSkeleton() {
  return (
    <div className="feed-content" aria-label={i18n.t('common:loading')}>
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={`alert-skel-${i}`}
          className="alert-card"
          style={{
            padding: '15px',
            background: 'var(--bg-secondary)',
            borderRadius: '8px',
            marginBottom: '10px',
            borderLeft: '4px solid var(--accent)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
            <Skeleton height={16} radius={999} style={{ width: 180 }} />
          </div>
          <SkeletonText lines={2} />
        </div>
      ))}
    </div>
  )
}

function DashboardGroupsSkeleton() {
  return (
    <div className="feed-content" aria-label={i18n.t('common:loading')}>
      {Array.from({ length: 7 }).map((_, i) => (
        <article className="news-group-card" key={`group-skel-${i}`}>
          <div className="group-card-header">
            <Skeleton height={18} radius={999} style={{ width: 26 }} />
            <Skeleton height={16} radius={999} style={{ width: '72%' }} />
          </div>
          <div className="group-meta" style={{ marginTop: 12 }}>
            <div className="group-source-badges">
              <Skeleton height={26} radius={999} style={{ width: 110 }} />
              <Skeleton height={26} radius={999} style={{ width: 120 }} />
              <Skeleton height={26} radius={999} style={{ width: 98 }} />
            </div>
            <div className="group-stats">
              <Skeleton height={14} radius={999} style={{ width: 96 }} />
              <Skeleton height={14} radius={999} style={{ width: 84 }} />
            </div>
          </div>
        </article>
      ))}
    </div>
  )
}

function RightPanelSkeleton({ title }: { title: string }) {
  return (
    <div style={{ padding: '0 16px 16px' }} aria-label={`${title} ${i18n.t('common:loading')}`}>
      <section className="analysis-summary">
        <Skeleton height={18} radius={999} style={{ width: '80%', marginBottom: 12 }} />
        <div className="summary-channels" style={{ marginBottom: 14 }}>
          <Skeleton height={26} radius={999} style={{ width: 110 }} />
          <Skeleton height={26} radius={999} style={{ width: 120 }} />
          <Skeleton height={26} radius={999} style={{ width: 98 }} />
        </div>
        <div className="summary-stat-row">
          <div className="summary-stat-card">
            <Skeleton height={24} radius={12} style={{ width: 52 }} />
            <Skeleton height={12} radius={999} style={{ width: 90, marginTop: 10 }} />
          </div>
          <div className="summary-stat-card">
            <Skeleton height={24} radius={12} style={{ width: 52 }} />
            <Skeleton height={12} radius={999} style={{ width: 90, marginTop: 10 }} />
          </div>
        </div>
      </section>

      <section className="sentiment-dashboard" style={{ marginTop: 14 }}>
        <div className="sentiment-header">
          <Skeleton height={14} radius={999} style={{ width: 180 }} />
        </div>
        <div className="sentiment-grid" style={{ marginTop: 12 }}>
          {Array.from({ length: 2 }).map((_, i) => (
            <div className="sentiment-panel" key={`sentiment-panel-skel-${i}`}>
              <div className="sentiment-panel-header" style={{ marginBottom: 12 }}>
                <Skeleton height={14} radius={999} style={{ width: 120 }} />
                <Skeleton height={12} radius={999} style={{ width: 110 }} />
              </div>
              <Skeleton height={180} radius={16} />
              <div style={{ marginTop: 12 }}>
                <SkeletonText lines={4} />
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

const ALGORITHM_ORDER = [
  { key: 'bert', title: 'BERT', fallbackEngine: 'bert-model' },
  { key: 'api', title: 'Gemini API', fallbackEngine: 'gemini-api' },
]

/* ========== Main App ========== */

export default function App() {
  const { t } = useTranslation(['common', 'dashboard', 'settings', 'analysis'])
  const { mode: themeMode, setMode: setThemeMode } = useTheme()
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
  const [selectedTweetIndex, setSelectedTweetIndex] = useState(0)
  const [selectedAlgorithmKey, setSelectedAlgorithmKey] = useState<string>(ALGORITHM_ORDER[0]?.key ?? 'bert')
  const [editingChannelIndex, setEditingChannelIndex] = useState<number | null>(null)
  const [expandedReplies, setExpandedReplies] = useState<Record<string, boolean>>({})
  const [commentSortMode, setCommentSortMode] = useState<'newest' | 'top'>('newest')
  const [commentSentimentFilter, setCommentSentimentFilter] = useState<'all' | 'positive' | 'negative' | 'neutral'>('all')

  const [isLeftPanelOpen, setIsLeftPanelOpen] = useState(false)
  const [isRightPanelOpen, setIsRightPanelOpen] = useState(true)
  const [rightPanelWidthPx, setRightPanelWidthPx] = useState<number>(520)

  const [currentView, setCurrentView] = useState<'dashboard' | 'archive' | 'analytics' | 'alerts'>('dashboard')
  const [searchQuery, setSearchQuery] = useState('')
  const [currentRunId, setCurrentRunId] = useState<string | null>(null)
  const [archiveRuns, setArchiveRuns] = useState<RunSummary[]>([])
  const [archiveLoading, setArchiveLoading] = useState(false)
  const [archiveError, setArchiveError] = useState<string | null>(null)
  const [archiveOpeningId, setArchiveOpeningId] = useState<string | null>(null)
  const [archiveDeletingId, setArchiveDeletingId] = useState<string | null>(null)
  const [onboardingDismissed, setOnboardingDismissed] = useState<boolean>(() => {
    try {
      return window.localStorage.getItem('onboardingDismissed') === 'true'
    } catch {
      return false
    }
  })

  const activeChannels = useMemo(
    () => channels.map((item) => item.trim()).filter((item) => item.length > 0),
    [channels],
  )

  const rawGroups = repliesResult?.matched_groups ?? matchResult?.matched_groups ?? []
  const shownGroups = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    if (!q) return rawGroups
    return rawGroups.filter((g) => {
      const inTopic = g.topic?.toLowerCase().includes(q)
      const inChannels = (g.channels ?? []).some((c: string) => c.toLowerCase().includes(q))
      const inTweets = (g.tweets ?? []).some((t: { text?: string; channel?: string }) => {
        const textHit = (t.text ?? '').toLowerCase().includes(q)
        const chHit = (t.channel ?? '').toLowerCase().includes(q)
        return textHit || chHit
      })
      return Boolean(inTopic || inChannels || inTweets)
    })
  }, [rawGroups, searchQuery])
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

  const sentimentByText = useMemo(() => {
    if (!selectedCompareGroup || !selectedAlgorithmKey) return null
    const map = new Map<string, { label?: string; score?: number }>()
    Object.values(selectedCompareGroup.channel_results).forEach((cr) => {
      const algo = cr.algorithms?.[selectedAlgorithmKey]
      if (!algo?.items) return
      algo.items.forEach((item) => {
        const text = (item.text ?? '').trim()
        if (!text) return
        const key = text.toLowerCase()
        if (!map.has(key)) {
          map.set(key, { label: item.label, score: item.score })
        }
      })
    })
    return map
  }, [selectedAlgorithmKey, selectedCompareGroup])

  /* --- Handlers --- */
  function closeLeftPanel() {
    setIsLeftPanelOpen(false)
    setEditingChannelIndex(null)
  }

  function toggleLeftPanel() {
    setIsLeftPanelOpen((prev) => !prev)
    setEditingChannelIndex(null)
  }

  function toggleRightPanel() {
    setIsRightPanelOpen((prev) => !prev)
  }

  function clampRightPanelWidth(nextWidth: number) {
    const sidebarWidth = 72
    const minRight = 320
    const minCenter = 360
    const available = Math.max(0, window.innerWidth - sidebarWidth)
    const maxRight = Math.max(minRight, available - minCenter)
    return Math.min(Math.max(nextWidth, minRight), maxRight)
  }

  function startResizeRightPanel(ev: React.PointerEvent<HTMLDivElement>) {
    if (!isRightPanelOpen) return
    ev.preventDefault()

    const onMove = (e: PointerEvent) => {
      const next = clampRightPanelWidth(window.innerWidth - e.clientX)
      setRightPanelWidthPx(next)
    }

    const onUp = () => {
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerup', onUp)
      document.body.classList.remove('is-resizing')
    }

    window.addEventListener('pointermove', onMove)
    window.addEventListener('pointerup', onUp, { once: true })
    document.body.classList.add('is-resizing')
  }

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
    closeLeftPanel()
    if (activeChannels.length < 2) {
      setError(t('dashboard:errors.needMinChannels'))
      return
    }
    setIsMatching(true)
    setRepliesResult(null)
    setCompareResult(null)
    setCurrentRunId(null)
    try {
      const response = await runMatch({
        channels: activeChannels,
        tweets_per_channel: Number(tweetsPerChannel) || 10,
        min_channels_for_match: Number(minChannelsForMatch) || 2,
        twitter_bearer_token: twitterBearerToken.trim(),
      })
      setMatchResult(response)
      setCurrentRunId(response.run_id ?? null)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : t('dashboard:errors.matchUnexpected'))
    } finally {
      setIsMatching(false)
    }
  }

  async function handleFetchReplies() {
    setError(null)
    closeLeftPanel()
    if (!matchResult?.matched_groups?.length) {
      setError(t('dashboard:errors.repliesNeedMatchFirst'))
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
      setError(requestError instanceof Error ? requestError.message : t('dashboard:errors.repliesUnexpected'))
    } finally {
      setIsFetchingReplies(false)
    }
  }

  async function handleCompareSentiment() {
    setError(null)
    closeLeftPanel()
    if (!repliesResult?.matched_groups?.length) {
      setError(t('dashboard:errors.sentimentNeedRepliesFirst'))
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
      setError(requestError instanceof Error ? requestError.message : t('dashboard:errors.sentimentUnexpected'))
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
      setArchiveError(e instanceof Error ? e.message : t('dashboard:errors.archiveListFailed'))
    } finally {
      setArchiveLoading(false)
    }
  }

  function showDashboardView() {
    setCurrentView('dashboard')
    closeLeftPanel()
  }

  async function showArchiveView() {
    setCurrentView('archive')
    closeLeftPanel()
    await refreshArchiveList()
  }

  async function showAnalyticsView() {
    setCurrentView('analytics')
    closeLeftPanel()
    await refreshArchiveList()
  }

  async function showAlertsView() {
    setCurrentView('alerts')
    closeLeftPanel()
    await refreshArchiveList()
  }

  async function openArchiveRun(runId: string) {
    setArchiveOpeningId(runId)
    setArchiveError(null)
    closeLeftPanel()
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
      setArchiveError(e instanceof Error ? e.message : t('dashboard:errors.archiveRunLoadFailed'))
    } finally {
      setArchiveOpeningId(null)
    }
  }

  async function removeArchiveRun(runId: string) {
    if (!window.confirm(t('common:confirm.deleteRun'))) return
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
      setArchiveError(e instanceof Error ? e.message : t('dashboard:errors.archiveRunDeleteFailed'))
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

  useEffect(() => {
    const saved = window.localStorage.getItem('rightPanelWidthPx')
    const parsed = saved ? Number(saved) : NaN
    if (Number.isFinite(parsed) && parsed > 0) {
      setRightPanelWidthPx(clampRightPanelWidth(parsed))
      return
    }
    // Default to half of available space (best first impression)
    const sidebarWidth = 72
    const available = Math.max(0, window.innerWidth - sidebarWidth)
    setRightPanelWidthPx(clampRightPanelWidth(Math.round(available / 2)))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    window.localStorage.setItem('rightPanelWidthPx', String(rightPanelWidthPx))
  }, [rightPanelWidthPx])

  function dismissOnboarding() {
    setOnboardingDismissed(true)
    try {
      window.localStorage.setItem('onboardingDismissed', 'true')
    } catch {
      // ignore
    }
  }

  function openChannelSettings() {
    setIsLeftPanelOpen(true)
    window.setTimeout(() => {
      const el = document.getElementById('channel-management')
      el?.scrollIntoView({ block: 'start', behavior: 'smooth' })
    }, 50)
  }

  useEffect(() => {
    setSelectedTweetIndex(0)
  }, [selectedGroup?.topic])

  /* ========== RENDER ========== */

  return (
    <div
      className={[
        'app-shell',
        isLeftPanelOpen ? '' : 'left-panel-collapsed',
        isRightPanelOpen ? '' : 'right-panel-collapsed',
      ]
        .filter(Boolean)
        .join(' ')}
      style={
        {
          // allow drag-resizing by overriding the CSS variable
          ['--right-panel-width' as any]: `${rightPanelWidthPx}px`,
        } as React.CSSProperties
      }
    >
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
          title={t('dashboard:nav.archive')}
          id="nav-archive"
          type="button"
          onClick={showArchiveView}
        >
          <span className="icon">history</span>
        </button>
        <button
          className={`nav-item${currentView === 'analytics' ? ' active' : ''}`}
          title="Raporlar"
          id="nav-reports"
          type="button"
          onClick={showAnalyticsView}
        >
          <span className="icon">assessment</span>
        </button>
        <button
          className={`nav-item${currentView === 'alerts' ? ' active' : ''}`}
          title="Bildirimler"
          id="nav-notifications"
          type="button"
          onClick={showAlertsView}
        >
          <span className="icon">notifications</span>
        </button>

        <div className="nav-spacer" />

        <button
          className={`nav-item${isLeftPanelOpen ? ' active' : ''}`}
          title={isLeftPanelOpen ? t('dashboard:nav.settingsClose') : t('dashboard:nav.settings')}
          id="nav-settings"
          type="button"
          onClick={toggleLeftPanel}
          aria-expanded={isLeftPanelOpen}
          aria-controls="left-panel"
        >
          <span className="icon">settings</span>
        </button>
      </nav>

      {/* Backdrop for closing left panel */}
      {isLeftPanelOpen && (
        <button
          type="button"
          className="left-panel-backdrop"
          aria-label="Ayarlar panelini kapat"
          onClick={closeLeftPanel}
        />
      )}

      {/* ===== 2. Left Panel (Settings + Channels) ===== */}
      <aside className="left-panel" id="left-panel">
        <div className="left-panel-header">
          <h1>{t('settings:title')}</h1>
          <button
            type="button"
            className="left-panel-close"
            onClick={closeLeftPanel}
            aria-label={t('common:close')}
            title={t('common:close')}
          >
            <span className="icon">close</span>
          </button>
        </div>

        {/* API Settings */}
        <section className="left-panel-section" id="api-settings">
          <div className="section-label">
            <span className="icon">key</span>
            {t('settings:apiSettings')}
          </div>
          <div className="settings-grid">
            <div className="setting-field">
              <label htmlFor="auth-token-input">{t('settings:fields.authToken')}</label>
              <input id="auth-token-input" type="password" value={twitterAuthToken} onChange={(e) => setTwitterAuthToken(e.target.value)} placeholder="auth_token" />
            </div>
            <div className="setting-field">
              <label htmlFor="ct0-input">{t('settings:fields.ct0')}</label>
              <input id="ct0-input" type="password" value={twitterCt0} onChange={(e) => setTwitterCt0(e.target.value)} placeholder="ct0" />
            </div>
            <div className="setting-field">
              <label htmlFor="bearer-input">{t('settings:fields.bearerToken')}</label>
              <input id="bearer-input" type="password" value={twitterBearerToken} onChange={(e) => setTwitterBearerToken(e.target.value)} placeholder="Bearer ..." />
            </div>
          </div>
        </section>

        {/* Numeric Settings */}
        <section className="left-panel-section" id="numeric-settings">
          <div className="section-label">
            <span className="icon">tune</span>
            {t('settings:parameters')}
          </div>
          <div className="numeric-settings">
            <div className="numeric-field">
              <label>{t('settings:fields.tweetsPerChannel')}</label>
              <input type="number" min={1} max={50} value={tweetsPerChannel} onChange={(e) => setTweetsPerChannel(e.target.value === '' ? '' : Number(e.target.value))} />
            </div>
            <div className="numeric-field">
              <label>{t('settings:fields.minCommonThreshold')}</label>
              <input type="number" min={2} max={10} value={minChannelsForMatch} onChange={(e) => setMinChannelsForMatch(e.target.value === '' ? '' : Number(e.target.value))} />
            </div>
            <div className="numeric-field">
              <label>{t('settings:fields.repliesPerTweet')}</label>
              <input type="number" min={1} max={100} value={replyCount} onChange={(e) => setReplyCount(e.target.value === '' ? '' : Number(e.target.value))} />
            </div>
          </div>
        </section>

        {/* Channel Management */}
        <section className="left-panel-section" id="channel-management">
          <div className="section-label">
            <span className="icon">group</span>
            {t('settings:channelManagement')}
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
                      title={t('settings:fields.clickToEdit')}
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
                      placeholder={t('settings:fields.channelPlaceholder')}
                      aria-label={`Kanal ${index + 1}`}
                    />
                  )}
                  <button
                    className="channel-remove-btn"
                    type="button"
                    onClick={() => removeChannel(index)}
                    disabled={channels.length <= 2}
                    title={channels.length <= 2 ? t('settings:fields.minTwoChannels') : t('settings:fields.deleteChannel')}
                    aria-label={`Kanal ${index + 1} sil`}
                  >
                    <span className="icon">close</span>
                  </button>
                </div>
              )
            })}
            <button className="add-channel-btn" type="button" onClick={addChannel} id="add-channel-btn">
              <span className="icon">add</span>
              {t('settings:fields.addChannel')}
            </button>
          </div>
        </section>

        <AppearanceSettings
          t={t}
          themeMode={themeMode}
          setThemeMode={setThemeMode}
          locale={(i18n.language as SupportedLocale) || 'tr'}
        />
      </aside>

      {/* ===== 3. Center Feed (Grouped News or Archive) ===== */}
      <main className="center-feed" id="center-feed">
        {currentView === 'archive' ? (
          <>
            <div className="feed-header">
              <h2>
                {t('dashboard:nav.archive')}
                {archiveRuns.length > 0 && <span className="feed-header-count">({archiveRuns.length})</span>}
              </h2>
              <div className="feed-header-tools">
                <div className="feed-search">
                  <span className="icon">search</span>
                  <input
                    type="text"
                    placeholder={t('dashboard:feed.archiveSearchPlaceholder')}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    aria-label={`${t('common:search')} (${t('dashboard:nav.archive')})`}
                  />
                </div>
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
                    {t('common:loading')}
                  </>
                ) : (
                  <>
                    <span className="icon">refresh</span>
                    {t('common:refresh')}
                  </>
                )}
              </button>
              </div>
            </div>

            {archiveLoading && archiveRuns.length === 0 ? (
              <ArchiveListSkeleton />
            ) : (
              <div className="feed-content">
                {archiveError && (
                  <div className="error-banner" role="alert">
                    <span className="icon">error</span>
                    <span>{archiveError}</span>
                  </div>
                )}

                {!archiveLoading && archiveRuns.length === 0 && !archiveError ? (
                  <div className="feed-empty">
                  <span className="icon icon-lg" aria-hidden="true">
                    inventory_2
                  </span>
                    <h3>{t('dashboard:feed.archiveEmptyTitle')}</h3>
                    <p>{t('dashboard:feed.archiveEmptyBody')}</p>
                  </div>
                ) : (
                  archiveRuns
                    .filter((r) => {
                      const q = searchQuery.trim().toLowerCase()
                      if (!q) return true
                      return (
                        r.run_id.toLowerCase().includes(q) ||
                        r.channels.some((c) => c.toLowerCase().includes(q))
                      )
                    })
                    .map((run) => {
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
                                {t('dashboard:archive.flags.sentimentOn')}
                              </span>
                            ) : (
                              <span className="archive-flag flag-off">
                                <span className="icon">insights</span>
                                {t('dashboard:archive.flags.sentimentOff')}
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="archive-card-channels">
                          {run.channels.map((ch) => (
                            <span className="source-badge" key={`${run.run_id}-${ch}`}>
                              <ChannelAvatar channel={ch} className="source-badge-avatar" size={20} />
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
                                {t('common:opening')}
                              </>
                            ) : (
                              <>
                                <span className="icon">open_in_new</span>
                                {t('dashboard:archive.open')}
                              </>
                            )}
                          </button>
                          <button
                            className="archive-delete-btn"
                            type="button"
                            onClick={() => removeArchiveRun(run.run_id)}
                            disabled={isDeleting}
                            title={t('dashboard:archive.deleteTitle')}
                          >
                            {isDeleting ? <span className="spinner" /> : <span className="icon">delete</span>}
                          </button>
                        </div>
                      </article>
                    )
                  })
                )}
              </div>
            )}
          </>
        ) : currentView === 'analytics' ? (
          <>
            <div className="feed-header">
              <h2>{t('dashboard:reports.title')}</h2>
              <div className="feed-header-tools">
                <div className="feed-search">
                  <span className="icon">search</span>
                  <input
                    type="text"
                    placeholder={t('dashboard:feed.reportsSearchPlaceholder')}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    aria-label={`${t('common:search')} (${t('dashboard:reports.title')})`}
                  />
                </div>
                <button className="fetch-btn" type="button" onClick={refreshArchiveList} disabled={archiveLoading}>
                  {archiveLoading ? <span className="spinner" /> : <span className="icon">refresh</span>}
                  {t('common:refresh')}
                </button>
              </div>
            </div>
            <div className="feed-content">
              {archiveLoading && archiveRuns.length === 0 ? (
                <AnalyticsSkeleton />
              ) : (
                <div className="analytics-overview">
                  <div className="summary-stat-row" style={{ marginBottom: '20px' }}>
                    <div className="summary-stat-card">
                      <span className="stat-value">{archiveRuns.length}</span>
                      <span className="stat-label">{t('dashboard:reports.totalRuns')}</span>
                    </div>
                    <div className="summary-stat-card">
                      <span className="stat-value">{archiveRuns.reduce((acc, r) => acc + r.total_groups, 0)}</span>
                      <span className="stat-label">{t('dashboard:reports.totalGroups')}</span>
                    </div>
                    <div className="summary-stat-card">
                      <span className="stat-value">{archiveRuns.reduce((acc, r) => acc + r.total_replies, 0)}</span>
                      <span className="stat-label">{t('dashboard:reports.totalReplies')}</span>
                    </div>
                  </div>
                  <h3>{t('dashboard:reports.allChannels')}</h3>
                  <div className="archive-card-channels" style={{ marginBottom: '20px' }}>
                    {Array.from(new Set(archiveRuns.flatMap((r) => r.channels))).map((ch) => (
                      <span className="source-badge" key={ch}>
                        <ChannelAvatar channel={ch} className="source-badge-avatar" size={20} />
                        @{ch}
                      </span>
                    ))}
                  </div>
                  <h3 style={{ margin: '0 0 10px' }}>{t('dashboard:reports.history')}</h3>
                  <div className="analytics-table">
                    <div className="analytics-table-header">
                      <div>Tarih</div>
                      <div>Kanallar</div>
                      <div>Grup</div>
                      <div>Yorum</div>
                      <div>Durum</div>
                    </div>
                    {archiveRuns
                      .filter((r) => {
                        const q = searchQuery.trim().toLowerCase()
                        if (!q) return true
                        return (
                          r.run_id.toLowerCase().includes(q) ||
                          r.channels.some((c) => c.toLowerCase().includes(q))
                        )
                      })
                      .map((r) => (
                        <button
                          key={`analytics-row-${r.run_id}`}
                          type="button"
                          className="analytics-table-row"
                          onClick={() => openArchiveRun(r.run_id)}
                          title={t('dashboard:reports.openDetails')}
                        >
                          <div>{formatRunTimestamp(r.created_at)}</div>
                          <div className="mono">{r.channels.join(', ')}</div>
                          <div>{r.total_groups}</div>
                          <div>{r.total_replies}</div>
                          <div className="pill-group">
                            <span className={`pill ${r.has_replies ? 'on' : 'off'}`}>Yorum</span>
                            <span className={`pill ${r.has_sentiment ? 'on' : 'off'}`}>Analiz</span>
                          </div>
                        </button>
                      ))}
                  </div>
                </div>
              )}
            </div>
          </>
        ) : currentView === 'alerts' ? (
          <>
            <div className="feed-header">
              <h2>{t('dashboard:alerts.title')}</h2>
              <div className="feed-header-tools">
                <div className="feed-search">
                  <span className="icon">search</span>
                  <input
                    type="text"
                    placeholder={t('dashboard:feed.alertsSearchPlaceholder')}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    aria-label={`${t('common:search')} (${t('dashboard:alerts.title')})`}
                  />
                </div>
                <button className="fetch-btn" type="button" onClick={refreshArchiveList} disabled={archiveLoading}>
                  {archiveLoading ? <span className="spinner" /> : <span className="icon">refresh</span>}
                  {t('common:refresh')}
                </button>
              </div>
            </div>
            <div className="feed-content">
               {archiveLoading && archiveRuns.length === 0 ? (
                 <AlertsSkeleton />
               ) : archiveRuns.length === 0 ? (
                 <div className="feed-empty">{t('dashboard:alerts.empty')}</div>
               ) : (
                 archiveRuns
                   .filter((r) => {
                     const q = searchQuery.trim().toLowerCase()
                     if (!q) return true
                     return (
                       r.run_id.toLowerCase().includes(q) ||
                       r.channels.some((c) => c.toLowerCase().includes(q))
                     )
                   })
                   .map((run) => (
                   <div key={`alert-${run.run_id}`} className="alert-card" style={{ padding: '15px', background: 'var(--bg-secondary)', borderRadius: '8px', marginBottom: '10px', borderLeft: '4px solid var(--accent)' }}>
                     <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '5px' }}>
                       <span className="icon" style={{ color: 'var(--accent)', fontSize: '1.2rem' }}>notifications</span>
                       <strong style={{ color: 'var(--text-primary)' }}>{formatRunTimestamp(run.created_at)}</strong>
                     </div>
                     <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem', paddingLeft: '34px' }}>
                       {t('dashboard:alerts.message', {
                         channels: run.channels.join(', '),
                         groups: run.total_groups,
                         replies: run.total_replies,
                       })}
                     </p>
                   </div>
                 ))
               )}
            </div>
          </>
        ) : (
          <>
        <div className="feed-header">
          <h2>
            {t('dashboard:feed.groupedNews')}
            {shownGroups.length > 0 && <span className="feed-header-count">({shownGroups.length})</span>}
          </h2>
          <div className="feed-header-tools">
            <div className="feed-search">
              <span className="icon">search</span>
              <input
                type="text"
                placeholder={t('dashboard:feed.newsSearchPlaceholder')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                aria-label={`${t('common:search')} (${t('dashboard:feed.groupedNews')})`}
              />
            </div>
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
                {t('dashboard:feed.fetchingTweets')}
              </>
            ) : (
              <>
                <span className="icon">download</span>
                {t('dashboard:feed.fetchTweets')}
              </>
            )}
          </button>
          </div>
        </div>

        {isMatching ? (
          <DashboardGroupsSkeleton />
        ) : (
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
              <span>{t('dashboard:info.noRepliesFound')}</span>
            </div>
          )}

          {shownGroups.length === 0 ? (
            <>
              <div id="feed-empty">
                {!onboardingDismissed && (
                  <OnboardingCard
                    t={t}
                    onDismiss={dismissOnboarding}
                    onOpenSettings={openChannelSettings}
                    onFetchTweets={handleFetchMatches}
                    isFetching={isMatching}
                  />
                )}
              </div>
              <EmptyState
                icon="newspaper"
                title={t('dashboard:feed.emptyTitle')}
                body={t('dashboard:feed.emptyBody')}
              />
            </>
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
                    (() => {
                      const safeIndex = Math.max(0, Math.min(selectedTweetIndex, group.tweets.length - 1))
                      const tweet = group.tweets[safeIndex]
                      if (!tweet) return null

                      const allReplies = Object.entries(group.replies_by_channel ?? {}).flatMap(([sourceChannel, replies]) =>
                        (replies ?? []).map((r) => ({ ...r, __sourceChannel: sourceChannel })),
                      )
                      const repliesKey = `${group.topic}::all`
                      const isOpen = expandedReplies[repliesKey]
                      const replyCount = allReplies.length
                      const sortedReplies = [...allReplies].sort((a: any, b: any) => {
                        if (commentSortMode === 'top') {
                          return Number(b.likes ?? 0) - Number(a.likes ?? 0)
                        }
                        const da = Date.parse(String(a.date ?? ''))
                        const db = Date.parse(String(b.date ?? ''))
                        if (Number.isFinite(db) && Number.isFinite(da)) return db - da
                        return 0
                      })

                      const filteredReplies = sortedReplies.filter((r: any) => {
                        if (commentSentimentFilter === 'all') return true
                        const key = String(r.text ?? '').trim().toLowerCase()
                        const hit = sentimentByText?.get(key)
                        const label = (hit?.label ?? '').toLowerCase()
                        return label === commentSentimentFilter
                      })

                      return (
                        <div className="tweet-focus" id="tweet-focus">
                          <article className="split-tweet">
                            <div className="tweet-author">
                              <div className="tweet-channel-switch">
                                <AvatarGroup
                                  avatars={group.tweets.map((tw, idx) => {
                                    const ch = tw.channel ? `@${tw.channel}` : `#${idx + 1}`
                                    const letter = ch.replace('@', '').slice(0, 1).toUpperCase()
                                    const src = buildLetterAvatarDataUrl(letter, ch)
                                    return { src, label: ch }
                                  })}
                                  maxVisible={4}
                                  size={30}
                                  overlap={12}
                                  value={safeIndex}
                                  onChange={(idx) => setSelectedTweetIndex(idx)}
                                />
                              </div>
                              <div className="tweet-author-info">
                                <span className="tweet-author-name">{tweet.channel ? `@${tweet.channel}` : renderTweetLabel(tweet, safeIndex)}</span>
                              </div>
                              <span className="tweet-author-time">{tweet.date_formatted || '-'}</span>
                            </div>

                            <p className="tweet-text">{tweet.text ?? '-'}</p>

                            <div className="tweet-media" aria-hidden="true">
                              <div className="tweet-media-placeholder">
                                <span className="icon">image</span>
                              </div>
                            </div>

                            <div className="tweet-engagement">
                              <Metric icon="favorite" value={formatMetricValue(tweet.likes)} />
                              <Metric icon="chat_bubble_outline" value={formatMetricValue(tweet.replies)} />
                              <Metric icon="repeat" value={formatMetricValue(tweet.retweets)} />
                            </div>

                            {tweet.url && (
                              <a className="tweet-link-external" href={tweet.url} target="_blank" rel="noreferrer">
                                <span className="icon">open_in_new</span>
                                {t('dashboard:tweet.openOnX')}
                              </a>
                            )}

                            <div className="tweet-replies" id={`tweet-replies-${groupIndex}-${safeIndex}`}>
                              <button
                                className="tweet-replies-toggle"
                                type="button"
                                onClick={() => {
                                  setExpandedReplies((prev) => ({ ...prev, [repliesKey]: !prev[repliesKey] }))
                                }}
                                disabled={replyCount === 0}
                              >
                                <span className="icon">forum</span>
                                {replyCount === 0
                                  ? t('dashboard:tweet.noComments')
                                  : isOpen
                                    ? t('dashboard:tweet.hideComments', { count: replyCount })
                                    : t('dashboard:tweet.showComments', { count: replyCount })}
                                <span className={`icon reply-caret${isOpen ? ' open' : ''}`}>expand_more</span>
                              </button>

                              {isOpen && replyCount > 0 && (
                                <div className="tweet-replies-list">
                                  <div className="reply-filters">
                                    <SegmentedControl<'newest' | 'top'>
                                      value={commentSortMode}
                                      onChange={setCommentSortMode}
                                      ariaLabel="Sort comments"
                                      options={[
                                        { value: 'newest', label: t('dashboard:comments.sort.newest') },
                                        { value: 'top', label: t('dashboard:comments.sort.top') },
                                      ]}
                                    />
                                    {compareResult && (
                                      <SegmentedControl<'all' | 'positive' | 'negative' | 'neutral'>
                                        value={commentSentimentFilter}
                                        onChange={setCommentSentimentFilter}
                                        ariaLabel="Filter comments"
                                        options={[
                                          { value: 'all', label: t('dashboard:comments.sentiment.all') },
                                          { value: 'positive', label: t('dashboard:comments.sentiment.positive') },
                                          { value: 'negative', label: t('dashboard:comments.sentiment.negative') },
                                          { value: 'neutral', label: t('dashboard:comments.sentiment.neutral') },
                                        ]}
                                      />
                                    )}
                                  </div>

                                  {filteredReplies.map((reply, replyIndex) => (
                                    <article className="reply-card" key={`${group.topic}-all-${replyIndex}`}>
                                      <div className="reply-header">
                                        <div className="reply-avatar">{(reply.user || reply.name || '?').slice(0, 1).toUpperCase()}</div>
                                        <div className="reply-user">
                                          <span className="reply-name">{reply.name || t('common:unknown')}</span>
                                          <span className="reply-handle">@{reply.user || '-'}</span>
                                        </div>
                                        <span className="reply-time">{formatDateLabel(reply.date)}</span>
                                      </div>
                                      <div className="reply-source-row">
                                        <span className="reply-source-badge">@{(reply as any).__sourceChannel ?? '-'}</span>
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
                          </article>
                        </div>
                      )
                    })()
                  )}
                </div>
              )
            })
          )}
        </div>
        )}
          </>
        )}
      </main>

      {/* Splitter between center and right panel */}
      {isRightPanelOpen && (
        <div
          className="splitter"
          role="separator"
          aria-orientation="vertical"
          aria-label={t('analysis:resizeHandleLabel')}
          onPointerDown={startResizeRightPanel}
        />
      )}

      {/* ===== 4. Right Panel (Dynamic Analysis) ===== */}
      <aside className="right-panel" id="right-panel">
        <div className="right-panel-header">
          <h2>{t('analysis:panelTitle')}</h2>
          <button
            type="button"
            className="right-panel-collapse"
            onClick={toggleRightPanel}
            aria-label={isRightPanelOpen ? t('analysis:closePanel') : t('analysis:openPanel')}
            title={isRightPanelOpen ? t('common:close') : t('common:open')}
          >
            <span className="icon">{isRightPanelOpen ? 'chevron_right' : 'chevron_left'}</span>
          </button>
        </div>

        {(isFetchingReplies || isComparingSentiment) && selectedGroup ? (
          <RightPanelSkeleton title={isFetchingReplies ? t('analysis:commentsShort') : t('analysis:sentimentCompareShort')} />
        ) : !selectedGroup ? (
          <div className="analysis-empty" id="analysis-empty">
            <span className="icon icon-lg" aria-hidden="true">
              analytics
            </span>
            <h3>{t('analysis:selectGroupTitle')}</h3>
            <p>{t('analysis:selectGroupBody')}</p>
          </div>
        ) : (
          <>
            {/* Summary of selected group */}
            <section className="analysis-summary" id="analysis-summary">
              <h3 className="summary-title">{selectedGroup.topic}</h3>
              <div className="summary-channels">
                {selectedGroup.channels.map((ch) => (
                  <span className="source-badge" key={ch}>
                    <ChannelAvatar channel={ch} className="source-badge-avatar" size={20} />
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
                    {t('analysis:pullingComments')}
                  </>
                ) : (
                  <>
                    <span className="icon">cloud_download</span>
                    {t('analysis:pullComments')}
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
                        {t('analysis:comparingSentiment')}
                      </>
                    ) : (
                      <>
                        <span className="icon">compare_arrows</span>
                        {t('analysis:compareSentiment')}
                      </>
                    )}
                  </button>
                </section>

                {compareResult && selectedCompareGroup && algorithmTotals && (
                  <section className="sentiment-dashboard" id="sentiment-dashboard">
                    <div className="sentiment-header">
                      <span className="icon">insights</span>
                      <h3>{t('analysis:sentimentResults')}</h3>
                    </div>

                    <SentimentDashboard
                      t={t}
                      algorithmOrder={ALGORITHM_ORDER}
                      selectedAlgorithmKey={selectedAlgorithmKey}
                      setSelectedAlgorithmKey={setSelectedAlgorithmKey}
                      algorithmTotals={algorithmTotals}
                      wordCloudByAlgorithm={wordCloudByAlgorithm}
                      selectedCompareGroup={selectedCompareGroup}
                    />

                    {/* Save notice */}
                    {compareResult.saved_file && (
                      <div className="save-notice" id="save-notice">
                        <span className="icon">check_circle</span>
                        {t('analysis:jsonSaved', { path: compareResult.saved_file })}
                      </div>
                    )}
                  </section>
                )}
              </>
            )}
          </>
        )}
      </aside>

      {!isRightPanelOpen && (
        <button
          type="button"
          className="right-panel-handle"
          onClick={toggleRightPanel}
          aria-label={t('analysis:openPanel')}
          title={t('analysis:openPanel')}
        >
          <span className="icon">chevron_left</span>
        </button>
      )}
    </div>
  )
}
