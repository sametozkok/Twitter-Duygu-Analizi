export type MatchRequest = {
  channels: string[]
  tweets_per_channel: number
  min_channels_for_match: number
  twitter_bearer_token?: string
}

export type TweetItem = {
  channel?: string
  tweet_id?: string
  id?: string
  text?: string
  url?: string
  likes?: number
  replies?: number
  retweets?: number
  date_formatted?: string
}

export type ReplyItem = {
  text?: string
  user?: string
  name?: string
  date?: string
  likes?: number
  views?: number
  retweets?: number
  replies?: number
  quotes?: number
}

export type AnalysisGroup = {
  topic: string
  channels: string[]
  channel_count: number
  total_reply_count: number
  tweets: TweetItem[]
  replies_by_channel: Record<string, ReplyItem[]>
  emotion_results: Record<string, Record<string, unknown>>
}

export type MatchResponse = {
  matched_groups: AnalysisGroup[]
  total_groups: number
  status: string
  run_id?: string | null
}

export type RepliesRequest = {
  matched_groups: AnalysisGroup[]
  reply_count: number
  twitter_auth_token: string
  twitter_ct0: string
  twitter_bearer_token: string
  run_id?: string | null
}

export type RepliesResponse = {
  matched_groups: AnalysisGroup[]
  total_groups: number
  total_replies: number
  status: string
  run_id?: string | null
}

export type SentimentCompareRequest = {
  matched_groups: AnalysisGroup[]
  algorithms: string[]
  save_to_json?: boolean
  run_id?: string | null
}

export type SentimentSummary = {
  total: number
  positive: number
  negative: number
  neutral: number
  dominant: string
}

export type SentimentAlgorithmResult = {
  engine?: string
  summary: SentimentSummary
  items: Array<{
    user?: string
    name?: string
    text?: string
    label?: string
    score?: number
  }>
}

export type SentimentChannelResult = {
  algorithms: Record<string, SentimentAlgorithmResult>
  best_algorithm: string
}

export type SentimentCompareGroup = {
  topic: string
  channels: string[]
  channel_results: Record<string, SentimentChannelResult>
}

export type SentimentCompareResponse = {
  compared_groups: SentimentCompareGroup[]
  total_groups: number
  status: string
  saved_file?: string | null
  run_id?: string | null
}

export type RunSummary = {
  run_id: string
  created_at: string
  updated_at: string
  channels: string[]
  total_groups: number
  total_replies: number
  has_replies: boolean
  has_sentiment: boolean
}

export type RunListResponse = {
  runs: RunSummary[]
  total: number
}

export type RunDetail = {
  run_id: string
  created_at: string
  updated_at: string
  channels: string[]
  matched_groups: AnalysisGroup[]
  total_groups: number
  total_replies: number
  has_replies: boolean
  has_sentiment: boolean
  sentiment_compare: {
    algorithms: string[]
    compared_groups: SentimentCompareGroup[]
  } | null
}
