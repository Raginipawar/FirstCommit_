import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Reveal } from './Reveal'
import { DecisionLog } from './DecisionLog'
import { Caveats } from './Caveats'
import { PipelineDiagram } from './PipelineDiagram'
import { Validation } from './Validation'
import {
  checkBackendOnline,
  getDecisions,
  runGate,
  streamSwarm,
  type DecisionsResult,
  type GateResult,
  type PipelineEvent,
  type SwarmResult,
} from '../lib/api'
import { SITE_LABEL, pct } from '../lib/format'
import { CAPTURED_DECISIONS, CAPTURED_GATE, CAPTURED_SWARM } from '../data/captured-run'

type Phase = 'idle' | 'running' | 'done'
type Source = 'live' | 'captured' | 'fallback'

const RUNNING_LINES = [
  'Watching site_a, site_b and site_c_low_data for drift…',
  'Stripping identifying fields, building signatures…',
  'Checking every signature against the Cedar policy gate…',
  'Pooling what was permitted…',
  'Re-checking each site against the shared pool…',
]

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms))
}

function syntheticEvents(swarm: SwarmResult): PipelineEvent[] {
  const order: (keyof typeof swarm.sites)[] = ['site_a', 'site_b', 'site_c_low_data']
  const events: PipelineEvent[] = []
  for (const id of order) {
    const site = swarm.sites[id]
    events.push({ phase: 'detect', site_id: id, flagged: site.share.flagged })
  }
  for (const id of order) {
    const site = swarm.sites[id]
    events.push({
      phase: 'share',
      site_id: id,
      drift_candidates: site.share.drift_candidates,
      shared: site.share.shared,
      denied: site.share.denied ?? 0,
    })
  }
  for (const id of order) {
    const site = swarm.sites[id]
    events.push({ phase: 'recheck', site_id: id, pooled_flagged: site.pooled.flagged })
  }
  return events
}

