export type MatchRequest = {
  channels: string[]
  tweets_per_channel: number
  min_channels_for_match: number
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
}

export type RepliesRequest = {
  matched_groups: AnalysisGroup[]
  reply_count: number
  twitter_auth_token: string
  twitter_ct0: string
  twitter_bearer_token: string
}

export type RepliesResponse = {
  matched_groups: AnalysisGroup[]
  total_groups: number
  total_replies: number
  status: string
}

export type SentimentCompareRequest = {
  matched_groups: AnalysisGroup[]
  algorithms: string[]
  save_to_json?: boolean
}

export type SentimentSummary = {
  total: number
  positive: number
  negative: number
  neutral: number
  dominant: string
}

export type SentimentAlgorithmResult = {
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
}
