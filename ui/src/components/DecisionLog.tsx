import { useState } from 'react'
import { motion } from 'framer-motion'
import { Reveal } from './Reveal'
import { clearDecisions, type DecisionsResult } from '../lib/api'
import { SITE_LABEL } from '../lib/format'

type Filter = 'all' | 'allowed' | 'denied'

export function DecisionLog({
  data,
  online,
  onCleared,
}: {
  data: DecisionsResult | null
  online: boolean
  onCleared: () => void
}) {
  const [filter, setFilter] = useState<Filter>('all')
  const [clearing, setClearing] = useState(false)

  if (!data) return null

  const records = [...data.records].reverse()
  const filtered = records.filter((r) => {
    if (filter === 'allowed') return r.allowed
    if (filter === 'denied') return !r.allowed
    return true
  })

  async function handleClear() {
    if (!online) return
    setClearing(true)
    try {
      await clearDecisions()
      onCleared()
    } finally {
      setClearing(false)
    }
  }

  return (
    <Reveal>
      <div
        className="mt-6 rounded-2xl border border-line p-6 sm:p-8"
        style={{ background: 'var(--c-surface)' }}
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="tag">Decision log, this session</p>
          <div className="flex items-center gap-2">
            {(['all', 'allowed', 'denied'] as Filter[]).map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setFilter(f)}
                className="rounded-full border border-line px-3 py-1 text-[0.68rem] capitalize tracking-wide transition-colors"
                style={{
                  background: filter === f ? 'var(--c-accent-soft)' : 'transparent',
                  color: filter === f ? 'var(--c-accent)' : 'var(--c-muted)',
                }}
              >
                {f}
              </button>
            ))}
            {online && (
              <button
                type="button"
                onClick={handleClear}
                disabled={clearing}
                className="rounded-full border border-line px-3 py-1 text-[0.68rem] tracking-wide text-faint transition-colors hover:bg-accent-soft disabled:opacity-50"
              >
                {clearing ? 'Clearing…' : 'Reset log'}
              </button>
            )}
          </div>
        </div>

        <p className="mt-3 text-xs leading-relaxed text-muted">
          Every share request this server has evaluated, oldest first below,
          reading straight from{' '}
          <code className="font-mono text-[0.75em] text-faint">
            policy/decision_log.py
          </code>
          . This is the artifact a DISCOM compliance officer would actually
          audit — not a rendering, the log itself.
        </p>

        <div className="mt-5 max-h-[22rem] overflow-y-auto pr-1">
          <table className="w-full border-collapse text-left text-xs">
            <thead>
              <tr className="text-faint">
                <th className="border-b border-line pb-2 pr-3 font-normal">Time</th>
                <th className="border-b border-line pb-2 pr-3 font-normal">Site</th>
                <th className="border-b border-line pb-2 pr-3 font-normal">Kind</th>
                <th className="border-b border-line pb-2 pr-3 font-normal">Gran.</th>
                <th className="border-b border-line pb-2 pr-3 font-normal">Decision</th>
                <th className="border-b border-line pb-2 font-normal">Reason</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r, i) => (
                <motion.tr
                  key={`${r.resource_id}-${i}`}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.3, delay: Math.min(i, 8) * 0.03 }}
                  className="align-top"
                >
                  <td className="border-b border-line/60 py-2 pr-3 font-mono text-[0.65rem] text-faint">
                    {r.checked_at.slice(11, 19)}
                  </td>
                  <td className="border-b border-line/60 py-2 pr-3 text-muted">
                    {SITE_LABEL[r.site_id] ?? r.site_id}
                  </td>
                  <td className="border-b border-line/60 py-2 pr-3 font-mono text-[0.65rem] text-faint">
                    {r.kind}
                  </td>
                  <td className="border-b border-line/60 py-2 pr-3 font-mono text-[0.65rem] text-faint">
                    {r.granularity}
                  </td>
                  <td className="border-b border-line/60 py-2 pr-3">
                    <span
                      className="rounded px-2 py-0.5 font-mono text-[0.6rem] tracking-wider"
                      style={{
                        background: r.allowed ? 'rgba(90,190,140,0.16)' : 'rgba(220,80,60,0.14)',
                        color: r.allowed ? 'var(--c-good)' : 'var(--c-bad)',
                      }}
                    >
                      {r.allowed ? 'ALLOW' : 'DENY'}
                    </span>
                  </td>
                  <td className="border-b border-line/60 py-2 text-muted">
                    {r.reasons[0]}
                  </td>
                </motion.tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-6 text-center text-faint">
                    No {filter === 'all' ? '' : filter} decisions yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2 border-t border-line pt-4 text-xs text-faint">
          <span>{data.summary.total} total</span>
          <span style={{ color: 'var(--c-good)' }}>{data.summary.allowed} allowed</span>
          <span style={{ color: 'var(--c-bad)' }}>{data.summary.denied} denied</span>
          <span>
            {(data.summary.allow_rate * 100).toFixed(0)}% allow rate
          </span>
        </div>
      </div>
    </Reveal>
  )
}
