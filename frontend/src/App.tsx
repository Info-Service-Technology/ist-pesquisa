import { useEffect, useState } from 'react'
import './App.css'
import { submitSurvey } from './services/surveyApi'
import CookieBanner from './components/CookieBanner'
type Question = {
  title: string
  options: string[]
}

const questions: Question[] = [
  {
    title: 'Qual é o perfil da sua instituição?',
    options: [
      'Hospital privado',
      'Clínica médica',
      'Laboratório de análises ou diagnóstico',
      'Consultório médico',
      'Outro estabelecimento privado de saúde',
    ],
  },
  {
  title: 'Quais dificuldades operacionais ou assistenciais sua instituição enfrenta atualmente?',
  options: [
    'Acesso ao histórico clínico completo dos pacientes',
    'Informações clínicas dispersas em diferentes sistemas ou registros',
    'Agendamento e faltas de pacientes',
    'Produção de relatórios e indicadores',
    'Processos manuais e retrabalho',
    'Segurança e proteção de dados',
    'Outra dificuldade',
  ],
},
  {
    title: 'Como sua instituição registra e consulta as informações dos pacientes?',
    options: [
      'Prontuário eletrônico integrado',
      'Prontuário eletrônico sem integração externa',
      'Sistema próprio e planilhas',
      'Registros em papel',
      'Outro modelo',
    ],
  },
  {
    title: 'Sua instituição enfrenta dificuldades para consultar o histórico clínico completo dos pacientes devido a informações dispersas em diferentes sistemas ou registros?',
    options: [
      'Sim, frequentemente',
      'Sim, ocasionalmente',
      'Raramente',
      'Não enfrentamos essa dificuldade',
      'Não sei informar',
    ],
  },
  {
    title: 'Qual é a importância de resolver essa dificuldade?',
    options: [
      'Muito alta',
      'Alta',
      'Média',
      'Baixa',
      'Não é uma prioridade',
    ],
  },
  {
    title: 'Sua instituição consideraria contratar uma solução para centralizar ou integrar informações clínicas dispersas, facilitando o acesso ao histórico completo dos pacientes?',
    options: [
      'Sim, temos interesse',
      'Talvez, dependendo da solução',
      'Não temos interesse',
      'Precisamos entender melhor',
    ],
  },
  {
  title: 'Qual é o volume médio mensal de atendimentos realizados pela sua instituição? (Pode ser uma estimativa)',
    options: [
      'Até 100 atendimentos',
      '101 a 500 atendimentos',
      '501 a 2.000 atendimentos',
      '2.001 a 5.000 atendimentos',
      '5.001 a 10.000 atendimentos',
      'Mais de 10.000 atendimentos',
    ],
  },
  {
    title: 'Além do histórico clínico, existe outro problema que sua instituição gostaria de resolver com tecnologia?',
    options: [
      'Sim',
      'Não',
      'Gostaria de conversar para identificar oportunidades',
    ],
  },
]

const TOTAL_STEPS = 10

function formatPhone(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 11)

  if (!digits) return ''
  if (digits.length <= 2) return `(${digits}`
  if (digits.length <= 6) {
    return `(${digits.slice(0, 2)}) ${digits.slice(2)}`
  }
  if (digits.length <= 10) {
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`
  }

  return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`
}


function formatCnpj(value: string): string {
  const digits = value.replace(/\\D/g, '').slice(0, 14)

  return digits
    .replace(/^(\\d{2})(\\d)/, '$1.$2')
    .replace(/^(\\d{2})\\.(\\d{3})(\\d)/, '$1.$2.$3')
    .replace(/\\.(\\d{3})(\\d)/, '.$1/$2')
    .replace(/(\\d{4})(\\d)/, '$1-$2')
}

