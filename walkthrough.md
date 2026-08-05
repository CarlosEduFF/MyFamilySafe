# MyFamilySafe API — Guia Completo de Go 🛡️

App para monitoramento familiar: localização em tempo real, status WiFi, geofencing e alertas.

**Stack**: Go + Gin (HTTP) + PostgreSQL (Supabase) + JWT (autenticação)

---

## 1. Estrutura do Projeto

```
api/
├── .env                          # Variáveis de ambiente (senhas, configs)
├── go.mod                        # Dependências do projeto (como package.json)
├── main.go                       # Ponto de entrada — inicia tudo
└── internal/                     # Código privado do projeto
    ├── models/models.go          # Structs que representam as tabelas do banco
    ├── database/database.go      # Conexão com PostgreSQL + criação de tabelas
    ├── middleware/middleware.go   # JWT (autenticação) e CORS
    └── handlers/
        ├── auth.go               # Register, Login, RefreshToken
        ├── handler.go            # CRUD de Famílias, Membros, Perfil
        └── resources.go          # Localização, WiFi, Geofences, Alertas
```

> [!IMPORTANT]
> A pasta `internal/` é especial em Go. Código dentro dela **só pode ser importado** pelo próprio módulo (`myfamilysafe`). Nenhum projeto externo consegue importar esses pacotes.

---

## 2. `go.mod` — Gerenciamento de Dependências

```go
module myfamilysafe    // Nome do módulo (usado nos imports)
go 1.22                // Versão mínima do Go

require (
    github.com/gin-gonic/gin v1.10.0      // Framework HTTP (como Express do Node)
    github.com/golang-jwt/jwt/v5 v5.2.1   // Criação/validação de tokens JWT
    github.com/joho/godotenv v1.5.1        // Lê arquivo .env
    github.com/lib/pq v1.10.9             // Driver PostgreSQL
    golang.org/x/crypto v0.23.0           // bcrypt para hash de senhas
)
```

**Conceitos Go:**
- `module myfamilysafe` → define o nome do módulo. Todos os imports internos começam com esse nome
- `require (...)` → lista as dependências externas com versões exatas
- Para instalar: `go mod tidy` baixa tudo automaticamente

---

## 3. `main.go` — Ponto de Entrada

```go
package main  // Todo executável Go precisa ter package main
```

Em Go, o programa começa **sempre** na função `main()` do `package main`.

### Imports

```go
import (
    "log"    // Pacote padrão para logs
    "os"     // Pacote padrão para variáveis de ambiente

    "github.com/gin-gonic/gin"    // Framework web
    "github.com/joho/godotenv"    // Carregar .env

    // Imports internos do projeto (prefixo = nome do módulo)
    "myfamilysafe/internal/database"
    "myfamilysafe/internal/handlers"
    "myfamilysafe/internal/middleware"
)
```

### Função `main()`

```go
func main() {
    // 1. Carrega variáveis do .env
    if err := godotenv.Load(); err != nil {
        log.Println("No .env file found, using environment variables")
    }
```

**Conceito: Error Handling em Go** — Go **não tem try/catch**. Funções retornam erros como segundo valor. O padrão é:
```go
resultado, err := algumaFuncao()
if err != nil {
    // tratar o erro
}
```

```go
    // 2. Conecta ao banco de dados
    db, err := database.Connect()
    if err != nil {
        log.Fatalf("Failed to connect to database: %v", err)
        // log.Fatalf imprime o erro E encerra o programa
    }
    defer db.Close()  // ← defer: executa db.Close() quando main() terminar
```

**Conceito: `defer`** — Agenda uma função para executar **quando a função atual terminar**. Útil para fechar conexões, arquivos, etc. Garante que o recurso sempre será liberado.

