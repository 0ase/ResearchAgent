export type AgentKind = 'supervisor' | 'search' | 'filter' | 'read' | 'analysis' | 'synthesize' | 'critic'

export interface AgentRole {
  avatar: AgentKind
  name: string
  tool: string
  description: string
  input: string
  output: string
}

const roles: Record<AgentKind, AgentRole> = {
  supervisor: {
    avatar: 'supervisor', name: '调度员', tool: '耳麦与调度台',
    description: '拆解研究问题，安排各个研究阶段，并根据阶段反馈决定下一步工作。研究结束时，负责汇总任务结果。',
    input: '研究问题、各阶段反馈', output: '研究计划、子问题、下一步任务',
  },
  search: {
    avatar: 'search', name: '检索员', tool: '放大镜',
    description: '根据研究子问题搜索不同来源的论文，整理来源统计，并将去重后的候选文献交给筛选环节。',
    input: '研究子问题、检索词', output: '候选论文、检索来源与数量',
  },
  filter: {
    avatar: 'filter', name: '筛选员', tool: '穿孔卡与筛选漏斗',
    description: '结合论文元数据进行排序，再评估问题相关性、证据质量和方法价值，选出需要进一步阅读的文献。',
    input: '候选论文、目标阅读数量', output: '入选论文、评分与筛选记录',
  },
  read: {
    avatar: 'read', name: '阅读员', tool: '展开的书册',
    description: '阅读可获取的论文内容，提取研究方法、实验结果、结论与局限，为跨论文比较准备证据。',
    input: '入选论文及其可获取内容', output: '逐篇阅读笔记、关键证据',
  },
  analysis: {
    avatar: 'analysis', name: '分析员', tool: '双列对照图表',
    description: '将不同论文的方法、数据和结论放在一起比较，梳理研究共识、结论差异以及尚未解决的问题。',
    input: '逐篇阅读笔记、研究问题', output: '研究共识、矛盾与研究空白',
  },
  synthesize: {
    avatar: 'synthesize', name: '撰写员', tool: '打字机',
    description: '把阅读证据与跨论文分析组织成研究综述，并整理结论与参考文献之间的引用关系。',
    input: '研究分析、文献证据', output: '研究综述、报告引用',
  },
  critic: {
    avatar: 'critic', name: '审查员', tool: '核验清单与印章',
    description: '检查报告是否回答研究问题、结论是否有证据支持、引用是否一致，并给出质量评价和修改意见。',
    input: '报告草稿、研究问题与证据', output: '质量评分、审查意见与通过状态',
  },
}

export function getAgentRole(agent: string): AgentRole {
  const aliases: Record<string, AgentKind> = { orchestrate: 'supervisor', plan_queries: 'supervisor', analyze: 'analysis', writer: 'synthesize', review_search: 'critic' }
  if (Object.hasOwn(aliases, agent)) return roles[aliases[agent]]
  if (Object.hasOwn(roles, agent)) return roles[agent as AgentKind]
  return { avatar: 'supervisor', name: '研究助手', tool: '研究终端', description: '负责当前研究阶段的任务处理与结果整理。', input: '当前阶段资料', output: '阶段结果与记录' }
}