function validCnpj(value: string): boolean {
  const digits = value.replace(/\\D/g, '')

  if (!/^\\d{14}$/.test(digits) || /^(\\d)\\1+$/.test(digits)) {
    return false
  }

  const check = (base: string, weights: number[]): number => {
    const total = weights.reduce(
      (sum, weight, index) => sum + Number(base[index]) * weight,
      0
    )
    const remainder = total % 11
    return remainder < 2 ? 0 : 11 - remainder
  }

  const first = check(
    digits.slice(0, 12),
    [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
  )

  const second = check(
    digits.slice(0, 12) + first,
    [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
  )

  return digits.endsWith(`${first}${second}`)
}

function App() {
  const [respondent, setRespondent] = useState('')
  const [role, setRole] = useState('')
  const [phone, setPhone] = useState('')
  const [privacyAccepted, setPrivacyAccepted] = useState(false)
  const [warning, setWarning] = useState('')
  const [sending, setSending] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [website, setWebsite] = useState('')
  const [step, setStep] = useState(-1)
  const [answers, setAnswers] = useState<Record<number, string>>({})
  const [multipleAnswers, setMultipleAnswers] = useState<string[]>([])
  const [otherDetails, setOtherDetails] = useState<Record<number, string>>({})
  const [description, setDescription] = useState('')
  const [city, setCity] = useState('')
  const [institution, setInstitution] = useState('')
  const [cnpj, setCnpj] = useState('')
  const [email, setEmail] = useState('')
  const [consent, setConsent] = useState(false)

  const validEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())

  const validPhone = (() => {
    const digits = phone.replace(/\D/g, '')
    return digits.length >= 10 && digits.length <= 13
  })()

  const identityValid =
    institution.trim().length >= 2 &&
    validCnpj(cnpj) &&
    city.trim().length >= 2 &&
    respondent.trim().length >= 2 &&
    role.trim().length >= 2 &&
    validEmail &&
    validPhone &&
    privacyAccepted

  const isIntro = step === -1
  const isComplete = step === TOTAL_STEPS
  const isQuestion = step >= 0 && step < questions.length
  const selectedAnswer = answers[step] ?? ''

  const isMultipleQuestion = step === 1

  const isOtherSelected =
    isQuestion &&
    (isMultipleQuestion
      ? multipleAnswers.some(option =>
          /^(outro|outra)\b/i.test(option.trim())
        )
      : /^(outro|outra)\b/i.test(selectedAnswer.trim()))

  const otherDescriptionIsValid =
    !isOtherSelected || Boolean(otherDetails[step]?.trim())

  const canContinue =
    isQuestion
      ? (
          isMultipleQuestion
            ? multipleAnswers.length > 0
            : Boolean(selectedAnswer)
        ) && otherDescriptionIsValid
      : step === 8
        ? description.trim().length >= 10
        : step === 9
          ? identityValid
          : true

  function toggleDifficulty(option: string) {
    setMultipleAnswers(previous =>
      previous.includes(option)
        ? previous.filter(item => item !== option)
        : [...previous, option]
    )
  }

  async function next() {
    if (sending) return

    if (!canContinue) {
      setWarning(
        step === 9
          ? 'Preencha todos os campos obrigatórios, informe um e-mail e telefone válidos e confirme a ciência do aviso de privacidade.'
          : 'Esta resposta é obrigatória. Preencha antes de continuar.'
      )
      return
    }

    setWarning('')
    setSubmitError('')

    if (step !== 9) {
      setStep(current => current + 1)
      return
    }

    const surveyAnswers = questions.map((_, index) => {
      const selections =
        index === 1
          ? multipleAnswers
          : [answers[index]]

      const hasOther = selections.some(option =>
        /^(outro|outra)\b/i.test(option.trim())
      )

      return {
        question: index,
        selections,
        other_detail: hasOther
          ? otherDetails[index]?.trim() || null
          : null,
      }
    })

    surveyAnswers.push({
      question: 8,
      selections: [description.trim()],
      other_detail: null,
    })

    setSending(true)

    try {
      await submitSurvey({
        institution: institution.trim(),
        cnpj: cnpj.replace(/\D/g, ''),
        city: city.trim(),
        respondent: respondent.trim(),
        role: role.trim(),
        email: email.trim(),
        phone: phone.trim(),
        answers: surveyAnswers,
        privacy_accepted: privacyAccepted,
        commercial_contact: consent,
        website,
      })

      setStep(TOTAL_STEPS)
    } catch (error) {
      setSubmitError(
        error instanceof Error
          ? error.message
          : 'Não foi possível enviar a pesquisa.'
      )
    } finally {
      setSending(false)
    }
  }

  function back() {
    setStep(current => Math.max(-1, current - 1))
  }

  function restart() {
    setStep(-1)
    setAnswers({})
    setDescription('')
    setCity('')
    setInstitution('')
    setCnpj('')
    setEmail('')
    setConsent(false)
    setMultipleAnswers([])
    setOtherDetails({})
    setRespondent('')
    setRole('')
    setPhone('')
    setPrivacyAccepted(false)
    setWarning('')
    setSubmitError('')
    setSending(false)
    setWebsite('')
  }

  useEffect(() => {
    if (!warning) return

    const timer = window.setTimeout(() => {
      setWarning('')
    }, 10000)

    return () => window.clearTimeout(timer)
  }, [warning])

  return (
    <div className="page">
      <header className="header">
        <div className="brand">
          <div className="brand-icon">
            <img
              src="/brand/favicon.png"
              alt="Logo Info Service Technology"
            />
          </div>

          <div>
            <strong>Info Service Technology</strong>
            <span>Inteligência e inovação em saúde</span>
          </div>
        </div>

        <span className="header-label">PESQUISA DE MERCADO</span>
      </header>

      <main className="main">
        {isIntro ? (
          <section className="intro">
            <h1>Sua instituição está preparada para os desafios da saúde digital?</h1>
            <p className="lead">
              Queremos conhecer os desafios enfrentados por hospitais,
              clínicas, laboratórios e consultórios médicos para desenvolver
              soluções tecnológicas alinhadas às necessidades reais do setor.
            </p>

            <div className="intro-features">
              <span>◷ Aproximadamente 3 minutos</span>
              <span>✓ Participação voluntária</span>
              <span>◇ Sem dados clínicos de pacientes</span>
            </div>

            <button className="primary" onClick={() => setStep(0)}>
              Iniciar pesquisa <span>→</span>
            </button>
            
          </section>
        ) : isComplete ? (
          <section className="survey-card finish">
            <div className="success-icon">✓</div>
            <h1>Obrigado pela participação!</h1>
            <p>
              Sua participação foi registrada com sucesso.
              A Info Service Technology agradece sua contribuição
              para a pesquisa sobre os desafios da saúde digital.
            </p>
            <button className="primary" onClick={restart}>
              Voltar ao início
            </button>
          </section>
        ) : (
          <section className="survey-card">
            <div className="progress-meta">
              <span>ETAPA {step + 1} DE {TOTAL_STEPS}</span>
              <span>{Math.round(((step + 1) / TOTAL_STEPS) * 100)}%</span>
            </div>
            <div className="progress-track">
              <div
                className="progress-fill"
                style={{ width: `${((step + 1) / TOTAL_STEPS) * 100}%` }}
              />
            </div>

            {isQuestion ? (
              <>
                <div className="eyebrow">SOBRE SUA INSTITUIÇÃO</div>
                <h2>
                  {questions[step].title}{' '}
                  <span className="required">*</span>
                </h2>
                <p className="hint">
                  {isMultipleQuestion
                    ? 'Selecione todas as dificuldades que sua instituição enfrenta.'
                    : 'Selecione a alternativa que melhor representa sua realidade.'}
                </p>

                <div className="options">
                  {questions[step].options.map(option => {
                    const selected = isMultipleQuestion
                      ? multipleAnswers.includes(option)
                      : answers[step] === option

                    return (
                      <button
                        type="button"
                        key={option}
                        aria-pressed={selected}
                        className={`option ${selected ? 'selected' : ''}`}
                        onClick={() => {
                          if (isMultipleQuestion) {
                            toggleDifficulty(option)
                          } else {
                            setAnswers(previous => ({
                              ...previous,
                              [step]: option,
                            }))
                          }
                        }}
                      >
                        <span
                          className={
                            isMultipleQuestion
                              ? 'checkbox-dot'
                              : 'radio-dot'
                          }
                        />
                        <span>{option}</span>
                      </button>
                    )
                  })}
                </div>
                {isOtherSelected && (
                  <div className="other-field">
                    <label htmlFor={`other-${step}`}>
                      Por favor, especifique sua resposta <span className="required">*</span>
                    </label>

                    <textarea
                      id={`other-${step}`}
                      value={otherDetails[step] ?? ''}
                      onChange={event =>
                        setOtherDetails(previous => ({
                          ...previous,
                          [step]: event.target.value,
                        }))
                      }
                      placeholder="Descreva sua resposta..."
                      rows={4}
                      maxLength={1000}
                      required
                    />

                    <span className="field-hint">
                      Este campo é obrigatório quando a opção
                      "Outro" é selecionada.
                    </span>
                  </div>
                )}
              </>
            ) : step === 8 ? (
              <>
                <div className="eyebrow">OUTRAS OPORTUNIDADES</div>
                <h2>Existe algum desafio que você gostaria de compartilhar? <span className="required">*</span></h2>
                <p className="hint">
                  Conte brevemente qual problema sua instituição gostaria
                  de resolver com tecnologia. Caso não exista outro desafio, informe isso.
                </p>
                <textarea
                  value={description}
                  onChange={event => setDescription(event.target.value)}
                  placeholder="Descreva o desafio enfrentado pela instituição..."
                  rows={6}
                />
              </>
            ) : (
              <>
                <div className="eyebrow">FINALIZAÇÃO</div>
                <h2>Conte um pouco sobre sua instituição.</h2>
                <p className="hint">
                  Todos os campos de identificação são obrigatórios.
                  Os dados serão utilizados para validar a participação
                  institucional e analisar as respostas da pesquisa.
                </p>

                  <div className="fields">
                    {[
                      {
                        label: 'Nome da instituição',
                        value: institution,
                        setter: setInstitution,
                        placeholder: 'Razão social ou nome fantasia',
                      },
                      {
                        label: 'CNPJ da unidade',
                        value: cnpj,
                        setter: setCnpj,
                        placeholder: '00.000.000/0000-00',
                      },
                      {
                        label: 'Município',
                        value: city,
                        setter: setCity,
                        placeholder: 'Ex.: Petrópolis',
                      },
                      {
                        label: 'Nome do responsável',
                        value: respondent,
                        setter: setRespondent,
                        placeholder: 'Nome completo',
                      },
                      {
                        label: 'Cargo ou função',
                        value: role,
                        setter: setRole,
                        placeholder: 'Ex.: Diretor administrativo',
                      },
                      {
                        label: 'E-mail profissional',
                        value: email,
                        setter: setEmail,
                        placeholder: 'nome@instituicao.com.br',
                      },
                      {
                        label: 'Telefone ou WhatsApp',
                        value: phone,
                        setter: setPhone,
                        placeholder: '(24) 99999-9999',
                      },
                    ].map(field => (
                      <label key={field.label}>
                        <span>
                          {field.label} <span className="required">*</span>
                        </span>
                        <input
                          type={field.label === 'Telefone ou WhatsApp' ? 'tel' : field.label === 'E-mail profissional' ? 'email' : 'text'}
                          inputMode={field.label === 'Telefone ou WhatsApp' ? 'numeric' : undefined}
                          autoComplete={field.label === 'Telefone ou WhatsApp' ? 'tel-national' : undefined}
                          value={field.value}
                          onChange={event =>
                            field.setter(
                              field.label === 'Telefone ou WhatsApp'
                                ? formatPhone(event.target.value)
                                : field.label === 'CNPJ da unidade'
                                  ? formatCnpj(event.target.value)
                                  : event.target.value
                            )
                          }
                          placeholder={field.placeholder}
                          maxLength={field.label === 'Telefone ou WhatsApp' ? 15 : field.label === 'CNPJ da unidade' ? 18 : undefined}
                          required
                        />
                      </label>
                    ))}

                    <div className="privacy-notice">
                      <strong>Cookies e localização</strong>
                      <p>
                        Utilizamos apenas os recursos técnicos necessários para
                        o funcionamento desta pesquisa. Caso sejam ativados
                        serviços de proteção contra abuso que utilizem cookies,
                        este aviso será atualizado antes da publicação.
                        Esta pesquisa não solicita sua localização pelo navegador.
                      </p>
                      <a
                        href="https://infoservicetechnology.com.br/privacidade"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Leia a Política de Privacidade e o canal do DPO
                      </a>
                    </div>

                    <label className="consent">
                      <input
                        type="checkbox"
                        checked={privacyAccepted}
                        onChange={event => setPrivacyAccepted(event.target.checked)}
                      />
                      <span>
                        Li o aviso de privacidade e estou ciente do tratamento
                        dos dados fornecidos para realização desta pesquisa.
                        <span className="required"> *</span>
                      </span>
                    </label>

                    <label className="consent">
                      <input
                        type="checkbox"
                        checked={consent}
                        onChange={event => setConsent(event.target.checked)}
                      />
                      <span>
                        Autorizo a IST a entrar em contato para apresentar
                        possíveis soluções tecnológicas. (Opcional)
                      </span>
                    </label>

                    <input
                      className="honeypot"
                      tabIndex={-1}
                      autoComplete="off"
                      aria-hidden="true"
                      value={website}
                      onChange={event => setWebsite(event.target.value)}
                    />
                  </div>
              </>
            )}

            {warning && (
              <div className="validation-warning" role="alert">
                <span>⚠ {warning}</span>
                <button
                  type="button"
                  onClick={() => setWarning('')}
                  aria-label="Fechar aviso"
                >
                  ×
                </button>
              </div>
            )}
            {submitError && (
              <div className="validation-warning" role="alert">
                <span>⚠ {submitError}</span>
                <button
                  type="button"
                  onClick={() => setSubmitError('')}
                  aria-label="Fechar erro"
                >
                  ×
                </button>
              </div>
            )}

            <div className="navigation">
              <button
                type="button"
                className="secondary"
                onClick={back}
                disabled={sending}
              >
                ← Voltar
              </button>

              <button
                type="button"
                className="primary"
                onClick={next}
                disabled={sending}
              >
                {sending
                  ? 'Enviando...'
                  : step === 9
                    ? 'Finalizar pesquisa'
                    : 'Continuar →'}
              </button>
            </div>
          </section>
        )}
      </main>

      <footer className="footer">
        <span>© 2026 Info Service Technology</span>
        <span>Pesquisa exploratória • Saúde privada</span>
      </footer>
      <CookieBanner />
    </div>

  )
}

export default App
