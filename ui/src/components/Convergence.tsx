import { useLayoutEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

// labels land in each circle's exclusive lobe once the three converge,
// so they never sit on top of one another
const CIRCLES = [
  { id: 'c-a', from: 170, to: 352, labelFrom: 170, labelTo: 233, labelY: 238, label: 'Site A', sub: '93.3% alone' },
  { id: 'c-b', from: 450, to: 450, labelFrom: 450, labelTo: 450, labelY: 40, label: 'Site B', sub: '97.2% alone' },
  { id: 'c-c', from: 730, to: 548, labelFrom: 730, labelTo: 667, labelY: 238, label: 'Site C', sub: 'low data · 33.3% alone' },
]

export function Convergence() {
  const root = useRef<HTMLElement>(null)

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: root.current,
          start: 'top top',
          end: '+=200%',
          pin: root.current,
          scrub: 0.8,
        },
      })

      CIRCLES.forEach((c) => {
        tl.fromTo(
          `#${c.id}`,
          { attr: { cx: c.from }, opacity: 0.5 },
          { attr: { cx: c.to }, opacity: 1, ease: 'power2.inOut' },
          0,
        )
        tl.fromTo(
          `#${c.id}-label`,
          { attr: { x: c.labelFrom }, opacity: 0 },
          { attr: { x: c.labelTo }, opacity: 1, ease: 'power2.inOut' },
          0,
        )
        tl.fromTo(
          `#${c.id}-sub`,
          { attr: { x: c.labelFrom }, opacity: 0 },
          { attr: { x: c.labelTo }, opacity: 1, ease: 'power2.inOut' },
          0,
        )
      })

      tl.fromTo('#pool-core', { opacity: 0, scale: 0.7 }, { opacity: 1, scale: 1 }, 0.55)
      tl.fromTo(
        '#converge-caption',
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0 },
        0.7,
      )
    }, root)
    return () => ctx.revert()
  }, [])

  return (
    <section
      id="converge"
      ref={root}
      className="relative flex h-[100svh] flex-col items-center justify-center overflow-hidden bg-bg px-6 pt-24 pb-10"
    >
      <div className="mb-2 text-center">
        <p className="eyebrow mb-4">The swarm</p>
        <h2 className="mx-auto max-w-2xl font-display text-[1.9rem] leading-[1.1] sm:text-[2.9rem]">
          No central brain. Three sites, one pooled memory.
        </h2>
      </div>

      <svg
        viewBox="0 0 900 460"
        className="w-full max-w-3xl"
        role="img"
        aria-label="Three utility sites converging on one shared pattern store"
      >
        {CIRCLES.map((c) => (
          <circle
            key={c.id}
            id={c.id}
            cx={c.from}
            cy="230"
            r="168"
            fill="none"
            stroke="var(--c-text)"
            strokeWidth="1.25"
            opacity="0.5"
          />
        ))}

        <defs>
          <radialGradient id="pool-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="var(--c-accent)" stopOpacity="0.32" />
            <stop offset="100%" stopColor="var(--c-accent)" stopOpacity="0" />
          </radialGradient>
        </defs>

        <g id="pool-core" style={{ transformOrigin: '450px 230px' }}>
          <circle cx="450" cy="230" r="86" fill="url(#pool-glow)" />
          <circle cx="450" cy="230" r="54" fill="var(--c-accent-soft)" />
          <circle cx="450" cy="230" r="54" fill="none" stroke="var(--c-accent)" strokeWidth="1" />
          <text
            x="450"
            y="235"
            textAnchor="middle"
            fontSize="19"
            fontStyle="italic"
            fill="var(--c-accent)"
            fontFamily="var(--font-display)"
          >
            shared pool
          </text>
        </g>

        {CIRCLES.map((c) => (
          <g key={`${c.id}-label`}>
            <text
              id={`${c.id}-label`}
              x={c.labelFrom}
              y={c.labelY}
              textAnchor="middle"
              fontSize="16"
              fontWeight="500"
              fill="var(--c-text)"
              fontFamily="var(--font-sans)"
              opacity="0"
            >
              {c.label}
            </text>
            <text
              id={`${c.id}-sub`}
              x={c.labelFrom}
              y={c.labelY + 20}
              textAnchor="middle"
              fontSize="11.5"
              letterSpacing="0.02em"
              fill="var(--c-faint)"
              fontFamily="var(--font-sans)"
              opacity="0"
            >
              {c.sub}
            </text>
          </g>
        ))}
      </svg>

      <p
        id="converge-caption"
        className="mx-auto mt-4 max-w-xl text-center text-sm leading-relaxed text-muted opacity-0"
      >
        Every site decides for itself what is surprising enough to share. When
        one fires, its peers receive, check and adapt on their own terms. The
        intelligence sits across the sites, not above them.
      </p>
    </section>
  )
}
