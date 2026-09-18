import { useLayoutEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { motion } from 'framer-motion'
import {
  AbstractViz,
  DetectViz,
  GateViz,
  LiftViz,
  PoolViz,
} from './StepVisuals'
import stepDetect from '../assets/step-detect.jpg'
import stepAbstract from '../assets/step-abstract.jpg'
import stepGate from '../assets/step-gate.jpg'
import stepPool from '../assets/step-pool.jpg'
import stepLift from '../assets/step-lift.jpg'

gsap.registerPlugin(ScrollTrigger)

const STEPS = [
  {
    n: '01',
    eyebrow: 'Local intelligence',
    title: 'Detect',
    body: 'Each site runs its own agent over its own meters, watching for drift. A load shape that does not match anything the site has seen before is what fires. Small deviations are noise and stay ignored.',
    tone: 'var(--grad-1)',
    image: stepDetect,
    alt: 'A high voltage electrical substation against a clear sky',
    Viz: DetectViz,
  },
  {
    n: '02',
    eyebrow: 'Abstraction',
    title: 'Abstract',
    body: 'The anomaly is stripped of every identifying field and rewritten as a signature. No customer ID, no meter ID, no raw series, no location. What survives is the shape of the theft, nothing else.',
    tone: 'var(--grad-2)',
    image: stepAbstract,
    alt: 'Macro photograph of a green circuit board',
    Viz: AbstractViz,
  },
  {
    n: '03',
    eyebrow: 'Enforcement',
    title: 'Policy gate',
    body: 'A Cedar policy engine authorises every signature before it moves. Anything still carrying an identifying field is denied and logged. The boundary holds by rule, not by promise.',
    tone: 'var(--grad-3)',
    image: stepGate,
    alt: 'A row of padlocks against city lights at night',
    Viz: GateViz,
  },
  {
    n: '04',
    eyebrow: 'Shared memory',
    title: 'Shared pool',
    body: 'Permitted signatures land in a store every site can read. The pooled knowledge grows while the models stay exactly where they are. Test time memory, no retraining anywhere.',
    tone: 'var(--grad-4)',
    image: stepPool,
    alt: 'Fibre network cables glowing inside a server rack',
    Viz: PoolViz,
  },
  {
    n: '05',
    eyebrow: 'The payoff',
    title: 'Catch what you could not',
    body: 'A site with too little history checks its unflagged consumers against the pool, and catches theft it never had the data to learn on its own. Same site, same consumers, no new collection.',
    tone: 'var(--grad-5)',
    image: stepLift,
    alt: 'Aerial view of a lit city skyline at dusk',
    Viz: LiftViz,
  },
]

export function HowItWorks() {
  const root = useRef<HTMLElement>(null)

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      const wraps = gsap.utils.toArray<HTMLElement>('.stack-wrap')

      wraps.forEach((wrap, i) => {
        const card = wrap.querySelector('.stack-card')
        const img = wrap.querySelector('.stack-img')
        const line = wrap.querySelector('.stack-accent-line')

        // the incoming card's photo settles from a slight zoom as it
        // arrives, and the accent line draws itself in underneath the title
        gsap.fromTo(
          img,
          { scale: 1.22 },
          {
            scale: 1.02,
            ease: 'none',
            scrollTrigger: {
              trigger: wrap,
              start: 'top bottom',
              end: 'top 20%',
              scrub: 0.6,
            },
          },
        )
        gsap.fromTo(
          line,
          { scaleX: 0 },
          {
            scaleX: 1,
            ease: 'none',
            transformOrigin: 'left center',
            scrollTrigger: {
              trigger: wrap,
              start: 'top 65%',
              end: 'top 15%',
              scrub: 0.6,
            },
          },
        )

        if (i === wraps.length - 1) return
        // pushed back as the next card arrives on top. Dimming is a plain
        // opacity overlay, not a `filter` on the card itself. Animating
        // `filter` on an element that contains a `backdrop-filter` child
        // (the glass viz panel) makes Chromium drop a frame to solid black
        // while it re-promotes the compositing layer, which read as a hard
        // flash between steps instead of a fade.
        const dim = wrap.querySelector('.stack-dim')
        gsap.to(card, {
          scale: 0.93,
          y: -26,
          ease: 'none',
          scrollTrigger: {
            trigger: wrap,
            start: 'top top',
            end: '+=100%',
            scrub: 0.6,
          },
        })
        gsap.fromTo(
          dim,
          { opacity: 0 },
          {
            opacity: 0.55,
            ease: 'none',
            scrollTrigger: {
              trigger: wrap,
              start: 'top top',
              end: '+=100%',
              scrub: 0.6,
            },
          },
        )
      })
    }, root)
    return () => ctx.revert()
  }, [])

  return (
    <section id="how" ref={root} className="relative bg-bg px-4 pt-24 sm:px-8">
      <div className="mx-auto mb-12 max-w-6xl">
        <p className="eyebrow mb-6">How it works</p>
        <h2 className="max-w-3xl font-display text-[2.2rem] leading-[1.06] sm:text-[3.4rem]">
          Five steps between a suspicious meter and a peer who can use it.
        </h2>
      </div>

      {STEPS.map((step, i) => (
        <div
          key={step.n}
          className="stack-wrap sticky top-0 flex h-[100svh] items-center justify-center"
        >
          <article
            className="stack-card relative mx-auto grid w-full max-w-6xl overflow-hidden rounded-[1.75rem] border border-line will-change-transform lg:grid-cols-2"
            style={{
              background: step.tone,
              marginTop: i * 18,
              height: 'min(86svh, 660px)',
            }}
          >
            <div className="relative h-40 overflow-hidden sm:h-56 lg:hidden">
              <img
                src={step.image}
                alt={step.alt}
                className="stack-img h-full w-full object-cover"
              />
              <div
                className="absolute inset-0"
                style={{
                  background:
                    'linear-gradient(180deg, rgba(0,0,0,0.05) 0%, rgba(0,0,0,0.45) 100%)',
                }}
              />
            </div>

            <div className="flex flex-col justify-between p-8 sm:p-12">
              <div className="flex items-baseline justify-between">
                <p className="eyebrow">{step.eyebrow}</p>
                <span className="font-display text-2xl text-faint">
                  {step.n}
                </span>
              </div>

              <div className="py-6 sm:py-8">
                <h3 className="font-display text-[2.2rem] leading-[1.05] sm:text-[3rem]">
                  {step.title}
                </h3>
                <span
                  className="stack-accent-line mt-4 block h-[3px] w-16"
                  style={{ background: 'var(--c-accent)' }}
                />
                <p className="mt-5 max-w-md text-[0.93rem] leading-relaxed text-muted">
                  {step.body}
                </p>
              </div>

              <div className="h-px w-full bg-line" />
            </div>

            <div className="relative hidden overflow-hidden border-l border-line lg:block">
              <img
                src={step.image}
                alt={step.alt}
                className="stack-img absolute inset-0 h-full w-full object-cover"
              />
              <div
                className="absolute inset-0"
                style={{
                  background:
                    'linear-gradient(200deg, rgba(8,8,10,0.08) 10%, rgba(8,8,10,0.72) 100%)',
                }}
              />
              <motion.div
                initial={{ opacity: 0, y: 24, scale: 0.96 }}
                whileInView={{ opacity: 1, y: 0, scale: 1 }}
                viewport={{ once: true, amount: 0.6 }}
                transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
                className="glass absolute inset-x-8 bottom-8 rounded-2xl p-6"
              >
                <step.Viz />
              </motion.div>
            </div>

            <div
              className="stack-dim pointer-events-none absolute inset-0 z-20 rounded-[1.75rem]"
              style={{ background: '#000', opacity: 0 }}
            />
          </article>
        </div>
      ))}
    </section>
  )
}
