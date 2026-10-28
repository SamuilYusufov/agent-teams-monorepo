/** "1 role", "3 roles". */
export function plural(count: number, word: string): string {
  return `${count} ${word}${count === 1 ? '' : 's'}`
}

/** Look up items by ID, e.g. the role of an agent. */
export function byId<T extends { id: string }>(items: T[]): Map<string, T> {
  return new Map(items.map((item) => [item.id, item]))
}

/** A trimmed text field of a submitted form. */
export function textField(form: FormData, name: string): string {
  return String(form.get(name) ?? '').trim()
}

/** A textarea with one entry per line, without blank lines. */
export function linesField(form: FormData, name: string): string[] {
  return textField(form, name)
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
}
