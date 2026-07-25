import { useRef } from 'react'

import { FinalBenefitsSection } from '@/components/FinalBenefitsSection'
import { HeroSection } from '@/components/HeroSection'
import { RoomFocusSection, type RoomFocusSectionHandle } from '@/components/RoomFocusSection'
import { useSectionSnapScroll } from '@/hooks/useSectionSnapScroll'

export default function Home() {
  const roomFocusRef = useRef<RoomFocusSectionHandle | null>(null)

  useSectionSnapScroll({
    sectionSelector: '[data-scroll-section]',
    onBeforeSnap: ({ currentSection, direction }) => {
      if (direction > 0 && currentSection.id === 'room-focus' && roomFocusRef.current?.isFocused()) {
        roomFocusRef.current.exitFocusMode()
        return true
      }

      return false
    },
  })

  return (
    <main className="page-shell relative z-10 min-h-screen bg-black text-white">
      <HeroSection />
      <RoomFocusSection ref={roomFocusRef} />
      <FinalBenefitsSection />
    </main>
  )
}
