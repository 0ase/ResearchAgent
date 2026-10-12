import type { DemoSettings, ResearchSession } from '../types'

export type ResearchEvent =
  | { type: 'stage.started'; stageId: string }
  | { type: 'stage.output'; stageId: string; line: string }
  | { type: 'stage.completed'; stageId: string }
  | { type: 'research.completed' }
  | { type: 'research.failed'; stageId: string; errorId: string }

// This adapter performs no network calls. Replace it with the real stream adapter later.
export function startMockResearch(
  session: ResearchSession,
  settings: DemoSettings,
  onEvent: (event: ResearchEvent) => void,
): () => void {
  const events: ResearchEvent[] = []
  for (const stage of session.stages) {
    events.push({ type: 'stage.started', stageId: stage.id })
    if (settings.outcome === 'failure' && stage.id === 'analysis') {
      events.push({ type: 'stage.output', stageId: stage.id, line: '跨论文分析未获得完整结果。' })
      events.push({ type: 'research.failed', stageId: stage.id, errorId: `DEMO-${session.id.slice(-8).toUpperCase()}` })
      break
    }
    events.push(...stage.lines.map(line => ({ type: 'stage.output' as const, stageId: stage.id, line })))
    events.push({ type: 'stage.completed', stageId: stage.id })
  }
  if (settings.outcome === 'success') events.push({ type: 'research.completed' })
  const interval = settings.duration * 1000 / events.length
  let cursor = 0
  const timer = window.setInterval(() => {
    onEvent(events[cursor++])
    if (cursor >= events.length) window.clearInterval(timer)
  }, interval)
  return () => window.clearInterval(timer)
}

export function applyResearchEvent(session: ResearchSession, event: ResearchEvent): ResearchSession {
  if (event.type === 'research.completed') return { ...session, status: 'completed' }
  if (event.type === 'research.failed') return {
    ...session, status: 'failed', errorId: event.errorId,
    stages: session.stages.map(stage => stage.id === event.stageId ? { ...stage, status: 'failed' } : stage),
  }
  return {
    ...session,
    stages: session.stages.map(stage => {
      if (stage.id !== event.stageId) return stage
      if (event.type === 'stage.started') return { ...stage, status: 'running', lines: [] }
      if (event.type === 'stage.output') return { ...stage, lines: [...stage.lines, event.line] }
      return { ...stage, status: 'completed' }
    }),
  }
}
