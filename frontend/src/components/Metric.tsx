import React from 'react'

type MetricProps = {
  icon: string
  value: React.ReactNode
  label?: string
}

export function Metric({ icon, value, label }: MetricProps) {
  return (
    <span className="tweet-metric" aria-label={label}>
      <span className="icon">{icon}</span>
      <strong>{value}</strong>
    </span>
  )
}

