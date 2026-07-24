import { FloatingNav } from '@/components/FloatingNav'

interface HeroSectionProps {
  sectionIds: string[]
}

export const HeroSection = ({ sectionIds }: HeroSectionProps) => {
  return (
    <section id="landing" className="relative z-10 min-h-screen overflow-hidden px-4 pb-0 pt-20 text-white sm:px-6 md:px-10">
      <FloatingNav sectionIds={sectionIds} />

      <div className="relative mx-auto flex min-h-[calc(100vh-5rem)] max-w-[1400px] flex-col justify-between">
        <div className="flex items-start justify-between">
          <div className="px-1 py-2 text-xs uppercase tracking-[0.32em] text-white/88 sm:px-0">
            EEG Nexus
          </div>
        </div>

        <div className="relative flex flex-1 items-center justify-center pb-16 pt-6">
          <div className="grid w-full gap-10 lg:grid-cols-[0.8fr_1.2fr] lg:items-end">
            <div className="max-w-sm">
              <p className="text-[11px] uppercase tracking-[0.34em] text-white/42 sm:text-xs">motor imagery interface</p>
              <h1 className="mt-6 text-4xl font-medium tracking-[-0.06em] text-white sm:text-6xl">
                Real-time EEG
                <br />
                interface system
              </h1>
              <p className="mt-5 max-w-xs text-sm leading-7 text-white/58 sm:text-base">
                Single-page interface for decoding, application staging, and live monitoring.
              </p>
            </div>
            <div className="flex min-h-[52vh] items-end justify-end">
              <div className="w-full max-w-[760px] rounded-[40px] border border-white/12 bg-white p-6 sm:p-8">
                <div className="grid gap-4 sm:grid-cols-3">
                  {['signal', 'inference', 'mapping'].map((item) => (
                    <div key={item} className="h-28 rounded-[28px] bg-[#f4f4f4]" />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
