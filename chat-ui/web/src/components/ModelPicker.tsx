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
    <div className="relative flex items-center gap-1 text-sm">
      <select
        className="border border-gray-300 rounded px-1 py-1 max-w-48"
        value={active?.file ?? ''}
        onChange={(e) => select(e.target.value)}
      >
        {configs.map((c) => (
          <option key={c.file} value={c.file}>
            {label(c)}
          </option>
        ))}
      </select>
      <button className="border border-gray-300 rounded px-2 py-1" onClick={() => setAdding(!adding)}>
        +
      </button>
      {adding && (
        <div className="absolute bottom-full right-0 mb-2 w-72 border border-gray-300 rounded bg-white p-2 space-y-1">
          <input
            className="w-full border border-gray-300 rounded px-2 py-1"
            placeholder="Paste API key…"
            value={key}
            onChange={(e) => setKey(e.target.value)}
          />
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>{detected ? `detected: ${detected}` : 'provider auto-detected from prefix'}</span>
            <button
              className="border border-gray-300 rounded px-2 py-0.5 disabled:opacity-50"
              disabled={!detected}
              onClick={submitKey}
            >
              Add
            </button>
          </div>
          {status && <div className="text-xs text-gray-500">{status}</div>}
        </div>
      )}
    </div>
  )
}