```go
    // 3. Cria as tabelas no banco (migrations)
    if err := database.RunMigrations(db); err != nil {
        log.Fatalf("Failed to run migrations: %v", err)
    }

    // 4. Cria o roteador HTTP (Gin)
    r := gin.Default()          // Cria router com logger e recovery padrão
    r.Use(middleware.CORS())    // Aplica middleware CORS em todas as rotas

    // 5. Cria o handler (contém todas as funções de endpoint)
    h := handlers.New(db)       // Passa o banco de dados pro handler
```

### Definição de Rotas

```go
    // ROTAS PÚBLICAS (sem autenticação)
    auth := r.Group("/auth")
    {
        auth.POST("/register", h.Register)      // POST /auth/register
        auth.POST("/login", h.Login)             // POST /auth/login
        auth.POST("/refresh", h.RefreshToken)    // POST /auth/refresh
    }

    // ROTAS PROTEGIDAS (precisam de token JWT)
    api := r.Group("/api")
    api.Use(middleware.JWT())  // ← Middleware JWT aplicado a TODAS as rotas /api/*
    {
        api.POST("/families", h.CreateFamily)
        api.GET("/families/:id", h.GetFamily)         // :id = parâmetro de URL
        api.POST("/location", h.UpdateLocation)
        // ... mais rotas
    }
```

**Conceito: Grupos de Rota** — `r.Group("/api")` cria um prefixo. Todas as rotas dentro herdam o prefixo e os middlewares aplicados com `.Use()`.

```go
    // 6. Inicia o servidor
    port := os.Getenv("PORT")
    if port == "" {
        port = "8080"  // Valor padrão
    }
    log.Fatal(r.Run(":" + port))  // Bloqueia aqui, servindo HTTP
}
```

---

## 4. `models/models.go` — Structs (Modelos de Dados)

### O que são Structs?

Structs em Go são como **classes sem métodos** (similar a um DTO/POJO em Java). Definem a forma dos dados.

```go
package models

import "time"

type User struct {
    ID           string    `json:"id" db:"id"`
    Name         string    `json:"name" db:"name"`
    Email        string    `json:"email" db:"email"`
    PasswordHash string    `json:"-" db:"password_hash"`
    AvatarURL    *string   `json:"avatar_url" db:"avatar_url"`
    FCMToken     *string   `json:"fcm_token" db:"fcm_token"`
    CreatedAt    time.Time `json:"created_at" db:"created_at"`
    UpdatedAt    time.Time `json:"updated_at" db:"updated_at"`
}
```

**Conceitos importantes:**

| Sintaxe | Significado |
|---------|-------------|
| `string` | Tipo string obrigatório (nunca é null) |
| `*string` | **Ponteiro** para string — pode ser `nil` (null). Usado para campos opcionais |
| `time.Time` | Tipo de data/hora do pacote `time` |
| `` `json:"id"` `` | **Struct tag** — diz ao JSON encoder para usar `"id"` como nome do campo |
| `` `json:"-"` `` | **Ignora** o campo na serialização JSON (senha nunca vai na resposta!) |
| `` `db:"id"` `` | Tag para mapear ao nome da coluna no banco |

**Conceito: Ponteiros (`*`)** — Em Go, um `string` sempre tem um valor (no mínimo `""`). Se o campo pode ser NULL no banco, usamos `*string` (ponteiro). Um ponteiro pode ser `nil`, representando a ausência de valor.

### Outros Models

```go
type Family struct {
    ID         string    `json:"id" db:"id"`
    Name       string    `json:"name" db:"name"`
    OwnerID    string    `json:"owner_id" db:"owner_id"`
    InviteCode string    `json:"invite_code" db:"invite_code"`
    CreatedAt  time.Time `json:"created_at" db:"created_at"`
}

type FamilyMember struct {
    FamilyID string    `json:"family_id"`
    UserID   string    `json:"user_id"`
    Role     string    `json:"role"`           // "admin" ou "member"
    JoinedAt time.Time `json:"joined_at"`
    User     *User     `json:"user,omitempty"` // omitempty: omite se nil
}
```

