import { useEffect, useState, type ChangeEventHandler, type KeyboardEventHandler, type Ref } from 'react'

const researchExamples = ['大语言模型如何辅助科研？', '检索增强方法有哪些局限？', '这个领域有哪些研究空白？', '如何比较不同方法的证据？']
const followupExamples = ['这些结论有哪些共同局限？', '哪些文献支持主要观点？', '不同方法之间有哪些差异？']
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

// Only this decorative child updates during decoding; reports and input state
// never subscribe to the animation clock. Text here is not the textarea value.
function AnimatedPromptHint({ examples }: { examples: string[] }) {
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

export function ResearchPrompt({ inputRef, value, onChange, onKeyDown, disabled, placeholder, maxLength, followup, suspended }: {
  inputRef: Ref<HTMLTextAreaElement>
  value: string
  onChange: ChangeEventHandler<HTMLTextAreaElement>
  onKeyDown: KeyboardEventHandler<HTMLTextAreaElement>
  disabled: boolean
  placeholder: string
  maxLength: number
  followup: boolean
  suspended: boolean
}) {
  const [focused, setFocused] = useState(false)
  const [motionAllowed, setMotionAllowed] = useState(() => !window.matchMedia('(prefers-reduced-motion: reduce)').matches && !document.hidden)
  useEffect(() => {
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setMotionAllowed(!preference.matches && !document.hidden)
    preference.addEventListener('change', update)
    document.addEventListener('visibilitychange', update)
    return () => { preference.removeEventListener('change', update); document.removeEventListener('visibilitychange', update) }
  }, [])
  const animated = motionAllowed && !focused && !value && !disabled && !suspended
  return <div className={`composer-input ${animated ? 'has-animated-hint' : ''}`}>
    <textarea id="research-prompt" ref={inputRef} value={value} onChange={onChange} onKeyDown={onKeyDown}
      onFocus={() => setFocused(true)} onBlur={() => setFocused(false)} rows={1} maxLength={maxLength}
      disabled={disabled} placeholder={placeholder} />
    {animated ? <AnimatedPromptHint key={followup ? 'followup' : 'research'} examples={followup ? followupExamples : researchExamples} /> : null}
  </div>
}
