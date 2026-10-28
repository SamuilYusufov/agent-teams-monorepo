import { useEffect, useId, useRef, type ReactNode } from 'react'
import { CloseIcon } from './icons'

type ModalProps = {
  title: string
  onClose: () => void
  children: ReactNode
  /** `dialog` is centered; `drawer` slides in from the right for longer, side-by-side work. */
  variant?: 'dialog' | 'drawer'
}

/**
 * A modal built on the native <dialog> element, which gives us for free: focus moves into the dialog and is
 * trapped there, Escape closes it, the rest of the page is inert, and focus returns to the opening button.
 *
 * Put `data-autofocus` on the element that should have focus first; otherwise it's the first focusable one.
 *
 * Render it conditionally (`{open && <Modal …/>}`): it opens when it mounts and calls `onClose` when it closes.
 */
export function Modal({ title, onClose, children, variant = 'dialog' }: ModalProps) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()

  useEffect(() => {
    const dialog = ref.current
    if (!dialog || dialog.open) return
    dialog.showModal()
    // React's `autoFocus` runs before the dialog is open, when nothing in it can take focus. So mark the element
    // that should start with focus with `data-autofocus`, and focus it here once the dialog is open.
    dialog.querySelector<HTMLElement>('[data-autofocus]')?.focus()
  }, [])

  return (
    <dialog
      ref={ref}
      className={`modal modal-${variant}`}
      aria-labelledby={titleId}
      onClose={onClose}
      // A click on the backdrop lands on the <dialog> itself rather than on its content.
      onClick={(event) => event.target === ref.current && ref.current.close()}
    >
      <div className="modal-body">
        <header className="modal-header">
          <h2 id={titleId}>{title}</h2>
          <button type="button" className="icon-button" aria-label="Close" onClick={() => ref.current?.close()}>
            <CloseIcon />
          </button>
        </header>
        {children}
      </div>
    </dialog>
  )
}