export function LiveRun() {
  const [online, setOnline] = useState<boolean | null>(null)
  const [phase, setPhase] = useState<Phase>('idle')
  const [source, setSource] = useState<Source>('captured')
  const [gate, setGate] = useState<GateResult | null>(null)
  const [swarm, setSwarm] = useState<SwarmResult | null>(null)
  const [pipelineEvents, setPipelineEvents] = useState<PipelineEvent[]>([])
  const [decisions, setDecisions] = useState<DecisionsResult | null>(null)
  const [line, setLine] = useState(0)
  const tickRef = useRef<number | null>(null)

  useEffect(() => {
    checkBackendOnline().then(setOnline)
  }, [])

  useEffect(() => {
    if (phase !== 'running') {
      if (tickRef.current) window.clearInterval(tickRef.current)
      return
    }
    setLine(0)
    tickRef.current = window.setInterval(() => {
      setLine((v) => Math.min(v + 1, RUNNING_LINES.length - 1))
    }, 480)
    return () => {
      if (tickRef.current) window.clearInterval(tickRef.current)
    }
  }, [phase])

  async function refreshDecisions() {
    if (!online) return
    try {
      setDecisions(await getDecisions())
    } catch {
      /* leave whatever was showing */
    }
  }

  async function handleRun() {
    setPhase('running')
    setPipelineEvents([])
    try {
      if (online) {
        const swarmPromise = new Promise<SwarmResult>((resolve, reject) => {
          streamSwarm(
            (e) => {
              setPipelineEvents((prev) => [...prev, e])
              if (e.phase === 'done') resolve(e.result)
            },
            reject,
          )
        })
        const [g, s] = await Promise.all([runGate(), swarmPromise])
        setGate(g)
        setSwarm(s)
        setSource('live')
        setDecisions(await getDecisions())
      } else {
        await sleep(1300)
        setGate(CAPTURED_GATE)
        setSwarm(CAPTURED_SWARM)
        setPipelineEvents(syntheticEvents(CAPTURED_SWARM))
        setDecisions(CAPTURED_DECISIONS)
        setSource('captured')
      }
    } catch {
      await sleep(400)
      setGate(CAPTURED_GATE)
      setSwarm(CAPTURED_SWARM)
      setPipelineEvents(syntheticEvents(CAPTURED_SWARM))
      setDecisions(CAPTURED_DECISIONS)
      setSource('fallback')
    }
    setPhase('done')
  }

  return (
    <section id="live" className="relative bg-bg px-6 py-28 sm:px-12 sm:py-36">
      <div className="mx-auto max-w-6xl">
        <Reveal>
          <p className="eyebrow mb-6">Live run</p>
        </Reveal>
        <Reveal delay={0.08}>
          <h2 className="max-w-3xl font-display text-[2.2rem] leading-[1.06] sm:text-[3.4rem]">
            Press run. Watch the grid defend itself.
          </h2>
        </Reveal>

        <div className="mt-10 grid gap-10 lg:grid-cols-[1fr_1.15fr] lg:gap-16">
          <Reveal delay={0.14}>
            <div
              className="rounded-2xl border border-line p-7 sm:p-9"
              style={{ background: 'var(--grad-4)' }}
            >
              <p className="tag mb-4">If you are the one paying the bill</p>
              <p className="text-sm leading-relaxed text-muted">
                Every unit someone else steals gets billed to everyone else,
                through tariffs that assume a certain amount of theft and
                spread it across honest customers. It also means inspectors
                show up at random houses, yours included, because the utility
                has no better way to decide where to look.
              </p>
              <p className="mt-4 text-sm leading-relaxed text-muted">
                What is below is not a video of that getting better. It is the
                actual detector, the actual policy gate and the actual shared
                pool, running right now, so a utility can point at exactly
                where a suspicious meter came from and why it was flagged,
                instead of guessing.
              </p>
            </div>
          </Reveal>

          <Reveal delay={0.2}>
            <div
              className="flex h-full flex-col justify-between rounded-2xl border border-line p-7 sm:p-9"
              style={{ background: 'var(--grad-1)' }}
            >
              <div className="flex items-center gap-2.5">
                <span
                  className={`h-2 w-2 rounded-full ${online ? 'pulse-live' : ''}`}
                  style={{
                    background:
                      online === null
                        ? 'var(--c-faint)'
                        : online
                          ? 'var(--c-good)'
                          : 'var(--c-accent)',
                  }}
                />
                <span className="text-xs tracking-wide text-muted">
                  {online === null
                    ? 'Checking for a live backend…'
                    : online
                      ? 'Live backend connected: server.py, port 8000'
                      : 'Backend offline. Will replay a captured real run'}
                </span>
              </div>

              <button
                type="button"
                onClick={handleRun}
                disabled={phase === 'running' || online === null}
                className="group mt-8 flex w-full items-center justify-between rounded-xl border border-line px-6 py-5 text-left transition-colors hover:bg-accent-soft disabled:cursor-wait disabled:opacity-70"
                style={{ background: 'var(--c-surface)' }}
              >
                <span className="font-display text-2xl">
                  {phase === 'done' ? 'Run it again' : 'Run TRIPWIRE now'}
                </span>
                <span
                  className={`grid h-9 w-9 place-items-center rounded-full border border-line transition-transform group-hover:scale-110 ${
                    phase === 'running' ? 'spin-slow' : ''
                  }`}
                >
                  {phase === 'running' ? (
                    <SpinnerIcon />
                  ) : (
                    <PlayIcon />
                  )}
                </span>
              </button>

              <div className="mt-5 min-h-[1.5rem] font-mono text-[0.72rem] text-faint">
                {phase === 'running' && (
                  <AnimatePresence mode="wait">
                    <motion.span
                      key={line}
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      {RUNNING_LINES[line]}
                    </motion.span>
                  </AnimatePresence>
                )}
                {phase === 'idle' && 'Waiting to run.'}
                {phase === 'done' && (
                  <span>
                    {source === 'live'
                      ? 'Fresh result, computed just now.'
                      : source === 'fallback'
                        ? 'The live call failed mid-run. Showing a captured real run instead.'
                        : 'Backend was offline. Showing a captured real run.'}
                  </span>
                )}
              </div>
            </div>
          </Reveal>
        </div>

        <AnimatePresence>
          {phase === 'done' && gate && swarm && (
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
              className="mt-16"
            >
              <div className="grid gap-6 lg:grid-cols-[1fr_1.15fr] lg:gap-8">
                <GatePanel gate={gate} />
                <SwarmPanel swarm={swarm} />
              </div>

              <PipelineDiagram events={pipelineEvents} active={false} />
              <DecisionLog data={decisions} online={!!online} onCleared={refreshDecisions} />
            </motion.div>
          )}
        </AnimatePresence>

        {phase === 'running' && pipelineEvents.length > 0 && (
          <PipelineDiagram events={pipelineEvents} active />
        )}

        <div className="mt-6">
          <Validation online={!!online} />
        </div>

        <Caveats />
      </div>
    </section>
  )
}

