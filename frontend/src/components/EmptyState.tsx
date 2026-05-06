import React from 'react'

type EmptyStateProps = {
  icon: string
  title: React.ReactNode
  body?: React.ReactNode
  children?: React.ReactNode
}

export function EmptyState({ icon, title, body, children }: EmptyStateProps) {
  return (
    <div className="feed-empty">
      <span className="icon icon-lg" aria-hidden="true">
        {icon}
      </span>
      <h3>{title}</h3>
      {body ? <p>{body}</p> : null}
      {children}
    </div>
  )
}

