import type { ReactNode } from 'react'

import { useRevealOnce } from '@/hooks/useRevealOnce'
import { cn } from '@/lib/utils'

interface SectionCardProps {
  eyebrow?: string
  title?: string
  description?: string
  className?: string
  children: ReactNode
}

export const SectionCard = ({
  eyebrow,
  title,
  description,
  className,
  children,
}: SectionCardProps) => {
  const { ref, isVisible } = useRevealOnce<HTMLElement>()

  return (
    <section
      ref={ref}
      data-reveal={isVisible ? 'visible' : 'pending'}
      className={cn(
        'scroll-float-card relative overflow-hidden rounded-[32px] bg-white p-5 shadow-[0_28px_90px_rgba(0,0,0,0.08)] sm:p-6',
        className,
      )}
    >
      {(eyebrow || title || description) && (
        <header className="mb-5 flex items-start justify-between gap-4">
          <div className="space-y-2">
            {eyebrow ? (
              <p className="scroll-float-item scroll-delay-1 text-[11px] uppercase tracking-[0.28em] text-black/35">{eyebrow}</p>
            ) : null}
            {title ? <h3 className="scroll-float-item scroll-delay-2 text-base font-medium text-[#121318] sm:text-lg">{title}</h3> : null}
            {description ? (
              <p className="scroll-float-item scroll-delay-3 max-w-xl text-sm leading-6 text-black/55">{description}</p>
            ) : null}
          </div>
        </header>
      )}
      <div className="scroll-float-item scroll-delay-4">{children}</div>
    </section>
  )
}
