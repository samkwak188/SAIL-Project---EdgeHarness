import { useEffect, useRef } from 'react'
import Markdown from 'react-markdown'
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

function Working() {
  return (
    <div className="flex items-center gap-2 text-ink-3 text-[13px]">
      <span className="sail-pulse inline-block w-1.5 h-1.5 rounded-full bg-ink-3" />
      Working…
    </div>
  )
}

function AssistantMessage({ turn }: { turn: AssistantTurn }) {
  const router = turn.events.find((e) => e.type === 'router_decision')
  const answer = turn.events.find((e) => e.type === 'answer')
  const error = turn.events.find((e) => e.type === 'error')
  const cards = toolCards(turn.events)
  const working = !turn.done && !answer && !error
  return (
    <div className="space-y-2">
      {router && router.type === 'router_decision' && (
        <div>
          <RouterChip taskType={router.data.task_type} confidence={router.data.confidence} path={router.data.path} />
        </div>
      )}
      {cards.map((c, i) => (
        <ToolCard key={i} tool={c} />
      ))}
      {answer && answer.type === 'answer' && (
        <div className="sail-prose max-w-[72ch] pt-1">
          <Markdown>{answer.data.text}</Markdown>
        </div>
      )}
      {error && error.type === 'error' && <div className="text-err text-[13px] pt-1">{error.data.message}</div>}
      {working && <Working />}
    </div>
  )
}

export function Thread({ turns }: { turns: Turn[] }) {
  const endRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns])

  if (turns.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-ink-3 text-[13px]">
        Send a message — the router picks a specialist and you watch it work.
      </div>
    )
  }

  return (
    <div className="flex-1 min-h-0 overflow-y-auto">
      <div className="max-w-[760px] mx-auto px-6 py-8 space-y-8">
        {turns.map((t, i) =>
          t.role === 'user' ? (
            <div key={i} className="flex justify-end">
              <div className="bg-panel rounded-[10px] px-4 py-2 max-w-[60%] whitespace-pre-wrap">{t.text}</div>
            </div>
          ) : (
            <AssistantMessage key={i} turn={t} />
          ),
        )}
        <div ref={endRef} />
      </div>
    </div>
  )
}
