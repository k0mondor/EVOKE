import { useEffect, useRef } from 'react'

import { usePageMotionStore } from '@/stores/pageMotionStore'

const SCENES = [
  {
    title: 'Left Hand Command',
    description: 'Motor imagery of the left hand triggers the first scenario layer and its control response.',
    label: 'left hand',
  },
  {
    title: 'Right Hand Command',
    description: 'Right-hand imagery shifts the scene to a second state with its own visual response.',
    label: 'right hand',
  },
  {
    title: 'Feet Command',
    description: 'Feet imagery drives the third scenario, completing the three-class interaction set.',
    label: 'feet',
  },
]

export const ApplicationPlaceholderSection = () => {
  const sectionRef = useRef<HTMLElement | null>(null)
  const stripRef = useRef<HTMLDivElement | null>(null)
  const currentProgressRef = useRef(0)
  const targetProgressRef = useRef(0)
  const setApplicationProgress = usePageMotionStore((state) => state.setApplicationProgress)

  useEffect(() => {
    const updateTarget = () => {
      const section = sectionRef.current
      if (!section) {
        return
      }

      const rect = section.getBoundingClientRect()
      const scrollY = Math.max(0, -rect.top)
      const maxScroll = Math.max(section.offsetHeight - window.innerHeight, 1)
      targetProgressRef.current = Math.max(0, Math.min(1, scrollY / maxScroll))
    }

    let frameId = 0

    const animate = () => {
      currentProgressRef.current += (targetProgressRef.current - currentProgressRef.current) * 0.08
      setApplicationProgress(currentProgressRef.current)
      frameId = window.requestAnimationFrame(animate)
    }

    updateTarget()
    frameId = window.requestAnimationFrame(animate)
    window.addEventListener('scroll', updateTarget, { passive: true })
    window.addEventListener('resize', updateTarget)

    return () => {
      window.cancelAnimationFrame(frameId)
      window.removeEventListener('scroll', updateTarget)
      window.removeEventListener('resize', updateTarget)
    }
  }, [setApplicationProgress])

  const progress = usePageMotionStore((state) => state.applicationProgress)

  return (
    <section ref={sectionRef} id="applications" className="relative h-[300vh]">
      <div className="sticky top-0 h-screen w-screen overflow-hidden">
        <div
          ref={stripRef}
          className="flex h-full w-max gap-12 px-[10vw] transition-transform duration-300 ease-out will-change-transform"
          style={{ transform: `translate3d(-${progress * Math.max((stripRef.current?.scrollWidth ?? window.innerWidth) - window.innerWidth, 0)}px, 0, 0)` }}
        >
          {SCENES.map((scene, index) => (
            <article key={scene.label} className="flex h-screen w-[88vw] min-w-[88vw] items-end py-16">
              <div className="grid h-full w-full grid-rows-[1fr_auto] gap-8">
                <div />
                <div className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-end">
                  <div className="max-w-xl">
                    <p className="text-xs uppercase tracking-[0.26em] text-black/32">application scenarios</p>
                    <h2 className="mt-4 text-3xl font-medium tracking-[-0.04em] text-[#14161b] sm:text-4xl">{scene.title}</h2>
                    <p className="mt-5 text-sm leading-7 text-black/55 sm:text-base">{scene.description}</p>
                  </div>

                  <div className="rounded-[32px] bg-white p-6 shadow-[0_14px_50px_rgba(17,17,17,0.06)] sm:p-8">
                    <div className="mb-12 h-[260px] rounded-[28px] bg-[#f3f3f3]" />
                    <p className="text-xs uppercase tracking-[0.24em] text-black/35">scene {index + 1}</p>
                    <p className="mt-3 text-sm text-black/72">{scene.label}</p>
                  </div>
                </div>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}
