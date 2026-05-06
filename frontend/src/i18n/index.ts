import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import trCommon from './locales/tr/common.json'
import trDashboard from './locales/tr/dashboard.json'
import trSettings from './locales/tr/settings.json'
import trAnalysis from './locales/tr/analysis.json'

import enCommon from './locales/en/common.json'
import enDashboard from './locales/en/dashboard.json'
import enSettings from './locales/en/settings.json'
import enAnalysis from './locales/en/analysis.json'

export const DEFAULT_LOCALE = 'tr' as const
export const SUPPORTED_LOCALES = ['tr', 'en'] as const
export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number]

const LOCALE_STORAGE_KEY = 'locale'

export function normalizeLocale(input?: string | null): SupportedLocale {
  const raw = String(input ?? '').toLowerCase()
  if (raw.startsWith('tr')) return 'tr'
  if (raw.startsWith('en')) return 'en'
  return DEFAULT_LOCALE
}

export function getStoredLocale(): SupportedLocale {
  try {
    return normalizeLocale(window.localStorage.getItem(LOCALE_STORAGE_KEY))
  } catch {
    return DEFAULT_LOCALE
  }
}

export function storeLocale(locale: SupportedLocale) {
  try {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, locale)
  } catch {
    // ignore
  }
}

export function getIntlLocaleTag(locale: SupportedLocale): string {
  return locale === 'tr' ? 'tr-TR' : 'en-US'
}

export async function setAppLocale(locale: SupportedLocale) {
  const next = normalizeLocale(locale)
  storeLocale(next)
  await i18n.changeLanguage(next)
  document.documentElement.lang = next
}

void i18n
  .use(initReactI18next)
  .init({
    lng: getStoredLocale(),
    fallbackLng: 'en',
    supportedLngs: [...SUPPORTED_LOCALES],
    interpolation: { escapeValue: false },
    resources: {
      tr: {
        common: trCommon,
        dashboard: trDashboard,
        settings: trSettings,
        analysis: trAnalysis,
      },
      en: {
        common: enCommon,
        dashboard: enDashboard,
        settings: enSettings,
        analysis: enAnalysis,
      },
    },
  })
  .then(() => {
    document.documentElement.lang = normalizeLocale(i18n.language)
  })
  .catch(() => {
    document.documentElement.lang = DEFAULT_LOCALE
  })

export default i18n

