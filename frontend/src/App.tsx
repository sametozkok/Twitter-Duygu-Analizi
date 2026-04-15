import { useMemo, useState } from 'react'
import { Sidebar } from './components/Sidebar'
import { runMatch, runReplies, runSentimentCompare } from './lib/api'
import type { MatchResponse, RepliesResponse, SentimentCompareResponse, TweetItem } from './types'

function renderTweetLabel(tweet: TweetItem, index: number) {
  return tweet.channel ? `@${tweet.channel}` : `Tweet ${index + 1}`
}

function formatCompactNumber(value?: number) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric) || numeric < 0) {
    return '0'
  }

  return new Intl.NumberFormat('tr-TR', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(numeric)
}

function formatMetricValue(value?: number) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return '-'
  }
  return formatCompactNumber(numeric)
}

function formatDateLabel(value?: string) {
  if (!value) {
    return '-'
  }

  const parsed = Date.parse(value)
  if (Number.isNaN(parsed)) {
    return value
  }

  return new Intl.DateTimeFormat('tr-TR', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(parsed))
}

function buildReplyMetrics(reply: {
  likes?: number
  views?: number
  retweets?: number
  replies?: number
  quotes?: number
}) {
  const metrics = [
    { label: 'Beğeni', value: Number(reply.likes ?? 0) },
    { label: 'Görüntüleme', value: Number(reply.views ?? 0) },
    { label: 'Retweet', value: Number(reply.retweets ?? 0) },
    { label: 'Yorum', value: Number(reply.replies ?? 0) },
    { label: 'Alıntı', value: Number(reply.quotes ?? 0) },
  ]

  return metrics.filter((item) => Number.isFinite(item.value) && item.value > 0)
}

