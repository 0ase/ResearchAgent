import { useEffect, useState, type MouseEvent } from 'react'
import { exampleQuestions, homeNodes, type HomeNodeName } from '../data/homepage'
import { PixelIcon } from './PixelIcon'

function Eyes({ enabled, focused }: { enabled: boolean; focused: boolean }) {
  const [closed, setClosed] = useState(false)
  useEffect(() => {
    setClosed(false)
    if (!enabled) return
    let timer: ReturnType<typeof setTimeout>
    function blink() {
      setClosed(true)
      timer = setTimeout(() => { setClosed(false); timer = setTimeout(blink, 6500) }, 120)
    }
    timer = setTimeout(blink, 6500)
    return () => clearTimeout(timer)
  }, [enabled])
  const blink = enabled && closed
  return <g className="home-eyes" data-eye-state={focused ? 'look-left' : blink ? 'blink' : 'idle'} transform={focused ? 'translate(-1 0)' : undefined} fill="var(--color-keycap)">
    <path d={blink ? 'M13 24h3v1h-3v-1zm11 0h3v1h-3v-1z' : 'M13 20h3v6h-3v-6zm11 0h3v6h-3v-6z'} />
  </g>
}

function WriterCursor({ enabled }: { enabled: boolean }) {
  const [visible, setVisible] = useState(true)
  useEffect(() => {
    if (!enabled) return
    const timer = setInterval(() => setVisible(current => !current), 500)
    return () => clearInterval(timer)
  }, [enabled])
  return <rect x="27" y="23" width="1" height="4" fill="var(--color-keycap)" opacity={!enabled || visible ? 1 : 0} />
}

function RobotHead({ focused, motionEnabled, previewRole }: { focused: boolean; motionEnabled: boolean; previewRole: HomeNodeName | null }) {
  const role = homeNodes.find(node => node.name === previewRole)
  return <g shapeRendering="crispEdges">
    <path fill="#080c0d" d="M17 0h6v1h1v5h-1v1h-6V6h-1V1h1V0zM19 7h2v4h-2V7z" />
    <path className="home-antenna-light" fill="#f48022" d="M17 1h6v5h-6V1z" />
    <path fill="#080c0d" d="M0 23h5v7H0v-7zm35 0h5v7h-5v-7z" />
    <path fill="var(--color-keycap)" d="M2 24h2v5H2v-5zm34 0h2v5h-2v-5z" />
    <path fill="#080c0d" d="M9 11h22v1h2v1h1v2h1v22h-1v2h-2v1h-2v1H10v-1H8v-1H6v-2H5V15h1v-2h1v-1h2v-1z" />
    <path fill="var(--color-keycap)" d="M10 12h20v1h2v1h1v2h1v20h-1v2h-2v1h-2v1H11v-1H9v-1H7v-2H6V16h1v-2h1v-1h2v-1z" />
    <path fill="#080c0d" d="M10 18h20v1h1v9h-1v1H10v-1H9v-9h1v-1z" />
    {role ? <g className="home-visor-tool" data-role={role.name} color="var(--color-keycap)">
      <PixelIcon name={role.icon} x="14" y="19" width="12" height="9" />
      {role.name === 'writer' ? <WriterCursor enabled={motionEnabled} /> : null}
    </g> : <Eyes enabled={motionEnabled && !focused} focused={focused} />}
    <path fill="#080c0d" d="M15 32h2v2h6v-2h2v2h-2v2h-6v-2h-2v-2z" />
  </g>
}

