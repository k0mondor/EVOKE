import { ApplicationPlaceholderSection } from '@/components/ApplicationPlaceholderSection'
import { DashboardSection } from '@/components/DashboardSection'
import { HeroSection } from '@/components/HeroSection'
import { RoomFocusSection } from '@/components/RoomFocusSection'
import { useRealtimeStream } from '@/hooks/useRealtimeStream'

const SECTION_IDS = ['landing', 'room-focus', 'applications', 'dashboard']

export default function Home() {
  useRealtimeStream()

  return (
    <main className="relative z-10 min-h-[300vh] bg-black text-white">
      <HeroSection sectionIds={SECTION_IDS} />
      <div className="relative">
        <RoomFocusSection />
        <ApplicationPlaceholderSection />
        <DashboardSection />
      </div>
    </main>
  )
}
