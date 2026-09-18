import { Fragment } from 'react'
import { motion } from 'framer-motion'
import { Reveal } from './Reveal'
import type { PipelineEvent } from '../lib/api'
import { SITE_LABEL } from '../lib/format'

const SITES = ['site_a', 'site_b', 'site_c_low_data']
const STAGES = ['detect', 'share', 'recheck'] as const
const STAGE_LABEL: Record<(typeof STAGES)[number], string> = {
  detect: 'Detect',
  share: 'Abstract + Cedar gate',
  recheck: 'Pooled recheck',
}

type Cell = { done: boolean; detail?: string }

function buildGrid(events: PipelineEvent[]): Record<string, Record<string, Cell>> {
  const grid: Record<string, Record<string, Cell>> = {}
  for (const site of SITES) {
    grid[site] = { detect: { done: false }, share: { done: false }, recheck: { done: false } }
  }
  for (const e of events) {
    if (e.phase === 'detect') {
      grid[e.site_id].detect = { done: true, detail: `${e.flagged} flagged` }
    } else if (e.phase === 'share') {
      grid[e.site_id].share = { done: true, detail: `${e.shared} shared, ${e.denied} denied` }
    } else if (e.phase === 'recheck') {
      grid[e.site_id].recheck = { done: true, detail: `${e.pooled_flagged} flagged (pooled)` }
    }
  }
  return grid
}

export function PipelineDiagram({
  events,
  active,
}: {
  events: PipelineEvent[]
  active: boolean
}) {
  const grid = buildGrid(events)

  return (
    <Reveal>
      <div
        className="mt-6 rounded-2xl border border-line p-6 sm:p-8"
        style={{ background: 'var(--c-surface)' }}
      >
        <div className="flex items-center justify-between">
          <p className="tag">Pipeline, stage by stage</p>
          {active && (
            <span className="flex items-center gap-2 text-[0.68rem] text-faint">
              <span className="h-1.5 w-1.5 rounded-full pulse-live" style={{ background: 'var(--c-accent)' }} />
              running
            </span>
          )}
        </div>

        <div className="mt-6 overflow-x-auto">
          <div className="grid min-w-[520px] grid-cols-[1fr_repeat(3,1.3fr)] gap-x-4 gap-y-3">
            <div />
            {STAGES.map((s) => (
              <div key={s} className="text-[0.65rem] uppercase tracking-wide text-faint">
                {STAGE_LABEL[s]}
              </div>
            ))}

            {SITES.map((site) => (
              <Fragment key={site}>
                <div className="self-center text-sm text-muted">
                  {SITE_LABEL[site]}
                </div>
                {STAGES.map((stage) => {
                  const cell = grid[site][stage]
                  const isLow = site === 'site_c_low_data'
                  return (
                    <div
                      key={`${site}-${stage}`}
                      className="flex items-center gap-2 rounded-lg border border-line px-3 py-2"
                      style={{
                        background: cell.done
                          ? isLow
                            ? 'var(--c-accent-soft)'
                            : 'rgba(90,190,140,0.1)'
                          : 'transparent',
                        borderColor: cell.done
                          ? isLow
                            ? 'var(--c-accent)'
                            : 'rgba(90,190,140,0.35)'
                          : 'var(--c-line)',
                      }}
                    >
                      <motion.span
                        className="h-2 w-2 shrink-0 rounded-full"
                        initial={false}
                        animate={{
                          background: cell.done
                            ? isLow
                              ? 'var(--c-accent)'
                              : 'var(--c-good)'
                            : 'var(--c-line)',
                          scale: cell.done ? 1 : 0.8,
                        }}
                        transition={{ duration: 0.3 }}
                      />
                      <span className="truncate text-[0.7rem] text-faint">
                        {cell.detail ?? '—'}
                      </span>
                    </div>
                  )
                })}
              </Fragment>
            ))}
          </div>
        </div>

        <p className="mt-5 text-xs leading-relaxed text-faint">
          Each cell lights up when orchestration/agent.py::SiteAgent actually
          finishes that call for that site — detect(), share_round(), then
          receive_and_recheck() once every site has shared.
        </p>
      </div>
    </Reveal>
  )
}
