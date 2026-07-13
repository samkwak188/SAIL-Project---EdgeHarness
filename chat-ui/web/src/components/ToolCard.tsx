import { useState } from 'react'

export type ToolCardData = {
  name: string
  args: Record<string, unknown>
  status: 'running' | 'done' | 'failed'
  output?: string
  error?: string
}

function StatusMark({ status }: { status: ToolCardData['status'] }) {
  if (status === 'running')
    return (
      <span className="flex items-center gap-1.5 text-ink-3">
        <span className="sail-pulse inline-block w-1.5 h-1.5 rounded-full bg-ink-3" />
        running
      </span>
    )
  if (status === 'failed') return <span className="text-err">×&ensp;failed</span>
  return <span className="text-ok">✓</span>
}

export function ToolCard({ tool }: { tool: ToolCardData }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-line rounded-[10px] bg-bg font-mono text-[12.5px]">
      <button
        className="w-full flex items-center gap-2 px-3 py-1.5 text-left cursor-pointer"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <span className="text-ink-3 text-[10px] select-none">{open ? '▾' : '▸'}</span>
        <span className="text-ink flex-1">{tool.name}</span>
        <StatusMark status={tool.status} />
      </button>
      {open && (
        <div className="border-t border-line bg-panel rounded-b-[10px] px-3 py-2 space-y-1.5 whitespace-pre-wrap break-all">
          <div className="text-ink-3">{JSON.stringify(tool.args)}</div>
          {tool.error && <div className="text-err">{tool.error}</div>}
          {tool.output && <div className="text-ink-2 max-h-48 overflow-y-auto">{tool.output}</div>}
        </div>
      )}
    </div>
  )
}
