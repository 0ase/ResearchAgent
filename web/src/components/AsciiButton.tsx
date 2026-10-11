import { useEffect, useRef, useState, type ButtonHTMLAttributes } from 'react'

const glyphs = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#$%&*+-/<>'

// The animation belongs to this label, not the page or the submitted question.
export function AsciiButton({ label, motionEnabled, children, onMouseEnter, onFocus, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { label: string; motionEnabled: boolean }) {
  const [frame, setFrame] = useState({ label, text: label, decoding: false })
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const sequence = useRef(0)
  useEffect(() => {
    if (!motionEnabled) { sequence.current++; clearTimeout(timer.current); setFrame({ label, text: label, decoding: false }) }
    return () => { sequence.current++; clearTimeout(timer.current) }
  }, [motionEnabled, label])

  function decode() {
    if (!motionEnabled || props.disabled) return
    clearTimeout(timer.current)
    const token = ++sequence.current
    const characters = Array.from(label)
    let step = 0
    function tick() {
      if (token !== sequence.current) return
      const resolved = Math.floor(step / 6 * characters.length)
      setFrame({ label, text: characters.map((character, index) => index < resolved ? character : glyphs[Math.floor(Math.random() * glyphs.length)]).join(''), decoding: step < 6 })
      if (step++ < 6) timer.current = setTimeout(tick, 55)
    }
    tick()
  }

  const animated = motionEnabled && frame.label === label && frame.decoding
  return <button {...props} aria-label={props['aria-label'] ?? label}
    onMouseEnter={event => { decode(); onMouseEnter?.(event) }}
    onFocus={event => { decode(); onFocus?.(event) }}>
    {children}<span className="ascii-key-label" aria-hidden="true" data-phase={animated ? 'decoding' : 'idle'} style={{ inlineSize: `${Array.from(label).length}em` }}>{animated ? frame.text : label}</span>
  </button>
}
