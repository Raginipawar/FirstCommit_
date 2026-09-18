import { useEffect, useState } from 'react'

const SECTIONS = [
  { id: 'problem', n: '01', label: 'The problem' },
  { id: 'how', n: '02', label: 'How it works' },
  { id: 'converge', n: '03', label: 'The swarm' },
  { id: 'live', n: '04', label: 'Live run' },
  { id: 'story', n: '05', label: 'Our story' },
  { id: 'about', n: '06', label: 'About' },
  // the footer flips to its own colour scheme, where the rail would be
  // unreadable, so reaching it just clears the label
  { id: 'site-footer', n: '', label: '' },
]

export function SideRail() {
  const [active, setActive] = useState<string | null>(null)

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]
        if (visible) setActive(visible.target.id)
      },
      { rootMargin: '-45% 0px -45% 0px', threshold: [0, 0.25, 0.5, 1] },
    )

    SECTIONS.forEach((s) => {
      const el = document.getElementById(s.id)
      if (el) observer.observe(el)
    })
    return () => observer.disconnect()
  }, [])

  const found = SECTIONS.find((s) => s.id === active)
  const current = found && found.label ? found : null

  return (
    <div className="pointer-events-none fixed left-0 top-0 z-40 hidden h-screen w-12 items-center justify-center lg:flex">
      <div
        className="rail-label whitespace-nowrap transition-opacity duration-500"
        style={{
          writingMode: 'vertical-rl',
          transform: 'rotate(180deg)',
          opacity: current ? 1 : 0,
          color: 'var(--c-muted)',
        }}
      >
        {current ? (
          <>
            <span style={{ color: 'var(--c-accent)' }}>{current.n}</span>
            <span>{'  '}</span>
            <span>{current.label}</span>
          </>
        ) : null}
      </div>
    </div>
  )
}
