import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { formatDate, getPapers, makeInitialSessions, makeStages } from './data/demo'
import { applyResearchEvent, startMockResearch } from './services/mockResearch'
import type { DemoSettings, Paper, ResearchSession } from './types'
import { Dialog } from './components/Dialog'
import { PaperPanel } from './components/PaperPanel'
import { PaperResizeHandle } from './components/PaperResizeHandle'
import { SidebarResizeHandle } from './components/SidebarResizeHandle'
import { PixelIcon, Wordmark } from './components/PixelIcon'
import { MarkdownContent, Report, reportMarkdown } from './components/Report'
import { SettingsDialog } from './components/SettingsDialog'
import { ApiError, apiJson, followup, loadHistory, loadMessages, loadSession, startResearch } from './services/apiClient'
import { applyApiEvent, historySession, restoreSession } from './services/researchAdapter'
import { ResearchTimeline } from './components/ResearchTimeline'
import { ResearchPrompt } from './components/ResearchPrompt'
import { Sidebar } from './components/Sidebar'
import { HomePage } from './components/HomePage'
import { DocumentationDialog } from './components/DocumentationDialog'
import { usePageNavigation } from './hooks/usePageNavigation'

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
const demo = new URLSearchParams(window.location.search).get('demo') === '1'
interface ChatState { busy: boolean; messageId: string; message: string; error?: string }

