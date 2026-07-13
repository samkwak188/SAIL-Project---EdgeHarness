export type SailEvent =
  | { type: 'session'; data: { id: string } }
  | { type: 'router_decision'; data: { task_type: string; confidence: number; path: string } }
  | { type: 'turn_start'; data: { agent: string; turn: number } }
  | { type: 'tool_call_start'; data: { name: string; arguments: Record<string, unknown> } }
  | { type: 'tool_result'; data: { name: string; ok: boolean; output: string; error: string } }
  | { type: 'answer'; data: { text: string; ok: boolean; error: string } }
  | { type: 'usage'; data: { tokens_in: number; tokens_out: number; cost: number; elapsed_ms: number } }
  | { type: 'error'; data: { message: string } }

export type UserTurn = { role: 'user'; text: string }
export type AssistantTurn = { role: 'assistant'; events: SailEvent[]; done: boolean }
export type Turn = UserTurn | AssistantTurn

export type Usage = { tokens_in: number; tokens_out: number; cost: number }
