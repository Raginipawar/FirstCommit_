import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useTheme } from '../lib/theme'

const LINKS = [
  { label: 'The problem', href: '#problem' },
  { label: 'How it works', href: '#how' },
  { label: 'Live run', href: '#live' },
  { label: 'Our story', href: '#story' },
  { label: 'About', href: '#about' },
]

export function Nav() {
  const { theme, toggle } = useTheme()
  const [open, setOpen] = useState(false)
  const [lifted, setLifted] = useState(false)

  useEffect(() => {
    const onScroll = () => setLifted(window.scrollY > 40)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <>
      <header className="fixed inset-x-0 top-0 z-50">
        <div
          className={`flex items-center justify-between px-5 py-4 transition-all duration-500 sm:px-8 ${
            lifted ? 'backdrop-blur-xl' : ''
          }`}
          style={{
            // over the hero photograph the bar has no panel behind it, and the
            // sky is bright in either theme, so it stays white until it lifts
            color: lifted || open ? 'var(--c-text)' : '#ffffff',
            background: lifted ? 'var(--glass)' : 'transparent',
            borderBottom: lifted
              ? '1px solid var(--glass-line)'
              : '1px solid transparent',
          }}
        >
          <a href="#top" className="flex items-baseline gap-2">
            <span className="font-display text-2xl leading-none">TRIPWIRE</span>
            <span className="hidden text-[0.6rem] tracking-[0.2em] opacity-60 uppercase sm:inline">
              Team Saturn
            </span>
          </a>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={toggle}
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
              className="grid h-10 w-10 place-items-center rounded-full border border-current/25 transition-colors hover:bg-accent-soft"
            >
              <AnimatePresence mode="wait" initial={false}>
                <motion.span
                  key={theme}
                  initial={{ opacity: 0, rotate: -45, scale: 0.6 }}
                  animate={{ opacity: 1, rotate: 0, scale: 1 }}
                  exit={{ opacity: 0, rotate: 45, scale: 0.6 }}
                  transition={{ duration: 0.28 }}
                  className="block"
                >
                  {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
                </motion.span>
              </AnimatePresence>
            </button>

            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              aria-label="Menu"
              aria-expanded={open}
              className="grid h-10 w-10 place-items-center rounded-full border border-current/25 transition-colors hover:bg-accent-soft"
            >
              <span className="relative block h-3 w-4">
                <span
                  className="absolute left-0 block h-px w-4 bg-current transition-transform duration-300"
                  style={{
                    top: open ? '6px' : '2px',
                    transform: open ? 'rotate(45deg)' : 'none',
                  }}
                />
                <span
                  className="absolute left-0 block h-px w-4 bg-current transition-transform duration-300"
                  style={{
                    top: open ? '6px' : '9px',
                    transform: open ? 'rotate(-45deg)' : 'none',
                  }}
                />
              </span>
            </button>
          </div>
        </div>
      </header>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
            className="fixed inset-0 z-40 flex items-center justify-center backdrop-blur-2xl"
            style={{ background: 'var(--glass)' }}
            onClick={() => setOpen(false)}
          >
            <nav className="px-8">
              <ul>
                {LINKS.map((link, i) => (
                  <motion.li
                    key={link.href}
                    initial={{ opacity: 0, y: 28 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.06 * i + 0.1, duration: 0.5 }}
                    className="overflow-hidden"
                  >
                    <a
                      href={link.href}
                      onClick={() => setOpen(false)}
                      className="block py-2 font-display text-5xl leading-tight transition-colors hover:text-accent sm:text-7xl"
                    >
                      {link.label}
                    </a>
                  </motion.li>
                ))}
              </ul>
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

function SunIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="12" cy="12" r="4.2" />
      <path d="M12 2v2.4M12 19.6V22M2 12h2.4M19.6 12H22M4.9 4.9l1.7 1.7M17.4 17.4l1.7 1.7M19.1 4.9l-1.7 1.7M6.6 17.4l-1.7 1.7" />
    </svg>
  )
}

function MoonIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M20 13.4A8.2 8.2 0 1 1 10.6 4a6.6 6.6 0 0 0 9.4 9.4Z" />
    </svg>
  )
}
