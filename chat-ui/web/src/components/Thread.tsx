import { useEffect, useRef } from 'react'
import type { AssistantTurn, SailEvent, Turn } from '../types'
import { RouterChip } from './RouterChip'
import { ToolCard, type ToolCardData } from './ToolCard'

function toolCards(events: SailEvent[]): ToolCardData[] {
  const cards: ToolCardData[] = []
  for (const ev of events) {
    if (ev.type === 'tool_call_start') {
      cards.push({ name: ev.data.name, args: ev.data.arguments, status: 'running' })
    } else if (ev.type === 'tool_result') {
      const card = cards.findLast((c) => c.status === 'running' && c.name === ev.data.name)
      if (card) {
        card.status = ev.data.ok ? 'done' : 'failed'
        card.output = ev.data.output
        card.error = ev.data.error
      }
    }
  }
  return cards
}

function AssistantMessage({ turn }: { turn: AssistantTurn }) {
  const router = turn.events.find((e) => e.type === 'router_decision')
  const answer = turn.events.find((e) => e.type === 'answer')
  const error = turn.events.find((e) => e.type === 'error')
  const cards = toolCards(turn.events)
  const working = !turn.done && !answer && !error
  return (
    <div className="my-3">
      {router && router.type === 'router_decision' && (
        <div className="mb-1">
          <RouterChip taskType={router.data.task_type} confidence={router.data.confidence} path={router.data.path} />
        </div>
      )}
      {cards.map((c, i) => (
        <ToolCard key={i} tool={c} />
      ))}
      {answer && answer.type === 'answer' && <div className="whitespace-pre-wrap">{answer.data.text}</div>}
      {error && error.type === 'error' && <div className="text-red-600">{error.data.message}</div>}
      {working && <div className="text-gray-400 animate-pulse">thinking…</div>}
    </div>
  )
}

export function Thread({ turns }: { turns: Turn[] }) {
  const endRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns])
  return (
    <div className="flex-1 overflow-y-auto px-4">
      {turns.map((t, i) =>
        t.role === 'user' ? (
          <div key={i} className="my-3 text-right">
            <span className="inline-block bg-gray-100 rounded px-3 py-1.5">{t.text}</span>
          </div>
        ) : (
          <AssistantMessage key={i} turn={t} />
        ),
      )}
      <div ref={endRef} />
    </div>
  )
}
