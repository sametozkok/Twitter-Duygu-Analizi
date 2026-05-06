import React from 'react'
import type { TFunction } from 'i18next'

type OnboardingCardProps = {
  t: TFunction
  onDismiss: () => void
  onOpenSettings: () => void
  onFetchTweets: () => void
  isFetching: boolean
}

export function OnboardingCard({ t, onDismiss, onOpenSettings, onFetchTweets, isFetching }: OnboardingCardProps) {
  return (
    <div className="onboarding-card" role="region" aria-label={t('dashboard:onboarding.title')}>
      <div className="onboarding-header">
        <div className="onboarding-title">
          <span className="icon">bolt</span>
          <strong>{t('dashboard:onboarding.title')}</strong>
        </div>
        <button className="onboarding-dismiss" type="button" onClick={onDismiss}>
          {t('dashboard:onboarding.dismiss')}
        </button>
      </div>
      <ol className="onboarding-steps">
        <li>{t('dashboard:onboarding.step1')}</li>
        <li>{t('dashboard:onboarding.step2')}</li>
        <li>{t('dashboard:onboarding.step3')}</li>
      </ol>
      <div className="onboarding-actions">
        <button type="button" className="btn-secondary" onClick={onOpenSettings}>
          <span className="icon">settings</span>
          {t('dashboard:onboarding.openSettings')}
        </button>
        <button type="button" className="fetch-btn" onClick={onFetchTweets} disabled={isFetching}>
          <span className="icon">download</span>
          {t('dashboard:onboarding.fetchTweets')}
        </button>
      </div>
    </div>
  )
}

