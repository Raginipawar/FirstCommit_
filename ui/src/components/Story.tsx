import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { SplitText } from 'gsap/SplitText'

gsap.registerPlugin(ScrollTrigger, SplitText)

function useCountOnFlag(target: number, play: boolean, decimals = 1, duration = 1400) {
  const [v, setV] = useState(0)
  const played = useRef(false)
  useEffect(() => {
    if (!play || played.current) return
    played.current = true
    const start = performance.now()
    let frame = 0
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration)
      setV(target * (1 - Math.pow(1 - p, 3)))
      if (p < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [play, target, duration])
  return v.toFixed(decimals)
}

/**
 * Every bar/circle visualization in this section sits inside one of these:
 * a frosted glass card (the shared `.glass` treatment used across the
 * site) floating over its own soft accent glow, so the blur actually has
 * something with color and shape behind it to frost, rather than
 * blurring a flat single-tone section background into itself.
 */
function GlassPanel({ children }: { children: ReactNode }) {
  return (
    <div className="relative mx-auto mt-8 w-full max-w-xs sm:max-w-sm">
      <div
        aria-hidden
        className="absolute -inset-6 -z-10 rounded-full opacity-70 blur-2xl"
        style={{ background: 'var(--c-accent-soft)' }}
      />
      <div className="glass rounded-2xl px-6 py-5 sm:px-7 sm:py-6">{children}</div>
    </div>
  )
}

function GapViz({ active }: { active: boolean }) {
  return (
    <GlassPanel>
      <svg viewBox="0 0 320 90" className="w-full" aria-hidden>
        <text x="0" y="14" fontSize="10" fill="var(--c-faint)" fontFamily="var(--font-sans)">
          best performer
        </text>
        <rect x="0" y="20" width="320" height="10" rx="5" fill="var(--c-line)" />
        <rect
          x="0"
          y="20"
          height="10"
          rx="5"
          fill="var(--c-good)"
          width={active ? 24 : 0}
          style={{ transition: 'width 1.1s cubic-bezier(.22,1,.36,1) .15s' }}
        />
        <text x="0" y="58" fontSize="10" fill="var(--c-faint)" fontFamily="var(--font-sans)">
          weakest performer
        </text>
        <rect x="0" y="64" width="320" height="10" rx="5" fill="var(--c-line)" />
        <rect
          x="0"
          y="64"
          height="10"
          rx="5"
          fill="var(--c-accent)"
          width={active ? 300 : 0}
          style={{ transition: 'width 1.3s cubic-bezier(.22,1,.36,1) .3s' }}
        />
      </svg>
    </GlassPanel>
  )
}

function DatasetViz({ active }: { active: boolean }) {
  const sites = [
    { label: 'Site A', n: 600, r: 34 },
    { label: 'Site B', n: 450, r: 28 },
    { label: 'Site C, low data', n: 90, r: 14 },
  ]
  return (
    <GlassPanel>
      <div className="flex items-end justify-center gap-8 sm:gap-10">
        {sites.map((s, i) => (
          <div key={s.label} className="flex flex-col items-center gap-3">
            <div
              className="glass rounded-full"
              style={{
                width: active ? s.r * 2 : 0,
                height: active ? s.r * 2 : 0,
                borderColor: i === 2 ? 'var(--c-accent)' : 'var(--glass-line)',
                boxShadow: i === 2 ? 'inset 0 0 16px var(--c-accent-soft)' : 'none',
                transition: `width .8s cubic-bezier(.22,1,.36,1) ${i * 0.15}s, height .8s cubic-bezier(.22,1,.36,1) ${i * 0.15}s`,
              }}
            />
            <span className="font-mono text-[0.65rem] text-faint">{s.n} consumers</span>
            <span className="text-xs text-muted">{s.label}</span>
          </div>
        ))}
      </div>
    </GlassPanel>
  )
}

function PayoffViz({ active }: { active: boolean }) {
  return (
    <GlassPanel>
      <div className="mb-2 flex justify-between font-mono text-[0.7rem] text-faint">
        <span>isolated</span>
        <span>33.3%</span>
      </div>
      <div className="glass mb-6 h-2 w-full overflow-hidden rounded-full">
        <div
          className="h-full rounded-full"
          style={{
            background: 'var(--c-faint)',
            width: active ? '33.3%' : 0,
            transition: 'width 1s cubic-bezier(.22,1,.36,1) .1s',
          }}
        />
      </div>
      <div className="mb-2 flex justify-between font-mono text-[0.7rem] text-accent">
        <span>pooled</span>
        <span>66.7%</span>
      </div>
      <div className="glass h-2 w-full overflow-hidden rounded-full">
        <div
          className="h-full rounded-full"
          style={{
            background: 'var(--c-accent)',
            width: active ? '66.7%' : 0,
            transition: 'width 1.3s cubic-bezier(.22,1,.36,1) .3s',
          }}
        />
      </div>
    </GlassPanel>
  )
}

type BeatProps = { active: boolean }

function Beat0({}: BeatProps) {
  return (
    <>
      <p className="eyebrow kinetic-line mb-6">Before it was code</p>
      <h2 className="kinetic-line max-w-3xl font-display text-[2.1rem] leading-[1.12] sm:text-[3.4rem]">
        Every rupee someone steals from the grid gets paid by someone who didn't.
      </h2>
      <p className="kinetic-line mt-6 max-w-lg text-sm text-muted opacity-80">
        You've just watched it work. Here's why it exists at all.
      </p>
    </>
  )
}

function Beat1({ active }: BeatProps) {
  const v = useCountOnFlag(1.32, active)
  return (
    <>
      <p className="eyebrow kinetic-line mb-6">The scale</p>
      <div className="stat-figure font-display text-[3.2rem] leading-none sm:text-[5.5rem]">
        &#8377;{v} <span className="text-[0.4em] align-top">lakh crore</span>
      </div>
      <p className="kinetic-line mt-6 max-w-lg text-sm leading-relaxed text-muted sm:text-base">
        lost to electricity theft in India, every year: about 2.4% of the
        entire GDP, gone before it's ever billed.
      </p>
    </>
  )
}

function Beat2({ active }: BeatProps) {
  const v = useCountOnFlag(45.8, active)
  return (
    <>
      <p className="eyebrow kinetic-line mb-6">The gap</p>
      <div className="stat-figure font-display text-[3.2rem] leading-none sm:text-[5.5rem]">
        {v}<span className="text-[0.5em]">pts</span>
      </div>
      <p className="kinetic-line mt-6 max-w-lg text-sm leading-relaxed text-muted sm:text-base">
        between India's best and worst performing power utility. Not a skill
        gap. A data gap: a big utility sees thousands of theft cases and
        learns the pattern. A small one sees a handful, ever.
      </p>
      <GapViz active={active} />
    </>
  )
}

function Beat3({}: BeatProps) {
  return (
    <>
      <p className="eyebrow kinetic-line mb-6">The obvious fix</p>
      <h2 className="kinetic-line font-display text-[2.1rem] leading-[1.1] sm:text-[3.2rem]">
        So, share the data?
        <br />
        <em className="text-accent">You can't.</em>
      </h2>
      <p className="kinetic-line mt-6 max-w-lg text-sm leading-relaxed text-muted sm:text-base">
        Household electricity data reveals when you're home, whether you run
        a business, roughly what you earn. Utilities are separate companies
        with no legal path to hand that over to a neighbour.
      </p>
    </>
  )
}

function Beat4({}: BeatProps) {
  return (
    <>
      <p className="eyebrow kinetic-line mb-6">The idea</p>
      <h2 className="kinetic-line font-display text-[2.3rem] leading-[1.1] italic sm:text-[3.6rem]">
        Don't share the data.
        <br />
        <span className="text-accent">Share the shape.</span>
      </h2>
      <p className="kinetic-line mt-6 max-w-lg text-sm leading-relaxed text-muted sm:text-base">
        Strip every identifying detail. Keep only the pattern: a sharp drop,
        lasting two weeks, right before a billing cycle, that never
        recovered. Useless to identify a person. Priceless to recognise theft.
      </p>
    </>
  )
}

function Beat5({ active }: BeatProps) {
  return (
    <>
      <p className="eyebrow kinetic-line mb-6">Grounded in something real</p>
      <h2 className="kinetic-line max-w-xl font-display text-[1.9rem] leading-[1.15] sm:text-[2.8rem]">
        42,372 real consumers. 1,035 days. Already labelled theft or honest.
      </h2>
      <p className="kinetic-line mt-6 max-w-lg text-sm leading-relaxed text-muted sm:text-base">
        The SGCC dataset, the same published research data behind real IEEE
        papers on this exact problem. This machine has no Kaggle login
        configured, so we built a stand-in that behaves exactly like it:
        same shape, same theft vocabulary. Swapping in the real file later
        is a one-line change, nothing else moves.
      </p>
      <DatasetViz active={active} />
    </>
  )
}

function Beat6({}: BeatProps) {
  return (
    <>
      <p className="eyebrow kinetic-line mb-6">What we got wrong first</p>
      <h2 className="kinetic-line max-w-xl font-display text-[2rem] leading-[1.15] sm:text-[3rem]">
        Early on, we shared everything the detector flagged, including its
        own mistakes.
      </h2>
      <p className="kinetic-line mt-6 max-w-lg text-sm leading-relaxed text-muted sm:text-base">
        That made the shared pool worse, not better. Adding a second check
        (only a genuinely sharp, sustained drop counts) fixed it completely.
        A real lesson, not a rehearsed one.
      </p>
    </>
  )
}

function Beat7({ active }: BeatProps) {
  return (
    <>
      <p className="eyebrow kinetic-line mb-6">The proof</p>
      <h2 className="kinetic-line max-w-xl font-display text-[2rem] leading-[1.15] sm:text-[2.8rem]">
        Detection rate on the low-data site, doubled.
      </h2>
      <p className="kinetic-line mt-6 max-w-lg text-sm leading-relaxed text-muted sm:text-base">
        Same site. Same consumers. Zero new false accusations, purely from
        checking against what its peers already found.
      </p>
      <PayoffViz active={active} />
    </>
  )
}

function Beat8({}: BeatProps) {
  return (
    <>
      <p className="eyebrow kinetic-line mb-6">Why it matters</p>
      <h2 className="kinetic-line max-w-xl font-display text-[2rem] leading-[1.15] sm:text-[2.9rem]">
        Theft's cost doesn't disappear. It gets passed to honest customers
        through higher tariffs.
      </h2>
      <p className="kinetic-line mt-7 max-w-lg font-display text-xl italic text-accent sm:text-2xl">
        Share what your meters learn. Not what they see.
      </p>
      <p className="kinetic-line mt-6 text-xs tracking-[0.18em] text-faint uppercase">
        Team Saturn, next
      </p>
    </>
  )
}

const BEATS = [Beat0, Beat1, Beat2, Beat3, Beat4, Beat5, Beat6, Beat7, Beat8]

/**
 * Kinetic line reveal, the signature move on agency sites like
 * emotion-agency.com: each line of text sits behind its own mask and
 * slides up into view rather than the whole block just fading in.
 *
 * Split once on mount (SplitText needs real layout to compute line
 * breaks, which these elements have even at opacity:0 -- they're never
 * display:none, only invisible). The reveal itself replays on every
 * entry, not just the first: scrubbing back up into an earlier beat
 * should feel as alive as scrolling into it forward, so exiting resets
 * the lines instantly (a plain `set`, not a tween -- the whole beat is
 * already fading out via the parent timeline at that point) rather than
 * leaving them revealed for a stale "already played" look next time.
 */
function BeatFrame({ active, children }: { active: boolean; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)
  const splitRef = useRef<SplitText | null>(null)
  // `active` as it is *right now*, readable from inside the fonts.ready
  // callback below without adding `active` to that effect's deps (which
  // would re-split on every scroll tick, see the comment further down).
  const activeRef = useRef(active)
  activeRef.current = active

  const reveal = (split: SplitText, animate: boolean) => {
    if (activeRef.current) {
      if (animate) {
        gsap.to(split.lines, {
          yPercent: 0,
          skewY: 0,
          duration: 0.9,
          stagger: 0.055,
          ease: 'power4.out',
          overwrite: true,
        })
      } else {
        gsap.set(split.lines, { yPercent: 0, skewY: 0 })
      }
    } else {
      gsap.set(split.lines, { yPercent: 115, skewY: 4 })
    }
  }

  useLayoutEffect(() => {
    if (!ref.current) return
    let cancelled = false

    // SplitText measures line breaks against whatever font is actually
    // rendering *right now*. Instrument Sans loads async (a <link> tag,
    // not bundled), so splitting immediately on mount measures against
    // the fallback system font instead -- different character widths mean
    // different wrap points, and the split wrapper divs don't
    // automatically re-measure once the real font swaps in. Observed
    // result: a line wrapper 52px tall (two real lines of reflowed text
    // stacked inside what SplitText still thinks is one line) sitting
    // next to normal 26px single-line wrappers. Waiting for fonts.ready
    // first means we split against final layout, the only layout that
    // will ever actually be shown.
    document.fonts.ready.then(() => {
      if (cancelled || !ref.current) return
      const targets = ref.current.querySelectorAll('.kinetic-line')
      if (targets.length === 0) return
      const split = SplitText.create(targets, {
        type: 'lines',
        mask: 'lines',
        linesClass: 'kinetic-line-inner',
      })
      splitRef.current = split
      // fonts.ready can resolve after this beat already became active
      // (e.g. beat 0, visible from first paint) -- in that case `active`
      // won't flip again to retrigger the effect below, so the initial
      // state has to account for "already active" right here, snapped in
      // rather than animated since this isn't a real entrance.
      reveal(split, false)
    })

    return () => {
      cancelled = true
      splitRef.current?.revert()
      splitRef.current = null
    }
    // deliberately once-on-mount only: each beat's static text (eyebrow,
    // heading, paragraph) never changes after first render -- only the
    // live count-up *number* does, which isn't a `.kinetic-line` target.
    // `children` is a new element reference on every Story re-render
    // (i.e. every scroll tick, since that drives `activeBeat`), so
    // depending on it here would revert and rebuild the split constantly,
    // cancelling whatever reveal animation was mid-flight each time.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const split = splitRef.current
    if (!split) return // fonts.ready hasn't resolved yet -- it will set the correct initial state itself
    reveal(split, true)
  }, [active])

  return (
    <div ref={ref} className="mx-auto w-full max-w-3xl px-6 sm:px-12">
      {children}
    </div>
  )
}

export function Story() {
  const root = useRef<HTMLElement>(null)
  const [activeBeat, setActiveBeat] = useState(0)
  const [reducedMotion, setReducedMotion] = useState(false)

  useEffect(() => {
    setReducedMotion(window.matchMedia('(prefers-reduced-motion: reduce)').matches)
  }, [])

  useLayoutEffect(() => {
    if (reducedMotion) return
    const ctx = gsap.context(() => {
      const n = BEATS.length
      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: root.current,
          start: 'top top',
          end: `+=${n * 90}%`,
          pin: true,
          scrub: 0.7,
          onUpdate: (self) => {
            setActiveBeat(Math.min(n - 1, Math.floor(self.progress * n)))
          },
        },
      })

      // Beat 0 is what's on screen the instant the section pins, so it
      // starts already visible -- a fromTo starting at opacity 0 would
      // have GSAP snap it invisible the moment the timeline is built,
      // before any scrolling happens, since a scrubbed timeline renders
      // its own position-0 state immediately rather than waiting for
      // the user to scroll there.
      gsap.set('#story-beat-0', { opacity: 1, y: 0, scale: 1 })

      for (let i = 0; i < n; i++) {
        if (i > 0) {
          tl.fromTo(
            `#story-beat-${i}`,
            { opacity: 0, y: 36, scale: 0.97 },
            { opacity: 1, y: 0, scale: 1, duration: 0.32, ease: 'power2.out' },
            i,
          )
        }
        if (i < n - 1) {
          tl.to(
            `#story-beat-${i}`,
            { opacity: 0, y: -36, scale: 0.97, duration: 0.28, ease: 'power2.in' },
            i + 0.72,
          )
        }
      }
    }, root)
    return () => ctx.revert()
  }, [reducedMotion])

  if (reducedMotion) {
    return (
      <section id="story" ref={root} className="relative bg-bg px-6 py-28 sm:px-12">
        <div className="mx-auto max-w-3xl space-y-24">
          {BEATS.map((B, i) => (
            <div key={i}>
              <B active />
            </div>
          ))}
        </div>
      </section>
    )
  }

  return (
    <section id="story" ref={root} className="relative h-[100svh] overflow-hidden bg-bg">
      {BEATS.map((B, i) => (
        // full-bleed flex centering, not a translateY(-50%) centering hack
        // -- GSAP owns this element's transform for the enter/exit
        // animation, and would silently overwrite a CSS centering
        // transform sharing the same property. `inset-0` here positions
        // against the nearest positioned ancestor -- this <section> -- so
        // the max-width/padding that constrains reading width has to live
        // on the inner wrapper below, not on a non-positioned ancestor
        // further up, which an absolutely positioned element ignores
        // entirely for layout purposes.
        <div
          key={i}
          id={`story-beat-${i}`}
          className="absolute inset-0 flex items-center"
          style={{ opacity: i === 0 ? 1 : 0 }}
        >
          {/* BeatFrame is also the fix for a Beat returning a Fragment of
              several block siblings (p, h2, p...): without a real wrapper
              element they'd become direct children of the flex container
              above and get laid out as separate row items side by side
              instead of stacking. */}
          <BeatFrame active={activeBeat === i}>
            <B active={activeBeat === i} />
          </BeatFrame>
        </div>
      ))}

      <div className="pointer-events-none absolute inset-x-0 bottom-8 flex items-center justify-center gap-2 sm:bottom-10">
        {BEATS.map((_, i) => (
          <span
            key={i}
            className="h-1.5 rounded-full transition-all duration-500"
            style={{
              width: activeBeat === i ? '20px' : '6px',
              background: activeBeat === i ? 'var(--c-accent)' : 'var(--c-line)',
            }}
          />
        ))}
      </div>

      <div className="pointer-events-none absolute bottom-8 right-6 font-mono text-[0.65rem] text-faint sm:right-12">
        {String(activeBeat + 1).padStart(2, '0')} / {String(BEATS.length).padStart(2, '0')}
      </div>
    </section>
  )
}