export default function App() {
  const { page, navigate } = usePageNavigation()
  const [sessions, setSessions] = useState<ResearchSession[]>(() => demo ? makeInitialSessions() : [])
  const [activeId, setActiveId] = useState<string | null>(demo ? 'demo-0' : null)
  const [prompt, setPrompt] = useState('')
  const [expandedIds, setExpandedIds] = useState<Set<string>>(() => new Set())
  const [papersOpen, setPapersOpen] = useState(() => !window.matchMedia('(max-width: 1000px)').matches)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [sidebarWidth, setSidebarWidth] = useState<number>()
  const [paperWidth, setPaperWidth] = useState<number>()
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [documentationOpen, setDocumentationOpen] = useState(false)
  const [homeEntryMotion, setHomeEntryMotion] = useState(false)
  const [sourcePaper, setSourcePaper] = useState<Paper | null>(null)
  const [highlightedPaper, setHighlightedPaper] = useState<string | null>(null)
  const [settings, setSettings] = useState<DemoSettings>(initialSettings)
  const [notice, setNotice] = useState('')
  const [connection, setConnection] = useState(demo ? '本地演示' : '正在连接后端…')
  const [viewError, setViewError] = useState('')
  const [chatStates, setChatStates] = useState<Record<string, ChatState>>({})
  const narrow = useNarrowScreen()
  const runningTimers = useRef(new Map<string, () => void>())
  const requests = useRef(new Map<string, AbortController>())
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  const sidebarRef = useRef<HTMLElement>(null)
  const expandSidebarRef = useRef<HTMLButtonElement>(null)
  const activeSession = sessions.find(session => session.id === activeId) ?? null
  const isRunning = activeSession?.status === 'running'
  const hasReport = activeSession?.status === 'completed' && activeSession.loaded !== false
  const papers = hasReport && activeSession ? demo ? getPapers(activeSession) : activeSession.papers ?? [] : []
  const chatState = activeId ? chatStates[activeId] : undefined
  const busy = isRunning || Boolean(chatState?.busy) || (activeSession?.loaded === false && activeSession.status !== 'failed')

  useEffect(() => {
    const timers = runningTimers.current
    const controllers = requests.current
    return () => { timers.forEach(stop => stop()); timers.clear(); controllers.forEach(controller => controller.abort()); controllers.clear() }
  }, [])

  useEffect(() => {
    if (demo) return
    const controller = new AbortController()
    async function connect() {
      try {
        await apiJson('/health', { signal: controller.signal })
        if (controller.signal.aborted) return
        setConnection('后端已连接')
        const history = await loadHistory(controller.signal)
        if (controller.signal.aborted) return
        setSessions(current => {
          const known = new Set(current.map(session => session.serverId ?? session.id))
          return [...current, ...history.filter(record => !known.has(record.session_id)).map(historySession)]
        })
      } catch (reason) {
        if (!controller.signal.aborted) setConnection((reason instanceof Error ? reason.message : '连接失败。') + (reason instanceof ApiError && reason.errorId ? ` 追踪编号：${reason.errorId}` : ''))
      }
    }
    void connect()
    return () => controller.abort()
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
    setViewError('')
    setPapersOpen(false)
    contentRef.current?.scrollTo({ top: 0 })
  }

  async function selectSession(id: string) {
    resetView(id)
    const session = sessions.find(item => item.id === id)
    if (demo || !session || session.loaded !== false) return
    const controller = new AbortController()
    requests.current.get(`detail-${id}`)?.abort()
    requests.current.set(`detail-${id}`, controller)
    try {
      const [detail, messages] = await Promise.all([loadSession(session.serverId ?? id, controller.signal), loadMessages(session.serverId ?? id, controller.signal)])
      if (controller.signal.aborted) return
      setSessions(current => current.map(item => item.id === id ? { ...restoreSession(item, detail.result), messages } : item))
    } catch (reason) {
      if (!controller.signal.aborted) {
        setSessions(current => current.map(item => item.id === id ? { ...item, status: 'failed', loaded: false, errorMessage: reason instanceof Error ? reason.message : '历史读取失败。', errorId: reason instanceof ApiError ? reason.errorId : undefined } : item))
      }
    } finally { if (requests.current.get(`detail-${id}`) === controller) requests.current.delete(`detail-${id}`) }
  }

  function newResearch() {
    navigate('research')
    resetView(null)
    window.requestAnimationFrame(() => inputRef.current?.focus())
  }

  useEffect(() => {
    if (!homeEntryMotion) return
    const timer = window.setTimeout(() => setHomeEntryMotion(false), 400)
    return () => window.clearTimeout(timer)
  }, [homeEntryMotion])

  function startFromHome(question: string) {
    setHomeEntryMotion(!window.matchMedia('(prefers-reduced-motion: reduce)').matches && !document.hidden)
    beginResearch(question)
  }

  function beginResearch(question: string, options = settings, previousQuestion?: string) {
    const cleaned = question.trim()
    if (!cleaned) return
    navigate('research')
    const id = `run-${crypto.randomUUID()}`
    const template: ResearchSession = {
      id, question: cleaned, title: cleaned.length > 26 ? `${cleaned.slice(0, 26)}…` : cleaned,
      createdAt: new Date().toISOString(), status: 'running', paperCount: options.paperCount, sourceCount: 93,
      stages: demo ? makeStages(cleaned, options.paperCount) : [], previousQuestion,
      ...(demo ? {} : { loaded: true, sourceCount: 0, paperCount: 0 }),
    }
    setSessions(current => [{ ...template, stages: template.stages.map(stage => ({ ...stage, lines: [] })) }, ...current])
    resetView(id)
    setExpandedIds(current => new Set(current).add(id))
    if (!demo) {
      const controller = new AbortController()
      requests.current.set(id, controller)
      void startResearch(cleaned, options.paperCount, controller.signal, event => {
        setSessions(current => current.map(session => session.id === id ? applyApiEvent(session, event) : session))
        if (event.event === 'done') {
          setExpandedIds(current => { const next = new Set(current); next.delete(id); return next })
          setConnection('后端已连接')
        }
      }).catch(reason => {
        if (controller.signal.aborted) return
        setSessions(current => current.map(session => session.id === id ? { ...session, status: 'failed', errorMessage: reason instanceof Error ? reason.message : '研究失败。', errorId: reason instanceof ApiError ? reason.errorId : undefined, requestId: reason instanceof ApiError ? reason.requestId ?? session.requestId : session.requestId } : session))
      }).finally(() => requests.current.delete(id))
      return
    }
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
    if (busy || !prompt.trim()) return
    if (hasReport && activeSession && !demo) void sendFollowup(activeSession, prompt.trim(), crypto.randomUUID())
    else if (prompt.trim().length > 2000) setViewError('新研究问题最多 2000 字。')
    else beginResearch(prompt, settings, hasReport ? activeSession?.question : undefined)
  }

  async function sendFollowup(session: ResearchSession, message: string, messageId: string) {
    setPrompt(''); setViewError('')
    setChatStates(current => ({ ...current, [session.id]: { busy: true, messageId, message } }))
    setSessions(current => current.map(item => item.id !== session.id ? item : { ...item, messages: item.messages?.some(entry => entry.message_id === messageId) ? item.messages : [...(item.messages ?? []), { message_id: messageId, role: 'user', content: message, citations: [] }] }))
    const controller = new AbortController()
    requests.current.set(`chat-${session.id}`, controller)
    try {
      const answer = await followup(session.serverId ?? session.id, message, messageId, controller.signal)
      if (controller.signal.aborted) return
      setSessions(current => current.map(item => item.id !== session.id ? item : { ...item, messages: [...(item.messages ?? []).filter(entry => entry.message_id !== `${messageId}-assistant`), { message_id: `${messageId}-assistant`, role: 'assistant', content: answer.answer, citations: answer.citations }] }))
      setChatStates(current => ({ ...current, [session.id]: { busy: false, messageId, message } }))
    } catch (reason) {
      if (!controller.signal.aborted) setChatStates(current => ({ ...current, [session.id]: { busy: false, messageId, message, error: (reason instanceof Error ? reason.message : '追问失败。') + (reason instanceof ApiError && reason.errorId ? ` 追踪编号：${reason.errorId}` : '') } }))
    } finally { requests.current.delete(`chat-${session.id}`) }
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
    requests.current.get(activeSession.id)?.abort()
    requests.current.delete(activeSession.id)
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
    const references = demo ? getPapers(activeSession).map((paper, index) => `[${index + 1}] ${paper.title}. ${paper.authors}, ${paper.year}, ${paper.venue}. ${paper.cited ? '示例引用文献' : '示例阅读文献'}`).join('\n\n') : ''
    const blob = new Blob([`${reportMarkdown(activeSession)}${demo ? `\n## 参考文献（示例）\n\n${references}\n` : ''}`], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `B1GONE-研究综述-${formatDate(activeSession.createdAt).slice(0, 10)}.md`
    link.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    setNotice(demo ? '示例综述已导出' : '研究综述已导出')
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

  function goHome() {
    setSidebarOpen(false)
    setSourcePaper(null)
    setDocumentationOpen(false)
    setSettingsOpen(false)
    navigate('home')
  }

  const sidebar = <Sidebar demo={demo} sessions={sessions} activeId={activeId} onSelect={id => void selectSession(id)} onNew={newResearch} onSettings={() => { setSidebarOpen(false); setSettingsOpen(true) }} onCollapse={collapseSidebar} onHome={goHome} />
  const panel = <PaperPanel demo={demo} papers={papers} citationIncomplete={activeSession?.citationIncomplete} onClose={() => setPapersOpen(false)} highlightedPaper={highlightedPaper} onSource={setSourcePaper} />
  const showDesktopPapers = papersOpen && hasReport && !narrow

  return <div className={page === 'home' ? 'home-app' : `app-shell ${showDesktopPapers ? 'with-papers' : ''} ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
    {page === 'home' ? <HomePage onStart={startFromHome} onWorkspace={newResearch} onSettings={() => setSettingsOpen(true)} onDocumentation={() => setDocumentationOpen(true)} suspended={settingsOpen || documentationOpen} /> : <>
    <a className="skip-link" href="#workspace">跳到研究内容</a>
    <aside ref={sidebarRef} className="desktop-sidebar" aria-label="侧边栏">
      {sidebarCollapsed ? <div className="collapsed-sidebar"><button ref={expandSidebarRef} className="icon-button" onClick={expandSidebar} aria-label="展开侧边栏" aria-expanded="false" aria-controls="desktop-sidebar-content" title="展开侧边栏"><PixelIcon name="expand" /></button></div> : null}
      <div id="desktop-sidebar-content" hidden={sidebarCollapsed}>{sidebar}</div>
      {!sidebarCollapsed ? <SidebarResizeHandle preferredWidth={sidebarWidth} papersVisible={showDesktopPapers} onWidthChange={setSidebarWidth} /> : null}
    </aside>
    <main id="workspace" className={'workspace' + (homeEntryMotion ? ' home-research-entry' : '')} tabIndex={-1}>
      {homeEntryMotion ? <span className="home-entry-line" aria-hidden="true" /> : null}
      <div className="mobile-toolbar"><button className="icon-button" onClick={() => setSidebarOpen(true)} aria-label="打开研究记录"><PixelIcon name="menu" /></button><button className="brand-home-button" onClick={goHome} aria-label="返回首页"><Wordmark /></button><button className="icon-button" onClick={newResearch} aria-label="新建研究"><PixelIcon name="plus" /></button></div>
      <div className="workspace-scroll" ref={contentRef}>
        {!demo && !['后端已连接', '正在连接后端…'].includes(connection) ? <p className="connection-error" role="alert">{connection}<button onClick={() => window.location.reload()}>重新连接</button></p> : null}
        {viewError ? <p className="connection-error" role="alert">{viewError}</p> : null}
        {activeSession ? <>
          <div className="user-question"><span className="user-avatar"><PixelIcon name="user" /></span><div><p>{activeSession.question}</p>{activeSession.previousQuestion ? <span className="followup-note">继续追问 · {activeSession.previousQuestion}</span> : null}</div></div>
          <ResearchTimeline session={activeSession} expanded={expandedIds.has(activeSession.id)} onToggle={toggleTimeline} />
          {hasReport ? <Report session={activeSession} onCitation={openCitation} /> : null}
          {!demo && activeSession.loaded === false && activeSession.status !== 'failed' ? <p role="status">读取历史研究中…</p> : null}
          {!demo && hasReport ? <section className="followup-messages" aria-label="研究追问">{activeSession.messages?.filter(message => !message.message_id.startsWith(`${activeSession.serverId ?? activeSession.id}:initial:`)).map(message => <div key={message.message_id} className={`chat-message chat-${message.role}`}><h3>{message.role === 'user' ? '追问' : '回答'}</h3><MarkdownContent content={message.content} papers={papers} onCitation={openCitation} /></div>)}{chatState?.busy ? <p role="status">正在依据当前研究回答…</p> : null}{chatState?.error ? <div className="error-panel" role="alert"><p>{chatState.error}</p><button className="key-button" onClick={() => void sendFollowup(activeSession, chatState.message, chatState.messageId)}>重试追问</button></div> : null}</section> : null}
          {isRunning ? <div className="running-hint" role="status">正在整理研究证据，阶段记录会逐行更新。</div> : null}
          {activeSession.status === 'failed' ? <section className="error-panel" role="alert"><div className="error-title"><PixelIcon name="close" /><h1>研究任务中断</h1></div><p>{activeSession.errorMessage ?? '跨论文分析未获得完整结果。已完成的搜索、筛选和阅读记录保留在研究过程中。'}</p>{activeSession.errorId ? <div className="trace-row"><span>追踪编号</span><code>{activeSession.errorId}</code><button className="icon-button" onClick={copyError} aria-label="复制追踪编号"><PixelIcon name="copy" /></button></div> : null}{activeSession.requestId ? <p className="request-trace">请求编号：{activeSession.requestId}</p> : null}<button className="key-button" onClick={() => activeSession.loaded === false ? void selectSession(activeSession.id) : beginResearch(activeSession.question, { ...settings, outcome: 'success' })}>{activeSession.loaded === false ? '重新读取历史' : '重试研究'}</button>{demo ? <p className="error-demo-note">这是原型的失败示例，可在设置中切换演示结果。</p> : <p className="error-demo-note">当前页面保留已收到的过程记录；失败任务未写入历史。</p>}</section> : null}
          {activeSession.status === 'cancelled' ? <section className="error-panel cancelled-panel"><h1>{demo ? '研究已停止' : '已停止接收研究结果'}</h1><p>{demo ? '当前进度已保留，可以展开研究过程查看。' : '连接已断开，后端按现有流清理机制处理。当前记录仅保留在本页，未取得服务器取消确认。'}</p><button className="key-button" onClick={() => beginResearch(activeSession.question)}>重新研究</button></section> : null}
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
          <ResearchPrompt inputRef={inputRef} value={prompt} onChange={event => setPrompt(event.target.value)} onKeyDown={inputKeyDown} maxLength={hasReport ? 4000 : 2000} disabled={busy} followup={hasReport} suspended={settingsOpen || sidebarOpen || Boolean(sourcePaper) || (narrow && papersOpen && hasReport)}
            placeholder={isRunning ? '研究正在进行中… |<' : chatState?.busy ? '正在回答追问… |<' : hasReport ? demo ? '继续追问，或输入新的研究问题… |<' : '继续追问当前研究… |<' : '输入你的研究问题… |<'} />
          {isRunning ? <button className="key-button submit-button" type="button" onClick={stopResearch}><PixelIcon name="stop" /><span>停止</span></button> : <button className="key-button submit-button" type="submit" disabled={!prompt.trim() || busy}><PixelIcon name="enter" /><span>提交</span></button>}
        </form>
        {!hasReport ? <p className="composer-hint">Enter 提交 · Shift + Enter 换行<span>{connection}</span></p> : null}
      </div>
    </main>
    {showDesktopPapers ? <aside id="research-paper-panel" className="paper-panel" aria-labelledby="papers-heading"><PaperResizeHandle preferredWidth={paperWidth} onWidthChange={setPaperWidth} />{panel}</aside> : null}

    <Dialog open={sidebarOpen} onClose={() => setSidebarOpen(false)} labelId="mobile-history-heading" className="sidebar-dialog">
      <h2 id="mobile-history-heading" className="sr-only">研究记录</h2><Sidebar demo={demo} sessions={sessions} activeId={activeId} onSelect={id => void selectSession(id)} onNew={newResearch} onSettings={() => { setSidebarOpen(false); setSettingsOpen(true) }} onClose={() => setSidebarOpen(false)} onHome={goHome} />
    </Dialog>
    {narrow ? <Dialog open={papersOpen && Boolean(hasReport)} onClose={() => setPapersOpen(false)} labelId="papers-heading" className="papers-dialog">{papersOpen && hasReport ? <PaperResizeHandle preferredWidth={paperWidth} onWidthChange={setPaperWidth} /> : null}{panel}</Dialog> : null}
    </>}
    <DocumentationDialog open={documentationOpen} onClose={() => setDocumentationOpen(false)} onWorkspace={() => { setDocumentationOpen(false); navigate('research') }} />
    {settingsOpen ? <SettingsDialog onClose={() => setSettingsOpen(false)} paperCount={settings.paperCount} onPaperCount={paperCount => setSettings(current => ({ ...current, paperCount }))}>
      {demo ? <details className="settings-group">
        <summary>演示选项</summary>
        <p className="settings-detail">研究使用示例报告与文献，在浏览器本地模拟；环境配置仍通过下方表单保存到本机后端。</p>
        <label className="setting-field"><span>演示时长</span><select value={settings.duration} onChange={event => setSettings(current => ({ ...current, duration: Number(event.target.value) }))}><option value={6}>快速 · 6 秒</option><option value={12}>标准 · 12 秒</option><option value={24}>慢速 · 24 秒</option></select></label>
        <label className="setting-field"><span>演示结果</span><select value={settings.outcome} onChange={event => setSettings(current => ({ ...current, outcome: event.target.value as DemoSettings['outcome'] }))}><option value="success">完成研究</option><option value="failure">模拟分析失败</option></select></label>
      </details> : null}
    </SettingsDialog> : null}
    <Dialog open={Boolean(sourcePaper)} onClose={() => setSourcePaper(null)} labelId="source-heading" className="source-dialog">
      <div className="dialog-heading"><h2 id="source-heading">论文原文</h2><button className="icon-button" onClick={() => setSourcePaper(null)} aria-label="关闭论文原文"><PixelIcon name="close" /></button></div>
      <h3>{sourcePaper?.title}</h3><p>这是一条界面演示文献，暂时没有真实原文链接。</p><p>接入后端后，这里会打开论文原文或 PDF。</p><button className="key-button dialog-done" onClick={() => setSourcePaper(null)}>返回文献</button>
    </Dialog>
    <div className={`toast ${notice ? 'toast-visible' : ''}`} role="status" aria-live="polite">{notice}</div>
  </div>
}
