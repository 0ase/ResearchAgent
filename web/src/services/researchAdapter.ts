import type { Paper, ResearchSession, ResearchStage } from '../types'
import type { ApiEvent } from './apiClient'

type Data = Record<string, unknown>
const data = (value: unknown): Data => value && typeof value === 'object' && !Array.isArray(value) ? value as Data : {}
const items = (value: unknown): Data[] => Array.isArray(value) ? value.map(data) : []
const text = (value: unknown, fallback = '') => typeof value === 'string' ? value : fallback
const count = (value: unknown) => typeof value === 'number' ? value : 0
const titles: Record<string, string> = { orchestrate: '拆解研究问题', search: '搜索相关文献', filter: '评估与筛选论文', read: '阅读与提取证据', analyze: '跨论文比较分析', synthesize: '撰写研究综述', critic: '审查报告质量' }
const screeningLabels: Record<string, string> = { candidates: '候选数量', attempted: '已评估', scored: '有效评分', failed: '评分失败', not_evaluated: '未评估', qualified: '达到门槛', qualified_primary: '达到标准门槛', supplemented: '补充入选', target: '目标阅读数量', selected: '实际入选', minimum_score: '标准阈值', supplement_minimum_score: '补充阈值', applied_minimum_score: '采用阈值', batch_size: '每批篇数', max_tokens: '每次评分 token 上限', batches_evaluated: '评估批次', model_calls: '评分请求次数', score_scale: '分数满分' }

export function safePaperUrl(value: unknown): string | undefined {
  if (typeof value !== 'string') return
  try { const url = new URL(value); if (['https:', 'http:'].includes(url.protocol) && !url.username && !url.password) return url.href }
  catch { /* Unusable source links remain unavailable. */ }
}

export function citationLookup(papers: Paper[]): Map<string, string> {
  const candidates = new Map<string, Set<string>>()
  for (const paper of papers) for (const alias of [paper.id, ...(paper.citationAliases ?? [])]) {
    const ids = candidates.get(alias) ?? new Set<string>()
    ids.add(paper.id); candidates.set(alias, ids)
  }
  return new Map([...candidates].filter(([, ids]) => ids.size === 1).map(([alias, ids]) => [alias, [...ids][0]]))
}

