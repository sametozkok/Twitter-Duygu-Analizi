import React from 'react'
import { SegmentedControl } from '../../components/SegmentedControl'
import { setAppLocale, type SupportedLocale } from '../../i18n'
import type { TFunction } from 'i18next'
import type { ThemeMode } from '../../theme/ThemeProvider'

type AppearanceSettingsProps = {
  t: TFunction
  themeMode: ThemeMode
  setThemeMode: (mode: ThemeMode) => void
  locale: SupportedLocale
}

export function AppearanceSettings({ t, themeMode, setThemeMode, locale }: AppearanceSettingsProps) {
  return (
    <section className="left-panel-section" id="appearance-settings">
      <div className="section-label">
        <span className="icon">palette</span>
        {t('settings:display')}
      </div>
      <div className="setting-field">
        <label style={{ marginBottom: 8 }}>{t('settings:theme')}</label>
        <SegmentedControl<ThemeMode>
          value={themeMode}
          onChange={setThemeMode}
          ariaLabel={t('settings:theme')}
          options={[
            { value: 'dark', label: t('settings:themeModes.dark') },
            { value: 'light', label: t('settings:themeModes.light') },
            { value: 'system', label: t('settings:themeModes.system') },
          ]}
        />
      </div>
      <div className="setting-field" style={{ marginTop: 12 }}>
        <label style={{ marginBottom: 8 }}>{t('settings:language')}</label>
        <SegmentedControl<SupportedLocale>
          value={locale}
          onChange={(next) => {
            void setAppLocale(next)
          }}
          ariaLabel={t('settings:language')}
          options={[
            { value: 'tr', label: t('settings:languageModes.tr') },
            { value: 'en', label: t('settings:languageModes.en') },
          ]}
        />
      </div>
    </section>
  )
}

