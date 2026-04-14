import type {
  MatchRequest,
  MatchResponse,
  RepliesRequest,
  RepliesResponse,
  SentimentCompareRequest,
  SentimentCompareResponse,
} from '../types'

const runtimeFallbackBaseUrl = `${window.location.protocol}//${window.location.hostname}:8000`

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? runtimeFallbackBaseUrl

export async function getHealth() {
  const response = await fetch(`${API_BASE_URL}/health`)
  if (!response.ok) {
    throw new Error('Health check failed')
  }
  return response.json()
}

export async function runMatch(payload: MatchRequest): Promise<MatchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/match`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `Match request failed with status ${response.status}`)
  }

  return response.json() as Promise<MatchResponse>
}

export async function runReplies(payload: RepliesRequest): Promise<RepliesResponse> {
  const response = await fetch(`${API_BASE_URL}/api/replies`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `Replies request failed with status ${response.status}`)
  }

  return response.json() as Promise<RepliesResponse>
}

export async function runSentimentCompare(payload: SentimentCompareRequest): Promise<SentimentCompareResponse> {
  const response = await fetch(`${API_BASE_URL}/api/sentiment/compare`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `Sentiment compare request failed with status ${response.status}`)
  }

  return response.json() as Promise<SentimentCompareResponse>
}
