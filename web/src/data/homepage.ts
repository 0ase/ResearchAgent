import type { IconName } from '../components/PixelIcon'

export const projectGitHub = 'https://github.com/0ase/ResearchAgent'

export const homeNodes = [
  { name: 'supervisor', description: '任务规划与调度', icon: 'pipeline' },
  { name: 'retrieval', description: '问题拆解、检索、筛选与阅读', icon: 'search' },
  { name: 'analysis', description: '比较共识、差异与研究空白', icon: 'analysis' },
  { name: 'writer', description: '整理证据并撰写综述', icon: 'archive' },
  { name: 'critic', description: '检查论证与引用', icon: 'check' },
] as const satisfies readonly { name: string; description: string; icon: IconName }[]

export type HomeNodeName = typeof homeNodes[number]['name']

// Short English labels translated from the recorded Transformer decomposition.
// Sources: docs/design/b1gone-mascot-v2-questions.json and -v7-labels.json.
export const exampleQuestions = [
  { id: 'attention', lines: ['NEW ATTENTION', 'MECHANISMS?'], beam: '#ef4315', ink: '#942e12', edge: [10, 50],
    question: '2024-2026年Transformer在长序列建模与注意力机制方面有哪些基础性创新？',
    full: 'What innovations in long-sequence modeling and attention mechanisms have emerged in Transformer architectures from 2024 to 2026?' },
  { id: 'variants', lines: ['NEW EFFICIENT', 'VARIANTS?'], beam: '#ffd452', ink: '#68430d', edge: [105, 145],
    question: '2024-2026年Transformer稀疏化、线性化及混合架构等高效变体有哪些新方法？',
    full: 'What new methods have emerged in efficient Transformer variants, including sparse, linear and hybrid architectures, from 2024 to 2026?' },
  { id: 'benchmarks', lines: ['WHICH BENCHMARKS', 'AND DATASETS?'], beam: '#087c94', ink: '#00576b', edge: [205, 250],
    question: '近两年有哪些针对Transformer架构创新的评测基准与实证数据集？',
    full: 'Which benchmarks and empirical datasets evaluate Transformer architecture innovations over the past two years?' },
  { id: 'gains', lines: ['EFFICIENCY AND', 'ACCURACY GAINS?'], beam: '#7940dd', ink: '#4c247e', edge: [320, 365],
    question: '2024-2026年不同Transformer变体在推理效率与精度上有哪些对比改进？',
    full: 'How have different Transformer variants improved inference efficiency and accuracy from 2024 to 2026?' },
]
