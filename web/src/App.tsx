import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { formatDate, getPapers, makeInitialSessions, makeStages } from './data/demo'
import { applyResearchEvent, startMockResearch } from './services/mockResearch'
import type { DemoSettings, Paper, ResearchSession } from './types'
import { Dialog } from './components/Dialog'
import { PaperPanel } from './components/PaperPanel'
import { PaperResizeHandle } from './components/PaperResizeHandle'
import { PixelIcon, Wordmark } from './components/PixelIcon'
import { Report, reportMarkdown } from './components/Report'
import { ResearchTimeline } from './components/ResearchTimeline'
import { Sidebar } from './components/Sidebar'

function useNarrowScreen() {
  const [narrow, setNarrow] = useState(() => window.matchMedia('(max-width: 1000px)').matches)
  useEffect(() => {
    const query = window.matchMedia('(max-width: 1000px)')
    const update = () => setNarrow(query.matches)
    query.addEventListener('change', update)
    return () => query.removeEventListener('change', update)
  }, [])
  return narrow
}

const suggestions = ['比较现有方法、研究共识与研究空白', '梳理大语言模型在科学研究中的应用', '分析检索增强方法的优势与局限']
const initialSettings: DemoSettings = { duration: 12, outcome: 'success', paperCount: 15 }