function GatePanel({ gate }: { gate: GateResult }) {
  const steps = [
    {
      label: 'Raw reading, untouched',
      kind: gate.raw_attempt.kind,
      granularity: gate.raw_attempt.granularity,
      decision: gate.raw_attempt,
    },
    {
      label: 'Signature, but a bug left the meter ID on',
      kind: gate.leaky_signature.decision.kind,
      granularity: gate.leaky_signature.granularity,
      decision: gate.leaky_signature.decision,
    },
    {
      label: 'Signature, properly abstracted',
      kind: gate.clean_signature.decision.kind,
      granularity: gate.clean_signature.granularity,
      decision: gate.clean_signature.decision,
      extra: gate.clean_signature,
    },
  ]

  return (
    <div className="rounded-2xl border border-line p-6 sm:p-8" style={{ background: 'var(--c-surface)' }}>
      <p className="tag mb-6">The boundary, live</p>
      <div className="space-y-4">
        {steps.map((s, i) => (
          <motion.div
            key={s.decision.resource_id}
            initial={{ opacity: 0, x: -14 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.45, delay: i * 0.12 }}
            className="rounded-xl border p-4"
            style={{
              borderColor: s.decision.allowed
                ? 'rgba(90,190,140,0.4)'
                : 'rgba(220,80,60,0.35)',
            }}
          >
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm">{s.label}</span>
              <span
                className="rounded px-2 py-0.5 font-mono text-[0.62rem] tracking-wider"
                style={{
                  background: s.decision.allowed
                    ? 'rgba(90,190,140,0.16)'
                    : 'rgba(220,80,60,0.14)',
                  color: s.decision.allowed ? 'var(--c-good)' : 'var(--c-bad)',
                }}
              >
                {s.decision.allowed ? 'ALLOW' : 'DENY'}
              </span>
            </div>
            <p className="mt-2 font-mono text-[0.68rem] text-faint">
              {s.kind} · granularity {s.granularity} · {s.decision.resource_id}
            </p>
            <p className="mt-1.5 text-xs text-muted">{s.decision.reasons[0]}</p>
          </motion.div>
        ))}
      </div>
      <p className="mt-6 text-xs leading-relaxed text-faint">
        {gate.summary.total} checked this run · {gate.summary.allowed} allowed
        · {gate.summary.denied} denied
      </p>
    </div>
  )
}

function SwarmPanel({ swarm }: { swarm: SwarmResult }) {
  const order: (keyof typeof swarm.sites)[] = [
    'site_c_low_data',
    'site_a',
    'site_b',
  ]

  return (
    <div className="rounded-2xl border border-line p-6 sm:p-8" style={{ background: 'var(--c-surface)' }}>
      <div className="flex items-baseline justify-between">
        <div>
          <p className="tag">The pool, live</p>
          {swarm.seed_offset !== undefined && (
            <p className="mt-1 font-mono text-[0.65rem] text-faint">
              seed +{swarm.seed_offset} · a new dataset every run
            </p>
          )}
        </div>
        <p className="font-display text-2xl">
          {swarm.pool_size}{' '}
          <span className="text-sm text-faint">signatures pooled</span>
        </p>
      </div>

      <div className="mt-6 space-y-5">
        {order.map((id, i) => {
          const site = swarm.sites[id]
          const before = site.isolated.detection_rate
          const after = site.pooled.detection_rate
          const isLow = id === 'site_c_low_data'
          return (
            <motion.div
              key={id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: i * 0.1 }}
              className="rounded-xl border p-4"
              style={{
                borderColor: isLow ? 'var(--c-accent)' : 'var(--c-line)',
                background: isLow ? 'var(--c-accent-soft)' : 'transparent',
              }}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{SITE_LABEL[id]}</span>
                <span className="font-mono text-[0.68rem] text-faint">
                  {site.n_consumers} consumers
                </span>
              </div>
              <div className="mt-3 flex items-center gap-3">
                <span className="font-display text-xl text-faint">
                  {pct(before)}
                </span>
                <span className="text-faint">→</span>
                <span
                  className="font-display text-2xl"
                  style={{ color: isLow ? 'var(--c-accent)' : 'var(--c-text)' }}
                >
                  {pct(after)}
                </span>
                {after > before && (
                  <span className="text-xs" style={{ color: 'var(--c-good)' }}>
                    +{((after - before) * 100).toFixed(1)} pts
                  </span>
                )}
              </div>
              <div
                className="mt-3 h-1.5 w-full overflow-hidden rounded-full"
                style={{ background: 'var(--c-line)' }}
              >
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: isLow ? 'var(--c-accent)' : 'var(--c-text)' }}
                  initial={{ width: 0 }}
                  animate={{ width: `${after * 100}%` }}
                  transition={{ duration: 0.8, delay: 0.2 + i * 0.1, ease: [0.22, 1, 0.36, 1] }}
                />
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}

function PlayIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
      <path d="M8 5v14l11-7z" />
    </svg>
  )
}

function SpinnerIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 12a9 9 0 1 1-9-9" strokeLinecap="round" />
    </svg>
  )
}
