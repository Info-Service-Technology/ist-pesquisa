import { useState } from 'react'
import './CookieBanner.css'

type CookieChoice = 'accepted' | 'rejected'

const STORAGE_KEY = 'ist-pesquisa-cookie-consent-v1'

function getSavedChoice(): CookieChoice | null {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    return saved === 'accepted' || saved === 'rejected'
      ? saved
      : null
  } catch {
    return null
  }
}

export default function CookieBanner() {
  const [choice, setChoice] = useState<CookieChoice | null>(getSavedChoice)

  function saveChoice(value: CookieChoice) {
    try {
      localStorage.setItem(STORAGE_KEY, value)
    } catch {
      // O banner permanece funcional mesmo com armazenamento bloqueado.
    }

    setChoice(value)
  }

  if (choice !== null) return null

  return (
    <section
      className="cookie-banner"
      aria-label="Preferências de cookies"
    >
      <div className="cookie-banner__content">
        <div className="cookie-banner__text">
          <h2>Cookies e localização</h2>

          <p>
            Utilizamos armazenamento local necessário para lembrar sua escolha.
            Serviços opcionais, quando disponibilizados, somente serão ativados
            mediante sua autorização. Esta pesquisa não solicita localização
            pelo navegador.
          </p>

          <a
            href="https://infoservicetechnology.com.br/privacidade"
            target="_blank"
            rel="noopener noreferrer"
          >
            Leia a Política de Privacidade e o canal do DPO.
          </a>
        </div>

        <div className="cookie-banner__actions">
          <button
            type="button"
            className="cookie-banner__reject"
            onClick={() => saveChoice('rejected')}
          >
            Recusar opcionais
          </button>

          <button
            type="button"
            className="cookie-banner__accept"
            onClick={() => saveChoice('accepted')}
          >
            Aceitar cookies opcionais
          </button>
        </div>
      </div>
    </section>
  )
}
