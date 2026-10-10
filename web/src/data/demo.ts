import type { Paper, ResearchSession, ResearchStage } from '../types'

export const DEFAULT_QUESTION = '请比较现有方法、研究共识与研究空白。'

const paperTopics = [
  ['研究方法与实验设计', 'Zhang et al.', 2023, 'Nature Machine Intelligence', '探讨大语言模型在科学研究中的应用方法与实验设计，分析多种任务设置下的表现。'],
  ['数据来源与评价指标', 'Li et al.', 2023, 'ACL', '系统比较不同数据来源和评价指标对模型性能的影响。'],
  ['跨数据集验证', 'Wang et al.', 2022, 'EMNLP', '在多个公开数据集上验证了模型的泛化能力，并分析了领域迁移的效果。'],
  ['证据一致性分析', 'Chen et al.', 2023, 'arXiv', '提出一种基于证据一致性的评估方法，用于衡量生成内容的真实性和可靠性。'],
  ['方法的适用边界', 'Kumar et al.', 2022, 'NeurIPS', '分析了不同方法在复杂任务中的适用边界，并给出了案例研究。'],
  ['可复现性与研究局限', 'Deng et al.', 2021, 'ICLR', '从可复现性的角度讨论了现有研究的局限，提出了改进建议。'],
  ['检索增强与知识更新', 'Liu et al.', 2024, 'ACL', '讨论检索增强方法对知识更新和可解释性的影响。'],
  ['科学任务中的提示设计', 'Wu et al.', 2023, 'EMNLP', '比较多种提示策略在科学问答中的表现和适用条件。'],
  ['领域迁移与泛化能力', 'Park et al.', 2024, 'ICLR', '考察模型在未见领域和不同任务分布中的表现。'],
  ['长程规划与任务分解', 'Zhao et al.', 2024, 'NeurIPS', '研究复杂任务的分解方式和长期规划中的误差积累。'],
  ['人机协作与验证流程', 'Sun et al.', 2023, 'arXiv', '探索研究人员介入模型推理与证据验证的协作流程。'],
  ['研究助手的比较评估', 'Kim et al.', 2024, 'ACL', '提出面向研究助手的多维评估框架，关注质量与效率。'],
  ['开放数据与实验标准', 'He et al.', 2022, 'EMNLP', '梳理开放数据集的构建过程与实验报告规范。'],
  ['多模态证据整合', 'Yang et al.', 2024, 'ICLR', '分析文本、图表和实验数据在证据整合中的作用。'],
  ['长期使用与研究可靠性', 'Lin et al.', 2023, 'arXiv', '讨论研究助手的长期影响、使用反馈与可靠性评估。'],
] as const

// All papers are fictional interface fixtures, not bibliographic records.
export const DEMO_PAPERS: Paper[] = paperTopics.map(([topic, authors, year, venue, description], index) => ({
  id: `paper-${index + 1}`,
  title: `示例论文 ${String(index + 1).padStart(2, '0')}：${topic}`,
  authors, year, venue, description,
  cited: index < 12,
  abstract: `${description} 这条示例摘要用于展示文献查看交互，包括研究问题、方法、评价设置和局限性。正式接入后，这里将展示论文的真实摘要，并与报告中的引用位置对应。`,
}))

export function makeStages(question: string, paperCount: number): ResearchStage[] {
  const citationCount = Math.min(paperCount, 12)
  return [
    { id: 'supervisor', agent: 'supervisor', title: '拆解研究问题', lines: [`研究问题：${question}`, '子问题 1 / 现有研究采用了哪些主要方法？', '子问题 2 / 方法的适用条件与证据有什么差异？', '子问题 3 / 已有共识、矛盾与研究空白是什么？'], status: 'waiting' },
    { id: 'search', agent: 'search', title: '搜索相关文献', lines: ['arXiv                 26 篇', 'Semantic Scholar      38 篇', 'PubMed                17 篇', 'Crossref              12 篇', '去重后候选论文：93 篇'], status: 'waiting' },
    { id: 'filter', agent: 'filter', title: '评估与筛选论文', lines: ['排序依据：引用量、发表来源、摘要与全文可用性', '评分维度：问题相关性、证据质量、方法价值、互补性', '评估批次：5 篇 / 批次', `达到目标数量：${paperCount} 篇，结束筛选`], status: 'waiting' },
    { id: 'read', agent: 'read', title: '阅读与提取证据', lines: [`进入阅读：${paperCount} 篇`, '提取研究方法、实验结果与适用条件', '整理每篇论文的结论、局限与证据出处'], status: 'waiting' },
    { id: 'analysis', agent: 'analysis', title: '跨论文比较分析', lines: ['研究共识：3 项', '结论差异：2 项', '研究空白：3 项', '对照数据来源、实验设置与评价指标'], status: 'waiting' },
    { id: 'synthesize', agent: 'synthesize', title: '撰写研究综述', lines: ['生成方法比较、研究共识与研究空白', `整理引用：${citationCount} 篇`, '保留结论与参考文献之间的对应关系'], status: 'waiting' },
    { id: 'critic', agent: 'critic', title: '审查报告质量', lines: ['检查问题覆盖、证据支持与引用一致性', '审查轮次：1', '质量评分：8.6 / 10', '审查结果：通过'], status: 'waiting' },
    { id: 'finish', agent: 'supervisor', title: '完成研究任务', lines: ['研究综述已完成', `已阅读 ${paperCount} 篇 / 报告引用 ${citationCount} 篇`], status: 'waiting' },
  ]
}

const history = [
  ['大语言模型与科学研究', DEFAULT_QUESTION, '2026-10-09T10:28:00'],
  ['文献筛选方法', '如何提高文献筛选的相关性与覆盖率？', '2026-10-08T09:17:00'],
  ['研究方法比较', '比较不同研究方法的适用条件与局限。', '2026-10-07T16:03:00'],
  ['科研评价指标分析', '科研任务中应当如何选择评价指标？', '2026-10-06T11:20:00'],
  ['多模态模型的应用', '多模态模型在科学研究中有哪些应用？', '2026-10-05T10:42:00'],
  ['生成式 AI 的局限性', '分析生成式 AI 在研究任务中的局限。', '2026-10-04T15:36:00'],
  ['相关工作调研', '梳理现有研究助手的方法与证据。', '2026-10-03T09:14:00'],
] as const

export function makeInitialSessions(): ResearchSession[] {
  return history.map(([title, question, createdAt], index) => ({
    id: `demo-${index}`, title, question, createdAt, status: 'completed', paperCount: 15, sourceCount: 93,
    stages: makeStages(question, 15).map(stage => ({ ...stage, status: 'completed' })),
  }))
}

export function getPapers(session: ResearchSession): Paper[] {
  return DEMO_PAPERS.slice(0, session.paperCount)
}

export function formatDate(date: string): string {
  const value = new Date(date)
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')} ${String(value.getHours()).padStart(2, '0')}:${String(value.getMinutes()).padStart(2, '0')}`
}
