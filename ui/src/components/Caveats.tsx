import { Reveal } from './Reveal'

const ITEMS = [
  {
    title: 'Strands agent wiring',
    status: 'Scoped, not yet live',
    detail:
      'Each site runs as a plain Python SiteAgent, not yet a model-backed Strands agent. Wrapping share_round() and receive_and_recheck() as @tool-decorated functions is a one-call-site change — it needs model credentials this environment doesn’t have provisioned, not new logic.',
  },
  {
    title: 'Live OpenSearch cluster',
    status: 'Implemented, untested live',
    detail:
      'OpenSearchPatternStore is written against the real opensearch-py API but has never run against a live cluster here — Docker wasn’t available in this dev environment. It satisfies the identical PatternStore interface as the LocalPatternStore this demo actually runs against, so swapping it in touches no other file.',
  },
  {
    title: 'Real Kaggle SGCC data',
    status: 'Synthetic by default',
    detail:
      'detection/dataset.py ships a synthetic generator matching the same shape and theft vocabulary as the real SGCC dataset. load_real_sgcc() is a documented placeholder — the real dataset needs an authenticated Kaggle API key. Every number on this page is real, computed output; the question worth asking is which dataset produced it.',
  },
  {
    title: 'Everything else on this page',
    status: 'Live, no mocking',
    detail:
      'Every panel above traces to a real backend call — the same Cedar gate, IsolationForest, drift filter, and pooled recheck the test suite exercises. If a panel can’t point to a real endpoint, it isn’t demoed here.',
  },
]

export function Caveats() {
  return (
    <Reveal>
      <div
        className="mt-6 rounded-2xl border border-line p-6 sm:p-8"
        style={{ background: 'var(--grad-4)' }}
      >
        <p className="tag mb-2">Honest caveats</p>
        <p className="mb-6 text-xs leading-relaxed text-muted">
          Stated up front, not waiting for a question to surface them.
        </p>
        <div className="grid gap-4 sm:grid-cols-2">
          {ITEMS.map((item) => (
            <div key={item.title} className="rounded-xl border border-line p-4">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-medium">{item.title}</span>
                <span className="whitespace-nowrap rounded px-2 py-0.5 font-mono text-[0.6rem] tracking-wide text-faint">
                  {item.status}
                </span>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-muted">{item.detail}</p>
            </div>
          ))}
        </div>
      </div>
    </Reveal>
  )
}
