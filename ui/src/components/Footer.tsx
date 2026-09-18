const PHRASE = 'Stop the leak.'

export function Footer() {
  return (
    <footer
      id="site-footer"
      className="relative overflow-hidden rounded-t-[2rem] pt-20"
      style={{ background: 'var(--c-inverse)', color: 'var(--c-inverse-text)' }}
    >
      <div className="relative flex select-none overflow-hidden py-6">
        <div className="marquee-track flex shrink-0">
          {Array.from({ length: 8 }).map((_, i) => (
            <span
              key={i}
              className="font-display whitespace-nowrap px-6 text-[3.5rem] leading-none sm:text-[7rem]"
            >
              {PHRASE}
            </span>
          ))}
        </div>
        <div className="marquee-track flex shrink-0" aria-hidden>
          {Array.from({ length: 8 }).map((_, i) => (
            <span
              key={i}
              className="font-display whitespace-nowrap px-6 text-[3.5rem] leading-none sm:text-[7rem]"
            >
              {PHRASE}
            </span>
          ))}
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-6 pt-16 pb-10 sm:px-12">
        <div
          className="grid gap-10 border-t pt-10 sm:grid-cols-3"
          style={{ borderColor: 'rgba(128,128,128,0.25)' }}
        >
          <div>
            <p className="font-display text-2xl">TRIPWIRE</p>
            <p className="mt-2 text-sm opacity-60">
              Share what your meters learn.
            </p>
          </div>
          <div className="text-sm opacity-60">
            <p>Team Saturn</p>
            <p>First Commit Hackathon</p>
            <p>Bharat Builds Tour Stop 01</p>
          </div>
          <div className="text-sm opacity-60">
            <p>Detection, Person 1</p>
            <p>Policy and abstraction, Person 2</p>
            <p>Orchestration and memory, Person 3</p>
          </div>
        </div>

        <p className="mt-10 text-xs opacity-40">
          Photography from Unsplash, free to use under the Unsplash License.
        </p>
      </div>
    </footer>
  )
}