export default function App() {
  const [sessions, setSessions] = useState(makeInitialSessions)
  const [activeId, setActiveId] = useState<string | null>('demo-0')
  const [prompt, setPrompt] = useState('')
  const [expandedIds, setExpandedIds] = useState<Set<string>>(() => new Set())
  const [papersOpen, setPapersOpen] = useState(() => !window.matchMedia('(max-width: 1000px)').matches)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [paperWidth, setPaperWidth] = useState<number>()
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [sourcePaper, setSourcePaper] = useState<Paper | null>(null)
  const [highlightedPaper, setHighlightedPaper] = useState<string | null>(null)
  const [settings, setSettings] = useState<DemoSettings>(initialSettings)
  const [notice, setNotice] = useState('')
  const narrow = useNarrowScreen()
  const runningTimers = useRef(new Map<string, () => void>())
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  const sidebarRef = useRef<HTMLElement>(null)
  const expandSidebarRef = useRef<HTMLButtonElement>(null)
  const activeSession = sessions.find(session => session.id === activeId) ?? null
  const isRunning = activeSession?.status === 'running'
  const hasReport = activeSession?.status === 'completed'
  const papers = hasReport && activeSession ? getPapers(activeSession) : []

  useEffect(() => {
    const timers = runningTimers.current
    return () => { timers.forEach(stop => stop()); timers.clear() }
  }, [])

  useEffect(() => {
    if (!notice) return
    const timer = window.setTimeout(() => setNotice(''), 3200)
    return () => window.clearTimeout(timer)
  }, [notice])

  function resetView(id: string | null) {
    setActiveId(id)
    setPrompt('')
    setSidebarOpen(false)
    setHighlightedPaper(null)
    setPapersOpen(false)
    contentRef.current?.scrollTo({ top: 0 })
  }

  function newResearch() {
    resetView(null)
    window.requestAnimationFrame(() => inputRef.current?.focus())
  }

  function beginResearch(question: string, options = settings, previousQuestion?: string) {
    const cleaned = question.trim()
    if (!cleaned) return
    const id = `run-${crypto.randomUUID()}`
    const template: ResearchSession = {
      id, question: cleaned, title: cleaned.length > 26 ? `${cleaned.slice(0, 26)}…` : cleaned,
      createdAt: new Date().toISOString(), status: 'running', paperCount: options.paperCount, sourceCount: 93,
      stages: makeStages(cleaned, options.paperCount), previousQuestion,
    }
    setSessions(current => [{ ...template, stages: template.stages.map(stage => ({ ...stage, lines: [] })) }, ...current])
    resetView(id)
    setExpandedIds(current => new Set(current).add(id))
    const stop = startMockResearch(template, options, event => {
      setSessions(current => current.map(session => session.id === id ? applyResearchEvent(session, event) : session))
      if (event.type === 'research.completed' || event.type === 'research.failed') {
        runningTimers.current.delete(id)
        if (event.type === 'research.completed') setExpandedIds(current => { const next = new Set(current); next.delete(id); return next })
      }
    })
    runningTimers.current.set(id, stop)
  }

  function submit(event?: FormEvent) {
    event?.preventDefault()
    if (!isRunning) beginResearch(prompt, settings, hasReport ? activeSession?.question : undefined)
  }

  function inputKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      submit()
    }
  }

  function stopResearch() {
    if (!activeSession) return
    runningTimers.current.get(activeSession.id)?.()
    runningTimers.current.delete(activeSession.id)
    setSessions(current => current.map(session => session.id === activeSession.id ? {
      ...session, status: 'cancelled',
      stages: session.stages.map(stage => stage.status !== 'completed' ? { ...stage, status: 'cancelled' } : stage),
    } : session))
  }

  function toggleTimeline() {
    if (!activeId) return
    setExpandedIds(current => { const next = new Set(current); if (next.has(activeId)) next.delete(activeId); else next.add(activeId); return next })
  }

  function openCitation(id: string) {
    setHighlightedPaper(id)
    setPapersOpen(true)
  }

  function exportReport() {
    if (!activeSession || !hasReport) return
    const references = getPapers(activeSession).map((paper, index) => `[${index + 1}] ${paper.title}. ${paper.authors}, ${paper.year}, ${paper.venue}. ${paper.cited ? '示例引用文献' : '示例阅读文献'}`).join('\n\n')
    const blob = new Blob([`${reportMarkdown(activeSession)}\n## 参考文献（示例）\n\n${references}\n`], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `B1GONE-研究综述-${formatDate(activeSession.createdAt).slice(0, 10)}.md`
    link.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    setNotice('示例综述已导出')
  }

  async function copyError() {
    if (!activeSession?.errorId) return
    try { await navigator.clipboard.writeText(activeSession.errorId); setNotice('追踪编号已复制') }
    catch { setNotice('请选中追踪编号手动复制') }
  }

  function collapseSidebar() {
    setSidebarCollapsed(true)
    window.requestAnimationFrame(() => expandSidebarRef.current?.focus())
  }

  function expandSidebar() {
    setSidebarCollapsed(false)
    window.requestAnimationFrame(() => sidebarRef.current?.querySelector<HTMLButtonElement>('.sidebar-collapse')?.focus())
  }

  const sidebar = <Sidebar sessions={sessions} activeId={activeId} onSelect={resetView} onNew={newResearch} onSettings={() => { setSidebarOpen(false); setSettingsOpen(true) }} onCollapse={collapseSidebar} />
  const panel = <PaperPanel papers={papers} onClose={() => setPapersOpen(false)} highlightedPaper={highlightedPaper} onSource={setSourcePaper} />
  const showDesktopPapers = papersOpen && hasReport && !narrow

  return <div className={`app-shell ${showDesktopPapers ? 'with-papers' : ''} ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
    <a className="skip-link" href="#workspace">跳到研究内容</a>
    <aside ref={sidebarRef} className="desktop-sidebar" aria-label="侧边栏">
      {sidebarCollapsed ? <div className="collapsed-sidebar"><button ref={expandSidebarRef} className="icon-button" onClick={expandSidebar} aria-label="展开侧边栏" aria-expanded="false" aria-controls="desktop-sidebar-content" title="展开侧边栏"><PixelIcon name="expand" /></button></div> : null}
      <div id="desktop-sidebar-content" hidden={sidebarCollapsed}>{sidebar}</div>
    </aside>
    <main id="workspace" className="workspace" tabIndex={-1}>
      <div className="mobile-toolbar"><button className="icon-button" onClick={() => setSidebarOpen(true)} aria-label="打开研究记录"><PixelIcon name="menu" /></button><Wordmark /><button className="icon-button" onClick={newResearch} aria-label="新建研究"><PixelIcon name="plus" /></button></div>
      <div className="workspace-scroll" ref={contentRef}>
        {activeSession ? <>
          <div className="user-question"><span className="user-avatar"><PixelIcon name="user" /></span><div><p>{activeSession.question}</p>{activeSession.previousQuestion ? <span className="followup-note">继续追问 · {activeSession.previousQuestion}</span> : null}</div></div>
          <ResearchTimeline session={activeSession} expanded={expandedIds.has(activeSession.id)} onToggle={toggleTimeline} />
          {hasReport ? <Report session={activeSession} onCitation={openCitation} /> : null}
          {isRunning ? <div className="running-hint" role="status">正在整理研究证据，阶段记录会逐行更新。</div> : null}
          {activeSession.status === 'failed' ? <section className="error-panel" role="alert"><div className="error-title"><PixelIcon name="close" /><h1>研究任务中断</h1></div><p>跨论文分析未获得完整结果。已完成的搜索、筛选和阅读记录保留在研究过程中。</p><div className="trace-row"><span>追踪编号</span><code>{activeSession.errorId}</code><button className="icon-button" onClick={copyError} aria-label="复制追踪编号"><PixelIcon name="copy" /></button></div><button className="key-button" onClick={() => beginResearch(activeSession.question, { ...settings, outcome: 'success' })}>重试研究</button><p className="error-demo-note">这是原型的失败示例，可在设置中切换演示结果。</p></section> : null}
          {activeSession.status === 'cancelled' ? <section className="error-panel cancelled-panel"><h1>研究已停止</h1><p>当前进度已保留，可以展开研究过程查看。</p><button className="key-button" onClick={() => beginResearch(activeSession.question)}>重新研究</button></section> : null}
        </> : <section className="welcome" aria-label="新建研究">
          <div className="welcome-symbol" aria-hidden="true"><span>[</span><PixelIcon name="archive" /><span>]</span></div>
          <h1>从一个问题开始。</h1>
          <p>搜索文献，比较证据，形成你的研究综述。</p>
          <div className="suggestion-list">{suggestions.map(question => <button key={question} onClick={() => { setPrompt(question); inputRef.current?.focus() }}><span>{question}</span><PixelIcon name="enter" /></button>)}</div>
          <p className="welcome-note">输入研究问题，查看每一步如何展开。</p>
        </section>}
      </div>
      <div className="workspace-footer">
        {hasReport ? <div className="report-actions"><button className="key-button" onClick={() => { setHighlightedPaper(null); setPapersOpen(!papersOpen) }} aria-expanded={papersOpen}><PixelIcon name="archive" /><span>研究文献 · {papers.length}</span><PixelIcon name="chevron" /></button><button className="key-button" onClick={exportReport}><PixelIcon name="download" /><span>导出综述</span></button></div> : null}
        <form className="composer" onSubmit={submit}>
          <label className="sr-only" htmlFor="research-prompt">研究问题</label>
          <textarea id="research-prompt" ref={inputRef} value={prompt} onChange={event => setPrompt(event.target.value)} onKeyDown={inputKeyDown} rows={1} maxLength={4000} disabled={isRunning}
            placeholder={isRunning ? '研究正在进行中… |<' : activeSession ? '继续追问，或输入新的研究问题… |<' : '输入你的研究问题… |<'} />
          {isRunning ? <button className="key-button submit-button" type="button" onClick={stopResearch}><PixelIcon name="stop" /><span>停止</span></button> : <button className="key-button submit-button" type="submit" disabled={!prompt.trim()}><PixelIcon name="enter" /><span>提交</span></button>}
        </form>
        {!hasReport ? <p className="composer-hint">Enter 提交 · Shift + Enter 换行<span>本地演示</span></p> : null}
      </div>
    </main>
    {showDesktopPapers ? <aside id="research-paper-panel" className="paper-panel" aria-labelledby="papers-heading"><PaperResizeHandle preferredWidth={paperWidth} onWidthChange={setPaperWidth} />{panel}</aside> : null}

    <Dialog open={sidebarOpen} onClose={() => setSidebarOpen(false)} labelId="mobile-history-heading" className="sidebar-dialog">
      <h2 id="mobile-history-heading" className="sr-only">研究记录</h2><Sidebar sessions={sessions} activeId={activeId} onSelect={resetView} onNew={newResearch} onSettings={() => { setSidebarOpen(false); setSettingsOpen(true) }} onClose={() => setSidebarOpen(false)} />
    </Dialog>
    {narrow ? <Dialog open={papersOpen && Boolean(hasReport)} onClose={() => setPapersOpen(false)} labelId="papers-heading" className="papers-dialog">{papersOpen && hasReport ? <PaperResizeHandle preferredWidth={paperWidth} onWidthChange={setPaperWidth} /> : null}{panel}</Dialog> : null}
    <Dialog open={settingsOpen} onClose={() => setSettingsOpen(false)} labelId="settings-heading" className="settings-dialog">
      <div className="dialog-heading"><h2 id="settings-heading">原型设置</h2><button className="icon-button" onClick={() => setSettingsOpen(false)} aria-label="关闭设置"><PixelIcon name="close" /></button></div>
      <p className="dialog-intro">调整下一次研究的演示方式。</p>
      <label className="setting-field"><span>目标阅读数量</span><select value={settings.paperCount} onChange={event => setSettings({ ...settings, paperCount: Number(event.target.value) })}><option value={5}>5 篇</option><option value={10}>10 篇</option><option value={15}>15 篇</option></select></label>
      <label className="setting-field"><span>演示时长</span><select value={settings.duration} onChange={event => setSettings({ ...settings, duration: Number(event.target.value) })}><option value={6}>快速 · 6 秒</option><option value={12}>标准 · 12 秒</option><option value={24}>慢速 · 24 秒</option></select></label>
      <label className="setting-field"><span>演示结果</span><select value={settings.outcome} onChange={event => setSettings({ ...settings, outcome: event.target.value as DemoSettings['outcome'] })}><option value="success">完成研究</option><option value="failure">模拟分析失败</option></select></label>
      <p className="settings-note">当前使用示例报告与文献；所有研究在浏览器本地模拟。</p>
      <button className="key-button dialog-done" onClick={() => setSettingsOpen(false)}>完成</button>
    </Dialog>
    <Dialog open={Boolean(sourcePaper)} onClose={() => setSourcePaper(null)} labelId="source-heading" className="source-dialog">
      <div className="dialog-heading"><h2 id="source-heading">论文原文</h2><button className="icon-button" onClick={() => setSourcePaper(null)} aria-label="关闭论文原文"><PixelIcon name="close" /></button></div>
      <h3>{sourcePaper?.title}</h3><p>这是一条界面演示文献，暂时没有真实原文链接。</p><p>接入后端后，这里会打开论文原文或 PDF。</p><button className="key-button dialog-done" onClick={() => setSourcePaper(null)}>返回文献</button>
    </Dialog>
    <div className={`toast ${notice ? 'toast-visible' : ''}`} role="status" aria-live="polite">{notice}</div>
  </div>
}
