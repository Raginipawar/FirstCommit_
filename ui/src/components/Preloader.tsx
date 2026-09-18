import { useEffect, useRef, useState } from 'react'
import { gsap } from 'gsap'

const SEEN_KEY = 'tripwire-seen-preloader'

export function Preloader() {
  const [hidden] = useState(() => {
    try {
      return sessionStorage.getItem(SEEN_KEY) === '1'
    } catch {
      return false
    }
  })
  const [gone, setGone] = useState(hidden)
  const root = useRef<HTMLDivElement>(null)
  const sparkRef = useRef<SVGCircleElement>(null)
  const wireRef = useRef<SVGPathElement>(null)
  const countRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (hidden) return
    try {
      sessionStorage.setItem(SEEN_KEY, '1')
    } catch {
      /* private mode, it just plays every time, harmless */
    }

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduced) {
      setGone(true)
      return
    }

    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const wire = wireRef.current
    const spark = sparkRef.current
    const length = wire?.getTotalLength() ?? 0
    const counter = { n: 0 }

    const tl = gsap.timeline({
      defaults: { ease: 'power2.inOut' },
      onComplete: () => {
        document.body.style.overflow = prevOverflow
        setGone(true)
      },
    })

    tl.to('.pl-pole', { opacity: 1, duration: 0.5 })
      .to(
        wire,
        {
          strokeDashoffset: 0,
          duration: 0.85,
          ease: 'power1.inOut',
        },
        0.15,
      )
      .to(
        counter,
        {
          n: 100,
          duration: 1.3,
          ease: 'power1.inOut',
          onUpdate: () => {
            if (countRef.current) {
              countRef.current.textContent = String(Math.round(counter.n)).padStart(3, '0')
            }
            if (spark && wire) {
              const pt = wire.getPointAtLength(length * (counter.n / 100))
              spark.setAttribute('cx', String(pt.x))
              spark.setAttribute('cy', String(pt.y))
            }
          },
        },
        0.15,
      )
      .to('.pl-spark', { opacity: 1, duration: 0.2 }, 0.15)
      .fromTo(
        '.pl-wordmark',
        { opacity: 0, y: 8 },
        { opacity: 1, y: 0, duration: 0.55 },
        1.1,
      )
      .to({}, { duration: 0.35 })
      .to(root.current, {
        yPercent: -100,
        duration: 0.8,
        ease: 'power3.inOut',
      })

    return () => {
      tl.kill()
      document.body.style.overflow = prevOverflow
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (gone) return null

  return (
    <div
      ref={root}
      className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-bg"
      aria-hidden
    >
      <svg
        width="220"
        height="120"
        viewBox="0 0 220 120"
        className="pl-pole"
        style={{ opacity: 0 }}
      >
        <line x1="30" y1="20" x2="30" y2="95" stroke="var(--c-faint)" strokeWidth="2" />
        <line x1="14" y1="30" x2="46" y2="30" stroke="var(--c-faint)" strokeWidth="2" />
        <line x1="190" y1="20" x2="190" y2="95" stroke="var(--c-faint)" strokeWidth="2" />
        <line x1="174" y1="30" x2="206" y2="30" stroke="var(--c-faint)" strokeWidth="2" />

        <path
          ref={wireRef}
          d="M 30 30 Q 110 62 190 30"
          fill="none"
          stroke="var(--c-line)"
          strokeWidth="1.5"
          strokeDasharray="220"
          strokeDashoffset="220"
        />

        <circle
          ref={sparkRef}
          className="pl-spark"
          cx="30"
          cy="30"
          r="4"
          fill="var(--c-accent)"
          style={{ opacity: 0, filter: 'drop-shadow(0 0 6px var(--c-accent))' }}
        />

        <line x1="30" y1="95" x2="30" y2="102" stroke="var(--c-faint)" strokeWidth="2" />
        <line x1="190" y1="95" x2="190" y2="102" stroke="var(--c-faint)" strokeWidth="2" />
      </svg>

      <div className="pl-wordmark mt-5 flex items-center gap-4" style={{ opacity: 0 }}>
        <span className="font-display text-2xl tracking-wide">TRIPWIRE</span>
        <span className="font-mono text-xs text-faint">
          <span ref={countRef}>000</span>
        </span>
      </div>
    </div>
  )
}
