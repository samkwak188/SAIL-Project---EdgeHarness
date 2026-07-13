import { useEffect, useState } from 'react'

export type SessionMeta = { id: string; title: string; pinned: boolean; created: number; updated: number }
type Skill = { name: string; description: string }

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

  const item = (s: SessionMeta) => (
    <div
      key={s.id}
      className={`flex items-center gap-1 px-2 py-1 rounded cursor-pointer text-sm ${s.id === currentId ? 'bg-gray-100' : ''}`}
      onClick={() => onOpen(s.id)}
    >
      <span className="flex-1 truncate">{s.title}</span>
      <button
        className="text-gray-400"
        onClick={(e) => {
          e.stopPropagation()
          togglePin(s)
        }}
      >
        {s.pinned ? '★' : '☆'}
      </button>
    </div>
  )

  const pinned = sessions.filter((s) => s.pinned)
  const rest = sessions.filter((s) => !s.pinned)

  return (
    <div className="w-60 border-r border-gray-300 flex flex-col p-2 gap-3 overflow-y-auto shrink-0">
      <button className="border border-gray-300 rounded px-2 py-1 text-sm text-left" onClick={onNew}>
        + New session
      </button>
      <div>
        <div className="text-xs text-gray-500 px-2 mb-1">Skills</div>
        {skills.map((sk) => (
          <div key={sk.name} className="px-2 py-0.5 text-sm text-gray-600" title={sk.description}>
            {sk.name}
          </div>
        ))}
      </div>
      {pinned.length > 0 && (
        <div>
          <div className="text-xs text-gray-500 px-2 mb-1">Pinned</div>
          {pinned.map(item)}
        </div>
      )}
      <div>
        <div className="text-xs text-gray-500 px-2 mb-1">Sessions</div>
        {rest.map(item)}
      </div>
    </div>
  )
}
