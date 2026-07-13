import type { SailEvent } from './types'

/** POST /api/chat and parse the SSE stream, invoking onEvent per event. */
export async function streamChat(
  message: string,
  sessionId: string | null,
  onEvent: (ev: SailEvent) => void,
): Promise<void> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId }),
  })
  if (!res.ok || !res.body) {
    onEvent({ type: 'error', data: { message: `HTTP ${res.status}` } })
    return
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    let idx
    while ((idx = buf.indexOf('\n\n')) !== -1) {
      const chunk = buf.slice(0, idx)
      buf = buf.slice(idx + 2)
      const evMatch = chunk.match(/^event: (.+)$/m)
      const dataMatch = chunk.match(/^data: (.+)$/m)
      if (evMatch && dataMatch) {
        onEvent({ type: evMatch[1], data: JSON.parse(dataMatch[1]) } as SailEvent)
      }
    }
  }
}
