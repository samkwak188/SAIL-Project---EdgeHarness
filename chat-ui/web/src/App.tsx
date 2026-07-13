import { useRef, useState } from 'react'
import { streamChat } from './api'
import { Composer } from './components/Composer'
import { Thread } from './components/Thread'
import type { AssistantTurn, Turn, Usage } from './types'

export default function App() {
  const [turns, setTurns] = useState<Turn[]>([])
  const [busy, setBusy] = useState(false)
  const [usage, setUsage] = useState<Usage>({ tokens_in: 0, tokens_out: 0, cost: 0 })
  const sessionId = useRef<string | null>(null)

  const send = async (text: string) => {
    setBusy(true)
    const assistant: AssistantTurn = { role: 'assistant', events: [], done: false }
    setTurns((t) => [...t, { role: 'user', text }, assistant])
    await streamChat(text, sessionId.current, (ev) => {
      if (ev.type === 'session') {
        sessionId.current = ev.data.id
        return
      }
      if (ev.type === 'usage') {
        setUsage((u) => ({
          tokens_in: u.tokens_in + ev.data.tokens_in,
          tokens_out: u.tokens_out + ev.data.tokens_out,
          cost: u.cost + ev.data.cost,
        }))
      }
      setTurns((t) => {
        const last = t[t.length - 1] as AssistantTurn
        return [...t.slice(0, -1), { ...last, events: [...last.events, ev] }]
      })
    })
    setTurns((t) => {
      const last = t[t.length - 1] as AssistantTurn
      return [...t.slice(0, -1), { ...last, done: true }]
    })
    setBusy(false)
  }

  return (
    <div className="h-screen flex flex-col max-w-3xl mx-auto">
      <Thread turns={turns} />
      <Composer onSend={send} busy={busy} />
      <div className="text-right text-xs text-gray-500 px-3 pb-1">
        ctx: {(usage.tokens_in + usage.tokens_out).toLocaleString()} tok · ${usage.cost.toFixed(4)}
      </div>
    </div>
  )
}
