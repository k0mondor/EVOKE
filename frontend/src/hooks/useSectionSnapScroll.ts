import { useEffect } from 'react'

interface SnapContext {
  currentSection: HTMLElement
  direction: -1 | 1
}

interface UseSectionSnapScrollOptions {
  sectionSelector?: string
  onBeforeSnap?: (context: SnapContext) => boolean
}

export const useSectionSnapScroll = ({
  sectionSelector = '[data-scroll-section]',
  onBeforeSnap,
}: UseSectionSnapScrollOptions = {}) => {
  useEffect(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
    const finePointer = window.matchMedia('(pointer: fine)')

    if (reduceMotion.matches || !finePointer.matches) {
      return
    }

    let locked = false
    let accumulatedDelta = 0
    let lastWheelTime = 0
    let unlockTimer: number | undefined

    const handleWheel = (event: WheelEvent) => {
      if (event.ctrlKey || Math.abs(event.deltaX) > Math.abs(event.deltaY)) {
        return
      }

      const target = event.target
      if (
        target instanceof Element &&
        target.closest('input, textarea, select, button, a, [contenteditable="true"]')
      ) {
        return
      }

      const sections = Array.from(document.querySelectorAll<HTMLElement>(sectionSelector))
      if (sections.length < 2) {
        return
      }

      const viewportCenter = window.scrollY + window.innerHeight * 0.5
      const currentIndex = sections.reduce((closestIndex, section, index) => {
        const sectionCenter = section.offsetTop + section.offsetHeight * 0.5
        const currentDistance = Math.abs(sectionCenter - viewportCenter)
        const closestDistance =
          Math.abs(sections[closestIndex].offsetTop + sections[closestIndex].offsetHeight * 0.5 - viewportCenter)

        return currentDistance < closestDistance ? index : closestIndex
      }, 0)

      const direction = Math.sign(event.deltaY) as -1 | 0 | 1
      if (direction === 0) {
        return
      }

      const currentSection = sections[currentIndex]
      const targetIndex = currentIndex + direction

      if (targetIndex < 0 || targetIndex >= sections.length) {
        return
      }

      event.preventDefault()

      if (locked) {
        return
      }

      const now = performance.now()
      if (now - lastWheelTime > 180) {
        accumulatedDelta = 0
      }

      lastWheelTime = now
      accumulatedDelta += event.deltaY

      if (Math.abs(accumulatedDelta) < 16) {
        return
      }

      accumulatedDelta = 0

      if (onBeforeSnap?.({ currentSection, direction })) {
        locked = true
        unlockTimer = window.setTimeout(() => {
          locked = false
        }, 520)
        return
      }

      locked = true
      sections[targetIndex].scrollIntoView({ behavior: 'smooth', block: 'start' })

      unlockTimer = window.setTimeout(() => {
        locked = false
      }, 920)
    }

    window.addEventListener('wheel', handleWheel, { passive: false })

    return () => {
      window.removeEventListener('wheel', handleWheel)
      if (unlockTimer !== undefined) {
        window.clearTimeout(unlockTimer)
      }
    }
  }, [onBeforeSnap, sectionSelector])
}
