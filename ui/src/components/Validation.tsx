import { useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { Reveal } from './Reveal'
import { streamValidation, type SeedRecord, type ValidationAggregate } from '../lib/api'
import { pct } from '../lib/format'
import {
  CAPTURED_VALIDATION_AGGREGATE,
  CAPTURED_VALIDATION_SEEDS,
} from '../data/captured-run'

const N_SEEDS = 8

type Status = 'idle' | 'running' | 'done'

export function Validation({ online }: { online: boolean }) {
  const [status, setStatus] = useState<Status>('idle')
  const [seeds, setSeeds] = useState<SeedRecord[]>([])
  const [aggregate, setAggregate] = useState<ValidationAggregate | null>(null)
  const [isCaptured, setIsCaptured] = useState(false)
  const stopRef = useRef<(() => void) | null>(null)

  function handleRun() {
    if (!online) {
      setStatus('running')
      setSeeds([])
      setIsCaptured(true)
      let i = 0
      const timer = setInterval(() => {
        i += 1
        setSeeds(CAPTURED_VALIDATION_SEEDS.slice(0, i))
        if (i >= CAPTURED_VALIDATION_SEEDS.length) {
          clearInterval(timer)
          setAggregate(CAPTURED_VALIDATION_AGGREGATE)
          setStatus('done')
        }
      }, 260)
      return
    }

    setStatus('running')
    setSeeds([])
    setAggregate(null)
    setIsCaptured(false)

    stopRef.current = streamValidation(
      N_SEEDS,
      (e) => {
        if (e.phase === 'seed') {
          setSeeds((prev) => [...prev, e])
        } else if (e.phase === 'done') {
          setAggregate(e.aggregate)
          setStatus('done')
        }
      },
      () => {
        setSeeds(CAPTURED_VALIDATION_SEEDS)
        setAggregate(CAPTURED_VALIDATION_AGGREGATE)
        setIsCaptured(true)
        setStatus('done')
      },
    )
  }

  const maxImprovement = Math.max(0.05, ...seeds.map((s) => s.low_data_improvement))

  return (
    <Reveal>
      <div
        className="mt-6 rounded-2xl border border-line p-6 sm:p-8"
        style={{ background: 'var(--c-surface)' }}
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="tag">Validation across seeds</p>
            <p className="mt-2 max-w-lg text-xs leading-relaxed text-muted">
              One measured result could be a lucky draw. This re-runs the
              full swarm cycle {N_SEEDS} times, each with every site's random
              seed offset by one more, and checks whether the pooled
              improvement on the low-data site holds — and whether pooled
              false positives ever get worse.
            </p>
          </div>
          <button
            type="button"
            onClick={handleRun}
            disabled={status === 'running'}
            className="shrink-0 rounded-full border border-line px-4 py-2 text-xs tracking-wide transition-colors hover:bg-accent-soft disabled:cursor-wait disabled:opacity-60"
          >
            {status === 'running'
              ? `Running… ${seeds.length}/${N_SEEDS}`
              : status === 'done'
                ? 'Re-validate'
                : `Validate across ${N_SEEDS} seeds`}
          </button>
        </div>

        {seeds.length > 0 && (
          <div className="mt-6">
            <p className="mb-2 text-[0.68rem] uppercase tracking-wide text-faint">
              site_c_low_data improvement, per seed
            </p>
            <div className="flex h-24 items-end gap-2">
              {seeds.map((s) => (
                <motion.div
                  key={s.seed_offset}
                  className="flex-1 rounded-t"
                  style={{ background: 'var(--c-accent)', minWidth: 8 }}
                  initial={{ height: 0 }}
                  animate={{ height: `${(s.low_data_improvement / maxImprovement) * 100}%` }}
                  transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                  title={`seed ${s.seed_offset}: +${pct(s.low_data_improvement)}`}
                />
              ))}
              {Array.from({ length: Math.max(0, N_SEEDS - seeds.length) }).map((_, i) => (
                <div
                  key={`pending-${i}`}
                  className="flex-1 rounded-t border border-dashed border-line"
                  style={{ minWidth: 8, height: '4%' }}
                />
              ))}
            </div>
          </div>
        )}

        {aggregate && (
          <div className="mt-6 grid grid-cols-2 gap-4 border-t border-line pt-5 sm:grid-cols-4">
            <Stat label="Mean improvement" value={`+${pct(aggregate.mean_improvement)}`} good />
            <Stat label="Min improvement" value={`+${pct(aggregate.min_improvement)}`} />
            <Stat label="Max improvement" value={`+${pct(aggregate.max_improvement)}`} />
            <Stat
              label="Pooled FPR ever worse?"
              value={aggregate.false_positive_rate_ever_worse_pooled ? 'Yes' : 'Never'}
              good={!aggregate.false_positive_rate_ever_worse_pooled}
            />
          </div>
        )}

        <p className="mt-5 text-[0.68rem] text-faint">
          {status === 'idle' && 'Not yet run this session.'}
          {status === 'running' && !isCaptured && 'Re-fitting real IsolationForests per seed — this genuinely takes a few seconds each.'}
          {status === 'done' && isCaptured && 'Backend offline or the live call failed — replaying a captured real 5-seed run.'}
          {status === 'done' && !isCaptured && `Fresh result: ${N_SEEDS} independent live runs, computed just now.`}
        </p>
      </div>
    </Reveal>
  )
}

function Stat({ label, value, good }: { label: string; value: string; good?: boolean }) {
  return (
    <div>
      <p className="text-[0.65rem] uppercase tracking-wide text-faint">{label}</p>
      <p
        className="mt-1 font-display text-xl"
        style={{ color: good ? 'var(--c-good)' : 'var(--c-text)' }}
      >
        {value}
      </p>
    </div>
  )
}