`omitempty` na tag JSON significa: se o valor for zero/nil, **não inclui** na resposta JSON.

```go
type Location struct { ... }       // Lat, Lon, Accuracy, Address
type MemberLocation struct { ... } // User + última Location + IsOnline
type WifiStatus struct { ... }     // SSID, BSSID, IsTrusted
type TrustedNetwork struct { ... } // Redes WiFi confiáveis da família
type Geofence struct { ... }       // Zona segura: ponto central + raio
type Alert struct { ... }          // Alertas: geofence_exit, unknown_wifi, etc.
```

---

## 5. `database/database.go` — Conexão e Migrations

### Conexão

```go
package database

import (
    "database/sql"  // Pacote padrão de SQL do Go
    "fmt"
    "os"
    _ "github.com/lib/pq"  // ← Import "blank" — apenas registra o driver
)
```

**Conceito: Blank Import (`_`)** — O `_` antes do import significa "importe este pacote apenas pelos seus efeitos colaterais". O driver `lib/pq` se registra automaticamente via `init()` para que `sql.Open("postgres", ...)` funcione.

```go
func Connect() (*sql.DB, error) {
    // Monta a string de conexão com variáveis de ambiente
    dsn := fmt.Sprintf(
        "host=%s port=%s user=%s password=%s dbname=%s sslmode=require",
        os.Getenv("DB_HOST"),
        os.Getenv("DB_PORT"),
        os.Getenv("DB_USER"),
        os.Getenv("DB_PASSWORD"),
        os.Getenv("DB_NAME"),
    )

    db, err := sql.Open("postgres", dsn)  // Cria pool de conexões
    if err != nil {
        return nil, err  // Retorna nil e o erro
    }

    if err := db.Ping(); err != nil {  // Testa se realmente conectou
        return nil, err
    }

    db.SetMaxOpenConns(25)  // Máximo de conexões abertas simultaneamente
    db.SetMaxIdleConns(5)   // Conexões ociosas mantidas no pool

    return db, nil  // Sucesso: retorna o db e nil (sem erro)
}
```

**Conceito: Retorno Múltiplo** — Funções Go podem retornar **múltiplos valores**. O padrão é `(resultado, error)`. Se tudo deu certo, o error é `nil`.

### Migrations (Criação de Tabelas)

```go
func RunMigrations(db *sql.DB) error {
    _, err := db.Exec(schema)  // Executa o SQL abaixo
    return err
}

const schema = `
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name          VARCHAR(100) NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    ...
);
-- ... demais tabelas
`
```

O `const schema` contém todo o SQL de criação das tabelas. `CREATE TABLE IF NOT EXISTS` garante que roda sem erro mesmo que as tabelas já existam.

---

## 6. `middleware/middleware.go` — JWT e CORS

### Struct Claims

```go
type Claims struct {
    UserID string `json:"user_id"`
    Email  string `json:"email"`
    jwt.RegisteredClaims  // ← Embedding (composição)
}
```

**Conceito: Embedding** — `jwt.RegisteredClaims` é "embutido" na struct. Claims herda todos os campos de `RegisteredClaims` (ExpiresAt, IssuedAt, etc.) sem precisar prefixar.

### Middleware JWT

