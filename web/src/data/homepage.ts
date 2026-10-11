import type { IconName } from '../components/PixelIcon'

export const projectGitHub = 'https://github.com/0ase/ResearchAgent'

export const homeNodes: { name: string; description: string; icon: IconName }[] = [
  { name: 'supervisor', description: '任务规划与调度', icon: 'pipeline' },
  { name: 'retrieval', description: '问题拆解、检索、筛选与阅读', icon: 'search' },
  { name: 'analysis', description: '比较共识、差异与研究空白', icon: 'analysis' },
  { name: 'writer', description: '整理证据并撰写综述', icon: 'archive' },
  { name: 'critic', description: '检查论证与引用', icon: 'check' },
]

// Short English labels translated from the recorded Transformer decomposition.
// Sources: docs/design/b1gone-mascot-v2-questions.json and -v7-labels.json.
export const exampleQuestions = [
  { id: 'attention', lines: ['NEW ATTENTION', 'MECHANISMS?'], beam: '#ef4315', ink: '#942e12', edge: [10, 50] },
  { id: 'variants', lines: ['NEW EFFICIENT', 'VARIANTS?'], beam: '#ffd452', ink: '#68430d', edge: [105, 145] },
  { id: 'benchmarks', lines: ['WHICH BENCHMARKS', 'AND DATASETS?'], beam: '#087c94', ink: '#00576b', edge: [205, 250] },
  { id: 'gains', lines: ['EFFICIENCY AND', 'ACCURACY GAINS?'], beam: '#7940dd', ink: '#4c247e', edge: [320, 365] },
]
