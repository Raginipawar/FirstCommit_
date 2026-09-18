import { useEffect, useRef, useState } from 'react'
import { motion, useInView } from 'framer-motion'

function Counter({ to, decimals = 2 }: { to: number; decimals?: number }) {
  const ref = useRef<HTMLSpanElement>(null)
  const inView = useInView(ref, { once: true, margin: '-15% 0px' })
  const [v, setV] = useState(0)

  useEffect(() => {
    if (!inView) return
    const start = performance.now()
    let frame = 0
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / 1700)
      setV(to * (1 - Math.pow(1 - p, 4)))
      if (p < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [inView, to])

  return <span ref={ref}>{v.toFixed(decimals)}</span>
}

export function Problem() {
  return (
    <section
      id="problem"
      className="relative z-10 rounded-t-[2rem] bg-bg px-6 pt-28 pb-28 panel-shadow sm:px-12 sm:pt-36 sm:pb-36"
    >
      <div className="mx-auto max-w-6xl">
        <motion.p
          initial={{ opacity: 0, y: 14 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-10% 0px' }}
          transition={{ duration: 0.6 }}
          className="eyebrow mb-8"
        >
          The problem
        </motion.p>

        <div className="grid gap-12 lg:grid-cols-[1.35fr_1fr] lg:gap-20">
          <motion.h2
            initial={{ opacity: 0, y: 22 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-10% 0px' }}
            transition={{ duration: 0.75, ease: [0.22, 1, 0.36, 1] }}
            className="font-display text-[2.3rem] leading-[1.06] sm:text-[3.6rem] lg:text-[4.2rem]"
          >
            India loses more to electricity theft than any country on earth.
          </motion.h2>

          <motion.div
            initial={{ opacity: 0, y: 22 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-10% 0px' }}
            transition={{ duration: 0.75, delay: 0.12 }}
            className="space-y-5 text-[0.95rem] leading-relaxed text-muted lg:pt-3"
          >
            <p>
              Not because smaller utilities are worse at their jobs. Because
              they see too few theft cases to learn the pattern alone, and the
              law rightly forbids them from pooling raw customer data to close
              that gap.
            </p>
            <p>
              So every small utility solves the same problem from scratch,
              while a handful of well resourced ones pull further ahead.
            </p>
          </motion.div>
        </div>

        <div className="mt-20 grid gap-5 sm:mt-28 sm:grid-cols-3 sm:gap-6">
          <Stat
            n="01"
            value={<>&#8377;<Counter to={1.32} /></>}
            unit="lakh crore"
            label="Lost to electricity theft in India every year"
          />
          <Stat
            n="02"
            value={<><Counter to={45.8} decimals={1} />%</>}
            unit="points"
            label="Gap between the best and worst performing utilities"
          />
          <Stat
            n="03"
            value={<>0</>}
            unit="records"
            label="Customer data a utility has to hand over to close it"
          />
        </div>
      </div>
    </section>
  )
}

function Stat({
  n,
  value,
  unit,
  label,
}: {
  n: string
  value: React.ReactNode
  unit: string
  label: string
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 26 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-10% 0px' }}
      transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
      className="group relative overflow-hidden rounded-2xl border border-line p-8 transition-transform duration-500 hover:-translate-y-1 sm:p-9"
      style={{ background: 'var(--grad-1)' }}
    >
      <div
        className="absolute inset-x-0 top-0 h-[3px] origin-left scale-x-0 transition-transform duration-500 group-hover:scale-x-100"
        style={{ background: 'var(--c-accent)' }}
      />
      <div className="flex items-center justify-between">
        <span className="font-display text-sm text-faint">{n}</span>
        <span className="text-[0.62rem] tracking-[0.18em] text-faint uppercase">
          {unit}
        </span>
      </div>
      <div className="stat-figure mt-4 font-display text-[2.6rem] leading-none sm:text-[3.1rem]">
        {value}
      </div>
      <p className="mt-5 text-sm leading-relaxed text-muted">{label}</p>
    </motion.div>
  )
}