```go
func JWT() gin.HandlerFunc {
    return func(c *gin.Context) {
        // 1. Pega o header Authorization
        authHeader := c.GetHeader("Authorization")
        if authHeader == "" {
            c.AbortWithStatusJSON(http.StatusUnauthorized,
                gin.H{"error": "missing authorization header"})
            return  // Para aqui, não chama o handler
        }

        // 2. Separa "Bearer <token>"
        parts := strings.SplitN(authHeader, " ", 2)
        if len(parts) != 2 || parts[0] != "Bearer" {
            c.AbortWithStatusJSON(http.StatusUnauthorized,
                gin.H{"error": "invalid authorization format"})
            return
        }

        // 3. Valida o token JWT
        tokenStr := parts[1]
        claims := &Claims{}
        token, err := jwt.ParseWithClaims(tokenStr, claims,
            func(t *jwt.Token) (interface{}, error) {
                // Verifica se o algoritmo é HMAC (segurança!)
                if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
                    return nil, jwt.ErrSignatureInvalid
                }
                return []byte(os.Getenv("JWT_SECRET")), nil
            })

        if err != nil || !token.Valid {
            c.AbortWithStatusJSON(http.StatusUnauthorized,
                gin.H{"error": "invalid or expired token"})
            return
        }

        // 4. Salva dados do usuário no contexto da requisição
        c.Set("user_id", claims.UserID)
        c.Set("email", claims.Email)
        c.Next()  // ← Passa para o próximo handler
    }
}
```

**Conceito: `gin.HandlerFunc`** — É uma função que recebe `*gin.Context`. O middleware é uma HandlerFunc que decide se chama `c.Next()` (continua) ou `c.Abort()` (bloqueia).

**Conceito: Type Assertion** — `t.Method.(*jwt.SigningMethodHMAC)` verifica se o método de assinatura é HMAC. O `ok` retorna `true/false`.

### Middleware CORS

```go
func CORS() gin.HandlerFunc {
    return func(c *gin.Context) {
        c.Header("Access-Control-Allow-Origin", "*")
        c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        c.Header("Access-Control-Allow-Headers", "Content-Type, Authorization")

        if c.Request.Method == "OPTIONS" {
            c.AbortWithStatus(http.StatusNoContent)  // Preflight request
            return
        }
        c.Next()
    }
}
```

---

## 7. `handlers/auth.go` — Autenticação

### Structs de Request/Response

```go
type RegisterRequest struct {
    Name     string `json:"name" binding:"required,min=2,max=100"`
    Email    string `json:"email" binding:"required,email"`
    Password string `json:"password" binding:"required,min=6"`
}
```

**Tags `binding`** — O Gin usa essas tags para **validação automática**:
- `required` → campo obrigatório
- `min=2` → mínimo 2 caracteres
- `email` → deve ser email válido

### Register

```go
func (h *Handler) Register(c *gin.Context) {
```

**Conceito: Method Receiver** — `(h *Handler)` faz `Register` ser um **método** do tipo `Handler`. É como se fosse `Handler.Register()`. O `h` dá acesso a `h.db`.

```go
    var req RegisterRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }
```

`c.ShouldBindJSON(&req)` — Lê o body JSON e preenche a struct `req`. O `&` passa o **endereço** (ponteiro) para que a função possa modificar o valor.

```go
    // Verifica se email já existe
    var exists bool
    h.db.QueryRow(`SELECT EXISTS(SELECT 1 FROM users WHERE email = $1)`,
        req.Email).Scan(&exists)

    // Hash da senha com bcrypt
    hash, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)

    // Insere no banco e retorna os dados
    var user models.User
    h.db.QueryRow(`
        INSERT INTO users (name, email, password_hash)
        VALUES ($1, $2, $3)
        RETURNING id, name, email, avatar_url, created_at, updated_at
    `, req.Name, req.Email, string(hash)).Scan(
        &user.ID, &user.Name, &user.Email,
        &user.AvatarURL, &user.CreatedAt, &user.UpdatedAt,
    )

    // Gera tokens JWT
    resp, _ := generateAuthResponse(user)
    c.JSON(http.StatusCreated, resp)
}
```

**Conceito: `$1, $2, $3`** — São **placeholders** do PostgreSQL para prevenir SQL Injection. O Go substitui pelos valores passados como argumentos.

### Geração de JWT

