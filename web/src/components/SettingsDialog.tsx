import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import type { SettingsSnapshot } from '../types'
import { ApiError, loadSettings, saveSettings } from '../services/apiClient'
import { Dialog } from './Dialog'
import { PixelIcon } from './PixelIcon'

const groups = [
  { title: '模型连接', fields: [['base_url', '模型 API 地址'], ['default_model', '主模型'], ['light_model', '轻量模型'], ['dashscope_base_url', '嵌入 API 地址'], ['embedding_model', '嵌入模型']] },
  { title: '文献检索', fields: [['unpaywall_email', 'Unpaywall 邮箱'], ['pubmed_email', 'PubMed 邮箱'], ['crossref_email', 'Crossref 邮箱'], ['max_search_rounds', '最大搜索轮次', 1, 6], ['min_candidate_papers', '最少候选论文', 80, 100], ['max_candidate_papers', '最多候选论文', 80, 100]] },
  { title: '筛选与生成', fields: [['screening_min_score', '筛选阈值', 0, 100], ['screening_supplement_min_score', '补充阈值', 0, 100], ['screening_batch_size', '每批评估篇数', 1, 15], ['screening_max_tokens', '筛选 token 上限', 2000, 16000], ['analysis_max_tokens', '分析 token 上限', 1500, 16000], ['analysis_retry_max_tokens', '分析重试 token', 1500, 16000], ['analysis_max_attempts', '分析尝试次数', 1, 3], ['writer_max_tokens', '写作 token 上限', 1000, 16000], ['read_concurrency', '阅读并发', 1, 10]] },
] as const
const secretLabels: Record<string, string> = { openai_api_key: 'OpenAI / 兼容密钥', anthropic_api_key: '备用兼容密钥（ANTHROPIC）', dashscope_api_key: 'DashScope 嵌入密钥', semantic_scholar_api_key: 'Semantic Scholar 密钥', pubmed_api_key: 'PubMed 密钥' }
const runtimeLabels: Record<string, string> = { config_file: '配置文件', session_database: '会话数据库', vector_directory: '向量库目录', paper_cache_directory: '论文缓存', log_directory: '日志目录' }

export function SettingsDialog({ onClose, paperCount, onPaperCount, children }: { onClose: () => void; paperCount: number; onPaperCount: (count: number) => void; children?: ReactNode }) {
  const [snapshot, setSnapshot] = useState<SettingsSnapshot>()
  const [values, setValues] = useState<Record<string, string | number>>({})
  const [secrets, setSecrets] = useState<Record<string, string>>({})
  const [clearSecrets, setClearSecrets] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    loadSettings(controller.signal).then(result => { setSnapshot(result); setValues(result.values) }).catch(reason => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : '读取设置失败。') })
    return () => controller.abort()
  }, [])
  async function save(event: FormEvent) {
    event.preventDefault()
    if (!snapshot) return
    setBusy(true); setError(''); setNotice('')
    try {
      const changed = Object.fromEntries(Object.entries(values).filter(([key, value]) => value !== snapshot.values[key]))
      const result = await saveSettings(changed, secrets, clearSecrets)
      setSnapshot(result); setValues(result.values); setSecrets({}); setClearSecrets([])
      setNotice(result.restart_required ? '配置已保存。请重启后端后使用新配置。' : '配置已保存。当前生效配置没有变化。')
    } catch (reason) {
      const detail = reason instanceof ApiError && reason.errorId ? ` 追踪编号：${reason.errorId}` : ''
      setError((reason instanceof Error ? reason.message : '保存失败。') + detail)
    } finally { setBusy(false) }
  }
  return <Dialog open onClose={onClose} labelId="settings-heading" className="settings-dialog live-settings">
    <div className="dialog-heading"><h2 id="settings-heading">研究设置</h2><button className="icon-button" onClick={onClose} aria-label="关闭设置"><PixelIcon name="close" /></button></div>
    <p className="dialog-intro">配置保存到本机，重启后端生效。当前任务继续使用启动时的配置。</p>
    <label className="setting-field"><span>目标阅读数量</span><input type="number" min={3} max={15} value={paperCount} onChange={event => { const count = Number(event.target.value); if (count >= 3 && count <= 15) onPaperCount(count) }} /></label>
    <p className="settings-detail">目标数量用于下一次新研究。追问沿用当前研究的文献。</p>
    {children}
    {error ? <p className="settings-error" role="alert">{error}</p> : null}
    {notice ? <p className="settings-success" role="status">{notice}</p> : null}
    {!snapshot && !error ? <p role="status">读取配置中…</p> : null}
    {snapshot ? <form onSubmit={save}>
      {snapshot.restart_required ? <p className="settings-success">已保存的配置待重启生效：{snapshot.pending_fields.join('、')}</p> : null}
      <fieldset disabled={busy || !snapshot.writable}>
        {groups.map(group => <section className="settings-group" key={group.title}><h3>{group.title}</h3>{group.fields.map(field => {
          const [name, label] = field
          const numeric = field.length > 2
          const overridden = snapshot.overridden_fields.includes(name)
          return <div key={name}><label className="setting-field"><span>{label}</span><input autoComplete="off" type={numeric ? 'number' : 'text'} min={numeric ? (field as readonly unknown[])[2] as number : undefined} max={numeric ? (field as readonly unknown[])[3] as number : undefined} step={name.includes('score') ? 'any' : 1} value={values[name] ?? ''} onChange={event => setValues(current => ({ ...current, [name]: numeric ? event.target.value === '' ? '' : Number(event.target.value) : event.target.value }))} /></label>{overridden || snapshot.pending_fields.includes(name) ? <p className="settings-detail">{overridden ? '系统环境变量覆盖。' : ''} 当前生效：{String(snapshot.effective_values[name])}</p> : null}</div>
        })}</section>)}
        <section className="settings-group"><h3>密钥</h3><p className="settings-detail">OpenAI 优先，备用密钥供同一兼容 API 使用；嵌入密钥独立。输入留空表示保留。</p>{Object.entries(snapshot.secrets).map(([name, state]) => <div className="secret-field" key={name}>
          <label className="setting-field"><span>{secretLabels[name] ?? name}</span><input type="password" autoComplete="new-password" value={secrets[name] ?? ''} disabled={clearSecrets.includes(name)} placeholder="留空保留原值" onChange={event => setSecrets(current => ({ ...current, [name]: event.target.value }))} /></label>
          <div className="secret-status"><span>当前{state.configured ? '已配置' : '未配置'} · 文件{state.saved ? '已保存' : '未保存'}{state.overridden ? ' · 系统环境覆盖' : ''}</span><label><input type="checkbox" checked={clearSecrets.includes(name)} onChange={event => { setSecrets(current => { const next = { ...current }; delete next[name]; return next }); setClearSecrets(current => event.target.checked ? [...current, name] : current.filter(key => key !== name)) }} />清除文件密钥</label></div>
        </div>)}</section>
      </fieldset>
      <section className="settings-group runtime-info"><h3>运行位置（只读）</h3>{Object.entries(snapshot.runtime).map(([key, value]) => <p key={key}><span>{runtimeLabels[key] ?? key}</span><code>{value}</code></p>)}</section>
      {!snapshot.writable ? <p role="alert">请从项目根目录使用 scripts/start_backend.ps1 启动后端后再保存。</p> : null}
      <button className="key-button dialog-done" disabled={busy || !snapshot.writable} type="submit">{busy ? '保存中…' : '保存配置'}</button>
    </form> : null}
  </Dialog>
}
