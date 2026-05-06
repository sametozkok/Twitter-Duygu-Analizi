import type {
  MatchRequest,
  MatchResponse,
  RepliesRequest,
  RepliesResponse,
  RunDetail,
  RunListResponse,
  SentimentCompareRequest,
  SentimentCompareResponse,
} from '../types'

function getApiBaseUrl(): string {
  const envBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()
  if (envBaseUrl) {
    return envBaseUrl.replace(/\/+$/, '')
  }

  const isLocalHost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  if (isLocalHost) {
    return `${window.location.protocol}//${window.location.hostname}:8000`
  }

  throw new Error(
    'VITE_API_BASE_URL is not set. Configure it to your backend URL before using the app.',
  )
}

export const API_BASE_URL = getApiBaseUrl()

async function fetchJson(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init)
  } catch {
    throw new Error(
      'Failed to fetch backend. Check VITE_API_BASE_URL, backend availability, and CORS settings.',
    )
  }
}

export async function getHealth() {
  const response = await fetchJson(`${API_BASE_URL}/health`)
  if (!response.ok) {
    throw new Error('Health check failed')
  }
  return response.json()
}

export async function runMatch(payload: MatchRequest): Promise<MatchResponse> {
  const response = await fetchJson(`${API_BASE_URL}/api/match`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const text = await response.text()
    try {
      const parsed = JSON.parse(text) as { detail?: string }
      throw new Error(parsed.detail || text || `Match request failed with status ${response.status}`)
    } catch {
      throw new Error(text || `Match request failed with status ${response.status}`)
    }
  }

  return response.json() as Promise<MatchResponse>
}

export async function runReplies(payload: RepliesRequest): Promise<RepliesResponse> {
  const response = await fetchJson(`${API_BASE_URL}/api/replies`, {
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
  const response = await fetchJson(`${API_BASE_URL}/api/sentiment/compare`, {
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

export async function listRuns(): Promise<RunListResponse> {
  const response = await fetchJson(`${API_BASE_URL}/api/runs`)
  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `Run listesi alinamadi (status ${response.status})`)
  }
  return response.json() as Promise<RunListResponse>
}

export async function getRun(runId: string): Promise<RunDetail> {
  const response = await fetchJson(`${API_BASE_URL}/api/runs/${encodeURIComponent(runId)}`)
  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `Run detayi alinamadi (status ${response.status})`)
  }
  return response.json() as Promise<RunDetail>
}

export async function deleteRun(runId: string): Promise<void> {
  const response = await fetchJson(`${API_BASE_URL}/api/runs/${encodeURIComponent(runId)}`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `Run silinemedi (status ${response.status})`)
  }
}
