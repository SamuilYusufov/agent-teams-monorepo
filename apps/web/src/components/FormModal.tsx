import type { FormEvent, ReactNode } from 'react'
import { useAction } from '../api/useAction'
import { Modal } from './Modal'

type FormModalProps = {
  title: string
  /** Says what happens, e.g. "Create project". */
  submitLabel: string
  /** Saves the form. Throw to keep the form open and show the error; return to close it. */
  onSubmit: (form: FormData) => Promise<unknown>
  onClose: () => void
  children: ReactNode
  submitDisabled?: boolean
}

/** A modal form that shows progress while saving, keeps the input when saving fails, and closes when done. */
export function FormModal({ title, submitLabel, onSubmit, onClose, children, submitDisabled }: FormModalProps) {
  const { run, busy, error } = useAction()

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault() // stop the browser from reloading the page, its default for a submitted form
    const form = new FormData(event.currentTarget)
    if (await run(() => onSubmit(form))) onClose()
  }

  return (
    <Modal title={title} onClose={onClose}>
      <form className="form" onSubmit={handleSubmit}>
        {children}
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <div className="form-actions">
          <button type="submit" className="button" disabled={busy || submitDisabled}>
            {busy ? 'Saving…' : submitLabel}
          </button>
        </div>
      </form>
    </Modal>
  )
}
