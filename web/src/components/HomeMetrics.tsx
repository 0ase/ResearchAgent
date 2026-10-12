import { useEffect, useRef, useState } from 'react'
import { parseEvaluationSnapshot, type EvaluationMetric, type EvaluationSnapshot } from '../types/evaluationMetrics'
import { AsciiButton } from './AsciiButton'

const primaryIds = ['latency_p50', 'latency_p99', 'mean_completion_seconds', 'mean_llm_tokens', 'rag_hit_rate', 'task_completion_rate']
const units: Record<EvaluationMetric['unit'], string> = { seconds: '秒', tokens: 'token / 任务', '%': '%', score: '' }
const valueText = (value: number | null, unit: EvaluationMetric['unit']) => value === null ? 'N/A' : value.toLocaleString('zh-CN', { maximumFractionDigits: unit === 'tokens' ? 0 : unit === 'score' ? 3 : 1 })
const timestamp = (value: string | null) => value && Number.isFinite(Date.parse(value)) ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '暂无记录'

export function HomeMetrics({ motionEnabled }: { motionEnabled: boolean }) {
  const [snapshot, setSnapshot] = useState<EvaluationSnapshot>()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const controller = useRef<AbortController | null>(null)

  async function refresh() {
    controller.current?.abort()
    const request = new AbortController()
    controller.current = request
    setBusy(true); setError('')
    try {
      const response = await fetch('/metrics/summary.json', { cache: 'no-store', signal: request.signal })
      if (!response.ok) throw new Error('unavailable')
      const report = parseEvaluationSnapshot(await response.json())
      if (!request.signal.aborted) setSnapshot(report)
    } catch {
      if (!request.signal.aborted) setError(snapshot ? '未能刷新，当前仍显示上一份快照。' : '尚无可读取的统计快照。生成实测数据后，可刷新查看。')
    } finally {
      if (!request.signal.aborted) setBusy(false)
    }
  }
  useEffect(() => { void refresh(); return () => controller.current?.abort() }, [])

  const metrics = snapshot?.groups.flatMap(group => group.metrics) ?? []
  const primary = primaryIds.map(id => metrics.find(metric => metric.id === id)).filter((metric): metric is EvaluationMetric => Boolean(metric))
  return <section className="home-metrics" aria-labelledby="home-metrics-heading" aria-busy={busy}>
    <div className="metrics-heading-row">
      <div><p className="metrics-kicker">本机真实运行 · 非演示研究</p><h2 id="home-metrics-heading">运行与评测</h2></div>
      <AsciiButton label="刷新读数" motionEnabled={motionEnabled} className="key-button metrics-refresh" disabled={busy} onClick={() => void refresh()} />
    </div>
    <p className="metrics-intro">从实际研究记录计算耗时、资源与完成情况。质量指标使用独立标注，缺少证据时显示 N/A。</p>
    {error ? <p className="metrics-status" role="status">{error}</p> : null}
    {!snapshot && busy ? <p className="metrics-status" role="status">正在读取统计快照…</p> : null}
    {snapshot ? <>
      <div className="metrics-population" aria-label="统计任务范围">
        <span><strong>{snapshot.population.started}</strong> 次研究启动</span>
        <span><strong>{snapshot.population.completed}</strong> 完成</span>
        <span><strong>{snapshot.population.failed}</strong> 失败</span>
        <span><strong>{snapshot.population.cancelled}</strong> 取消</span>
        <span><strong>{snapshot.population.incomplete}</strong> 未闭合记录</span>
      </div>
      <dl className="metrics-readouts">
        {primary.map(metric => <div key={metric.id} data-metric-id={metric.id} className={'metric-readout metric-' + metric.status}>
          <dt>{metric.label}</dt><dd><strong>{valueText(metric.value, metric.unit)}</strong>{metric.value !== null ? <span>{units[metric.unit]}</span> : null}</dd>
          <p className="metric-samples">{metric.value === null ? '待测 · 暂无有效数据' : `${metric.samples} 个有效统计单位`}</p>
          <p className="metric-definition">{metric.value === null || metric.status === 'partial' ? metric.reason : metric.definition}</p>
        </div>)}
      </dl>
      <p className="metrics-window">记录范围：{timestamp(snapshot.window.start)} — {timestamp(snapshot.window.end)}<br />快照更新：{timestamp(snapshot.generated_at)} · 耗时采用服务端处理时间</p>
      <div className="metrics-details-list">
        {snapshot.groups.map(group => <details className="metrics-details" key={group.id}>
          <summary>{group.label} · 完整指标与口径</summary>
          <dl className="metrics-detail-readouts">{group.metrics.map(metric => <div key={metric.id}>
            <dt>{metric.label}</dt><dd>{valueText(metric.value, metric.unit)}{metric.value !== null ? ' ' + units[metric.unit] : ''}<small>统计单位 {metric.samples}</small></dd>
            <p>{metric.definition}</p>{metric.reason ? <p className="metrics-missing">{metric.reason}</p> : null}
          </div>)}</dl>
        </details>)}
        <details className="metrics-details">
          <summary>阶段性能 · 完成耗时与失败记录</summary>
          <div className="metrics-table-scroll"><table><caption>以完成节点调用计时；失败数来自阶段失败事件。</caption><thead><tr><th>阶段</th><th>启动</th><th>计时完成</th><th>失败</th><th>降级</th><th>平均 / 秒</th><th>P50 / 秒</th><th>P99 / 秒</th></tr></thead>
            <tbody>{snapshot.stages.map(stage => <tr key={stage.stage}><th scope="row">{stage.stage}</th><td>{stage.started}</td><td>{stage.completed}</td><td>{stage.failed}</td><td>{stage.degraded}</td><td>{valueText(stage.mean_seconds, 'seconds')}</td><td>{valueText(stage.p50_seconds, 'seconds')}</td><td>{valueText(stage.p99_seconds, 'seconds')}</td></tr>)}</tbody>
          </table></div>
        </details>
      </div>
      <aside className="metrics-notes" aria-label="数据说明"><h3>读数说明</h3><ul>{snapshot.notes.map(note => <li key={note}>{note}</li>)}</ul><p>本面板展示观测统计，任务完成不等于研究结论已经通过独立质量评审。</p></aside>
    </> : !busy ? <p className="metrics-empty">P50、P99、平均耗时、token 消耗和 RAG 命中率将在取得有效记录后展示，不使用演示数值。</p> : null}
  </section>
}
