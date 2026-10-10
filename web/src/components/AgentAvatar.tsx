import type { AgentKind } from '../data/agentRoles'

// A shared 24-pixel character silhouette, with a distinct tool for each role.
const body = 'M7 3h10v1h1v6h-1v1H7v-1H6V4h1V3zM9 11h6v2h2v5h1v3h-5v-3h-2v3H6v-3h1v-5h2v-2z'

const equipment: Record<AgentKind, { solid: string; cutout: string; detail: string }> = {
  supervisor: {
    solid: 'M5 1h14v2H5V1zM4 5h2v5H4V5zm14 0h2v5h-2V5zm0 4h2v3h-6v-1h4V9zM3 16h18v5H3v-5z',
    cutout: 'M5 18h14v1H5v-1z',
    detail: 'M5 17h3v2H5v-2zm5 0h3v2h-3v-2zm5 0h4v2h-4v-2z',
  },
  search: {
    solid: 'M16 10h5v1h1v5h-1v1h-5v-1h-1v-5h1v-1zm4 7h2v2h2v3h-2v-2h-2v-3z',
    cutout: 'M17 12h3v3h-3v-3z',
    detail: 'M7 1h5v2H7V1zM17 12h1v3h-1v-3z',
  },
  filter: {
    solid: 'M15 10h7v5h-7v-5zM2 14h17v2h-2v2h-3v2h-2v3H8v-3H6v-2H4v-2H2v-2z',
    cutout: 'M16 11h1v1h-1v-1zm2 0h1v1h-1v-1zm2 0h1v1h-1v-1zM6 16h9v1H6v-1z',
    detail: 'M16 13h5v1h-5v-1zM9 20h2v2H9v-2z',
  },
  read: {
    solid: 'M2 12h7v1h6v-1h7v9h-7v1H9v-1H2v-9z',
    cutout: 'M4 14h5v1H4v-1zm0 3h5v1H4v-1zm11-3h5v1h-5v-1zm0 3h5v1h-5v-1zM11 14h2v6h-2v-6z',
    detail: 'M4 19h5v1H4v-1zm11 0h5v1h-5v-1z',
  },
  analysis: {
    solid: 'M1 12h9v10H1V12zm13 0h9v10h-9V12zM10 15h4v2h-4v-2z',
    cutout: 'M3 14h5v6H3v-6zm13 0h5v6h-5v-6z',
    detail: 'M3 18h1v2H3v-2zm2-3h1v5H5v-5zm2 2h1v3H7v-3zm9 0h1v3h-1v-3zm2-3h1v6h-1v-6zm2 2h1v4h-1v-4z',
  },
  synthesize: {
    solid: 'M7 10h11v7H7v-7zM3 15h4v2h11v-2h3v7H3v-7z',
    cutout: 'M9 11h7v1H9v-1zm0 2h5v1H9v-1zM5 18h2v1H5v-1zm4 0h2v1H9v-1zm4 0h2v1h-2v-1zm4 0h2v1h-2v-1zM7 20h10v1H7v-1z',
    detail: 'M4 15h2v2H4v-2zm14 0h2v2h-2v-2z',
  },
  critic: {
    solid: 'M1 12h9v10H1V12zm15-1h4v5h-4v-5zm-1 5h6v3h-6v-3zm-1 3h8v3h-8v-3z',
    cutout: 'M3 14h5v1H3v-1zm0 3h1v1H3v-1zm1 1h1v1H4v-1zm1-1h1v1H5v-1zm1-1h2v1H6v-1zM16 20h4v1h-4v-1z',
    detail: 'M9 1h6v2H9V1zM16 12h4v1h-4v-1z',
  },
}

export function AgentAvatar({ kind, className = '' }: { kind: AgentKind; className?: string }) {
  const tool = equipment[kind]
  return <svg className={`agent-avatar ${className}`} viewBox="0 0 24 24" fill="currentColor" shapeRendering="crispEdges" aria-hidden="true" focusable="false">
    <path d={body} />
    <path className="agent-cutout" d="M9 6h2v2H9V6zm4 0h2v2h-2V6zM10 9h4v1h-4V9z" />
    <path d={tool.solid} />
    <path className="agent-cutout" d={tool.cutout} />
    <path className="agent-detail" d={tool.detail} />
  </svg>
}
