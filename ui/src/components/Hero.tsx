import { useLayoutEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import nycMorning from '../assets/nyc-morning.jpg'
import nycNight from '../assets/nyc-night.jpg'
import { useTheme } from '../lib/theme'

gsap.registerPlugin(ScrollTrigger)

export function Hero() {
  const root = useRef<HTMLDivElement>(null)
  const { theme } = useTheme()

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: '#hero',
          start: 'top top',
          end: '+=160%',
          pin: true,
          scrub: 0.8,
        },
      })

      tl.to('#hero-frame', { inset: '1.25rem', borderRadius: '1.75rem' }, 0)
        .to('#hero-img', { scale: 1.22, ease: 'none' }, 0)
        .to('#hero-scrim', { opacity: 0.72 }, 0)
        .to(
          '#hero-copy',
          { scale: 1.55, y: '-14vh', ease: 'none', transformOrigin: 'left center' },
          0,
        )
        .to('#hero-copy', { opacity: 0 }, 0.68)
        .to('#hero-cue', { opacity: 0, duration: 0.2 }, 0)
    }, root)

    return () => ctx.revert()
  }, [])

  return (
    <div ref={root}>
      <section id="hero" className="relative h-[100svh] w-full overflow-hidden">
        <div
          id="hero-frame"
          className="absolute overflow-hidden"
          style={{ inset: 0, borderRadius: 0 }}
        >
          <div id="hero-img" className="absolute inset-0 h-full w-full">
            {/* Two real photographs of the same city, morning and night,
                cross-fading on the site's own theme toggle rather than a
                CSS filter pretending to change the light. */}
            <img
              src={nycMorning}
              alt="Manhattan at first light, seen from above"
              className="absolute inset-0 h-full w-full object-cover transition-opacity duration-[1400ms] ease-in-out"
              style={{ opacity: theme === 'light' ? 1 : 0 }}
            />
            <img
              src={nycNight}
              alt="Lower Manhattan lit up after dark"
              className="absolute inset-0 h-full w-full object-cover transition-opacity duration-[1400ms] ease-in-out"
              style={{ opacity: theme === 'dark' ? 1 : 0 }}
            />
          </div>
          <div
            id="hero-scrim"
            className="absolute inset-0"
            style={{
              opacity: 0.42,
              background:
                'linear-gradient(180deg, rgba(6,6,10,0.55) 0%, rgba(6,6,10,0.12) 38%, rgba(6,6,10,0.82) 100%)',
            }}
          />

          <div className="absolute inset-0 flex flex-col justify-end p-6 pb-16 sm:p-12 sm:pb-20">
            <div id="hero-copy" className="max-w-4xl will-change-transform">
              <p className="mb-4 text-[0.62rem] tracking-[0.26em] text-white/70 uppercase">
                Electricity theft detection, without the data sharing
              </p>
              <h1 className="font-display text-[2.7rem] leading-[1.02] text-white sm:text-[4.5rem] lg:text-[5.5rem]">
                Share what your meters learn.
                <br />
                <em className="text-[#ffc46b]">Not what they see.</em>
              </h1>
            </div>

            <div
              id="hero-cue"
              className="mt-10 flex items-center gap-3 text-white/60"
            >
              <span className="h-10 w-px bg-white/30" />
              <span className="text-[0.6rem] tracking-[0.26em] uppercase">
                Scroll
              </span>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