export function HomeMascot({ focused, motionEnabled, launching, previewRole, onSelect }: {
  focused: boolean; motionEnabled: boolean; launching: boolean; previewRole: HomeNodeName | null; onSelect: (question: string) => void
}) {
  const [activeId, setActiveId] = useState<string | null>(null)
  const [launchFrame, setLaunchFrame] = useState(0)
  const [desktop, setDesktop] = useState(() => window.matchMedia('(min-width: 1100px)').matches)
  const active = launching ? undefined : exampleQuestions.find(question => question.id === activeId)
  useEffect(() => {
    const query = window.matchMedia('(min-width: 1100px)')
    const update = () => setDesktop(query.matches)
    query.addEventListener('change', update)
    return () => query.removeEventListener('change', update)
  }, [])
  useEffect(() => {
    setLaunchFrame(0)
    if (!launching || !motionEnabled) return
    const timers = [1, 2, 3].map(frame => setTimeout(() => setLaunchFrame(frame), frame * 70))
    return () => timers.forEach(clearTimeout)
  }, [launching, motionEnabled])

  function leave(event: MouseEvent<Element>) {
    if (!event.currentTarget.contains(document.activeElement)) setActiveId(null)
  }
  function select(question: string) {
    if (launching) return
    setActiveId(null)
    onSelect(question)
  }
  const shrink = launching && motionEnabled ? launchFrame / 3 : 0
  return <figure className={'home-visual' + (active ? ' has-question-preview' : '')} aria-label="研究问题拆解示例">
    <div className="home-mascot-layer">
      <svg className="home-mascot" viewBox="0 0 1000 400" role="img" aria-labelledby="home-mascot-title">
        <title id="home-mascot-title">像素机器人将 Transformer 架构近两年的创新拆解为注意力机制、高效变体、评测数据及效率与精度四个子问题。</title>
        <path className="home-input-beam" d="M-2000 200H300" stroke="var(--color-ink)" strokeWidth="6" fill="none" />
        <g className="home-input-example" fill="var(--color-ink)">
          <text x="0" y="148">TRANSFORMER</text>
          <text x="0" y="180">ARCHITECTURE:</text>
          <text x="0" y="252">WHAT'S NEW OVER</text>
          <text x="0" y="284" textLength="320" lengthAdjust="spacingAndGlyphs">THE PAST TWO YEARS?</text>
        </g>
        <g className="home-question-rays">
          {exampleQuestions.map(question => {
            const chosen = active?.id === question.id
            const end = 825 - 195 * shrink
            const top = question.edge[0] + (200 - question.edge[0]) * shrink - (chosen ? 5 : 0)
            const bottom = question.edge[1] + (200 - question.edge[1]) * shrink + (chosen ? 5 : 0)
            return <g key={question.id} data-question={question.id} data-selected={chosen} opacity={active && !chosen ? 0.4 : 1}
              onMouseEnter={() => { if (!launching) setActiveId(question.id) }} onMouseLeave={leave} onClick={() => select(question.question)}>
              <polygon fill={question.beam} points={'620,200 ' + end + ',' + top + ' ' + end + ',' + bottom} />
              <text fill={question.ink} x="838" y={question.edge[0] + 24} opacity={1 - shrink}>
                {question.lines.map((line, index) => <tspan key={line} x="838" dy={index ? 32 : 0} textLength={line.length > 14 ? 245 : undefined} lengthAdjust="spacingAndGlyphs">{line}</tspan>)}
              </text>
            </g>
          })}
        </g>
        <g className="home-robot-head" transform="translate(300 -8) scale(8)">
          <RobotHead focused={focused} motionEnabled={motionEnabled && desktop && !launching} previewRole={previewRole} />
        </g>
        {previewRole ? <text className="home-role-caption" x="460" y="372" textAnchor="middle">{previewRole}</text> : null}
      </svg>
      <div className="home-ray-controls">
        {exampleQuestions.map(question => <button key={question.id} type="button" className="home-ray-control"
          style={{ left: '83.2%', top: question.edge[0] / 4 + '%', width: '26%', height: '17%', borderColor: question.beam }}
          aria-label={'填入研究子问题：' + question.question} aria-describedby={active?.id === question.id ? 'home-subquestion-preview' : undefined}
          disabled={launching} onMouseEnter={() => setActiveId(question.id)} onMouseLeave={leave}
          onFocus={() => setActiveId(question.id)} onBlur={() => setActiveId(null)} onClick={() => select(question.question)} />)}
      </div>
    </div>
    <div className="home-mobile-example">
      <p className="home-mobile-question">TRANSFORMER ARCHITECTURE:<br />WHAT'S NEW OVER THE PAST TWO YEARS?</p>
      <svg className="home-mobile-head" viewBox="0 0 40 44" aria-hidden="true"><RobotHead focused={focused} motionEnabled={motionEnabled && !desktop && !launching} previewRole={previewRole} /></svg>
      {previewRole ? <p className="home-mobile-role">{previewRole}</p> : null}
      <ul className="home-mobile-subquestions">
        {exampleQuestions.map(question => <li key={question.id} style={{ borderColor: question.beam, color: question.ink }}>
          <button type="button" aria-label={'填入研究子问题：' + question.question} disabled={launching}
            aria-describedby={active?.id === question.id ? 'home-subquestion-preview' : undefined}
            onMouseEnter={() => setActiveId(question.id)} onMouseLeave={leave} onFocus={() => setActiveId(question.id)}
            onBlur={() => setActiveId(null)} onClick={() => select(question.question)}>{question.lines.join(' ')}</button>
        </li>)}
      </ul>
    </div>
    {active ? <div className="home-question-preview" id="home-subquestion-preview" role="tooltip" style={{ borderColor: active.beam }}>
      <p className="home-question-full">{active.full}</p><p>{active.question}</p><span>点击填入研究问题</span>
    </div> : null}
    <figcaption className="sr-only">实际问题拆解的展示示例。点击子问题只填入输入框，开始研究时才提交。</figcaption>
  </figure>
}
