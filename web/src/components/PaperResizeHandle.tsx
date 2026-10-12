import { useLayoutEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from 'react'

interface ResizeState { width: number; min: number; max: number }
interface DragState { startX: number; startWidth: number; width: number }
const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, Math.round(value)))

export function PaperResizeHandle({ preferredWidth, onWidthChange }: {
  preferredWidth: number | undefined; onWidthChange: (width: number) => void
}) {
  const handleRef = useRef<HTMLDivElement>(null)
  const dragRef = useRef<DragState | null>(null)
  const [range, setRange] = useState<ResizeState>({ width: 340, min: 260, max: 960 })

  function getLayout() {
    const handle = handleRef.current
    const panel = handle?.parentElement
    const shell = panel?.closest<HTMLElement>('.app-shell')
    if (!handle || !panel || !shell) return null
    const sidebarWidth = shell.querySelector('.desktop-sidebar')?.getBoundingClientRect().width ?? 0
    const drawer = panel.matches('.papers-dialog')
    // Leave enough room for the report and composer while the papers are widened.
    const min = 260
    const max = Math.max(min, Math.floor(shell.getBoundingClientRect().width - (drawer ? 0 : sidebarWidth + 420)))
    return { handle, panel, shell, min, max }
  }

  function applyWidth(width: number) {
    const layout = getLayout()
    if (!layout) return
    const next = clamp(width, layout.min, layout.max)
    layout.shell.style.setProperty('--papers-current-width', `${next}px`)
    layout.handle.setAttribute('aria-valuenow', String(next))
    return next
  }

  useLayoutEffect(() => {
    const layout = getLayout()
    if (!layout) return
    const update = () => {
      const current = getLayout()
      if (!current || dragRef.current) return
      const measuredWidth = current.panel.getBoundingClientRect().width || Number.parseFloat(getComputedStyle(current.panel).width)
      const width = applyWidth(preferredWidth ?? measuredWidth)!
      setRange({ width, min: current.min, max: current.max })
    }
    update()
    const observer = new ResizeObserver(update)
    observer.observe(layout.shell)
    const sidebar = layout.shell.querySelector('.desktop-sidebar')
    if (sidebar) observer.observe(sidebar)
    return () => {
      observer.disconnect()
      dragRef.current = null
      layout.shell.classList.remove('is-resizing-papers')
      layout.shell.style.removeProperty('--papers-current-width')
    }
  }, [preferredWidth])

  function pointerDown(event: PointerEvent<HTMLDivElement>) {
    if (event.button !== 0) return
    const layout = getLayout()
    if (!layout) return
    event.preventDefault()
    event.currentTarget.focus()
    const width = layout.panel.getBoundingClientRect().width
    dragRef.current = { startX: event.clientX, startWidth: width, width }
    layout.shell.classList.add('is-resizing-papers')
    event.currentTarget.setPointerCapture(event.pointerId)
  }

  function pointerMove(event: PointerEvent<HTMLDivElement>) {
    const drag = dragRef.current
    if (!drag) return
    const width = applyWidth(drag.startWidth + drag.startX - event.clientX)
    if (width !== undefined) drag.width = width
  }

  function finishDrag(commit: boolean) {
    const drag = dragRef.current
    if (!drag) return
    dragRef.current = null
    const layout = getLayout()
    layout?.shell.classList.remove('is-resizing-papers')
    const width = applyWidth(commit ? drag.width : drag.startWidth)
    if (width !== undefined && layout) setRange({ width, min: layout.min, max: layout.max })
    if (commit && width !== undefined) onWidthChange(width)
  }

  function pointerEnd(event: PointerEvent<HTMLDivElement>, commit: boolean) {
    finishDrag(commit)
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
  }

  function keyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape' && dragRef.current) {
      event.preventDefault()
      finishDrag(false)
      return
    }
    const layout = getLayout()
    if (!layout) return
    const width = layout.panel.getBoundingClientRect().width
    const step = event.shiftKey ? 40 : 16
    const next = event.key === 'ArrowLeft' ? width + step : event.key === 'ArrowRight' ? width - step : event.key === 'Home' ? layout.min : event.key === 'End' ? layout.max : null
    if (next === null) return
    event.preventDefault()
    const applied = applyWidth(next)
    if (applied !== undefined) onWidthChange(applied)
  }

  return <div ref={handleRef} className="paper-resize-handle" role="separator" tabIndex={0}
    aria-label="调整研究文献栏宽度" aria-orientation="vertical" aria-controls="papers-heading"
    aria-valuemin={range.min} aria-valuemax={range.max} aria-valuenow={range.width}
    title="拖动调整宽度，也可使用左右方向键"
    onPointerDown={pointerDown} onPointerMove={pointerMove}
    onPointerUp={event => pointerEnd(event, true)} onPointerCancel={event => pointerEnd(event, false)}
    onLostPointerCapture={() => finishDrag(true)} onKeyDown={keyDown} />
}
