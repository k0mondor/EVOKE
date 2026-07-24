import { useMemo } from 'react'

import { cn } from '@/lib/utils'

interface FloatingNavProps {
  sectionIds: string[]
}

export const FloatingNav = ({ sectionIds }: FloatingNavProps) => {
  const offsets = useMemo(
    () =>
      sectionIds.map((id, index) => ({
        id,
        width: index === 0 ? 'w-10 sm:w-14' : index === 1 ? 'w-8 sm:w-12' : 'w-12 sm:w-16',
      })),
    [sectionIds],
  )

  const scrollToSection = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <nav className="absolute left-1/2 top-5 z-30 w-max max-w-[92vw] -translate-x-1/2 sm:top-8">
      <div className="flex items-center gap-2 rounded-full bg-[rgba(16,18,22,0.74)] p-2 shadow-[0_18px_80px_rgba(0,0,0,0.42)] backdrop-blur-xl">
        {offsets.map((item, index) => (
          <button
            key={item.id}
            type="button"
            aria-label={`jump to section ${index + 1}`}
            className={cn(
              'h-9 rounded-full bg-white/[0.05] transition duration-300 hover:bg-white/[0.09] sm:h-11',
              item.width,
            )}
            onClick={() => scrollToSection(item.id)}
          />
        ))}
      </div>
    </nav>
  )
}
