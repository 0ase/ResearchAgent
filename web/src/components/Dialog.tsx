import { useEffect, useRef, type ReactNode } from 'react'

export function Dialog({ open, onClose, labelId, className = '', children }: {
  open: boolean; onClose: () => void; labelId: string; className?: string; children: ReactNode
}) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])
  return <dialog ref={ref} className={className} aria-labelledby={labelId}
    onCancel={event => { event.preventDefault(); onClose() }}
    onClick={event => { if (event.target === ref.current) { const box = ref.current!.getBoundingClientRect(); if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) onClose() } }}>
    {children}
  </dialog>
}
