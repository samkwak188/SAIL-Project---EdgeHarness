import { useState } from 'react'

export function Composer({ onSend, busy }: { onSend: (text: string) => void; busy: boolean }) {
  const [text, setText] = useState('')
  const submit = () => {
    const t = text.trim()
    if (!t || busy) return
    setText('')
    onSend(t)
  }
  return (
    <div className="border-t border-gray-300 p-3 flex gap-2">
      <textarea
        className="flex-1 border border-gray-300 rounded px-2 py-1 resize-none"
        rows={2}
        value={text}
        placeholder="Message…"
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            submit()
          }
        }}
      />
      <button className="border border-gray-300 rounded px-3 disabled:opacity-50" onClick={submit} disabled={busy}>
        Send
      </button>
    </div>
  )
}
