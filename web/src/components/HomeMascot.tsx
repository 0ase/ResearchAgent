import { exampleQuestions } from '../data/homepage'

function RobotHead() {
  return <g shapeRendering="crispEdges">
    <path fill="#080c0d" d="M17 0h6v1h1v5h-1v1h-6V6h-1V1h1V0zM19 7h2v4h-2V7z" />
    <path fill="#f48022" d="M17 1h6v5h-6V1z" />
    <path fill="#080c0d" d="M0 23h5v7H0v-7zm35 0h5v7h-5v-7z" />
    <path fill="var(--color-keycap)" d="M2 24h2v5H2v-5zm34 0h2v5h-2v-5z" />
    <path fill="#080c0d" d="M9 11h22v1h2v1h1v2h1v22h-1v2h-2v1h-2v1H10v-1H8v-1H6v-2H5V15h1v-2h1v-1h2v-1z" />
    <path fill="var(--color-keycap)" d="M10 12h20v1h2v1h1v2h1v20h-1v2h-2v1h-2v1H11v-1H9v-1H7v-2H6V16h1v-2h1v-1h2v-1z" />
    <path fill="#080c0d" d="M10 18h20v1h1v9h-1v1H10v-1H9v-9h1v-1z" />
    <path fill="var(--color-keycap)" d="M13 20h3v6h-3v-6zm11 0h3v6h-3v-6z" />
    <path fill="#080c0d" d="M15 32h2v2h6v-2h2v2h-2v2h-6v-2h-2v-2z" />
  </g>
}

export function HomeMascot() {
  return <figure className="home-visual" aria-label="研究问题拆解示例">
    <svg className="home-mascot" viewBox="0 0 1000 400" role="img" aria-labelledby="home-mascot-title">
      <title id="home-mascot-title">像素机器人将 Transformer 架构近两年的创新拆解为注意力机制、高效变体、评测数据及效率与精度四个子问题。</title>
      <path className="home-input-beam" d="M-2000 200H300" stroke="var(--color-ink)" strokeWidth="6" fill="none" />
      <g className="home-input-example" fill="var(--color-ink)">
        <text x="0" y="148">TRANSFORMER</text>
        <text x="0" y="180">ARCHITECTURE:</text>
        <text x="0" y="252">WHAT'S NEW OVER</text>
        <text x="0" y="284" textLength="320" lengthAdjust="spacingAndGlyphs">THE PAST TWO YEARS?</text>
      </g>
      <g className="home-question-rays">
        {exampleQuestions.map(question => <g key={question.id} data-question={question.id}>
          <polygon fill={question.beam} points={`620,200 825,${question.edge[0]} 825,${question.edge[1]}`} />
          <text fill={question.ink} x="838" y={question.edge[0] + 24}>
            {question.lines.map((line, index) => <tspan key={line} x="838" dy={index ? 32 : 0} textLength={line.length > 14 ? 245 : undefined} lengthAdjust="spacingAndGlyphs">{line}</tspan>)}
          </text>
        </g>)}
      </g>
      <g className="home-robot-head" transform="translate(300 -8) scale(8)"><RobotHead /></g>
    </svg>
    <div className="home-mobile-example">
      <p className="home-mobile-question">TRANSFORMER ARCHITECTURE:<br />WHAT'S NEW OVER THE PAST TWO YEARS?</p>
      <svg className="home-mobile-head" viewBox="0 0 40 44" aria-hidden="true"><RobotHead /></svg>
      <ul className="home-mobile-subquestions">
        {exampleQuestions.map(question => <li key={question.id} style={{ borderColor: question.beam, color: question.ink }}>{question.lines.join(' ')}</li>)}
      </ul>
    </div>
    <figcaption className="sr-only">实际问题拆解的展示示例。开始研究时使用输入框中的问题。</figcaption>
  </figure>
}
