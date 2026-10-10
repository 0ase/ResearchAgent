import type { ResearchSession } from '../types'

export function Report({ session, onCitation }: { session: ResearchSession; onCitation: (paperId: string) => void }) {
  const citation = (index: number) => <button className="citation" onClick={() => onCitation(`paper-${index}`)} aria-label={`查看引用文献 ${index}`}>[{index}]</button>
  return <article className="report" aria-label="研究综述">
    <header className="report-header">
      <h1>研究综述</h1>
      <h2>方法比较与证据梳理</h2>
      <p>本报告围绕研究问题，对纳入文献的研究方法、主要结论与适用条件进行比较。<br className="wide-break" />比较结果需结合数据来源、实验设置和评价指标进行理解。</p>
      {session.id.startsWith('run-') ? <p className="report-question">本次问题：{session.question}</p> : null}
    </header>
    <section className="report-section">
      <h2>研究共识</h2>
      <p>现有研究在若干关键问题上已形成较为一致的认识。首先，大语言模型在知识理解、文本生成和科研辅助等任务上表现出显著潜力，尤其在文献检索、摘要生成和初步假设提出方面具有应用价值 {citation(1)}。其次，多数研究认为，模型效果与数据质量、任务定义和评测方式密切相关，需要在具体领域中进行针对性验证 {citation(2)}。</p>
    </section>
    <section className="report-section">
      <h2>方法比较</h2>
      <p>现有方法可分为三类：基于提示的方法、基于微调的方法和基于检索增强的方法。基于提示的方法实现简单、通用性强，但在复杂推理任务中的稳定性有限；基于微调的方法在特定领域表现更好，但需要高质量标注数据和更高的计算成本；检索增强的方法能够引入外部知识，提升事实性和可解释性，但其效果受检索质量和知识来源的影响 {citation(4)}。</p>
    </section>
    <section className="report-section">
      <h2>研究空白</h2>
      <p>尽管现有研究已取得积极进展，仍存在若干未充分探索的方向。例如，跨学科场景下的泛化能力、复杂科研任务的长程规划与验证，以及不同评价体系下的可比较性等问题，仍缺乏系统性研究。此外，关于模型在真实科研流程中的长期影响与潜在风险，也需要更多实证研究。</p>
    </section>
  </article>
}

export function reportMarkdown(session: ResearchSession): string {
  return `# 研究综述\n\n> B1GONE 交互原型示例，内容与参考文献均为演示数据。\n\n研究问题：${session.question}\n\n## 方法比较与证据梳理\n\n本报告围绕研究问题，对纳入文献的研究方法、主要结论与适用条件进行比较。比较结果需结合数据来源、实验设置和评价指标进行理解。\n\n## 研究共识\n\n现有研究在若干关键问题上已形成较为一致的认识。首先，大语言模型在知识理解、文本生成和科研辅助等任务上表现出显著潜力，尤其在文献检索、摘要生成和初步假设提出方面具有应用价值 [1]。其次，多数研究认为，模型效果与数据质量、任务定义和评测方式密切相关，需要在具体领域中进行针对性验证 [2]。\n\n## 方法比较\n\n现有方法可分为三类：基于提示的方法、基于微调的方法和基于检索增强的方法。基于提示的方法实现简单、通用性强，但在复杂推理任务中的稳定性有限；基于微调的方法在特定领域表现更好，但需要高质量标注数据和更高的计算成本；检索增强的方法能够引入外部知识，提升事实性和可解释性，但其效果受检索质量和知识来源的影响 [4]。\n\n## 研究空白\n\n尽管现有研究已取得积极进展，仍存在若干未充分探索的方向。例如，跨学科场景下的泛化能力、复杂科研任务的长程规划与验证，以及不同评价体系下的可比较性等问题，仍缺乏系统性研究。此外，关于模型在真实科研流程中的长期影响与潜在风险，也需要更多实证研究。\n`
}