```go
func generateAuthResponse(user models.User) (*AuthResponse, error) {
    expiresIn := 3600 // 1 hora

    accessClaims := middleware.Claims{
        UserID: user.ID,
        Email:  user.Email,
        RegisteredClaims: jwt.RegisteredClaims{
            ExpiresAt: jwt.NewNumericDate(time.Now().Add(
                time.Duration(expiresIn) * time.Second)),
            IssuedAt: jwt.NewNumericDate(time.Now()),
        },
    }

    // Assina o token com HMAC-SHA256
    accessToken, _ := jwt.NewWithClaims(
        jwt.SigningMethodHS256, accessClaims,
    ).SignedString([]byte(secret))

    // Refresh token (30 dias)
    refreshClaims := middleware.Claims{ ... }
    refreshToken, _ := jwt.NewWithClaims(
        jwt.SigningMethodHS256, refreshClaims,
    ).SignedString([]byte(refreshSecret))

    return &AuthResponse{
        AccessToken:  accessToken,
        RefreshToken: refreshToken,
        ExpiresIn:    expiresIn,
        User:         user,
    }, nil
}
```

---

## 8. `handlers/handler.go` — Famílias e Membros

### CreateFamily (com Transação)

```go
func (h *Handler) CreateFamily(c *gin.Context) {
    userID := c.GetString("user_id")  // Pego do middleware JWT

    tx, err := h.db.Begin()   // Inicia transação
    defer tx.Rollback()       // Se der erro, desfaz tudo

    // 1. Insere a família
    tx.QueryRow(`INSERT INTO families ...`)

    // 2. Adiciona o criador como admin
    tx.Exec(`INSERT INTO family_members ... 'admin'`)

    tx.Commit()  // Confirma ambas as operações
}
```

**Conceito: Transações** — `Begin()` inicia uma transação. Se `Commit()` não for chamado, o `defer tx.Rollback()` desfaz tudo. Garante que as duas operações aconteçam juntas.

### InviteMember (Código de Convite)

O fluxo é:
1. Usuário envia o `invite_code`
2. API busca a família pelo código
3. Verifica se já é membro
4. Adiciona como `member`

### GetMembers (Query com JOIN)

```go
rows, err := h.db.Query(`
    SELECT u.id, u.name, u.email, u.avatar_url, ...
    FROM family_members fm
    JOIN users u ON u.id = fm.user_id
    WHERE fm.family_id = $1
`, familyID)
defer rows.Close()  // Sempre fechar o cursor!

var members []models.FamilyMember
for rows.Next() {          // Itera cada linha
    var m models.FamilyMember
    var u models.User
    rows.Scan(&u.ID, &u.Name, ...)  // Preenche as structs
    m.User = &u                      // Ponteiro para o user
    members = append(members, m)     // Adiciona ao slice
}
```

**Conceito: Slices** — `[]models.FamilyMember` é um **slice** (array dinâmico). `append()` adiciona elementos.

### Helpers

```go
func (h *Handler) isFamilyMember(familyID, userID string) bool {
    var exists bool
    h.db.QueryRow(`
        SELECT EXISTS(SELECT 1 FROM family_members
        WHERE family_id = $1 AND user_id = $2)
    `, familyID, userID).Scan(&exists)
    return exists
}

func generateInviteCode() (string, error) {
    b := make([]byte, 6)       // Cria slice de 6 bytes
    _, err := rand.Read(b)     // Preenche com bytes aleatórios
    return hex.EncodeToString(b), err  // Converte para hex (12 chars)
}
```

---

## 9. `handlers/resources.go` — Localização, WiFi, Geofences

### UpdateLocation + Goroutine

```go
func (h *Handler) UpdateLocation(c *gin.Context) {
    // ... salva localização no banco ...

    // Verifica geofences em BACKGROUND (não bloqueia a resposta)
    go h.checkGeofences(body.FamilyID, userID, body.Latitude, body.Longitude)

    c.JSON(http.StatusCreated, loc)
}
```

**Conceito: Goroutines (`go`)** — A palavra-chave `go` executa a função em uma **thread leve** paralela. A resposta HTTP é enviada imediatamente, enquanto a verificação de geofences roda em background.

