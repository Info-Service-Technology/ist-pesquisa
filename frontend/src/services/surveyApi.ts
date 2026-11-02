export type SurveyAnswer = {
  question: number
  selections: string[]
  other_detail: string | null
}

export type SurveyPayload = {
  institution: string
  cnpj: string
  city: string
  respondent: string
  role: string
  email: string
  phone: string
  answers: SurveyAnswer[]
  privacy_accepted: boolean
  commercial_contact: boolean
  website: string
}

const API_URL = (import.meta.env.VITE_API_URL ?? '').trim().replace(/\/$/, '')

function getApiUrl(): string {
  if (!API_URL || !/^https?:\/\//i.test(API_URL)) {
    throw new Error(
      'A pesquisa está temporariamente indisponível. Tente novamente mais tarde.'
    )
  }

  return API_URL
}

export async function submitSurvey(payload: SurveyPayload) {
  const response = await fetch(`${getApiUrl()}/api/surveys`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    if (response.status === 409) {
      throw new Error(
        'Esta unidade de saúde já respondeu à pesquisa.'
      )
    }

    throw new Error(
      'Não foi possível registrar sua resposta. Tente novamente mais tarde.'
    )
  }

  return response.json()
}


export type VerificationRequestResponse = {
  verification_id: string
  expires_in_seconds: number
}

export type VerificationConfirmationResponse = {
  received: boolean
  id: string
}

export async function requestSurveyVerification(
  payload: SurveyPayload
): Promise<VerificationRequestResponse> {
  const response = await fetch(
    `${getApiUrl()}/api/surveys/verification/request`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    }
  )

  if (!response.ok) {
    if (response.status === 409) {
      throw new Error(
        'Esta unidade de saúde já respondeu à pesquisa.'
      )
    }

    if (response.status === 503) {
      throw new Error(
        'O serviço de verificação por e-mail está temporariamente indisponível.'
      )
    }

    throw new Error(
      'Não foi possível enviar o código de verificação. Tente novamente mais tarde.'
    )
  }

  return response.json()
}

export async function confirmSurveyVerification(
  verificationId: string,
  code: string
): Promise<VerificationConfirmationResponse> {
  const response = await fetch(
    `${getApiUrl()}/api/surveys/verification/confirm`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        verification_id: verificationId,
        code,
      }),
    }
  )

  if (!response.ok) {
    if (response.status === 400) {
      throw new Error('Código de verificação incorreto.')
    }

    if (response.status === 410) {
      throw new Error(
        'Código expirado ou já utilizado. Solicite uma nova verificação.'
      )
    }

    if (response.status === 429) {
      throw new Error(
        'Limite de tentativas atingido. Solicite um novo código.'
      )
    }

    if (response.status === 409) {
      throw new Error(
        'Esta pesquisa já foi registrada ou a verificação não está mais disponível.'
      )
    }

    throw new Error(
      'Não foi possível confirmar o código. Tente novamente mais tarde.'
    )
  }

  return response.json()
}
