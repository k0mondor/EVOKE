import type { ReactNode } from 'react'

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
  return (
    <section
      className={cn(
        'relative overflow-hidden rounded-[32px] bg-white p-5 shadow-[0_28px_90px_rgba(0,0,0,0.08)] sm:p-6',
        className,
      )}
    >
      {(eyebrow || title || description) && (
        <header className="mb-5 flex items-start justify-between gap-4">
          <div className="space-y-2">
            {eyebrow ? (
              <p className="text-[11px] uppercase tracking-[0.28em] text-black/35">{eyebrow}</p>
            ) : null}
            {title ? <h3 className="text-base font-medium text-[#121318] sm:text-lg">{title}</h3> : null}
            {description ? (
              <p className="max-w-xl text-sm leading-6 text-black/55">{description}</p>
            ) : null}
          </div>
        </header>
      )}
      {children}
    </section>
  )
}
