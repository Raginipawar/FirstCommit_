import { motion } from 'framer-motion'
import linesDawn from '../assets/lines-dawn.jpg'

const GROUNDING = [
  {
    k: 'Detection',
    v: 'Built on the SGCC dataset (Zheng et al., IEEE) and the EnsembleNTLDetect framework (Kulkarni et al., ICDMW 2021).',
  },
  {
    k: 'Shared memory',
    v: "Framed on Google Research's Titans. Test time memory, no retraining required.",
  },
  {
    k: 'Enforcement',
    v: 'Cedar, the same policy engine used for authorisation in production systems, running on every share request.',
  },
  {
    k: 'Stated plainly',
    v: 'This runs on a synthetic SGCC style site split, not live DISCOM data, and the pool is a local file rather than a cluster.',
  },
]

export function About() {
  return (
    <section id="about" className="relative bg-bg px-6 py-28 sm:px-12 sm:py-36">
      <div className="mx-auto max-w-6xl">
        <p className="eyebrow mb-6">About</p>

        <div className="grid gap-12 lg:grid-cols-[1.3fr_1fr] lg:gap-20">
          <motion.h2
            initial={{ opacity: 0, y: 22 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-10% 0px' }}
            transition={{ duration: 0.75, ease: [0.22, 1, 0.36, 1] }}
            className="font-display text-[2.2rem] leading-[1.06] sm:text-[3.4rem]"
          >
            A utility should not have to choose between protecting its
            customers and learning from its peers.
          </motion.h2>

          <motion.div
            initial={{ opacity: 0, y: 22 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-10% 0px' }}
            transition={{ duration: 0.75, delay: 0.12 }}
            className="space-y-5 text-[0.95rem] leading-relaxed text-muted lg:pt-3"
          >
            <p>
              TRIPWIRE was built by Team Saturn for the First Commit Hackathon,
              Bharat Builds Tour Stop 01.
            </p>
            <p>
              The whole system rests on one idea. A theft pattern is not
              personal data once you take the person out of it, and whether the
              person really came out is a question you can answer with a policy
              engine instead of a promise.
            </p>
          </motion.div>
        </div>

        <motion.figure
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-10% 0px' }}
          transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
          className="relative mt-20 overflow-hidden rounded-[1.75rem] border border-line sm:mt-28"
        >
          <img
            src={linesDawn}
            alt="Transmission lines silhouetted at first light"
            className="h-[42vh] w-full object-cover sm:h-[56vh]"
          />
          <div
            className="absolute inset-0"
            style={{
              background:
                'linear-gradient(180deg, rgba(6,6,10,0.1) 0%, rgba(6,6,10,0.72) 100%)',
            }}
          />
          <figcaption className="absolute inset-x-6 bottom-6 font-display text-xl leading-snug text-white sm:inset-x-10 sm:bottom-10 sm:text-3xl">
            <em>
              Every grid runs on the same quiet trust. This just makes it
              provable.
            </em>
          </figcaption>
        </motion.figure>

        <div className="mt-20 sm:mt-28">
          <p className="eyebrow mb-8">Grounded in</p>
          <div className="grid gap-5 sm:grid-cols-2 sm:gap-6">
            {GROUNDING.map((g) => (
              <div
                key={g.k}
                className="rounded-2xl border border-line p-7 sm:p-9"
                style={{ background: 'var(--grad-1)' }}
              >
                <p className="tag">{g.k}</p>
                <p className="mt-4 text-sm leading-relaxed text-muted">{g.v}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
