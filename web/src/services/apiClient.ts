import type { ChatMessage, SettingsSnapshot } from '../types'

export interface ApiEvent extends Record<string, unknown> { event: string }
export class ApiError extends Error {
  constructor(message: string, public errorId?: string, public requestId?: string) { super(message) }
}

async function checkedFetch(path: string, init?: RequestInit): Promise<Response> {
  let response: Response
  try { response = await fetch(path, init) }
  catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError('无法连接后端，请确认 BIGONE 后端正在运行。')
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const error = body.error ?? {}
    throw new ApiError(error.message ?? (response.status >= 500 ? '后端暂时不可用，请确认 BIGONE 后端正在运行并检查日志。' : `请求失败（HTTP ${response.status}）。`), error.error_id, error.request_id ?? response.headers.get('X-Request-ID') ?? undefined)
  }
  return response
}

export async function apiJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await checkedFetch(path, { ...init, signal: init?.signal ?? AbortSignal.timeout(15000) })
  return response.json() as Promise<T>
}

export function postJson(body: unknown, signal?: AbortSignal): RequestInit {
  return { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal }
}

// Network chunks are unrelated to SSE frame boundaries or UTF-8 code points.
export async function readEventStream(response: Response, onEvent: (event: ApiEvent) => void) {
  if (!response.body) throw new ApiError('后端没有返回研究事件流。')
  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8', { fatal: true })
  let buffer = ''
  let doneReceived = false
  const consume = (frame: string) => {
    const data = frame.split(/\r?\n/).filter(line => line.startsWith('data:')).map(line => line.slice(5).replace(/^ /, '')).join('\n')
    if (!data) return
    let event: ApiEvent
    try {
      event = JSON.parse(data) as ApiEvent
      if (!event || typeof event !== 'object' || Array.isArray(event) || typeof event.event !== 'string') throw new Error('event')
    }
    catch { throw new ApiError('研究事件格式无法解析，请检查后端日志。') }
    if (event.event === 'error') throw new ApiError(String(event.message ?? '研究任务失败。'), typeof event.error_id === 'string' ? event.error_id : undefined, typeof event.request_id === 'string' ? event.request_id : undefined)
    onEvent(event)
    if (event.event === 'done') doneReceived = true
  }
  try {
    while (true) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })
      let separator: RegExpExecArray | null
      while ((separator = /\r?\n\r?\n/.exec(buffer))) {
        consume(buffer.slice(0, separator.index))
        buffer = buffer.slice(separator.index + separator[0].length)
      }
      if (doneReceived) return
      if (done) break
    }
    if (buffer.trim()) consume(buffer)
    if (!doneReceived) throw new ApiError('研究连接提前断开，尚未收到完成结果。请检查日志后重试。', undefined, response.headers.get('X-Request-ID') ?? undefined)
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}

export async function startResearch(query: string, maxPapers: number, signal: AbortSignal, onEvent: (event: ApiEvent) => void) {
  const response = await checkedFetch('/api/research/stream', postJson({ query, max_papers: maxPapers }, signal))
  if (!response.headers.get('Content-Type')?.includes('text/event-stream')) throw new ApiError('后端未返回有效的研究事件流。')
  await readEventStream(response, onEvent)
}

export const loadHistory = (signal?: AbortSignal) => apiJson<Array<{ session_id: string; query: string; created_at: string; papers_count: number }>>('/api/research/history?limit=100', { signal })
export const loadSession = (id: string, signal?: AbortSignal) => apiJson<{ session_id: string; query: string; created_at: string; result: Record<string, unknown> }>(`/api/research/${encodeURIComponent(id)}`, { signal })
export const loadMessages = (id: string, signal?: AbortSignal) => apiJson<ChatMessage[]>(`/api/research/${encodeURIComponent(id)}/messages?limit=200`, { signal })
export const followup = (id: string, message: string, messageId: string, signal: AbortSignal) => apiJson<{ answer: string; citations: string[] }>(`/api/research/${encodeURIComponent(id)}/chat`, postJson({ message, message_id: messageId }, signal))
export const loadSettings = (signal?: AbortSignal) => apiJson<SettingsSnapshot>('/api/settings', { signal })
export const saveSettings = (values: Record<string, string | number>, secrets: Record<string, string>, clearSecrets: string[]) => apiJson<SettingsSnapshot>('/api/settings', { method: 'PUT', headers: { 'Content-Type': 'application/json', 'X-B1GONE-Config': 'local' }, body: JSON.stringify({ values, secrets, clear_secrets: clearSecrets }) })
