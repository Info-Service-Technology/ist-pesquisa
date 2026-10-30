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

const API_URL = import.meta.env.VITE_API_URL

export async function submitSurvey(payload: SurveyPayload) {
  const response = await fetch(`${API_URL}/api/surveys`, {
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
      `Não foi possível registrar a pesquisa. HTTP ${response.status}`
    )
  }

  return response.json()
}
