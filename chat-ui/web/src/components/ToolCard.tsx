import { useState } from 'react'

export type ToolCardData = {
  name: string
  args: Record<string, unknown>
  status: 'running' | 'done' | 'failed'
  output?: string
  error?: string
}

export function ToolCard({ tool }: { tool: ToolCardData }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-gray-300 rounded my-1 text-sm">
      <button className="w-full text-left px-2 py-1 flex items-center gap-2" onClick={() => setOpen(!open)}>
        <span>{open ? '▾' : '▸'}</span>
        <span className="font-mono">{tool.name}</span>
        <span className="text-gray-500">
          {tool.status === 'running' ? 'running…' : tool.status === 'failed' ? 'failed' : 'done'}
        </span>
      </button>
      {open && (
        <div className="border-t border-gray-200 px-2 py-1 font-mono text-xs whitespace-pre-wrap break-all">
          <div className="text-gray-500">args: {JSON.stringify(tool.args)}</div>
          {tool.error && <div className="text-red-600">{tool.error}</div>}
          {tool.output && <div className="max-h-48 overflow-y-auto">{tool.output}</div>}
        </div>
      )}
    </div>
  )
}
