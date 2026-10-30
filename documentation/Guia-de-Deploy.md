# Guia de Deploy — Art Archive AI (Vercel + Render)

Passo a passo da Fase 7 (doc 99). A arquitetura alvo e os limites do plano grátis estão em doc 04 §8.2.

```
Visitante ──HTTPS──▶ Vercel (Next.js) ──HTTPS──▶ Render: api (FastAPI) ──URL interna──▶ Render: Postgres
                                                        │
                                                        ├──▶ Harvard Art Museums API
                                                        └──▶ Azure OpenAI
```

**Tempo estimado:** 3 a 4 horas, sem contar a espera pela nova chave da Harvard.
**Custo inicial:** US$ 0 (Render Free + Vercel Hobby). A geração de IA sai do crédito Azure.

**Regra de ouro:** chaves e senhas só entram nos painéis do Render e da Vercel. Nunca em arquivo versionado, print, chat ou commit.

Marque cada `[ ]` ao concluir. Se algo der errado, anote a mensagem de erro exata e consulte a [seção 8](#8-problemas-comuns).

---

## ⚠️ Datas que não podem passar

| Quando | O quê |
| ------ | ----- |
| **Dia 30 após criar o banco** (crie hoje → por volta de **28/11**) | Upgrade do Postgres para um plano pago (seção 7). Se passar, o Render dá 14 dias de carência e depois **apaga o banco**. |
| Antes de cada demonstração | Abrir `https://SUA-API.onrender.com/health` e esperar o `{"status":"ok"}` (a API dorme após 15 min parada) |

---

## 0. Preparação (≈ 45 min)

### 0.1 Nova chave da Harvard
A chave atual circulou fora de um cofre de segredos durante o desenvolvimento, então ela precisa ser trocada antes de ir ao ar.

- [ ] Peça uma nova chave em <https://harvardartmuseums.org/collections/api> (confirme o processo no site; normalmente chega por e-mail)
- [ ] Coloque a nova chave no `backend/.env` local e teste o site em localhost
- [ ] Guarde a chave num lugar seguro (gerenciador de senhas) para o passo 2.4

### 0.2 Alerta de orçamento na Azure
Depois do deploy, qualquer visitante pode disparar uma geração, e cada geração é cobrada do crédito.

- [ ] Portal Azure → pesquise **Cost Management** → **Budgets** (Orçamentos) → **+ Add**
- [ ] Escopo: a sua assinatura Azure for Students
- [ ] Valor: por exemplo **US$ 20**, mensal
- [ ] Alertas: 50%, 80% e 100% do valor, enviados para o seu e-mail
- [ ] Salve

### 0.3 Separe os valores do Azure OpenAI
Eles estão no seu `backend/.env` local. Não copie para nenhum outro lugar além do Render (passo 2.4).

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_DEPLOYMENT` (`gpt-4.1-mini-art-archive`)

---

## 1. Levar o código para a `main` (≈ 10 min)

Vercel e Render publicam o que estiver na branch `main`.

- [ ] No PR `ai_expansion → main` do **seu** repositório (`Jeferson-Filho/Art-Archive-Front-AI`), revise a lista de arquivos e confirme que nenhum `.env` aparece
- [ ] **Merge pull request**

---

## 2. Render: banco e back-end (≈ 1h30)

### 2.1 Conta
- [ ] <https://render.com> → **Get Started** → **GitHub**
- [ ] Não precisa cadastrar cartão agora; ele só será pedido no upgrade (seção 7)

### 2.2 Criar o PostgreSQL
- [ ] Dashboard → **+ New** → **Postgres**
- [ ] Preencha:
  - **Name:** `art-archive-db`
  - **Database:** `art_archive`
  - **User:** `art_archive_user`
  - **Region:** **Virginia (US East)**, ou **Ohio (US East)** se Virginia não aparecer. Anote a região: a API precisa ficar na mesma.
  - **PostgreSQL Version:** a mais recente oferecida
  - **Instance Type:** **Free**
- [ ] **Create Database** e aguarde o status **Available** (1 a 3 min)
- [ ] Anote a **data de hoje** como a data de criação do banco. O upgrade (seção 7) vence 30 dias depois.

O usuário que o Render cria é dono do banco, mas **não** é superusuário. Isso já atende ao provisionamento da Fase 2, então não é preciso criar outro usuário.

### 2.3 Rodar as migrações (do seu computador)
No plano grátis não existe "pre-deploy command", então as migrações rodam da sua máquina. Isso só é necessário de novo quando uma migração nova for criada.

- [ ] No banco → **Info** → **Connections** → copie a **External Database URL**. Ela tem o formato `postgresql://art_archive_user:SENHA@dpg-xxxx.virginia-postgres.render.com/art_archive`.
- [ ] Monte a URL para o back-end, ainda fora de qualquer arquivo (num bloco de notas que você vai apagar depois):
  - troque `postgresql://` por **`postgresql+asyncpg://`**
  - acrescente **`?ssl=require`** no final, porque o acesso externo exige SSL
- [ ] No PowerShell, dentro da pasta `backend`:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://art_archive_user:SENHA@dpg-xxxx.virginia-postgres.render.com/art_archive?ssl=require"
venv\Scripts\alembic.exe upgrade head
Remove-Item Env:DATABASE_URL
Clear-History
```

- [ ] A saída deve listar `Running upgrade  -> 0001`, depois `0001 -> 0002` e assim por diante, até `0006`
- [ ] Apague a URL do bloco de notas

A variável de ambiente tem prioridade sobre o seu `backend/.env`, então o banco local não é afetado. `Remove-Item` e `Clear-History` tiram a senha da sessão.

### 2.4 Criar a API
- [ ] Dashboard → **+ New** → **Web Service** → **Git Provider** → **GitHub** → autorize o Render no seu repositório → selecione `Jeferson-Filho/Art-Archive-Front-AI`
- [ ] Preencha:
  - **Name:** `art-archive-api` (vira a URL `https://art-archive-api.onrender.com`; se o nome estiver ocupado, o Render acrescenta um sufixo)
  - **Language / Runtime:** **Docker**
  - **Branch:** `main`
  - **Region:** **a mesma do banco**
  - **Root Directory:** `backend`
  - **Dockerfile Path:** confira que aponta para o `Dockerfile` dentro de `backend`. Com o Root Directory definido, normalmente basta `./Dockerfile`.
  - **Instance Type:** **Free**
- [ ] Em **Environment Variables**, adicione uma por uma:

| Nome | Valor |
| ---- | ----- |
| `HARVARD_API_KEY` | a nova chave do passo 0.1 |
| `AZURE_OPENAI_ENDPOINT` | do seu `.env` local |
| `AZURE_OPENAI_API_KEY` | do seu `.env` local |
| `AZURE_OPENAI_DEPLOYMENT` | `gpt-4.1-mini-art-archive` |
| `DATABASE_URL` | a **Internal Database URL** do banco (banco → **Info** → **Connections**), com `postgresql://` trocado por **`postgresql+asyncpg://`** e **sem** `?ssl=require` |
| `FRONTEND_ORIGIN` | `https://temporario.invalid` (provisório, trocado no passo 4) |

Atenção:
- Não crie `PORT`. O Render define a porta sozinho, e o `Dockerfile` já a lê.
- Não use o botão que liga o banco à API automaticamente: ele cria uma URL com `postgresql://`, que o driver do back-end não aceita.

- [ ] Em **Advanced**:
  - **Health Check Path:** `/health`
  - **Auto-Deploy:** **On Commit** (padrão)
- [ ] **Deploy Web Service**

### 2.5 Conferir a API
- [ ] Acompanhe a aba **Logs**: o build do Docker leva alguns minutos. No fim deve aparecer `Uvicorn running on http://0.0.0.0:10000` (a porta pode variar) e o status **Live**.
- [ ] Abra no navegador:
  - `https://art-archive-api.onrender.com/health` → `{"status":"ok"}`
  - `https://art-archive-api.onrender.com/docs` → Swagger
  - `https://art-archive-api.onrender.com/proxy/century?size=3` → JSON da Harvard (confirma a chave nova)

---

## 3. Vercel: front-end (≈ 20 min)

O projeto já está conectado. Falta configurar as variáveis e confirmar a branch.

### 3.1 Variáveis de ambiente
Projeto → **Settings** → **Environment Variables**:

| Nome | Valor | Ambientes |
| ---- | ----- | --------- |
| `NEXT_PUBLIC_API_URL` | `https://art-archive-api.onrender.com/`, **com a barra no final** | Production, Preview |
| `NEXT_PUBLIC_INSIGHT_CARD_SOURCE` | `api` | Production, Preview |

Atenção:
- A barra final é obrigatória: o front-end chama caminhos como `proxy/century`, sem barra inicial.
- Variáveis `NEXT_PUBLIC_*` ficam visíveis para qualquer visitante. Nunca coloque chaves nelas.
- Elas são gravadas no momento do build: depois de criar ou mudar uma, é preciso fazer um novo deploy (passo 3.3).

### 3.2 Branch de produção
- [ ] **Settings** → **Git** (ou **Environments → Production**) → confirme que a **Production Branch** é `main`
- [ ] **Settings** → **General** → **Root Directory**: vazio ou `./` (não pode ser `backend`)

### 3.3 Novo deploy
- [ ] **Deployments** → o deploy mais recente da `main` → **⋯** → **Redeploy**
- [ ] Anote a URL de produção, por exemplo `https://art-archive-front-ai.vercel.app` (em **Domains**, na página do projeto)

---

## 4. Ligar o front-end à API (CORS) (≈ 10 min)

A API só aceita chamadas da origem configurada em `FRONTEND_ORIGIN`.

- [ ] Render → `art-archive-api` → **Environment** → `FRONTEND_ORIGIN` = `https://art-archive-front-ai.vercel.app`, a URL do passo 3.3, **sem barra no final**
- [ ] **Save Changes**. O Render faz um novo deploy sozinho; aguarde o status **Live**.

---

## 5. Validação: critérios da Fase 7 (≈ 30 min)

Antes de começar, abra `/health` da API e espere ela acordar. Depois, abra a URL da Vercel numa aba anônima.

- [ ] O site abre com cadeado (HTTPS)
- [ ] O grid carrega e rola, e os filtros (século, cultura, cores…) aplicam
- [ ] A página de uma obra mostra metadados, imagens e artistas
- [ ] **Insight Card:** abra `/object/306240`
  - [ ] na primeira visita, os dois blocos aparecem em até cerca de 30 s (o banco de produção começa vazio, então ele gera)
  - [ ] recarregue: os blocos aparecem quase na hora (vêm do banco)
- [ ] O banco tem o registro. No banco → **Connect** → copie o comando **PSQL**, rode-o no PowerShell com o `psql` do PostgreSQL 18 (`& "C:\Program Files\PostgreSQL\18\bin\psql.exe" "URL"`) e execute:

```sql
SELECT artwork_id, length(historical_context), length(comparative_analysis), expired_at
FROM artwork_ai_content;
```

- [ ] **Deploy automático:** faça um commit pequeno na `main`, por exemplo um texto deste guia, dê push e confira que a Vercel e o Render iniciam um deploy sozinhos
- [ ] **Segredos:** no site, abra DevTools → **Sources**, procure (Ctrl+Shift+F) por um trecho da sua chave Azure e da chave Harvard. Não pode haver resultado.
- [ ] O alerta de orçamento Azure (passo 0.2) está ativo
- [ ] O upgrade do banco está na agenda (seção 7)

Quando tudo estiver marcado, me avise: eu atualizo o doc 99 (critérios da Fase 7 e "Result") e fazemos o commit.

---

## 6. Manter a API acordada (opcional)

A API grátis dorme após 15 minutos sem acesso e leva cerca de 1 minuto para acordar. Enquanto acorda, o grid falha, porque o front-end espera só 10 s.

- **Só para as demonstrações:** abra `/health` 1 a 2 minutos antes de apresentar.
- **Sempre acordada:** crie uma conta grátis no <https://cron-job.org> e um job `GET https://art-archive-api.onrender.com/health` a cada **10 minutos**. Um único serviço ligado o mês todo usa cerca de 744 h, dentro das 750 h grátis do Render. Não faça isso para um segundo serviço grátis, porque as horas acabam.

---

## 7. Upgrade (antes do dia 30 do banco)

| O quê | Quando | Como |
| ----- | ------ | ---- |
| **Postgres → Basic** (cerca de US$ 6/mês) | **Obrigatório** antes do dia 30 | Banco → **Info** → **Instance Type** → **Update** → escolha o menor plano pago. É no mesmo banco, sem perder dados. O Render pede o cartão. |
| API → Starter (cerca de US$ 7/mês) | Se o "dorme-e-acorda" atrapalhar | `art-archive-api` → **Settings** → **Instance Type**. Depois, em **Settings** → **Pre-Deploy Command**, coloque `alembic upgrade head` (as migrações passam a rodar sozinhas) e avise para eu atualizar o doc 04 §8.2. |

Os preços vêm de fontes de 2026. Confirme na tela do upgrade.

---

## 8. Problemas comuns

| Sintoma | Causa provável | Solução |
| ------- | -------------- | ------- |
| Grid vazio; no DevTools → Console, erro **CORS** | `FRONTEND_ORIGIN` diferente da URL da Vercel | Copie a URL exata da Vercel, com `https://` e sem barra final, e salve no Render |
| Grid vazio, sem erro de CORS, e funciona ao recarregar | A API estava dormindo | Esperado no plano grátis (seção 6) |
| Requisições vão para `...onrender.comproxy/...` | `NEXT_PUBLIC_API_URL` sem barra final | Corrija na Vercel e faça **Redeploy** |
| Mudei variável na Vercel e nada mudou | `NEXT_PUBLIC_*` é gravada no build | Vercel → **Deployments** → último deploy → **⋯** → **Redeploy** |
| Logs da API: `ModuleNotFoundError: psycopg2` ou erro de dialeto | `DATABASE_URL` começando com `postgresql://` | Use `postgresql+asyncpg://` |
| Logs da API: erro de conexão com o banco usando a URL interna | Rede interna indisponível (região diferente ou limitação do plano grátis) | Confira se banco e API estão na mesma região. Se estiverem, use a **External** URL com `postgresql+asyncpg://` e `?ssl=require` no final |
| `alembic` local: erro de SSL ou conexão recusada | Faltou `?ssl=require`, ou o banco bloqueia o seu IP | Confira a URL; no banco → **Networking** / **Access Control**, a regra padrão permite todos os IPs |
| Build: `Dockerfile not found` | Caminho do Dockerfile errado | **Settings** → **Root Directory** = `backend` e **Dockerfile Path** = `./Dockerfile` |
| Deploy falha no health check | O app não subiu (variável errada) | Veja o primeiro erro em **Logs** |
| Insight Card vazio ou com erro para uma obra | Filtros de conteúdo da Azure (veja `documentation/Challenges.txt`) | Esperado nesta versão; teste com 306240 |
| Imagens do grid param de carregar na Vercel | Cota de otimização de imagens do Hobby | Me avise: a correção é `images.unoptimized` no `next.config.mjs`, uma mudança de código que passa pelas specs |

---

## 9. Depois do deploy

- **Domínio próprio (opcional):** compre o domínio e configure em Vercel → **Settings → Domains**. Depois atualize `FRONTEND_ORIGIN` no Render e registre a escolha no doc 04 §8.2.
- **Fase 8 (Tuning):** filtros de conteúdo, qualidade das fontes, limite de requisições por visitante (protege o crédito Azure) e testes rodando no GitHub Actions antes do deploy.
