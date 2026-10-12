import { useLayoutEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from 'react'

interface ResizeRange { width: number; min: number; max: number }
interface DragState { startX: number; startWidth: number; width: number }
const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, Math.round(value)))

export function SidebarResizeHandle({ preferredWidth, papersVisible, onWidthChange }: {
  preferredWidth: number | undefined; papersVisible: boolean; onWidthChange: (width: number) => void
}) {
  const handleRef = useRef<HTMLDivElement>(null)
  const dragRef = useRef<DragState | null>(null)
  const [range, setRange] = useState<ResizeRange>({ width: 294, min: 220, max: 480 })

  function getLayout() {
    const handle = handleRef.current
    const panel = handle?.parentElement
    const shell = panel?.closest<HTMLElement>('.app-shell')
    if (!handle || !panel || !shell) return null
    const papers = shell.querySelector<HTMLElement>('.paper-panel')
    const paperWidth = papers?.getBoundingClientRect().width ?? 0
    const min = 220
    // Both sidebars share the available space; preserve room for the report and composer.
    const max = Math.max(min, Math.min(480, Math.floor(shell.getBoundingClientRect().width - paperWidth - 420)))
    return { handle, panel, shell, papers, min, max }
  }

  function applyWidth(width: number) {
    const layout = getLayout()
    if (!layout || !layout.panel.getClientRects().length) return
    const next = clamp(width, layout.min, layout.max)
    layout.shell.style.setProperty('--sidebar-current-width', `${next}px`)
    layout.handle.setAttribute('aria-valuenow', String(next))
    return next
  }

  useLayoutEffect(() => {
    const layout = getLayout()
    if (!layout) return
    const update = () => {
      const current = getLayout()
      if (!current || dragRef.current || !current.panel.getClientRects().length) return
      const width = applyWidth(preferredWidth ?? current.panel.getBoundingClientRect().width)
      if (width === undefined) return
      setRange(previous => previous.width === width && previous.min === current.min && previous.max === current.max
        ? previous : { width, min: current.min, max: current.max })
    }
    update()
    const observer = new ResizeObserver(update)
    observer.observe(layout.shell)
    if (layout.papers) observer.observe(layout.papers)
    return () => {
      observer.disconnect()
      dragRef.current = null
      layout.shell.classList.remove('is-resizing-sidebar')
      layout.shell.style.removeProperty('--sidebar-current-width')
    }
  }, [preferredWidth, papersVisible])

  function pointerDown(event: PointerEvent<HTMLDivElement>) {
    if (event.button !== 0) return
    const layout = getLayout()
    if (!layout) return
    event.preventDefault()
    event.currentTarget.focus()
    const width = layout.panel.getBoundingClientRect().width
    dragRef.current = { startX: event.clientX, startWidth: width, width }
    layout.shell.classList.add('is-resizing-sidebar')
    event.currentTarget.setPointerCapture(event.pointerId)
  }

  function pointerMove(event: PointerEvent<HTMLDivElement>) {
    const drag = dragRef.current
    if (!drag) return
    const width = applyWidth(drag.startWidth + event.clientX - drag.startX)
    if (width !== undefined) drag.width = width
  }

  function finishDrag(commit: boolean) {
    const drag = dragRef.current
    if (!drag) return
    dragRef.current = null
    const layout = getLayout()
    layout?.shell.classList.remove('is-resizing-sidebar')
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
    const next = event.key === 'ArrowLeft' ? width - step : event.key === 'ArrowRight' ? width + step
      : event.key === 'Home' ? layout.min : event.key === 'End' ? layout.max : null
    if (next === null) return
    event.preventDefault()
    const applied = applyWidth(next)
    if (applied !== undefined) onWidthChange(applied)
  }

  return <div ref={handleRef} className="sidebar-resize-handle" role="separator" tabIndex={0}
    aria-label="调整研究记录栏宽度" aria-orientation="vertical" aria-controls="desktop-sidebar-content"
    aria-valuemin={range.min} aria-valuemax={range.max} aria-valuenow={range.width}
    title="拖动调整宽度，也可使用左右方向键"
    onPointerDown={pointerDown} onPointerMove={pointerMove}
    onPointerUp={event => pointerEnd(event, true)} onPointerCancel={event => pointerEnd(event, false)}
    onLostPointerCapture={() => finishDrag(true)} onKeyDown={keyDown} />
}
