import { useEffect, useState } from 'react'

export function useMotionEnabled(enabled = true) {
  const [allowed, setAllowed] = useState(() => !window.matchMedia('(prefers-reduced-motion: reduce)').matches && !document.hidden)
  useEffect(() => {
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setAllowed(!preference.matches && !document.hidden)
    preference.addEventListener('change', update)
    document.addEventListener('visibilitychange', update)
    return () => {
      preference.removeEventListener('change', update)
      document.removeEventListener('visibilitychange', update)
    }
  }, [])
  return enabled && allowed
}
