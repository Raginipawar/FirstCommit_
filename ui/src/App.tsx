import { useSmoothScroll } from './lib/useSmoothScroll'
import { Preloader } from './components/Preloader'
import { Nav } from './components/Nav'
import { SideRail } from './components/SideRail'
import { Hero } from './components/Hero'
import { Story } from './components/Story'
import { Problem } from './components/Problem'
import { HowItWorks } from './components/HowItWorks'
import { Convergence } from './components/Convergence'
import { LiveRun } from './components/LiveRun'
import { About } from './components/About'
import { Footer } from './components/Footer'

export default function App() {
  useSmoothScroll()

  return (
    <div id="top">
      <Preloader />
      <div className="grain" />
      <Nav />
      <SideRail />
      <main>
        <Hero />
        <Problem />
        <HowItWorks />
        <Convergence />
        <LiveRun />
        <Story />
        <About />
      </main>
      <Footer />
    </div>
  )
}
