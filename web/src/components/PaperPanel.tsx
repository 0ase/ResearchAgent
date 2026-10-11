import { useEffect, useRef, useState } from 'react'
import type { Paper } from '../types'
import { PixelIcon } from './PixelIcon'

export function PaperPanel({ papers, onClose, highlightedPaper, onSource, demo = false, citationIncomplete = false }: {
  papers: Paper[]; onClose: () => void; highlightedPaper: string | null; onSource: (paper: Paper) => void; demo?: boolean; citationIncomplete?: boolean
}) {
  const [expandedPaper, setExpandedPaper] = useState<string | null>(null)
  const listRef = useRef<HTMLOListElement>(null)
  useEffect(() => {
    if (!highlightedPaper) return
    Array.from(listRef.current?.querySelectorAll<HTMLElement>('[data-paper-id]') ?? []).find(element => element.dataset.paperId === highlightedPaper)?.scrollIntoView({ block: 'nearest' })
  }, [highlightedPaper])
  return <div className="paper-panel-inner">
    <header className="paper-panel-header"><div><h2 id="papers-heading">研究文献</h2><p>已阅读 {papers.length} · {citationIncomplete ? '已确认引用' : '报告引用'} {papers.filter(paper => paper.cited).length}</p></div><button className="icon-button" onClick={onClose} aria-label="关闭研究文献"><PixelIcon name="close" /></button></header>
    <ol className="paper-list" ref={listRef}>
      {papers.map((paper, index) => <li key={paper.id} data-paper-id={paper.id} className={`paper-item ${highlightedPaper === paper.id ? 'paper-highlighted' : ''}`}>
        <span className="paper-number">{String(index + 1).padStart(2, '0')}</span>
        <div className="paper-content">
          <div className="paper-title-row"><h3>{paper.title}</h3><span className={`paper-badge ${paper.cited ? 'is-cited' : ''}`}>{paper.cited ? '已引用' : '已阅读'}</span></div>
          <p className="paper-metadata">{paper.authors} &nbsp; {paper.year || '年份未知'} &nbsp; {paper.venue}</p>
          <p className="paper-description">{paper.description}</p>
          <div className="paper-actions"><button onClick={() => setExpandedPaper(expandedPaper === paper.id ? null : paper.id)} aria-expanded={expandedPaper === paper.id} aria-controls={`abstract-${paper.id}`}><PixelIcon name="archive" />{expandedPaper === paper.id ? '收起' : '摘要'}</button>{paper.url ? <a href={paper.url} target="_blank" rel="noopener noreferrer"><PixelIcon name="external" />原文</a> : demo ? <button onClick={() => onSource(paper)}><PixelIcon name="external" />原文</button> : <span className="source-unavailable">原文链接缺失</span>}</div>
          {expandedPaper === paper.id ? <div id={`abstract-${paper.id}`} className="paper-abstract"><h4>摘要</h4><p>{paper.abstract}</p></div> : null}
        </div>
      </li>)}
    </ol>
    <p className="paper-panel-note">{demo ? '界面演示 · 示例文献' : citationIncomplete ? '部分引用格式无法关联，计数仅含已确认引用' : '实际阅读文献 · 正文引用关联'}</p>
  </div>
}