export function citationInfo(markdown: string, knownIds: Map<string, string>) {
  const body = markdown.split(/^(?:#{1,6}[ \t]*|\*\*[ \t]*)(?:\d+[.)、][ \t]*)?(?:参考文献|References|Bibliography)(?:[ \t]|\*|：|:|$).*$/im)[0].replace(/```[\s\S]*?```|`[^`]*`/g, '')
  const ids = new Set<string>()
  let incomplete = /\[\d+(?:[,，–\-\s]\d+)*\]/.test(body)
  for (const match of body.matchAll(/\[([^\]\n]+)\]/g)) {
    const label = match[1].trim()
    const alias = label.replace(/^Source\s+/i, '')
    const id = knownIds.get(alias)
    if (id) ids.add(id)
    else if (/^(Source\s|arxiv:|crossref:|pubmed:|s2:|semantic_scholar:|10\.\d{4,9}\/)/i.test(label)) incomplete = true
  }
  return { ids, incomplete }
}

export function resultPapers(result: Data): { papers: Paper[]; citationIncomplete: boolean } {
  const metadata = new Map<string, Data>()
  for (const paper of [...items(result.papers), ...items(result.selected_papers)]) {
    const id = text(paper.source_id)
    if (id) metadata.set(id, paper)
  }
  const notes = new Map<string, string>()
  for (const insight of items(result.paper_insights)) {
    const id = text(insight.source)
    const answer = text(insight.answer).trim()
    if (id && answer) notes.set(id, answer)
  }
  const papers: Paper[] = [...notes].map(([id, note]) => {
    const paper = metadata.get(id) ?? {}
    const authors = Array.isArray(paper.authors) ? paper.authors.map(author => typeof author === 'string' ? author : text(data(author).name)).filter(Boolean).join(', ') : text(paper.authors)
    const rawAbstract = text(paper.abstract)
    const abstract = rawAbstract.includes('<jats:') ? rawAbstract.replace(/<\/?[A-Za-z][\w:.-]*(?:\s[^>]*)?\/?>/g, ' ').replace(/\s+/g, ' ').trim() : rawAbstract
    const date = text(paper.published_date)
    const doi = text(paper.doi).replace(/^https?:\/\/(?:dx\.)?doi\.org\//, '')
    return {
      id, title: text(paper.title, id) || id, authors: authors || '作者未知',
      year: Number(date.slice(0, 4)) || 0, venue: text(paper.venue) || text(paper.source) || '来源未知',
      source: text(paper.source), abstract: abstract || '暂无摘要',
      description: abstract ? abstract.slice(0, 180) : note.slice(0, 180), cited: false,
      citationAliases: doi ? [doi] : [],
      url: safePaperUrl(paper.pdf_url) ?? (doi ? safePaperUrl(`https://doi.org/${doi}`) : undefined),
    }
  })
  const citations = citationInfo(text(result.final_answer), citationLookup(papers))
  return { papers: papers.map(paper => ({ ...paper, cited: citations.ids.has(paper.id) })), citationIncomplete: citations.incomplete }
}

function stageLines(event: Data): string[] {
  switch (event.stage) {
    case 'orchestrate': return Array.isArray(event.sub_queries) ? event.sub_queries.map((query, i) => `子问题 ${i + 1} / ${text(query)}`) : []
    case 'search': return [`去重后候选论文：${count(event.total)} 篇`, `候选来源：arXiv ${count(event.arxiv)} / Semantic Scholar ${count(event.s2)} / PubMed ${count(event.pubmed)} / Crossref ${count(event.crossref)}`]
    case 'filter': {
      const summary = data(event.summary)
      return [`入选文献：${count(event.count)} 篇`, ...Object.entries(summary).filter(([key, value]) => key in screeningLabels && typeof value === 'number').map(([key, value]) => `${screeningLabels[key]}：${value}`), ...(typeof summary.stopped_early === 'boolean' ? [`筛选结束原因：${summary.stopped_early ? '达到目标，提前结束' : '候选评估完成'}`] : [])]
    }
    case 'read': return [`阅读结果：${count(event.papers_read)} 条`, text(event.preview)].filter(Boolean)
    case 'analyze': return [`研究共识：${count(event.agreements)} 项`, `结论矛盾：${count(event.contradictions)} 项`, `研究空白：${count(event.gaps)} 项`]
    case 'synthesize': return [`草稿长度：${count(event.length)} 字符`, text(event.preview)].filter(Boolean)
    case 'critic': return [`质量评分：${String(event.score ?? '未知')}`, `评审结论：${event.approved ? '通过' : '待改进'}`, `评审轮次：${count(event.round)}`]
    default: return []
  }
}

export function eventStage(event: Data, id: string): ResearchStage | null {
  if (event.event === 'agent') return { id, agent: 'supervisor', title: '调度记录', lines: [`下一步：${text(event.next_agent)}`, text(event.objective), text(event.reason)].filter(Boolean), status: 'completed' }
  if (event.event !== 'stage') return null
  const agent = text(event.stage)
  return { id, agent, title: titles[agent] ?? agent, lines: stageLines(event), status: 'completed', resultEvent: true }
}

export function applyApiEvent(session: ResearchSession, event: ApiEvent): ResearchSession {
  const stage = eventStage(event, `${session.id}-event-${session.stages.length}`)
  const next = { ...session, requestId: text(event.request_id) || session.requestId }
  if (stage) return { ...next, stages: [...next.stages, stage], sourceCount: event.stage === 'search' ? count(event.total) : next.sourceCount }
  if (event.event !== 'done') return next
  const { papers, citationIncomplete } = resultPapers(event)
  return { ...next, status: 'completed', serverId: text(event.session_id), finalAnswer: text(event.final_answer), papers, paperCount: papers.length,
    citationIncomplete, loaded: true, warnings: Array.isArray(event.warnings) ? event.warnings.map(value => typeof value === 'string' ? value : text(data(value).message)).filter(Boolean) : [] }
}

export function historySession(record: { session_id: string; query: string; created_at: string; papers_count: number }): ResearchSession {
  return { id: record.session_id, serverId: record.session_id, title: record.query.slice(0, 26), question: record.query, createdAt: record.created_at, status: 'completed', paperCount: 0, sourceCount: record.papers_count, stages: [], loaded: false }
}

export function restoreSession(session: ResearchSession, result: Data): ResearchSession {
  const stages: ResearchStage[] = items(result.agent_trace).map((trace, index) => eventStage({ ...trace, event: 'agent' }, `${session.id}-history-${index}`)!).filter(Boolean)
  const plan = items(result.research_plan)
  if (plan.length) stages.push(eventStage({ event: 'stage', stage: 'orchestrate', sub_queries: plan.map(task => task.sub_query) }, `${session.id}-plan`)!)
  // These are summaries of stored results, not reconstructed live timestamps.
  if (Array.isArray(result.selected_papers)) stages.push(eventStage({ event: 'stage', stage: 'filter', count: result.selected_papers.length, summary: result.screening_summary }, `${session.id}-filter`)!)
  if (Array.isArray(result.paper_insights)) stages.push(eventStage({ event: 'stage', stage: 'read', papers_read: result.paper_insights.length }, `${session.id}-read`)!)
  const analysis = data(result.analysis)
  if (Object.keys(analysis).length) stages.push(eventStage({ event: 'stage', stage: 'analyze', agreements: items(analysis.agreements).length, contradictions: items(analysis.contradictions).length, gaps: items(analysis.gaps).length }, `${session.id}-analysis`)!)
  return applyApiEvent({ ...session, stages }, { ...result, event: 'done', session_id: session.serverId ?? session.id })
}