### GetFamilyLocations (LEFT JOIN LATERAL)

```go
rows, err := h.db.Query(`
    SELECT u.id, u.name, ...
           l.id, l.latitude, l.longitude, ...
    FROM family_members fm
    JOIN users u ON u.id = fm.user_id
    LEFT JOIN LATERAL (
        SELECT * FROM locations WHERE user_id = u.id
        ORDER BY created_at DESC LIMIT 1
    ) l ON TRUE
    WHERE fm.family_id = $1
`, familyID)
```

Essa query busca **cada membro** com sua **última localização**. `LEFT JOIN LATERAL` é como um "for each" no SQL — para cada membro, pega a localização mais recente.

```go
onlineThreshold := time.Now().Add(-5 * time.Minute)
// ...
ml.IsOnline = locCreated.After(onlineThreshold)
// Se a última localização foi há menos de 5 minutos → está online
```

### UpdateWifi + Alerta Automático

```go
func (h *Handler) UpdateWifi(c *gin.Context) {
    // Verifica se a rede é confiável
    var isTrusted bool
    h.db.QueryRow(`SELECT EXISTS(SELECT 1 FROM trusted_networks
        WHERE family_id = $1 AND bssid = $2)
    `, body.FamilyID, body.BSSID).Scan(&isTrusted)

    // UPSERT: insere ou atualiza
    h.db.Exec(`
        INSERT INTO wifi_status (...) VALUES (...)
        ON CONFLICT (user_id, family_id) DO UPDATE SET ...
    `, ...)

    // Se NÃO é confiável → cria alerta em background
    if !isTrusted {
        go h.createAlert(body.FamilyID, userID, "unknown_wifi",
            "Conectado em rede WiFi desconhecida: "+body.SSID)
    }
}
```

### Haversine (Distância entre coordenadas)

```go
func haversineDistance(lat1, lon1, lat2, lon2 float64) float64 {
    const earthRadius = 6371000.0  // Raio da Terra em metros
    // ... cálculo de distância em metros entre dois pontos GPS
}
```

Usada para verificar se alguém **saiu** de uma geofence (zona segura).

---

## 10. Resumo dos Conceitos Go

| Conceito | Onde é usado | Exemplo |
|----------|-------------|---------|
| **Packages** | Todo arquivo | `package main`, `package handlers` |
| **Structs** | models.go | `type User struct { ... }` |
| **Struct Tags** | models.go | `` `json:"id" db:"id"` `` |
| **Ponteiros (`*`)** | models.go | `*string` para campos nullable |
| **Error handling** | Toda parte | `if err != nil { ... }` |
| **`defer`** | main.go, handlers | `defer db.Close()` |
| **Method receivers** | handlers | `func (h *Handler) GetMe(...)` |
| **Goroutines (`go`)** | resources.go | `go h.checkGeofences(...)` |
| **Slices** | handlers | `[]models.FamilyMember` |
| **Blank import (`_`)** | database.go | `_ "github.com/lib/pq"` |
| **Embedding** | middleware.go | `jwt.RegisteredClaims` dentro de Claims |
| **Múltiplos retornos** | database.go | `func Connect() (*sql.DB, error)` |
| **Transações** | handler.go | `tx.Begin()`, `tx.Commit()` |
| **Type assertion** | middleware.go | `t.Method.(*jwt.SigningMethodHMAC)` |
| **`gin.H`** | handlers | `gin.H{"error": "msg"}` (atalho p/ map) |

---

## 11. Fluxo Completo de uma Requisição

