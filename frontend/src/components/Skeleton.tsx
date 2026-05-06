import type { CSSProperties } from 'react'

type SkeletonProps = {
  className?: string
  style?: CSSProperties
  width?: number | string
  height?: number | string
  radius?: number | string
}

export function Skeleton({ className, style, width, height, radius }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={['skeleton', 'loading-shimmer', className].filter(Boolean).join(' ')}
      style={{
        width,
        height,
        borderRadius: radius,
        ...style,
      }}
    />
  )
}

type SkeletonTextProps = {
  className?: string
  style?: CSSProperties
  lines?: number
}

export function SkeletonText({ className, style, lines = 3 }: SkeletonTextProps) {
  const safeLines = Math.max(1, Math.min(8, Math.floor(lines)))
  return (
    <div className={['skeleton-text', className].filter(Boolean).join(' ')} style={style} aria-hidden="true">
      {Array.from({ length: safeLines }).map((_, i) => (
        <div key={i} className="skeleton-line">
          <Skeleton height={12} radius={999} className={i === safeLines - 1 ? 'skeleton-line-short' : ''} />
        </div>
      ))}
    </div>
  )
}

