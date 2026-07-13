import { useEffect, useState } from 'react'

type ConfigInfo = { file: string; providers: { name: string; model: string }[]; active: boolean }

function label(c: ConfigInfo): string {
  return c.providers[0]?.model ?? c.file
}

export function ModelPicker() {
  const [configs, setConfigs] = useState<ConfigInfo[]>([])
  const [adding, setAdding] = useState(false)
  const [key, setKey] = useState('')
  const [status, setStatus] = useState('')

  const refresh = () =>
    fetch('/api/models')
      .then((r) => r.json())
      .then(setConfigs)

  useEffect(() => {
    refresh()
  }, [])

  const select = async (file: string) => {
    await fetch('/api/models/select', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file }),
    })
    refresh()
  }

  const detected = key.startsWith('sk-or-')
    ? 'openrouter'
    : key.startsWith('sk-ant-')
      ? 'anthropic'
      : key.startsWith('AIza')
        ? 'google'
        : null

  const submitKey = async () => {
    setStatus('verifying…')
    const res = await fetch('/api/keys', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: key }),
    })
    const out = await res.json()
    if (out.ok) {
      setStatus(`added ${out.provider}`)
      setKey('')
      setAdding(false)
      refresh()
    } else {
      setStatus(out.error)
    }
  }

  const active = configs.find((c) => c.active)

  return (
    <div className="relative flex items-center gap-1.5 font-mono text-[12.5px] text-ink-2">
      <select
        className="border border-line rounded-[6px] px-1.5 py-1 max-w-52 bg-bg cursor-pointer hover:border-line-strong transition-colors duration-150"
        value={active?.file ?? ''}
        onChange={(e) => select(e.target.value)}
        aria-label="Model"
      >
        {configs.map((c) => (
          <option key={c.file} value={c.file}>
            {label(c)}
          </option>
        ))}
      </select>
      <button
        className="border border-line rounded-[6px] px-2 py-1 cursor-pointer hover:border-line-strong transition-colors duration-150"
        onClick={() => setAdding(!adding)}
        aria-label="Add API key"
      >
        +
      </button>
      {adding && (
        <div className="absolute bottom-full left-0 mb-2 w-80 border border-line rounded-[16px] bg-bg p-3 space-y-2 shadow-halo-lg z-10">
          <input
            className="w-full border border-line-strong rounded-[10px] px-3 py-1.5 font-mono text-[12.5px] focus-visible:outline-none focus-visible:border-ink"
            placeholder="Paste API key…"
            value={key}
            onChange={(e) => setKey(e.target.value)}
          />
          <div className="flex items-center justify-between">
            <span className="text-ink-3">{detected ? `detected: ${detected}` : 'auto-detects provider'}</span>
            <button
              className="bg-ink text-bg rounded-[6px] px-3 py-1 font-sans text-[12.5px] font-medium disabled:opacity-40 cursor-pointer disabled:cursor-default"
              disabled={!detected}
              onClick={submitKey}
            >
              Add
            </button>
          </div>
          {status && <div className="text-ink-3 break-all max-h-20 overflow-y-auto">{status}</div>}
        </div>
      )}
    </div>
  )
}
