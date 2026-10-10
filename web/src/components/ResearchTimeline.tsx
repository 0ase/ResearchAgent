import type { ResearchSession } from '../types'
import { PixelIcon } from './PixelIcon'

const statusText = { waiting: '待执行', running: '进行中', completed: '已完成', failed: '失败', cancelled: '已停止' }

export function ResearchTimeline({ session, expanded, onToggle }: { session: ResearchSession; expanded: boolean; onToggle: () => void }) {
  const completed = session.stages.filter(stage => stage.status === 'completed').length
  const label = session.status === 'completed' ? '已完成 · 点击展开' : session.status === 'failed' ? '任务中断' : session.status === 'cancelled' ? '已停止' : `${completed} / ${session.stages.length} 阶段完成`
  return <section className="research-process" aria-label="研究过程">
    <button className="process-toggle" onClick={onToggle} aria-expanded={expanded} aria-controls={`timeline-${session.id}`}>
      <span className="process-title"><PixelIcon name="play" className={expanded ? 'is-expanded' : ''} />研究过程</span>
      <span className="process-summary"><span className={`process-status ${session.status}`} />{expanded && session.status === 'completed' ? '已完成 · 点击折叠' : label}</span>
    </button>
    {expanded ? <ol id={`timeline-${session.id}`} className="timeline">
      {session.stages.map((stage, index) => <li key={stage.id} className={`timeline-stage stage-${stage.status}`}>
        <div className="node-marker" aria-hidden="true">{stage.status === 'completed' ? <PixelIcon name="check" /> : stage.status === 'failed' ? <PixelIcon name="close" /> : <span>{String(index + 1).padStart(2, '0')}</span>}</div>
        <div className="stage-panel">
          <div className="stage-header"><div><span className="agent-name">{stage.agent}</span><span className="stage-title">{stage.title}</span></div><span className="stage-status">{statusText[stage.status]}</span></div>
          {stage.status !== 'waiting' ? <div className="terminal-output">{stage.lines.map((line, lineIndex) => <p key={lineIndex}><span className="output-prefix" aria-hidden="true">›</span>{line}</p>)}{stage.status === 'running' ? <p className="terminal-pending">正在处理… <span aria-hidden="true">▌</span></p> : null}</div> : null}
        </div>
      </li>)}
    </ol> : null}
  </section>
}