```mermaid
sequenceDiagram
    participant App as Flutter App
    participant GIN as Gin Router
    participant CORS as CORS Middleware
    participant JWT as JWT Middleware
    participant H as Handler
    participant DB as PostgreSQL

    App->>GIN: POST /api/location (com Bearer token)
    GIN->>CORS: Adiciona headers CORS
    CORS->>JWT: Valida token JWT
    JWT->>JWT: Extrai user_id do token
    JWT->>H: Chama UpdateLocation()
    H->>DB: INSERT INTO locations
    DB-->>H: Retorna localização salva
    H-->>App: 201 Created + JSON
    H->>H: go checkGeofences() (background)

---

## 12. Detalhando os Recursos (`resources.go`)

Este arquivo é o "coração" do monitoramento. Vamos ver os pontos mais complexos:

### A. O conceito de "Online"
No método `GetFamilyLocations`, não existe um campo "online" no banco. O Go calcula isso em tempo real:
```go
onlineThreshold := time.Now().Add(-5 * time.Minute) // 5 minutos atrás
// ...
ml.IsOnline = locCreated.After(onlineThreshold)
```
*   **Lógica**: Se a última localização enviada pelo celular foi nos últimos 5 minutos, o app mostra o usuário como "Online". Caso contrário, ele é considerado "Offline" ou "Sem sinal".

### B. O UPSERT do WiFi
No método `UpdateWifi`, usamos uma técnica de SQL chamada **UPSERT**:
```go
INSERT INTO wifi_status (...) VALUES (...)
ON CONFLICT (user_id, family_id) DO UPDATE SET ...
```
*   **Por que?** Queremos que cada usuário tenha apenas **um** registro de status de WiFi por família. Se ele já existir, o banco apenas atualiza (UPDATE). Se não existir, ele cria (INSERT). Isso economiza espaço e simplifica a busca.

### C. Geofencing: A Matemática do Haversine
O projeto usa a **Fórmula de Haversine** para calcular a distância entre dois pontos no globo terrestre:
```go
func haversineDistance(lat1, lon1, lat2, lon2 float64) float64 {
    const earthRadius = 6371000.0 // Metros
    // ... cálculos de radianos e senos ...
}
```
*   **Fluxo**: Quando o celular envia uma nova posição (Latitude/Longitude), o Go percorre todas as "Zonas Seguras" (Geofences) cadastradas para aquela família. Se a distância calculada for maior que o `radius` (raio) da zona, um alerta é gerado.

---

## 13. O Esquema do Banco de Dados (SQL)

No arquivo `database/database.go`, definimos como os dados são organizados. Aqui está o porquê de cada tabela:

*   **`users`**: Cadastro base. Note o uso de `UUID` em vez de números sequenciais (1, 2, 3). Isso é mais seguro para APIs.
*   **`families`**: Criada por um dono (`owner_id`). Gera o `invite_code` único.
*   **`family_members`**: Tabela de ligação (Many-to-Many). Um usuário pode estar em várias famílias, e uma família tem vários usuários.
*   **`locations`**: Tabela histórica. **Não deletamos** localizações antigas para poder gerar o gráfico de histórico de trajeto.
*   **`alerts`**: Armazena notificações. Quando o Go detecta algo errado em uma goroutine, ele "cospe" um registro aqui para o Flutter ler.

---

## 14. Dicas de Aprendizado para você

Para dominar Go através deste projeto, foque em:

1.  **Tipagem Forte**: Note que você não pode somar um `int` com um `float64` sem converter. Go é muito rigoroso com isso para evitar bugs.
2.  **Ponteiros (`*`)**: Pratique entender que `user` é o objeto, mas `&user` é o endereço dele. Usamos `*User` nos modelos para que campos possam ser `null` (nil).
3.  **Simplicidade**: Go não tem herança de classes como Java ou C#. Ele usa **Composição** (uma struct dentro da outra) e **Interfaces**.
4.  **Concorrência**: O uso de `go func()` é o que torna o Go famoso. Ele permite processar coisas pesadas (como checar 50 geofences) sem travar a resposta do usuário.

---

## 15. Próximos Passos
Se você quiser ver como o **Flutter** consome essa API, podemos abrir os arquivos na pasta `flutter/lib/core` (como o `api_client.dart` ou `location_service.dart`). Quer que eu explique a conexão do lado do celular agora?
