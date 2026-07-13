export function RouterChip({ taskType, confidence, path }: { taskType: string; confidence: number; path: string }) {
  return (
    <span className="inline-block border border-gray-300 rounded px-2 py-0.5 text-xs text-gray-600">
      {taskType} · conf {confidence.toFixed(2)} · {path}
    </span>
  )
}
