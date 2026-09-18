const STROKE = 'var(--c-line)'
const INK = 'var(--c-text)'
const ACCENT = 'var(--c-accent)'
const MUTED = 'var(--c-muted)'

export function DetectViz() {
  // a normal weekly load shape, then the drop that fires the trigger
  const normal = '0,54 26,40 52,48 78,34 104,46 130,38 156,50 182,36'
  const theft = '182,36 208,44 234,86 260,92 286,88 312,94 338,90'

  return (
    <svg viewBox="0 0 350 130" className="w-full max-w-sm" role="img" aria-label="Load shape dropping sharply">
      <line x1="0" y1="110" x2="350" y2="110" stroke={STROKE} />
      {[0, 1, 2, 3].map((i) => (
        <line
          key={i}
          x1="0"
          y1={20 + i * 28}
          x2="350"
          y2={20 + i * 28}
          stroke={STROKE}
          strokeDasharray="2 6"
        />
      ))}
      <polyline points={normal} fill="none" stroke={MUTED} strokeWidth="1.6" />
      <polyline points={theft} fill="none" stroke={ACCENT} strokeWidth="2.2" />
      <circle cx="234" cy="86" r="4.5" fill={ACCENT} />
      <circle cx="234" cy="86" r="11" fill="none" stroke={ACCENT} opacity="0.35" />
      <text x="248" y="76" fontSize="9" fill={ACCENT} fontFamily="var(--font-mono)">
        drift fires
      </text>
    </svg>
  )
}

export function AbstractViz() {
  const stripped = ['consumer_id  4471-88F', 'meter_id  MH-22910', 'lat, lon  19.07, 72.87']
  const kept = [
    'load_drop_bucket      4',
    'timing_bucket         mid-cycle',
    'recovery_shape        none',
  ]

  return (
    <div className="w-full max-w-sm font-mono text-[0.68rem]">
      <p className="mb-3 tracking-[0.18em] text-faint uppercase">Discarded</p>
      {stripped.map((f) => (
        <div key={f} className="mb-1.5 flex items-center gap-2">
          <span className="text-faint line-through decoration-1">{f}</span>
        </div>
      ))}
      <div className="my-5 h-px w-full bg-line" />
      <p className="mb-3 tracking-[0.18em] text-faint uppercase">Shared</p>
      {kept.map((f) => (
        <div key={f} className="mb-1.5 whitespace-pre" style={{ color: INK }}>
          {f}
        </div>
      ))}
    </div>
  )
}

export function GateViz() {
  return (
    <div className="w-full max-w-sm space-y-3 font-mono text-[0.68rem]">
      <div className="rounded-lg border border-line p-3.5" style={{ borderColor: 'rgba(220,80,60,0.45)' }}>
        <div className="mb-1.5 flex items-center gap-2">
          <span
            className="rounded px-1.5 py-0.5 text-[0.62rem] tracking-wider"
            style={{ background: 'rgba(220,80,60,0.16)', color: '#e2664f' }}
          >
            DENY
          </span>
          <span className="text-faint">sig-006be9ffc00f</span>
        </div>
        <p className="text-faint">reason: has_meter_id</p>
      </div>

      <div className="pl-3 text-faint">rewrite, re-abstract</div>

      <div className="rounded-lg border p-3.5" style={{ borderColor: 'rgba(90,190,140,0.45)' }}>
        <div className="mb-1.5 flex items-center gap-2">
          <span
            className="rounded px-1.5 py-0.5 text-[0.62rem] tracking-wider"
            style={{ background: 'rgba(90,190,140,0.16)', color: '#58b98a' }}
          >
            ALLOW
          </span>
          <span className="text-faint">sig-ce5b2b4c8b75</span>
        </div>
        <p className="text-faint">granularity 6, clean</p>
      </div>
    </div>
  )
}

export function PoolViz() {
  const dots = Array.from({ length: 93 })
  return (
    <div className="w-full max-w-sm">
      <div className="flex flex-wrap gap-[5px]">
        {dots.map((_, i) => (
          <span
            key={i}
            className="block h-[7px] w-[7px] rounded-full"
            style={{
              background: i < 56 ? MUTED : i < 91 ? MUTED : ACCENT,
              opacity: i < 91 ? 0.45 : 1,
            }}
          />
        ))}
      </div>
      <p className="mt-5 font-mono text-[0.68rem] text-faint">
        93 signatures pooled, 2 of them from the low data site
      </p>
    </div>
  )
}

export function LiftViz() {
  return (
    <div className="w-full max-w-sm font-mono text-[0.68rem]">
      <Bar label="isolated" pct={33.3} tone={MUTED} />
      <Bar label="pooled" pct={66.7} tone={ACCENT} />
      <p className="mt-5 text-faint">
        site_c_low_data, 2 of 6 caught becomes 4 of 6
      </p>
    </div>
  )
}

function Bar({ label, pct, tone }: { label: string; pct: number; tone: string }) {
  return (
    <div className="mb-5">
      <div className="mb-2 flex justify-between text-faint">
        <span>{label}</span>
        <span style={{ color: tone }}>{pct.toFixed(1)}%</span>
      </div>
      <div className="h-1.5 w-full rounded-full" style={{ background: 'var(--c-line)' }}>
        <div
          className="h-full rounded-full"
          style={{ width: `${pct}%`, background: tone }}
        />
      </div>
    </div>
  )
}
