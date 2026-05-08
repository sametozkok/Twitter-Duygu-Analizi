import React, { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import { SegmentedControl } from '../../components/SegmentedControl'
import type { SentimentCompareGroup } from '../../types'

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

export type AlgorithmOrderItem = { key: string; title: string; fallbackEngine: string }

export function SentimentDashboard(props: {
  t: TFunction
  algorithmOrder: AlgorithmOrderItem[]
  selectedAlgorithmKey: string
  setSelectedAlgorithmKey: (k: string) => void
  algorithmTotals: Record<string, { positive: number; negative: number; neutral: number; total: number; engine?: string; available?: boolean; error?: string }>
  wordCloudByAlgorithm: Record<string, { text: string; weight: number }[]> | null
  selectedCompareGroup: SentimentCompareGroup
}) {
  const { t, algorithmOrder, selectedAlgorithmKey, setSelectedAlgorithmKey, algorithmTotals, wordCloudByAlgorithm, selectedCompareGroup } = props

  const selectedAlgo = useMemo(() => algorithmOrder.find((a) => a.key === selectedAlgorithmKey) ?? algorithmOrder[0], [algorithmOrder, selectedAlgorithmKey])
  const totals = selectedAlgo ? algorithmTotals[selectedAlgo.key] : null
  const words = selectedAlgo ? (wordCloudByAlgorithm?.[selectedAlgo.key] ?? []) : []
  const isUnavailable = totals?.available === false

  const engineLabel = useMemo(() => {
    if (!selectedAlgo || !totals) return ''
    if (isUnavailable) return ''
    return totals.engine ?? selectedAlgo.fallbackEngine
  }, [isUnavailable, selectedAlgo, totals])


  return (
    <>
      <div style={{ padding: '0 20px 12px' }}>
        <SegmentedControl<string>
          value={selectedAlgorithmKey}
          onChange={setSelectedAlgorithmKey}
          ariaLabel={t('analysis:sentimentResults')}
          options={algorithmOrder.map((algo) => ({
            value: algo.key,
            label: t(`analysis:algorithm.${algo.key}` as any, { defaultValue: algo.title }),
            disabled: false,
          }))}
        />
      </div>

      <div className="sentiment-grid">
        <div className="sentiment-panel">
          <div className="sentiment-panel-header">
            <div className="sentiment-panel-title">
              <span className="icon">psychology</span>
              <h4>{selectedAlgo ? t(`analysis:algorithm.${selectedAlgo.key}` as any, { defaultValue: selectedAlgo.title }) : '-'}</h4>
            </div>
            {engineLabel ? <span className="sentiment-engine">{engineLabel}</span> : null}
          </div>

          {isUnavailable ? (
            <div className="sentiment-empty sentiment-unavailable">
              <div className="sentiment-unavailable-title">
                {t('analysis:unavailable.title', { defaultValue: 'Bu model şu anda kullanılamıyor' })}
              </div>
              <div className="sentiment-unavailable-body">
                {totals?.error
                  ? totals.error
                  : t('analysis:unavailable.cuteFallback', {
                      defaultValue:
                        'Şu anda duygularla ilgilenmek istemiyorum, depresyondayım. 🥲',
                    })}
              </div>
            </div>
          ) : !totals || totals.total === 0 ? (
            <div className="sentiment-empty">{t('analysis:noResultForAlgorithm')}</div>
          ) : (
            <>
              <DoughnutChart positive={totals.positive} negative={totals.negative} neutral={totals.neutral} />

              <div className="sentiment-bars">
                <div className="sentiment-bar-row">
                  <div className="sentiment-bar-label">
                    <span>{t('analysis:sentiments.positive')}</span>
                    <span>{totals.positive} ({totals.total > 0 ? Math.round((totals.positive / totals.total) * 100) : 0}%)</span>
                  </div>
                  <div className="sentiment-bar-track">
                    <div className="sentiment-bar-fill" style={{ width: `${totals.total > 0 ? (totals.positive / totals.total) * 100 : 0}%`, background: 'var(--positive)' }} />
                  </div>
                </div>
                <div className="sentiment-bar-row">
                  <div className="sentiment-bar-label">
                    <span>{t('analysis:sentiments.negative')}</span>
                    <span>{totals.negative} ({totals.total > 0 ? Math.round((totals.negative / totals.total) * 100) : 0}%)</span>
                  </div>
                  <div className="sentiment-bar-track">
                    <div className="sentiment-bar-fill" style={{ width: `${totals.total > 0 ? (totals.negative / totals.total) * 100 : 0}%`, background: 'var(--negative)' }} />
                  </div>
                </div>
                <div className="sentiment-bar-row">
                  <div className="sentiment-bar-label">
                    <span>{t('analysis:sentiments.neutral')}</span>
                    <span>{totals.neutral} ({totals.total > 0 ? Math.round((totals.neutral / totals.total) * 100) : 0}%)</span>
                  </div>
                  <div className="sentiment-bar-track">
                    <div className="sentiment-bar-fill" style={{ width: `${totals.total > 0 ? (totals.neutral / totals.total) * 100 : 0}%`, background: 'var(--neutral)' }} />
                  </div>
                </div>
              </div>

              <WordCloud words={words} />
            </>
          )}
        </div>
      </div>

      <div className="channel-comparison" id="channel-comparison" style={isUnavailable ? { display: 'none' } : undefined}>
        <div className="comparison-title">
          <span className="icon">compare</span>
          {t('analysis:channelComparison')}
        </div>
        <div className="comparison-cards">
          {Object.entries(selectedCompareGroup.channel_results).map(([channel, result]) => {
            const algo = result.algorithms?.[selectedAlgorithmKey]
            const summary = algo?.summary
            const total = summary?.total ?? 0
            const positive = summary?.positive ?? 0
            const negative = summary?.negative ?? 0
            const neutral = summary?.neutral ?? 0

            const dominantRaw = String(summary?.dominant ?? '').toLowerCase()
            const dominantKey =
              dominantRaw === 'positive' || dominantRaw === 'pozitif'
                ? 'positive'
                : dominantRaw === 'negative' || dominantRaw === 'negatif'
                  ? 'negative'
                  : dominantRaw === 'neutral' || dominantRaw === 'nötr' || dominantRaw === 'notr'
                    ? 'neutral'
                    : null

            const pct = (n: number) => (total > 0 ? Math.round((n / total) * 100) : 0)

            return (
              <div className="comparison-card" key={`${selectedCompareGroup.topic}-${channel}`}>
                <div className="comparison-card-header">
                  <span className="comparison-channel-name">
                    <span className="icon">person</span>
                    @{channel}
                  </span>
                  <span className="comparison-best-algo">{t(`analysis:algorithm.${selectedAlgorithmKey}` as any, { defaultValue: selectedAlgorithmKey })}</span>
                </div>
                <div className="comparison-algo-row">
                  <span className={`algo-chip algo-chip-positive${dominantKey === 'positive' ? ' is-dominant' : ''}`}>
                    <span className="algo-chip-name">{t('analysis:sentiments.positive')}</span>
                    <span className="algo-chip-total">{positive} ({pct(positive)}%)</span>
                  </span>
                  <span className={`algo-chip algo-chip-negative${dominantKey === 'negative' ? ' is-dominant' : ''}`}>
                    <span className="algo-chip-name">{t('analysis:sentiments.negative')}</span>
                    <span className="algo-chip-total">{negative} ({pct(negative)}%)</span>
                  </span>
                  <span className={`algo-chip algo-chip-neutral${dominantKey === 'neutral' ? ' is-dominant' : ''}`}>
                    <span className="algo-chip-name">{t('analysis:sentiments.neutral')}</span>
                    <span className="algo-chip-total">{neutral} ({pct(neutral)}%)</span>
                  </span>
                </div>
                <div className="comparison-card-footer">
                  <span className="comparison-total-label">Toplam: <strong>{total}</strong></span>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </>
  )
}

