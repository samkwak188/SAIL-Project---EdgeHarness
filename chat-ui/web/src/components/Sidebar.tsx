import { useEffect, useState } from 'react'

export type SessionMeta = { id: string; title: string; pinned: boolean; created: number; updated: number }
type Skill = { name: string; description: string }

function GroupLabel({ children }: { children: string }) {
  return (
    <div className="text-[11px] font-[550] uppercase tracking-[0.04em] text-ink-3 px-2 mb-1.5">{children}</div>
  )
}

export function Sidebar({
  currentId,
  refreshKey,
  onNew,
  onOpen,
}: {
  currentId: string | null
  refreshKey: number
  onNew: () => void
  onOpen: (id: string) => void
}) {
  const [sessions, setSessions] = useState<SessionMeta[]>([])
  const [skills, setSkills] = useState<Skill[]>([])

  const refresh = () =>
    fetch('/api/sessions')
      .then((r) => r.json())
      .then(setSessions)

  useEffect(() => {
    refresh()
  }, [refreshKey])

  useEffect(() => {
    fetch('/api/skills')
      .then((r) => r.json())
      .then(setSkills)
  }, [])

  const togglePin = async (s: SessionMeta) => {
    await fetch(`/api/sessions/${s.id}/pin`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pinned: !s.pinned }),
    })
    refresh()
  }

  const item = (s: SessionMeta) => {
    const active = s.id === currentId
    return (
      <div
        key={s.id}
        className={`group flex items-center gap-1 px-2 py-1.5 rounded-[6px] cursor-pointer text-[13px] transition-colors duration-150 ${
          active ? 'bg-bg border border-line text-ink' : 'border border-transparent text-ink-2 hover:bg-bg/60'
        }`}
        onClick={() => onOpen(s.id)}
      >
        <span className="flex-1 truncate">{s.title}</span>
        <button
          className={`text-ink-3 transition-opacity duration-150 cursor-pointer ${
            s.pinned ? '' : 'opacity-0 group-hover:opacity-100'
          }`}
          aria-label={s.pinned ? 'Unpin session' : 'Pin session'}
          onClick={(e) => {
            e.stopPropagation()
            togglePin(s)
          }}
        >
          {s.pinned ? '★' : '☆'}
        </button>
      </div>
    )
  }

  const pinned = sessions.filter((s) => s.pinned)
  const rest = sessions.filter((s) => !s.pinned)

  return (
    <div className="w-60 shrink-0 bg-panel border-r border-line flex flex-col gap-6 p-3 overflow-y-auto max-[900px]:hidden">
      <button
        className="border border-line-strong bg-bg rounded-[10px] px-3 py-1.5 text-[13px] font-medium text-left cursor-pointer hover:border-ink transition-colors duration-150"
        onClick={onNew}
      >
        + New session
      </button>
      <div>
        <GroupLabel>Skills</GroupLabel>
        {skills.map((sk) => (
          <div key={sk.name} className="px-2 py-1 font-mono text-[12.5px] text-ink-2" title={sk.description}>
            {sk.name}
          </div>
        ))}
      </div>
      {pinned.length > 0 && (
        <div>
          <GroupLabel>Pinned</GroupLabel>
          {pinned.map(item)}
        </div>
      )}
      <div>
        <GroupLabel>Sessions</GroupLabel>
        {rest.length === 0 ? (
          <div className="px-2 py-1 text-[12.5px] text-ink-3">Start a session — your history lives here.</div>
        ) : (
          rest.map(item)
        )}
      </div>
    </div>
  )
}
