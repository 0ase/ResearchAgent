export type RunStatus = 'running' | 'completed' | 'failed' | 'cancelled'
export type StageStatus = 'waiting' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface ResearchStage {
  id: string
  agent: string
  title: string
  lines: string[]
  status: StageStatus
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
}

export interface DemoSettings {
  duration: number
  outcome: 'success' | 'failure'
  paperCount: number
}
