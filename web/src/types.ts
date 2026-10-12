export type RunStatus = 'running' | 'completed' | 'failed' | 'cancelled'
export type StageStatus = 'waiting' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface ResearchStage {
  id: string
  agent: string
  title: string
  lines: string[]
  status: StageStatus
  resultEvent?: boolean
}

export interface Paper {
  id: string
  title: string
  authors: string
  year: number
  venue: string
  description: string
  abstract: string
  cited: boolean
  url?: string
  source?: string
  citationAliases?: string[]
}

export interface ResearchSession {
  id: string
  title: string
  question: string
  createdAt: string
  status: RunStatus
  stages: ResearchStage[]
  paperCount: number
  sourceCount: number
  previousQuestion?: string
  errorId?: string
  requestId?: string
  errorMessage?: string
  finalAnswer?: string
  papers?: Paper[]
  loaded?: boolean
  serverId?: string
  citationIncomplete?: boolean
  warnings?: string[]
  messages?: ChatMessage[]
}

export interface ChatMessage {
  message_id: string
  role: 'user' | 'assistant'
  content: string
  citations: string[]
}

export interface SettingsSnapshot {
  values: Record<string, string | number>
  effective_values: Record<string, string | number>
  secrets: Record<string, { configured: boolean; saved: boolean; overridden: boolean; pending: boolean }>
  overridden_fields: string[]
  pending_fields: string[]
  restart_required: boolean
  writable: boolean
  runtime: Record<string, string>
  changed_fields?: string[]
}

export interface DemoSettings {
  duration: number
  outcome: 'success' | 'failure'
  paperCount: number
}
