import type { SVGProps } from 'react'

const paths = {
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
