import type { SVGProps } from 'react'

const paths = {
  pipeline: 'M8 1h4v4H8V1zM9 5h2v3h6v3h-2V10h-4v3h2v5H7v-5h2v-3H5v1H3V8h6V5zM1 12h6v6H1v-6zm12 0h6v6h-6v-6z',
  search: 'M5 2h6v1h2v2h1v6h-1v2h-2v1H5v-1H3v-2H2V5h1V3h2V2zm1 2v1H4v5h1v2h5v-1h2V6h-1V4H6zm7 9h2v2h2v2h2v2h-3v-2h-2v-2h-1v-2z',
  analysis: 'M3 10h3v8H3v-8zm5-5h3v13H8V5zm5 3h3v10h-3V8z',
  github: 'M10 1a9 9 0 0 0-2.85 17.54c.45.08.62-.19.62-.43v-1.68c-2.51.55-3.04-1.07-3.04-1.07-.41-1.04-1-1.32-1-1.32-.82-.56.06-.55.06-.55.9.06 1.38.93 1.38.93.8 1.37 2.11.98 2.63.75.08-.58.31-.98.57-1.2-2-.23-4.11-1-4.11-4.45 0-.98.35-1.78.93-2.41-.09-.23-.4-1.14.09-2.38 0 0 .76-.24 2.48.92a8.62 8.62 0 0 1 4.51 0c1.72-1.16 2.48-.92 2.48-.92.49 1.24.18 2.15.09 2.38.58.63.93 1.43.93 2.41 0 3.46-2.11 4.22-4.12 4.44.33.28.62.83.62 1.68v2.47c0 .24.16.51.62.43A9 9 0 0 0 10 1z',
  archive: 'M4 1h9v1h2v2h1v15H4V1zm2 2v14h8V5h-3V3H6zm7 0v2h1V4h-1V3zM7 6h2v2H7V6zm3 0h2v2h-2V6zM7 10h5v1H7v-1zm0 3h5v1H7v-1z',
  plus: 'M9 2h2v7h7v2h-7v7H9v-7H2V9h7V2z',
  close: 'M3 3h3v3h2v2h4V6h2V3h3v3h-3v2h-2v4h2v2h3v3h-3v-3h-2v-2H8v2H6v3H3v-3h3v-2h2V8H6V6H3V3z',
  user: 'M7 3h6v2h1v5h-2v2H8v-2H6V5h1V3zm0 11h6v1h3v2h1v2H3v-2h1v-2h3v-1z',
  chevron: 'M7 3h2v2h2v2h2v2h2v2h-2v2h-2v2H9v2H7v-2h2v-2h2v-2h2V9h-2V7H9V5H7V3z',
  play: 'M5 3h2v2h3v2h3v2h3v2h-3v2h-3v2H7v2H5V3z',
  download: 'M9 1h2v9h3v2h-2v2h-1v2H9v-2H8v-2H6v-2h3V1zM3 14h2v3h10v-3h2v5H3v-5z',
  enter: 'M15 3h2v9H7v3H5v-2H3v-2H1V9h2V7h2V5h2v3h8V3zM5 9v2h10V9H5z',
  external: 'M10 2h8v8h-2V6h-2v2h-2v2h-2v2H8v-2h2V8h2V6h2V4h-4V2zM2 5h6v2H4v9h9v-4h2v6H2V5z',
  check: 'M2 9h2v2h2v2h2v-2h2V9h2V7h2V5h2V3h2v4h-2v2h-2v2h-2v2h-2v2H8v2H6v-2H4v-2H2V9z',
  stop: 'M4 4h12v12H4V4z',
  menu: 'M2 4h16v2H2V4zm0 5h16v2H2V9zm0 5h16v2H2v-2z',
  collapse: 'M1 2h18v16H1V2zm2 2v12h14V4H3zm3 0h2v12H6V4zm7 3h2v2h-2V7zm-2 2h2v2h-2V9zm2 2h2v2h-2v-2z',
  expand: 'M1 2h18v16H1V2zm2 2v12h14V4H3zm3 0h2v12H6V4zm5 3h2v2h-2V7zm2 2h2v2h-2V9zm-2 2h2v2h-2v-2z',
  settings: 'M8 1h4v3h2V3h3v3h-1v2h3v4h-3v2h1v3h-3v-1h-2v3H8v-3H6v1H3v-3h1v-2H1V8h3V6H3V3h3v1h2V1zm0 6v1H7v4h1v1h4v-1h1V8h-1V7H8zm1 2h2v2H9V9z',
  copy: 'M6 2h11v13h-3v3H3V5h3V2zm2 2v1h6v8h1V4H8zM5 7v9h7V7H5z',
} as const

export type IconName = keyof typeof paths

export function PixelIcon({ name, ...props }: SVGProps<SVGSVGElement> & { name: IconName }) {
  return <svg viewBox="0 0 20 20" fill="currentColor" shapeRendering="crispEdges" aria-hidden="true" focusable="false" {...props}><path d={paths[name]} /></svg>
}

const letters: Record<string, string[]> = {
  B: ['11110', '11001', '11001', '11110', '11001', '11001', '11110'],
  '1': ['01100', '11100', '01100', '01100', '01100', '01100', '11111'],
  G: ['01111', '11000', '11000', '11011', '11001', '11001', '01111'],
  O: ['01110', '11011', '11011', '11011', '11011', '11011', '01110'],
  N: ['11001', '11101', '11101', '11011', '11011', '11001', '11001'],
  E: ['11111', '11000', '11000', '11110', '11000', '11000', '11111'],
}

export function Wordmark({ className = '' }: { className?: string }) {
  return <svg className={`wordmark ${className}`} viewBox="0 0 35 7" fill="currentColor" shapeRendering="crispEdges" role="img" aria-label="B1GONE">
    {'B1GONE'.split('').flatMap((letter, index) => letters[letter].flatMap((row, y) => row.split('').flatMap((pixel, x) => pixel === '1' ? <rect key={`${index}-${x}-${y}`} x={index * 6 + x} y={y} width="1" height="1" /> : [])))}
  </svg>
}
