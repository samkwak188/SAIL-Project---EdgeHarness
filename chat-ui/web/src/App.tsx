import { useRef, useState } from 'react'
import { streamChat } from './api'
import { Composer } from './components/Composer'
import { Sidebar } from './components/Sidebar'
import { Thread } from './components/Thread'
import type { AssistantTurn, SailEvent, Turn, Usage } from './types'

type StoredMessage = { role: 'user'; content: string } | { role: 'assistant'; events: SailEvent[] }

export default function App() {
  const [turns, setTurns] = useState<Turn[]>([])
  const [busy, setBusy] = useState(false)
  const [usage, setUsage] = useState<Usage>({ tokens_in: 0, tokens_out: 0, cost: 0 })
  const [currentId, setCurrentId] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const sessionId = useRef<string | null>(null)

  const newSession = () => {
    sessionId.current = null
    setCurrentId(null)
    setTurns([])
    setUsage({ tokens_in: 0, tokens_out: 0, cost: 0 })
  }

  const openSession = async (id: string) => {
    const s = await fetch(`/api/sessions/${id}`).then((r) => r.json())
    sessionId.current = id
    setCurrentId(id)
    const loaded: Turn[] = (s.messages as StoredMessage[]).map((m) =>
      m.role === 'user' ? { role: 'user', text: m.content } : { role: 'assistant', events: m.events, done: true },
    )
    setTurns(loaded)
    const total: Usage = { tokens_in: 0, tokens_out: 0, cost: 0 }
    for (const m of s.messages as StoredMessage[]) {
      if (m.role !== 'assistant') continue
      for (const ev of m.events) {
        if (ev.type === 'usage') {
          total.tokens_in += ev.data.tokens_in
          total.tokens_out += ev.data.tokens_out
          total.cost += ev.data.cost
        }
      }
    }
    setUsage(total)
  }

  const send = async (text: string) => {
    setBusy(true)
    const assistant: AssistantTurn = { role: 'assistant', events: [], done: false }
    setTurns((t) => [...t, { role: 'user', text }, assistant])
    await streamChat(text, sessionId.current, (ev) => {
      if (ev.type === 'session') {
        sessionId.current = ev.data.id
        setCurrentId(ev.data.id)
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
    setRefreshKey((k) => k + 1)
  }

  return (
    <div className="h-screen flex">
      <Sidebar currentId={currentId} refreshKey={refreshKey} onNew={newSession} onOpen={openSession} />
      <div className="flex-1 flex flex-col min-w-0">
        <Thread turns={turns} />
        <Composer onSend={send} busy={busy} />
        <div className="text-right text-xs text-gray-500 px-3 pb-1">
          ctx: {(usage.tokens_in + usage.tokens_out).toLocaleString()} tok · ${usage.cost.toFixed(4)}
        </div>
      </div>
    </div>
  )
}
