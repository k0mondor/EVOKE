import { EegWaveformPanel } from '@/components/EegWaveformPanel'
import { ProbabilityBarsPanel } from '@/components/ProbabilityBarsPanel'
import { TopomapPanel } from '@/components/TopomapPanel'

const TOPOMAP_CONFIGS = [
  {
    id: 'instant' as const,
    eyebrow: 'topomap a',
    title: 'Instant activity map',
    description: 'The first topomap focuses on the current spatial activity state. Hover to rotate the view with the mouse wheel.',
  },
  {
    id: 'temporal_mean' as const,
    eyebrow: 'topomap b',
    title: 'Temporal mean map',
    description: 'This paired view keeps the same language but evolves more smoothly to present a short-window average state.',
  },
]

export const DashboardSection = () => {
  return (
    <section
      id="dashboard"
      className="relative px-4 pb-20 pt-10 text-[#121318] sm:px-6 md:px-10 md:pb-28 md:pt-16"
    >
      <div className="mx-auto max-w-[1400px]">
        <div className="mb-12 max-w-2xl">
          <p className="text-xs uppercase tracking-[0.26em] text-black/35">monitoring dashboard</p>
          <h2 className="mt-4 text-3xl font-medium tracking-[-0.04em] text-[#111216] sm:text-4xl">Live EEG monitoring and three-class feedback</h2>
          <p className="mt-4 max-w-xl text-sm leading-7 text-black/55 sm:text-base">
            The monitoring layer follows a 2x2 rhythm: waveform and class probability on the first row, instant and temporal-mean topomaps on the second row.
          </p>
        </div>

        <div className="grid gap-5 lg:grid-cols-2">
          <EegWaveformPanel />
          <ProbabilityBarsPanel />
          {TOPOMAP_CONFIGS.map((config) => (
            <TopomapPanel key={config.id} {...config} />
          ))}
        </div>
      </div>
    </section>
  )
}
