import { useEffect, useState } from 'react'

const researchExamples = ['大语言模型如何辅助科研？', '检索增强方法有哪些局限？', '这个领域有哪些研究空白？', '如何比较不同方法的证据？']
const asciiCharacters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#$%&*+-/<>[]{}'
const scrambleFrames = 3
const scrambleInterval = 70
const characterPause = 45
const questionPause = 5900
const deleteInterval = 65
const switchPause = 500

interface HintFrame {
  text: string
  glyph: string
  phase: 'decoding' | 'holding' | 'deleting' | 'switching'
}

// Only this decorative child updates during decoding; input values and reports
// never subscribe to its clock. Unmounting the hint stops its pending frame.
export function AnimatedPromptHint({ examples = researchExamples }: { examples?: readonly string[] }) {
  const [frame, setFrame] = useState<HintFrame>({ text: '', glyph: '', phase: 'decoding' })
  useEffect(() => {
    let exampleIndex = 0
    let characters = Array.from(examples[exampleIndex])
    let resolved = 0
    let scrambleStep = 0
    let lastGlyph = ''
    let phase: HintFrame['phase'] = 'decoding'
    let timer: ReturnType<typeof setTimeout>
    const schedule = (delay: number) => { timer = setTimeout(tick, delay) }
    function tick() {
      if (phase === 'decoding') {
        if (resolved === characters.length) {
          phase = 'holding'
          setFrame({ text: characters.join(''), glyph: '', phase })
          schedule(questionPause)
        } else if (scrambleStep < scrambleFrames) {
          // Pick a different glyph each frame so a character visibly resolves.
          const candidates = asciiCharacters.replace(lastGlyph, '')
          lastGlyph = candidates[Math.floor(Math.random() * candidates.length)]
          setFrame({ text: characters.slice(0, resolved).join(''), glyph: lastGlyph, phase })
          scrambleStep++
          schedule(scrambleInterval)
        } else {
          resolved++
          scrambleStep = 0
          setFrame({ text: characters.slice(0, resolved).join(''), glyph: '', phase })
          schedule(characterPause)
        }
      } else if (phase === 'holding' || phase === 'deleting') {
        phase = 'deleting'
        resolved--
        setFrame({ text: characters.slice(0, resolved).join(''), glyph: '', phase })
        if (resolved > 0) schedule(deleteInterval)
        else { phase = 'switching'; schedule(switchPause) }
      } else {
        exampleIndex = (exampleIndex + 1) % examples.length
        characters = Array.from(examples[exampleIndex])
        phase = 'decoding'
        scrambleStep = 0
        tick()
      }
    }
    schedule(switchPause)
    return () => clearTimeout(timer)
  }, [examples])

  return <span className="prompt-animated-hint" aria-hidden="true" data-phase={frame.phase}>
    <span className="prompt-resolved-text">{frame.text}</span>
    {frame.glyph ? <span className="prompt-cipher-glyph">{frame.glyph}</span> : null}
    <span className="prompt-hint-cursor"> |&lt;</span>
  </span>
}
