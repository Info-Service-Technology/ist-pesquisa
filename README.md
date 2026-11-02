# IST-Pesquisa

Plataforma de pesquisas institucionais da Info Service Technology (IST).

## Objetivo

Coletar informações estruturadas para identificar necessidades,
dificuldades operacionais e oportunidades de melhoria em instituições
de saúde.

A pesquisa institucional busca compreender desafios relacionados a
fragmentação de informações clínicas, continuidade assistencial,
organização dos atendimentos e integração de dados.

Os resultados apoiarão a validação de mercado e a evolução das
soluções do ecossistema HDI.

## Arquitetura

| Componente | Tecnologia |
| --- | --- |
| Frontend | React, TypeScript e Vite |
| Backend | Python e FastAPI |
| Persistência atual | SQLite e SQLAlchemy |
| Verificação de e-mail | Amazon SES |
| Hospedagem do frontend | Cloudflare Pages |
| Hospedagem do backend | AWS (pendente) |

## Estrutura do repositório

- frontend/: interface e integração com a API.
- backend/: endpoints, validações e persistência.
- backend/test_*.py: testes automatizados.
- .github/workflows/: pipelines de CI/CD.

## Estratégia de versionamento

- main: branch de produção.
- feature/*: desenvolvimento de funcionalidades.
- fix/*: correções.

As alterações devem ser integradas à main por Pull Request,
com descrição técnica, testes e análise de impacto.

## Requisitos

- Python 3 com ambiente virtual.
- Node.js e npm compatíveis com o projeto.
- Acesso ao Amazon SES para testes reais de envio de e-mail.

## Instalação do frontend

A partir da raiz do repositório:

1. Acesse o diretório frontend.
2. Execute npm ci para instalar as dependências.
3. Configure VITE_API_URL com o endereço da API.
4. Execute npm run dev.

Para validar a aplicação:

- npm run lint
- npm run build

## Instalação do backend

A partir da raiz do repositório:

1. Acesse o diretório backend.
2. Crie um ambiente virtual com python3 -m venv .venv.
3. Ative o ambiente com source .venv/bin/activate.
4. Instale as dependências com pip install -r requirements.txt.
5. Configure as variáveis de ambiente necessárias.
6. Inicie a API com uvicorn main:app --reload --host 127.0.0.1 --port 8001.

O endpoint GET /health permite verificar a disponibilidade da API.

IMPORTANTE: antes de iniciar o backend, configure
IST_PESQUISA_DATABASE_PATH para um banco isolado de desenvolvimento.

Sem essa variável, a aplicação utiliza backend/pesquisa.db.
Esse banco não deve ser utilizado em testes automatizados.

## Variáveis de ambiente

Frontend:

- VITE_API_URL: endereço-base HTTPS ou HTTP da API.

Backend:

- IST_PESQUISA_DATABASE_PATH: caminho do banco SQLite.
- EMAIL_PROVIDER: provedor de e-mail; ses habilita Amazon SES.
- AWS_REGION: região AWS do Amazon SES.
- SES_SENDER_EMAIL: remetente verificado no Amazon SES.
- EMAIL_VERIFICATION_SECRET: segredo com pelo menos 32 caracteres.

Nunca registre credenciais, senhas ou segredos no repositório.
Em produção, utilize um gerenciador de segredos apropriado.

## Fluxo da pesquisa institucional

1. O participante informa os dados da instituição e responde ao questionário.
2. O backend valida os dados, incluindo CNPJ e e-mail profissional.
3. O sistema solicita o envio de um código de verificação por e-mail.
4. O participante informa o código recebido.
5. O backend confirma a verificação e registra a resposta.

O envio direto de respostas sem verificação está bloqueado.

## Testes automatizados

O backend possui testes para solicitação e confirmação de códigos,
controle de concorrência, limitação de requisições e falhas de envio.

Os testes devem utilizar bancos temporários e isolados.
Nunca execute testes contra o banco histórico de respostas.

A integração contínua será configurada no GitHub Actions.

## Publicação

### Frontend

Plataforma: Cloudflare Pages.

Projeto: pesquisa-institucional.

Endereço atual:
https://pesquisa-institucional.pages.dev

A branch de produção deverá ser main após a integração
das alterações por Pull Request.

### Backend

A implantação da API em produção ainda está pendente.

Antes de disponibilizar a pesquisa para instituições reais:

- Publicar a API em HTTPS.
- Configurar persistência de dados.
- Autorizar os domínios necessários no CORS.
- Configurar o envio de e-mails pelo Amazon SES.
- Validar o fluxo completo de envio e confirmação.
- Configurar monitoramento e backups.

## Segurança e privacidade

O projeto coleta dados institucionais, dados de contato
e respostas de pesquisa.

O tratamento dessas informações deve observar a LGPD,
incluindo finalidade, transparência, minimização e segurança.

Credenciais não devem ser versionadas.
Os dados históricos devem ser preservados.

## Responsável

Info Service Technology (IST).

## Execução dos testes do backend

Instale as dependências de desenvolvimento:

    python -m pip install -r backend/requirements-dev.txt

Execute os seis testes automatizados:

    python scripts/test_backend.py

O executor inicia cada teste em um processo independente,
com banco SQLite temporário e provedor de e-mail desabilitado.

## Integração contínua

O workflow .github/workflows/ci.yml executa automaticamente:

- Backend: instalação de dependências e testes isolados.
- Frontend: npm ci, npm run lint e npm run build.

A CI é acionada em Pull Requests direcionados à main
e em atualizações da própria main.

O workflow não realiza implantação em produção.
