import { useId, useState } from 'react'
import type { ResearchSession } from '../types'
import { getAgentRole } from '../data/agentRoles'
import { AgentAvatar } from './AgentAvatar'
import { Dialog } from './Dialog'
import { PixelIcon } from './PixelIcon'

const statusText = { waiting: '待执行', running: '进行中', completed: '已完成', failed: '失败', cancelled: '已停止' }

export function ResearchTimeline({ session, expanded, onToggle }: { session: ResearchSession; expanded: boolean; onToggle: () => void }) {
  const [inspectedId, setInspectedId] = useState<string | null>(null)
  const headingId = useId()
  const inspectedStage = session.stages.find(stage => stage.id === inspectedId)
  const inspectedRole = inspectedStage ? getAgentRole(inspectedStage.agent) : null
  const completed = session.stages.filter(stage => stage.status === 'completed').length
  const label = session.status === 'completed' ? '已完成 · 点击展开' : session.status === 'failed' ? '任务中断' : session.status === 'cancelled' ? '已停止' : session.loaded !== undefined ? `${session.stages.length} 条阶段记录 · 进行中` : `${completed} / ${session.stages.length} 阶段完成`
  return <section className="research-process" aria-label="研究过程">
    <button className="process-toggle" onClick={onToggle} aria-expanded={expanded} aria-controls={`timeline-${session.id}`}>
      <span className="process-title"><PixelIcon name="play" className={expanded ? 'is-expanded' : ''} />研究过程</span>
      <span className="process-summary"><span className={`process-status ${session.status}`} />{expanded && session.status === 'completed' ? '已完成 · 点击折叠' : label}</span>
    </button>
    {expanded ? <ol id={`timeline-${session.id}`} className="timeline">
      {session.stages.map(stage => {
        const role = getAgentRole(stage.agent)
        const stageStatus = stage.resultEvent ? '结果已返回' : session.loaded !== undefined ? '已记录' : statusText[stage.status]
        return <li key={stage.id} className={`timeline-stage stage-${stage.status}`}>
        <button className="node-marker agent-node" onClick={() => setInspectedId(stage.id)}
          aria-label={`查看${role.name}职责：${stage.title}，${stageStatus}`} aria-haspopup="dialog"
          title={`${role.name} · 点击查看职责`}>
          <AgentAvatar kind={role.avatar} />
          <span className={`agent-status-badge status-${stage.status}`} aria-hidden="true">{stage.status === 'completed' ? <PixelIcon name="check" /> : stage.status === 'failed' ? <PixelIcon name="close" /> : stage.status === 'cancelled' ? <span className="status-dash" /> : <span className="status-dot" />}</span>
        </button>
        <div className="stage-panel">
          <div className="stage-header"><div><span className="agent-name">{stage.agent}</span><span className="stage-title">{stage.title}</span></div><span className="stage-status">{stageStatus}</span></div>
          {stage.status !== 'waiting' ? <div className="terminal-output">{stage.lines.map((line, lineIndex) => <p key={lineIndex}><span className="output-prefix" aria-hidden="true">›</span>{line}</p>)}{stage.status === 'running' ? <p className="terminal-pending">正在处理… <span aria-hidden="true">▌</span></p> : null}</div> : null}
        </div>
      </li>})}
    </ol> : null}
    <Dialog open={Boolean(inspectedStage)} onClose={() => setInspectedId(null)} labelId={headingId} className="agent-dialog">
      <div className="dialog-heading"><h2 id={headingId}>{inspectedRole?.name ?? 'Agent 职能'}</h2><button className="icon-button" onClick={() => setInspectedId(null)} aria-label="关闭角色说明"><PixelIcon name="close" /></button></div>
      {inspectedStage && inspectedRole ? <>
        <div className="agent-profile"><div className="agent-profile-portrait"><AgentAvatar kind={inspectedRole.avatar} /></div><div><p className="agent-profile-name">{inspectedStage.agent}</p><h3>{inspectedStage.title}</h3><p className="agent-profile-tool">{inspectedRole.tool}</p></div></div>
        <p className="agent-description">{inspectedRole.description}</p>
        <dl className="agent-io"><div><dt>接收</dt><dd>{inspectedRole.input}</dd></div><div><dt>产出</dt><dd>{inspectedRole.output}</dd></div><div><dt>状态</dt><dd className="agent-live-status" aria-live="polite">{inspectedStage.resultEvent ? '结果已返回' : session.loaded !== undefined ? '已记录' : statusText[inspectedStage.status]}</dd></div></dl>
        <button className="key-button dialog-done" onClick={() => setInspectedId(null)}>返回研究过程</button>
      </> : null}
    </Dialog>
  </section>
}
