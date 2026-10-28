import { useState } from 'react'
import { describeError } from './errors'

/**
 * Run changes to the API from event handlers, e.g. a button click, and keep track of whether one is running
 * and whether the last one failed.
 */
export function useAction() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()

  async function run(action: () => Promise<unknown>): Promise<boolean> {
    setBusy(true)
    setError(undefined)
    try {
      await action()
      return true
    } catch (e) {
      setError(describeError(e))
      return false
    } finally {
      setBusy(false)
    }
  }

  return { run, busy, error }
}
