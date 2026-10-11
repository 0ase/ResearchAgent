import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent, type CSSProperties } from 'react'
import { homeNodes, projectGitHub, type HomeNodeName } from '../data/homepage'
import { useMotionEnabled } from '../hooks/useMotionEnabled'
import { AsciiButton } from './AsciiButton'
import { AnimatedPromptHint } from './AnimatedPromptHint'
import { HomeMascot } from './HomeMascot'
import { PixelIcon, Wordmark } from './PixelIcon'
import '../homepage.css'

interface PromptPacket { x: number; y: number; distance: number; question: string }

export function HomePage({ onStart, onWorkspace, onSettings, onDocumentation, suspended = false }: {
  onStart: (question: string) => void; onWorkspace: () => void; onSettings: () => void; onDocumentation: () => void; suspended?: boolean
}) {
  const [question, setQuestion] = useState('')
  const [focused, setFocused] = useState(false)
  const [previewRole, setPreviewRole] = useState<HomeNodeName | null>(null)
  const [launching, setLaunching] = useState(false)
  const [packet, setPacket] = useState<PromptPacket | null>(null)
  const screenRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const launchLocked = useRef(false)
  const launchTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const launchAction = useRef<(() => void) | null>(null)
  const motionEnabled = useMotionEnabled(!suspended)
  const animatedPrompt = motionEnabled && !focused && !question && !launching

  function finishLaunch() {
    clearTimeout(launchTimer.current)
    launchTimer.current = undefined
    const action = launchAction.current
    launchAction.current = null
    action?.()
  }
  useEffect(() => () => { clearTimeout(launchTimer.current); launchAction.current = null }, [])
  useEffect(() => {
    if (launching && !motionEnabled) finishLaunch()
  }, [launching, motionEnabled])

  function submit(event?: FormEvent) {
    event?.preventDefault()
    const cleaned = question.trim()
    if (launchLocked.current || cleaned.length > 2000) return
    launchLocked.current = true
    if (!cleaned) { onWorkspace(); return }
    if (!motionEnabled) { onStart(cleaned); return }
    const screen = screenRef.current
    if (screen) {
      const origin = screen.getBoundingClientRect()
      const example = screen.querySelector('.home-input-example')?.getBoundingClientRect()
      const head = screen.querySelector('.home-robot-head')?.getBoundingClientRect()
      const beam = screen.querySelector('.home-input-beam')?.getBoundingClientRect()
      const mobileHead = screen.querySelector('.home-mobile-head')?.getBoundingClientRect()
      if (example?.width && head && beam) {
        const x = Math.max(20, example.left - origin.left)
        setPacket({ x, y: beam.top - origin.top - 34, distance: Math.max(40, head.left - origin.left - x + 60), question: cleaned })
      } else if (mobileHead) {
        const x = Math.max(20, mobileHead.left - origin.left - 80)
        setPacket({ x, y: mobileHead.top - origin.top + mobileHead.height / 2, distance: 100, question: cleaned })
      }
    }
    setPreviewRole(null)
    setLaunching(true)
    launchAction.current = () => onStart(cleaned)
    launchTimer.current = setTimeout(finishLaunch, 360)
  }

  function inputKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      submit()
    }
  }
  function selectQuestion(selected: string) {
    if (launchLocked.current) return
    setQuestion(selected)
    setPreviewRole(null)
    inputRef.current?.focus()
  }

  return <div ref={screenRef} className={'home-screen' + (motionEnabled ? ' home-motion-enabled' : '') + (launching ? ' is-launching' : '')}
    data-motion={motionEnabled ? 'enabled' : 'paused'} data-launch-state={launching ? 'entering' : 'idle'} aria-busy={launching}>
    <a className="skip-link" href="#home-question">跳到研究问题</a>
    <header className="home-header">
      <nav aria-label="首页导航" className="home-nav">
        <div className="home-nav-start">
          <AsciiButton label="文档" motionEnabled={motionEnabled} className="key-button home-nav-key" onClick={onDocumentation} disabled={launching}><PixelIcon name="archive" /></AsciiButton>
          <AsciiButton label="设置" motionEnabled={motionEnabled} className="key-button home-nav-key" onClick={onSettings} disabled={launching}><PixelIcon name="settings" /></AsciiButton>
        </div>
        <a className="home-github" href={projectGitHub} target="_blank" rel="noopener noreferrer" aria-label="在 GitHub 查看 B1GONE 项目" title="GitHub"><PixelIcon name="github" /></a>
      </nav>
    </header>
    <main className="home-stage">
      <section className="home-introduction" aria-labelledby="home-heading">
        <h1 className="home-brand" id="home-heading"><span aria-hidden="true"><Wordmark /></span><span className="sr-only">B1GONE 研究助手</span></h1>
        <p>拆解问题、检索文献、比较证据，<br />生成可追溯的研究综述。</p>
      </section>
      <HomeMascot focused={focused} motionEnabled={motionEnabled} launching={launching} previewRole={previewRole} onSelect={selectQuestion} />
      <form className="home-entry" onSubmit={submit} aria-label="开始新研究">
        <label className="sr-only" htmlFor="home-question">研究问题</label>
        <div className={'home-entry-input' + (animatedPrompt ? ' has-animated-hint' : '')}>
          <textarea id="home-question" ref={inputRef} value={question} onChange={event => { if (!launchLocked.current) setQuestion(event.target.value) }}
            onFocus={() => setFocused(true)} onBlur={() => setFocused(false)} disabled={launching} onKeyDown={inputKeyDown}
            maxLength={2000} rows={1} placeholder="输入研究问题，开始探索… |<" />
          {animatedPrompt ? <AnimatedPromptHint /> : null}
        </div>
        <div className="home-entry-actions"><AsciiButton label="开始研究" motionEnabled={motionEnabled} className="key-button home-start" type="submit" disabled={launching} /></div>
        {launching ? <p className="sr-only" role="status">正在进入研究工作台</p> : null}
      </form>
      <section className="home-pipeline" aria-label="研究节点职责">
        <ul>{homeNodes.map(node => <li key={node.name}>
          <button className="home-node-trigger" type="button" disabled={launching}
            aria-label={'查看 ' + node.name + ' 职能：' + node.description} aria-pressed={previewRole === node.name}
            onMouseEnter={() => setPreviewRole(node.name)} onMouseLeave={event => { if (!event.currentTarget.contains(document.activeElement)) setPreviewRole(null) }}
            onFocus={() => setPreviewRole(node.name)} onBlur={() => setPreviewRole(null)} onClick={() => setPreviewRole(node.name)}>
            <span className="home-node-icon"><PixelIcon name={node.icon} /></span>
            <span className="home-node-name">{node.name}</span>
            <span className="home-node-description">{node.description}</span>
          </button>
        </li>)}</ul>
      </section>
    </main>
    {launching && packet && motionEnabled ? <div className="home-prompt-packet" aria-hidden="true"
      style={{ left: packet.x, top: packet.y, '--packet-distance': packet.distance + 'px' } as CSSProperties}>{packet.question}</div> : null}
    <div className="home-crt-sweep" aria-hidden="true" />
  </div>
}