export default function App() {
  const [channels, setChannels] = useState<string[]>(['', '', ''])
  const [tweetsPerChannel, setTweetsPerChannel] = useState(10)
  const [minChannelsForMatch, setMinChannelsForMatch] = useState(2)
  const [replyCount, setReplyCount] = useState(20)
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

  const activeChannels = useMemo(
    () => channels.map((item) => item.trim()).filter((item) => item.length > 0),
    [channels],
  )

  const shownGroups = repliesResult?.matched_groups ?? matchResult?.matched_groups ?? []
  const isRepliesReady = Boolean(repliesResult)
  const selectedGroupIndexSafe = selectedGroupIndex < shownGroups.length ? selectedGroupIndex : 0
  const selectedGroup = shownGroups[selectedGroupIndexSafe] ?? null
  const replyChannelCount = selectedGroup ? Object.keys(selectedGroup.replies_by_channel).length : 0
  const replyColumns = Math.min(3, replyChannelCount)
  const totalRepliesForGroup = selectedGroup
    ? Object.values(selectedGroup.replies_by_channel).reduce((sum, arr) => sum + arr.length, 0)
    : 0
  const selectedCompareGroup = compareResult?.compared_groups.find((group) => group.topic === selectedGroup?.topic) ?? null

  function extractChannelName(url: string): string {
    const trimmed = url.trim()
    const match = trimmed.match(/(?:x\.com|twitter\.com)\/(@?[\w]+)/i)
    if (match) return match[1].replace(/^@/, '')
    const atMatch = trimmed.match(/^@?([\w]+)$/)
    if (atMatch) return atMatch[1]
    return trimmed
  }

  function updateChannel(index: number, value: string) {
    setChannels((prev) => prev.map((item, i) => (i === index ? value : item)))
  }

  function addChannel() {
    setChannels((prev) => [...prev, ''])
  }

  function removeChannel(index: number) {
    setChannels((prev) => {
      if (prev.length <= 2) {
        return prev
      }
      return prev.filter((_, i) => i !== index)
    })
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

    try {
      const response = await runMatch({
        channels: activeChannels,
        tweets_per_channel: tweetsPerChannel,
        min_channels_for_match: minChannelsForMatch,
      })
      setMatchResult(response)
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : 'Eslestirme sirasinda beklenmeyen hata oldu.'
      setError(message)
    } finally {
      setIsMatching(false)
    }
  }

  async function handleFetchReplies() {
    setError(null)

    if (!matchResult?.matched_groups?.length) {
      setError('Once tweetleri cekip eslesmeleri bulman gerekiyor.')
      return
    }

    setIsFetchingReplies(true)

    try {
      const response = await runReplies({
        matched_groups: matchResult.matched_groups,
        reply_count: replyCount,
        twitter_auth_token: twitterAuthToken.trim(),
        twitter_ct0: twitterCt0.trim(),
        twitter_bearer_token: twitterBearerToken.trim(),
      })
      setRepliesResult(response)
      setCompareResult(null)
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : 'Yorum cekme sirasinda beklenmeyen hata oldu.'
      setError(message)
    } finally {
      setIsFetchingReplies(false)
    }
  }

  async function handleCompareSentiment() {
    setError(null)

    if (!repliesResult?.matched_groups?.length) {
      setError('Duygu karsilastirmasi icin once yorumlari cekmelisin.')
      return
    }

    setIsComparingSentiment(true)

    try {
      const response = await runSentimentCompare({
        matched_groups: repliesResult.matched_groups,
        algorithms: ['bert', 'hybrid'],
        save_to_json: true,
      })
      setCompareResult(response)
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : 'Duygu karsilastirmasi sirasinda beklenmeyen hata oldu.'
      setError(message)
    } finally {
      setIsComparingSentiment(false)
    }
  }

  return (
    <div className="app-shell">
      <Sidebar
        tweetsPerChannel={tweetsPerChannel}
        setTweetsPerChannel={setTweetsPerChannel}
        minChannelsForMatch={minChannelsForMatch}
        setMinChannelsForMatch={setMinChannelsForMatch}
        replyCount={replyCount}
        setReplyCount={setReplyCount}
        twitterAuthToken={twitterAuthToken}
        setTwitterAuthToken={setTwitterAuthToken}
        twitterCt0={twitterCt0}
        setTwitterCt0={setTwitterCt0}
        twitterBearerToken={twitterBearerToken}
        setTwitterBearerToken={setTwitterBearerToken}
      />

      <main className="main-shell">
        <section className="page-grid">
          <section className="channel-section">
            <div className="channel-toolbar">
              <p className="eyebrow">Kanallar</p>
              <button className="ghost-button" type="button" onClick={addChannel}>+ Kanal ekle</button>
            </div>

            <section className="channel-list">
              {channels.map((channel, index) => {
                const displayName = extractChannelName(channel)
                const hasValue = channel.trim().length > 0
                return (
                  <section className="channel-row" key={`channel-${index}`}>
                    {hasValue && displayName ? (
                      <span className="channel-name-display">@{displayName}</span>
                    ) : null}
                    <input
                      type="text"
                      value={channel}
                      onChange={(event) => updateChannel(index, event.target.value)}
                      placeholder="kullanıcı adı veya link"
                      aria-label={`Kanal ${index + 1}`}
                      className={hasValue && displayName ? 'channel-input-hidden' : ''}
                    />
                    <button
                      className="channel-remove-inline"
                      type="button"
                      onClick={() => removeChannel(index)}
                      disabled={channels.length <= 2}
                      title={channels.length <= 2 ? 'En az 2 kanal gerekli' : 'Kanali sil'}
                      aria-label={`Kanal ${index + 1} sil`}
                    >
                      ×
                    </button>
                  </section>
                )
              })}
            </section>
          </section>

          {error ? (
            <section className="results-panel">
              <div className="results-head">
                <div>
                  <p className="eyebrow">Hata</p>
                  <h3>{error}</h3>
                </div>
              </div>
            </section>
          ) : null}



          {isRepliesReady && (repliesResult?.total_replies ?? 0) === 0 ? (
            <section className="results-panel">
              <div className="results-head">
                <div>
                  <p className="eyebrow">Bilgilendirme</p>
                  <h3>Yorum bulunamadi</h3>
                </div>
              </div>
              <p className="reply-empty">
                Tweetlerde yorumlar kapali olabilir veya Twitter auth_token/ct0 bilgileri eksik-gecersiz olabilir.
              </p>
            </section>
          ) : null}

          <section className="results-split">
            <section className="results-column">
              <div className="results-head">
                <div>
                  <h3>Eşleşen Tweet Grupları {shownGroups.length > 0 && <span className="head-count">({shownGroups.length})</span>}</h3>
                </div>
                <button
                  className={`primary-button${isMatching ? ' primary-button-loading' : ''}`}
                  type="button"
                  onClick={handleFetchMatches}
                  disabled={isMatching}
                  aria-busy={isMatching}
                >
                  <span className="button-label">{isMatching ? 'Tweetler çekiliyor...' : 'Tweetleri Çek'}</span>
                  {isMatching ? (
                    <span className="button-progress" aria-hidden="true">
                      <span className="button-progress-bar" />
                    </span>
                  ) : null}
                </button>
              </div>

              <div className="group-list">
                {shownGroups.length ? (
                  shownGroups.map((group, groupIndex) => (
                    <article
                      className={`result-card group-card${groupIndex === selectedGroupIndexSafe ? ' group-card-active' : ''}`}
                      key={group.topic}
                      role="button"
                      tabIndex={0}
                      onClick={() => setSelectedGroupIndex(groupIndex)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          setSelectedGroupIndex(groupIndex)
                        }
                      }}
                    >
                      <div className="group-meta-row">
                        <span className="group-badge">Grup {groupIndex + 1}</span>
                        <span className="group-select-state">{groupIndex === selectedGroupIndexSafe ? 'Secili' : 'Secmek icin tikla'}</span>
                      </div>

                      <div className="result-card-head">
                        <div>
                          <strong>{group.topic}</strong>
                          <p className="group-channels">{group.channels.join(' • ')}</p>
                        </div>
                        <span>{group.channel_count} kanal</span>
                      </div>

                      <small>{group.total_reply_count} yorum</small>

                      <div className="group-divider" />

                      <div className="tweet-card-grid">
                        {group.tweets.map((tweet, idx) => (
                          <article className="tweet-card" key={`${group.topic}-${idx}`}>
                            <div className="tweet-head">
                              <div className="tweet-avatar">{renderTweetLabel(tweet, idx).replace('@', '').slice(0, 1).toUpperCase()}</div>
                              <div className="tweet-head-text">
                                <strong>{renderTweetLabel(tweet, idx)}</strong>
                                <span>{tweet.date_formatted || '-'}</span>
                              </div>
                            </div>

                            <p className="tweet-body">{tweet.text ?? '-'}</p>

                            <div className="tweet-metrics">
                              <span><strong>{formatMetricValue(tweet.likes)}</strong> Begeni</span>
                              <span><strong>{formatMetricValue(tweet.replies)}</strong> Yorum</span>
                              <span><strong>{formatMetricValue(tweet.retweets)}</strong> Retweet</span>
                            </div>

                            {tweet.url ? (
                              <a className="tweet-link" href={tweet.url} target="_blank" rel="noreferrer">
                                Tweeti X'te ac
                              </a>
                            ) : null}
                          </article>
                        ))}
                      </div>
                    </article>
                  ))
                ) : (
                  <article className="result-card">
                    <div className="result-card-head">
                      <strong>Henuz eslesme yok</strong>
                    </div>
                    <p>Once Tweet cek butonunu calistir.</p>
                  </article>
                )}
              </div>
            </section>

            <section className="results-column">
              <div className="results-head">
                <div>
                  <h3>Seçili Grubun Yorumları {totalRepliesForGroup > 0 && <span className="head-count">({totalRepliesForGroup})</span>}</h3>
                </div>
                <button
                  className="primary-button"
                  type="button"
                  onClick={handleFetchReplies}
                  disabled={isFetchingReplies || isMatching || !matchResult?.matched_groups?.length}
                >
                  {isFetchingReplies ? 'Yorumlar çekiliyor...' : 'Yorumları Çek'}
                </button>
              </div>

              {!selectedGroup ? (
                <p className="reply-empty">Yorumlarin gorunmesi icin once tweet eslesmeleri olusmali.</p>
              ) : !isRepliesReady ? (
                <p className="reply-empty">Secilen grup icin yorumlari almak adina ustteki Yorum cek butonuna basin.</p>
              ) : Object.entries(selectedGroup.replies_by_channel).length ? (
                <section className="reply-section">
                  <p className="reply-title">{selectedGroup.topic}</p>
                  <div
                    className="reply-channels"
                    style={
                      replyChannelCount <= 3
                        ? { gridAutoFlow: 'column', gridTemplateColumns: `repeat(${replyChannelCount}, 1fr)` }
                        : { gridAutoFlow: 'column', gridAutoColumns: `calc((100% - ${(2) * 0.45}rem) / 3)` }
                    }
                  >
                    {Object.entries(selectedGroup.replies_by_channel).map(([channel, replies]) => (
                      <section className="reply-channel-block" key={`${selectedGroup.topic}-${channel}`}>
                        <strong>@{channel}</strong>
                        <div className="reply-list">
                          {replies.map((reply, ridx) => (
                            <article className="reply-card" key={`${channel}-${ridx}`}>
                              <div className="reply-head">
                                <div className="reply-user-block">
                                  <span>{reply.name || 'Bilinmeyen Kullanıcı'}</span>
                                  <small>{reply.user ? `@${reply.user}` : '@bilinmiyor'}</small>
                                </div>
                                <small>{formatDateLabel(reply.date)}</small>
                              </div>
                              {buildReplyMetrics(reply).length ? (
                                <div className="reply-metrics">
                                  {buildReplyMetrics(reply).map((metric) => (
                                    <span key={metric.label}>
                                      <strong>{formatCompactNumber(metric.value)}</strong> {metric.label}
                                    </span>
                                  ))}
                                </div>
                              ) : null}
                              <p>{reply.text ?? '-'}</p>
                            </article>
                          ))}
                        </div>
                      </section>
                    ))}
                  </div>
                </section>
              ) : (
                <p className="reply-empty">Bu grup icin yorum verisi alinamadi.</p>
              )}

              <section className="result-card" style={{ marginTop: '16px' }}>
                <div className="results-head" style={{ padding: 0, borderBottom: 'none', marginBottom: '12px' }}>
                  <div>
                    <h3>Duygu Karsilastirmasi</h3>
                  </div>
                  <button
                    className="primary-button"
                    type="button"
                    onClick={handleCompareSentiment}
                    disabled={isComparingSentiment || !repliesResult?.matched_groups?.length}
                  >
                    {isComparingSentiment ? 'Karsilastiriliyor...' : 'Duygu Karsilastir'}
                  </button>
                </div>

                {!compareResult ? (
                  <p className="reply-empty">Karsilastirma sonuclarini gormek icin butona bas.</p>
                ) : !selectedCompareGroup ? (
                  <p className="reply-empty">Secili grup icin karsilastirma sonucu bulunamadi.</p>
                ) : (
                  <div className="reply-list">
                    {Object.entries(selectedCompareGroup.channel_results).map(([channel, result]) => (
                      <article className="reply-card" key={`${selectedCompareGroup.topic}-${channel}`}>
                        <div className="reply-head">
                          <div className="reply-user-block">
                            <span>@{channel}</span>
                            <small>En iyi: {result.best_algorithm}</small>
                          </div>
                        </div>
                        <div className="reply-metrics">
                          {Object.entries(result.algorithms).map(([name, algo]) => (
                            <span key={`${channel}-${name}`}>
                              <strong>{name}</strong> {algo.summary.dominant} ({algo.summary.total})
                            </span>
                          ))}
                        </div>
                      </article>
                    ))}
                    {compareResult.saved_file ? (
                      <small>JSON kaydi: {compareResult.saved_file}</small>
                    ) : null}
                  </div>
                )}
              </section>
            </section>
          </section>

        </section>
      </main>
    </div>
  )
}
