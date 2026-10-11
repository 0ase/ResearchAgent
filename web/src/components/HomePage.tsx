import { useState, type FormEvent, type KeyboardEvent } from 'react'
import { homeNodes, projectGitHub } from '../data/homepage'
import { HomeMascot } from './HomeMascot'
import { PixelIcon, Wordmark } from './PixelIcon'
import '../homepage.css'

export function HomePage({ onStart, onSettings, onDocumentation }: {
  onStart: (question: string) => void; onSettings: () => void; onDocumentation: () => void
}) {
  const [question, setQuestion] = useState('')

  function submit(event?: FormEvent) {
    event?.preventDefault()
    const cleaned = question.trim()
    if (cleaned && cleaned.length <= 2000) onStart(cleaned)
  }

  function inputKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      submit()
    }
  }

  return <div className="home-screen">
    <a className="skip-link" href="#home-question">跳到研究问题</a>
    <header className="home-header">
      <nav aria-label="首页导航" className="home-nav">
        <div className="home-nav-start">
          <button className="key-button home-nav-key" onClick={onDocumentation}><PixelIcon name="archive" /><span>文档</span></button>
          <button className="key-button home-nav-key" onClick={onSettings}><PixelIcon name="settings" /><span>设置</span></button>
        </div>
        <a className="home-github" href={projectGitHub} target="_blank" rel="noopener noreferrer" aria-label="在 GitHub 查看 B1GONE 项目" title="GitHub"><PixelIcon name="github" /></a>
      </nav>
    </header>
    <main className="home-stage">
      <section className="home-introduction" aria-labelledby="home-heading">
        <h1 className="home-brand" id="home-heading"><span aria-hidden="true"><Wordmark /></span><span className="sr-only">B1GONE 研究助手</span></h1>
        <p>拆解问题、检索文献、比较证据，<br />生成可追溯的研究综述。</p>
      </section>
      <HomeMascot />
      <form className="home-entry" onSubmit={submit} aria-label="开始新研究">
        <label className="sr-only" htmlFor="home-question">研究问题</label>
        <textarea id="home-question" value={question} onChange={event => setQuestion(event.target.value)} onKeyDown={inputKeyDown} maxLength={2000} rows={1} placeholder="输入研究问题，开始探索… |<" />
        <div className="home-entry-actions"><button className="key-button home-start" type="submit" disabled={!question.trim()}><span>开始研究</span></button></div>
      </form>
      <section className="home-pipeline" aria-label="研究节点职责">
        <ul>{homeNodes.map(node => <li key={node.name}>
          <span className="home-node-icon"><PixelIcon name={node.icon} /></span>
          <span className="home-node-name">{node.name}</span>
          <span className="home-node-description">{node.description}</span>
        </li>)}</ul>
      </section>
    </main>
  </div>
}
