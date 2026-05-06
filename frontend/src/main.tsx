import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'
import './styles.css'
import './i18n'
import { ThemeProvider } from './theme/ThemeProvider'

// Prevent Material Symbols ligature text from flashing:
// show skeletons until the icon font is ready.
const ICON_FONT_FAMILY = 'Material Symbols Rounded'
const ICON_READY_CLASS = 'icons-ready'
const ICON_FALLBACK_CLASS = 'icons-fallback'

try {
  const rootEl = document.documentElement
  const fonts = (document as unknown as { fonts?: FontFaceSet }).fonts
  if (fonts?.load && fonts?.check) {
    const fontSpec = `400 24px "${ICON_FONT_FAMILY}"`

    const markReady = () => {
      rootEl.classList.add(ICON_READY_CLASS)
      rootEl.classList.remove(ICON_FALLBACK_CLASS)
    }

    const markFallback = () => {
      if (!rootEl.classList.contains(ICON_READY_CLASS)) {
        rootEl.classList.add(ICON_FALLBACK_CLASS)
      }
    }

    // kick off load
    // eslint-disable-next-line @typescript-eslint/no-floating-promises
    fonts.load(fontSpec).then(() => {
      if (fonts.check(fontSpec)) markReady()
    })

    // poll a little (more reliable across browsers)
    const startedAt = Date.now()
    const timer = window.setInterval(() => {
      if (fonts.check(fontSpec)) {
        window.clearInterval(timer)
        markReady()
        return
      }
      if (Date.now() - startedAt > 3000) {
        window.clearInterval(timer)
        markFallback()
      }
    }, 150)
  } else {
    rootEl.classList.add(ICON_READY_CLASS)
  }
} catch {
  document.documentElement.classList.add(ICON_READY_CLASS)
}

createRoot(document.getElementById('root') as HTMLElement).render(
  <ThemeProvider>
    <App />
  </ThemeProvider>,
)
