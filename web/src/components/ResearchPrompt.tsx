import { useEffect, useState, type ChangeEventHandler, type KeyboardEventHandler, type Ref } from 'react'
import { AnimatedPromptHint } from './AnimatedPromptHint'

const followupExamples = ['这些结论有哪些共同局限？', '哪些文献支持主要观点？', '不同方法之间有哪些差异？']

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
    {animated ? <AnimatedPromptHint key={followup ? 'followup' : 'research'} examples={followup ? followupExamples : undefined} /> : null}
  </div>
}
