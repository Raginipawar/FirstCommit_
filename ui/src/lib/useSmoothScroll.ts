import { useEffect } from 'react'
import Lenis from 'lenis'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

export function useSmoothScroll() {
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    const lenis = new Lenis({
      duration: 1.15,
      easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
    })

    lenis.on('scroll', ScrollTrigger.update)

    const raf = (time: number) => lenis.raf(time * 1000)
    gsap.ticker.add(raf)
    gsap.ticker.lagSmoothing(0)

    // anchor links have to go through Lenis or they fight the rAF loop
    const onClick = (e: MouseEvent) => {
      const link = (e.target as HTMLElement).closest('a[href^="#"]')
      if (!link) return
      const id = link.getAttribute('href')
      if (!id || id === '#') return
      const el = document.querySelector(id)
      if (!el) return
      e.preventDefault()
      lenis.scrollTo(el as HTMLElement, { offset: 0, duration: 1.4 })
    }
    document.addEventListener('click', onClick)

    // Trigger positions (and pin-spacer heights) are cached the moment each
    // ScrollTrigger is created. Anything that changes document height after
    // that (a hero photo finishing decode, a webfont swapping in, a slow
    // connection) leaves every pin below it measuring against a stale
    // offset. On a fast/cached load that window is small enough not to
    // notice; on a real connection with ~1.2MB of hero photos still
    // in flight it's wide open, and the section below a still-resizing
    // pinned hero reports itself "in view" to things like the side rail
    // well before it visually is.
    //
    // A fixed timeout can only ever guess how long that takes, so instead
    // watch the actual page height and refresh whenever it moves. This
    // self-corrects no matter how slow the load is, and costs nothing once
    // the page has settled since it just stops firing.
    let debounce: number | undefined
    const refresh = () => {
      window.clearTimeout(debounce)
      debounce = window.setTimeout(() => ScrollTrigger.refresh(), 120)
    }
    const ro = new ResizeObserver(refresh)
    ro.observe(document.documentElement)
    document.fonts?.ready.then(refresh).catch(() => {})

    return () => {
      document.removeEventListener('click', onClick)
      ro.disconnect()
      window.clearTimeout(debounce)
      gsap.ticker.remove(raf)
      lenis.destroy()
    }
  }, [])
}
