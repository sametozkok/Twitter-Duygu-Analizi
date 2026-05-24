import React, { useState } from 'react'
import { getChannelLogoUrl } from '../lib/channelLogos'

type ChannelAvatarProps = {
  channel: string
  fallbackText?: string
  className?: string
  size?: number
}

export function ChannelAvatar({ channel, fallbackText, className, size = 20 }: ChannelAvatarProps) {
  const [imageFailed, setImageFailed] = useState(false)
  const logo = getChannelLogoUrl(channel)
  const letter = (fallbackText ?? channel.replace(/^@/, '').slice(0, 1) ?? '?').toUpperCase()

  if (logo && !imageFailed) {
    return (
      <img
        className={className ? `channel-avatar-img ${className}` : 'channel-avatar-img'}
        src={logo}
        alt=""
        width={size}
        height={size}
        loading="lazy"
        onError={() => {
          setImageFailed(true)
        }}
      />
    )
  }

  return (
    <span
      className={className ? `channel-avatar-fallback ${className}` : 'channel-avatar-fallback'}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      {letter}
    </span>
  )
}

