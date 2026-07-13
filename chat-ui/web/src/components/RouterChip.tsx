export function RouterChip({ taskType, confidence, path }: { taskType: string; confidence: number; path: string }) {
  return (
    <span className="inline-block font-mono text-[12.5px] text-ink-2 border border-line rounded-[6px] px-2 py-0.5 bg-bg">
      {taskType} · {confidence.toFixed(2)} · {path}
    </span>
  )
}
