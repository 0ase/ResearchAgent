import type { ResearchSession } from '../types'
import { formatDate } from '../data/demo'
import { PixelIcon, Wordmark } from './PixelIcon'

export function Sidebar({ sessions, activeId, onSelect, onNew, onSettings, onClose, onCollapse, demo = false }: {
  sessions: ResearchSession[]; activeId: string | null; onSelect: (id: string) => void;
  onNew: () => void; onSettings: () => void; onClose?: () => void; onCollapse?: () => void
  demo?: boolean
}) {
  return <div className={`sidebar-inner ${onCollapse ? 'has-collapse-control' : ''}`}>
    <div className="sidebar-top">
      <div className="brand-line"><Wordmark />{onClose ? <button className="icon-button sidebar-close" onClick={onClose} aria-label="关闭研究记录"><PixelIcon name="close" /></button> : null}</div>
      <button className="key-button new-research" onClick={onNew}><PixelIcon name="plus" /><span>新建研究</span></button>
    </div>
    <nav className="history-nav" aria-label="研究记录">
      <h2 id="history-heading" className="history-heading">研究记录</h2>
      <ul className="history-list">
        {sessions.map(session => <li key={session.id}>
          <button className={`history-item ${activeId === session.id ? 'is-active' : ''}`} onClick={() => onSelect(session.id)} aria-current={activeId === session.id ? 'page' : undefined}>
            <PixelIcon name="archive" className="history-icon" />
            <span className="history-copy"><span className="history-title">{session.title}</span><span className="history-date">{session.status === 'running' ? '研究进行中' : formatDate(session.createdAt)}</span></span>
            {session.status === 'running' ? <span className="history-running" aria-label="进行中" /> : null}
          </button>
        </li>)}
      </ul>
    </nav>
    <div className="sidebar-bottom">
      <div className="sidebar-settings-row">
        <button className="settings-button" onClick={onSettings}><PixelIcon name="settings" /><span>设置</span></button>
        {onCollapse ? <button className="icon-button sidebar-collapse" onClick={onCollapse} aria-label="收起侧边栏" aria-expanded="true" aria-controls="desktop-sidebar-content" title="收起侧边栏"><PixelIcon name="collapse" /></button> : null}
      </div>
      <p className="prototype-note">{demo ? '交互原型 · 示例数据' : 'B1GONE · 本机研究工作台'}</p>
    </div>
  </div>
}
