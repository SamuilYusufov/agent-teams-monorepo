import type { ReactNode } from 'react'
import { useAction } from '../api/useAction'
import { Modal } from './Modal'

type ConfirmDialogProps = {
  /** The question, naming the thing: "Delete Apollo?" */
  title: string
  /** What will happen, so the choice is informed. */
  children: ReactNode
  /** The action, never just "OK": "Delete project". */
  confirmLabel: string
  onConfirm: () => Promise<unknown>
  onClose: () => void
}

/** "Are you sure?" before a destructive action. Focus starts on Cancel, so a stray Enter doesn't delete. */
export function ConfirmDialog({ title, children, confirmLabel, onConfirm, onClose }: ConfirmDialogProps) {
  const { run, busy, error } = useAction()

  async function confirm() {
    if (await run(onConfirm)) onClose()
  }

  return (
    <Modal title={title} onClose={onClose}>
      <div className="confirm-text">{children}</div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <div className="form-actions">
        <button type="button" className="button-quiet" onClick={onClose} data-autofocus>
          Cancel
        </button>
        <button type="button" className="button button-danger" onClick={confirm} disabled={busy}>
          {busy ? 'Working…' : confirmLabel}
        </button>
      </div>
    </Modal>
  )
}
