import React from 'react'

export type SegmentedOption<T extends string> = {
  value: T
  label: string
  disabled?: boolean
}

type SegmentedControlProps<T extends string> = {
  value: T
  onChange: (value: T) => void
  options: Array<SegmentedOption<T>>
  ariaLabel: string
}

export function SegmentedControl<T extends string>({ value, onChange, options, ariaLabel }: SegmentedControlProps<T>) {
  return (
    <div className="segmented" role="radiogroup" aria-label={ariaLabel}>
      {options.map((opt) => {
        const checked = opt.value === value
        return (
          <button
            key={opt.value}
            type="button"
            className={`segmented-btn${checked ? ' is-active' : ''}${opt.disabled ? ' is-disabled' : ''}`}
            role="radio"
            aria-checked={checked}
            onClick={() => {
              if (!opt.disabled) onChange(opt.value)
            }}
            disabled={opt.disabled}
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}

