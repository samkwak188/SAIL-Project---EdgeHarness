import { useState } from 'react'
import { ModelPicker } from './ModelPicker'

export function Composer({ onSend, busy }: { onSend: (text: string) => void; busy: boolean }) {
  const [text, setText] = useState('')
  const submit = () => {
    const t = text.trim()
    if (!t || busy) return
    setText('')
    onSend(t)
  }
  return (
    <div className="max-w-[760px] w-full mx-auto px-6 pb-2">
      <div className="border border-line rounded-[16px] bg-bg shadow-halo">
        <textarea
          className="w-full resize-none px-4 pt-3 pb-1 bg-transparent focus-visible:outline-none"
          rows={2}
          value={text}
          placeholder="Message SAIL…"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submit()
            }
          }}
        />
        <div className="flex items-center justify-between px-3 pb-2.5">
          <ModelPicker />
          <button
            className="bg-ink text-bg rounded-[10px] px-4 py-1.5 text-[13px] font-medium transition-opacity duration-150 disabled:opacity-40 cursor-pointer disabled:cursor-default"
            onClick={submit}
            disabled={busy || !text.trim()}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
