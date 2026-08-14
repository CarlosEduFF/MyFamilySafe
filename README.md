# MyFamilySafe API 🛡️

API REST do **MyFamilySafe**, um app de segurança familiar: os membros de uma família
compartilham a localização em tempo real, e o sistema emite alertas quando alguém entra
ou sai de uma área definida (geofence) ou se conecta a uma rede WiFi desconhecida.

Este repositório contém **apenas a API**. O aplicativo Flutter que a consome vive em
outro repositório: **[CarlosEduFF/MyFamilySafeApp](https://github.com/CarlosEduFF/MyFamilySafeApp)**.

O contrato entre os dois é o arquivo [`openapi.json`](openapi.json), versionado aqui e
regenerado a cada mudança de rota ou schema (ver [Contrato OpenAPI](#contrato-openapi)).

---

## Sumário

- [Stack](#stack)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Como rodar](#como-rodar)
- [Migrations](#migrations)
- [Testes](#testes)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Rotas](#rotas)
- [Contrato OpenAPI](#contrato-openapi)
- [Deploy](#deploy)
- [Licença](#licença)

---

## Stack

| Camada | Tecnologia |
|---|---|
| Framework | FastAPI |
| ORM | SQLAlchemy 2.x (async) + asyncpg |
| Migrations | Alembic |
| Banco | PostgreSQL (local via Docker; Supabase em produção) |
| Autenticação | JWT — access token + refresh token (PyJWT) |
| Hash de senha | passlib + bcrypt |
| Servidor | Uvicorn |
| Testes | pytest + pytest-asyncio + httpx |

Requer **Python 3.11+**.

---

## Estrutura do projeto

```
.
├── app/
│   ├── main.py          # instância FastAPI, CORS, registro dos routers
│   ├── config.py        # settings via pydantic-settings (lê .env)
│   ├── database.py      # engine async, sessionmaker, Base
│   ├── models.py        # tabelas SQLAlchemy
│   ├── schemas.py       # modelos Pydantic de entrada/saída
│   ├── security.py      # hash de senha e emissão/validação de JWT
│   ├── deps.py          # dependências: get_db, get_current_user, require_family_member
│   └── routers/         # auth, families, locations, wifi, geofences, alerts, me
├── services/            # regras de negócio: alerts, auth, geofencing, wifi
├── alembic/             # migrations
├── scripts/
│   └── export_openapi.py
├── tests/
├── docker-compose.yml
├── Dockerfile
└── openapi.json         # contrato consumido pelo app Flutter
```

---

## Como rodar

### Opção 1 — Docker Compose (recomendado)

Sobe o Postgres e a API juntos. É o caminho mais curto para ter tudo de pé.

```bash
git clone https://github.com/CarlosEduFF/MyFamilySafe.git
cd MyFamilySafe

cp .env.example .env
```

Abra o `.env` e ajuste **duas coisas** para o ambiente local (os valores do
`.env.example` apontam para o Supabase, não para o Postgres do compose):

```env
DB_HOST=db          # nome do serviço no docker-compose
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=myfamilysafe
DB_SSL=disable      # o Postgres local não usa TLS
```

Defina também `JWT_SECRET` e `JWT_REFRESH_SECRET` com quaisquer valores (em
desenvolvimento não precisam ser fortes, mas precisam ser **diferentes entre si**).

Então:

```bash
docker compose up --build
```

A API sobe em **http://localhost:8080**. As migrations rodam automaticamente na
inicialização do container (o `CMD` do Dockerfile executa `alembic upgrade head`
antes do Uvicorn).

Documentação interativa:

- Swagger UI — http://localhost:8080/docs
- ReDoc — http://localhost:8080/redoc

Verifique que está no ar:

```bash
curl http://localhost:8080/health
# {"status":"ok","timestamp":"..."}
```

### Opção 2 — Python local (só a API, banco no Docker)

Útil para depurar com breakpoints ou reload automático.

```bash
# 1. Sobe apenas o Postgres
docker compose up -d db

# 2. Ambiente virtual e dependências
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 3. Configura o .env (note: DB_HOST=localhost, não 'db')
cp .env.example .env
```

No `.env`, para este modo use:

```env
DB_HOST=localhost
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=myfamilysafe
DB_SSL=disable
```

```bash
# 4. Aplica as migrations e sobe a API
alembic upgrade head
uvicorn app.main:app --reload --port 8080
```

---

## Migrations

Gerenciadas por Alembic, em `alembic/versions/`.

```bash
# Aplica todas as migrations pendentes
alembic upgrade head

# Cria uma nova migration a partir das mudanças em app/models.py
alembic revision --autogenerate -m "descrição da mudança"

# Volta uma migration
alembic downgrade -1

# Mostra a revisão atual do banco
alembic current
```

O `alembic.ini` **não** contém a URL do banco: ela é montada em tempo de execução a
partir das variáveis de ambiente (`app/config.py`), então o `.env` precisa estar
configurado antes de rodar qualquer comando do Alembic.

---

## Testes

A suíte é de **integração**: sobe a aplicação real contra um Postgres de verdade e
recria o schema a cada teste. Por isso o banco precisa estar no ar.

```bash
# 1. Postgres precisa estar rodando
docker compose up -d db

# 2. Roda a suíte
pytest

# Um arquivo específico, com output verboso
pytest tests/test_auth.py -v
```

O `tests/conftest.py` já define as variáveis de ambiente de teste (banco
`myfamilysafe` em `localhost:5432`, usuário/senha `postgres`), então **não é preciso
`.env` para rodar os testes** — apenas o Postgres do compose.

> Se todos os testes falharem com `OSError`/`getaddrinfo` ou timeout de conexão, é o
> Postgres que não está acessível em `localhost:5432`. Confirme com `docker compose ps`.

---

## Variáveis de ambiente

Fonte da verdade: [`.env.example`](.env.example). Copie com `cp .env.example .env` — o
`.env` está no `.gitignore` e **nunca** deve ser commitado.

| Variável | Obrigatória | Padrão | Descrição |
|---|---|---|---|
| `PORT` | não | `8080` | Lido pelas settings, mas a porta efetiva é definida no `Dockerfile`/comando do Uvicorn. |
| `DB_HOST` | **sim** | — | Host do Postgres. `db` no compose, `localhost` para execução local, pooler do Supabase em produção. |
| `DB_PORT` | **sim** | — | Porta do Postgres (`5432`). |
| `DB_USER` | **sim** | — | Usuário. No pooler do Supabase inclui o project ref (`postgres.xxxxxxxx`). |
| `DB_PASSWORD` | **sim** | — | Senha. Caracteres especiais são escapados automaticamente na URL. |
| `DB_NAME` | **sim** | — | Nome do banco (`myfamilysafe` local, `postgres` no Supabase). |
| `DB_SSL` | não | `require` | `require` em produção; **`disable`** no Postgres local do compose. |
| `DB_POOL_SIZE` | não | `5` | Tamanho do pool de conexões. Ver nota em [Deploy](#deploy). |
| `JWT_SECRET` | **sim** | — | Segredo de assinatura do access token. |
| `JWT_REFRESH_SECRET` | **sim** | — | Segredo do refresh token. Deve ser **diferente** do `JWT_SECRET`. |
| `CORS_ORIGINS` | não | `""` | Origens permitidas, separadas por vírgula. Vazio ⇒ `http://localhost`. |

Dois valores não vêm do `.env` e estão fixos em `app/config.py`: o access token expira
em **1 hora** e o refresh token em **30 dias**. Um membro é considerado *online* se
enviou localização nos últimos **5 minutos**.

---

## Rotas

Todas as rotas sob `/api` exigem o header `Authorization: Bearer <access_token>`, obtido
em `/auth/login` ou `/auth/register`. As rotas de família validam também que o usuário
autenticado é membro daquela família.

O parâmetro `{id}` é sempre o UUID da família.

### Autenticação — `/auth`

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/auth/register` | Cria a conta e já retorna os tokens. |
| `POST` | `/auth/login` | Autentica por email e senha. |
| `POST` | `/auth/refresh` | Troca um refresh token válido por um novo par de tokens. |

### Usuário autenticado — `/api/me`

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/me` | Dados do usuário logado. |
| `PUT` | `/api/me` | Atualiza os dados do próprio usuário. |
| `GET` | `/api/me/families` | Lista todas as famílias das quais o usuário participa. |

### Famílias — `/api/families`

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/families` | Cria uma família; quem cria vira `owner`. |
| `POST` | `/api/families/join` | Entra numa família usando o código de convite. |
| `GET` | `/api/families/{id}` | Detalhes da família. |
| `GET` | `/api/families/{id}/members` | Lista os membros e seus papéis. |
| `PUT` | `/api/families/{id}/members/{user_id}/role` | Promove ou rebaixa um membro. |
| `DELETE` | `/api/families/{id}/members/{user_id}` | Remove um membro (o próprio usuário ou, se for owner, qualquer um). |
| `POST` | `/api/families/{id}/leave-requests` | Solicita saída da família. |
| `GET` | `/api/families/{id}/leave-requests` | Lista as solicitações de saída pendentes. |
| `PUT` | `/api/families/{id}/leave-requests/{request_id}` | Aprova ou rejeita uma solicitação. |

### Localização — `/api/location`, `/api/families/{id}/locations`

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/location` | Envia a posição atual do usuário; dispara a avaliação de geofences. |
| `GET` | `/api/families/{id}/locations` | Última posição conhecida de cada membro, com status online. |
| `GET` | `/api/members/{user_id}/location/history` | Histórico de posições de um membro (exige família em comum). |

### WiFi — `/api/wifi`, `/api/families/{id}/wifi`

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/wifi` | Reporta a rede conectada; gera alerta se não for confiável. |
| `GET` | `/api/families/{id}/wifi` | Rede atual de cada membro da família. |
| `GET` | `/api/families/{id}/wifi/trusted` | Lista as redes marcadas como confiáveis. |
| `POST` | `/api/families/{id}/wifi/trusted` | Adiciona uma rede confiável. |
| `DELETE` | `/api/families/{id}/wifi/trusted?bssid=<bssid>` | Remove uma rede confiável (BSSID via query string). |

### Geofences — `/api/families/{id}/geofences`

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/families/{id}/geofences` | Cria uma área monitorada (centro + raio). |
| `GET` | `/api/families/{id}/geofences` | Lista as áreas da família. |
| `DELETE` | `/api/families/{id}/geofences/{geofence_id}` | Remove uma área. |

### Alertas — `/api/families/{id}/alerts`

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/families/{id}/alerts` | Lista os alertas da família. |
| `PUT` | `/api/alerts/{alert_id}/read` | Marca um alerta como lido. |

### Saúde do serviço

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/health` | Status e timestamp do servidor. |
| `GET` / `HEAD` | `/ping` | Keep-alive: não toca no banco. Ver [Deploy](#deploy). |

---

## Contrato OpenAPI

O [`openapi.json`](openapi.json) na raiz é o contrato consumido pelo app Flutter. Ele é
versionado de propósito: assim qualquer alteração de rota ou de schema fica visível no
diff do pull request.

**Regenere sempre que mexer em rotas ou schemas:**

```bash
python scripts/export_openapi.py
```

Para apenas verificar se está atualizado, sem escrever (útil em CI):

```bash
python scripts/export_openapi.py --check   # sai com código 1 se desatualizado
```

O script não abre conexão com o banco, então roda sem `.env` e sem Postgres no ar.

A mesma especificação também é servida pela aplicação em tempo de execução, em
`GET /openapi.json`.

---

## Deploy

A API roda no **Render**, a partir do `Dockerfile`, com banco no **Supabase**.

Pontos que costumam causar problema:

- **Use o *session pooler* do Supabase**, não a conexão direta. O host
  `db.xxxxx.supabase.co` é IPv6-only e o Render não alcança; o host do pooler
  (`aws-0-<região>.pooler.supabase.com`) é IPv4. No pooler, o `DB_USER` inclui o project
  ref (`postgres.xxxxxxxx`).
- **`DB_POOL_SIZE` conservador.** O pooler do Supabase limita conexões simultâneas por
  projeto; o padrão `5` existe para não estourar esse teto quando há mais de uma
  instância.
- **`DB_SSL=require`** em produção.
- **Cold start no free tier.** O plano gratuito do Render suspende o serviço após ~15
  minutos sem tráfego HTTP externo, e religar leva de 30 a 60 segundos. O endpoint
  `/ping` existe para ser chamado por um cron externo (UptimeRobot, cron-job.org) num
  intervalo menor que 15 minutos. Ele não consulta o banco, para não gastar cota do
  Supabase à toa. Um "self-ping" interno **não** resolve: quando o Render suspende o
  serviço, qualquer timer interno é suspenso junto.

As migrations são aplicadas automaticamente a cada deploy, pelo `CMD` do Dockerfile.

---

## Licença

[MIT](LICENSE).
