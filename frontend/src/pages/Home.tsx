import { ApplicationPlaceholderSection } from '@/components/ApplicationPlaceholderSection'
import { DashboardSection } from '@/components/DashboardSection'
import { GlobalBackground } from '@/components/GlobalBackground'
import { HeroSection } from '@/components/HeroSection'
import { useRealtimeDemo } from '@/hooks/useRealtimeDemo'
import { useScrollMotion } from '@/hooks/useScrollMotion'

const SECTION_IDS = ['landing', 'applications', 'dashboard']

export default function Home() {
  useRealtimeDemo()
  useScrollMotion()

  return (
    <main className="relative z-10 min-h-[300vh] bg-transparent text-white">
      <GlobalBackground />
      <HeroSection sectionIds={SECTION_IDS} />
      <div className="relative">
        <ApplicationPlaceholderSection />
        <DashboardSection />
      </div>
    </main>
  )
}
