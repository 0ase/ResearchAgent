import { useCallback, useEffect, useState } from 'react'

export type PageName = 'home' | 'research'

function currentPage(): PageName {
  return window.location.pathname.replace(/\/$/, '') === '/research' ? 'research' : 'home'
}

export function usePageNavigation() {
  const [page, setPage] = useState(currentPage)

  useEffect(() => {
    const update = () => setPage(currentPage())
    window.addEventListener('popstate', update)
    return () => window.removeEventListener('popstate', update)
  }, [])

  const navigate = useCallback((next: PageName) => {
    const url = new URL(window.location.href)
    const path = next === 'home' ? '/' : '/research'
    if (url.pathname !== path) {
      url.pathname = path
      url.hash = ''
      window.history.pushState(null, '', url)
    }
    setPage(next)
  }, [])

  return { page, navigate }
}
