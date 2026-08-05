# MyFamilySafe Flutter — Guia Passo a Passo 📱

Este guia explica como o aplicativo mobile foi construído para se conectar à API Go e fornecer monitoramento em tempo real.

---

## 1. Estrutura do Projeto

O projeto segue um padrão de separação de responsabilidades:

```
lib/
├── main.dart                 # Ponto de entrada, login e navegação inicial
├── core/                     # O "cérebro" do app (conexão e sensores)
│   ├── api_client.dart       # Cliente HTTP (Dio) e Repositórios
│   ├── location_service.dart # GPS e rastreamento
│   └── wifi_service.dart     # Monitoramento de rede WiFi
└── screens/                  # Telas da interface (UI)
    └── dashboard_page.dart   # Mapa e status da família
```

---

## 2. `api_client.dart` — A Ponte com a API

O Flutter usa a biblioteca **Dio** para conversar com o Go. O segredo aqui é o uso de **Interceptadores**.

### Gerenciamento Automático de JWT
```dart
_dio.interceptors.add(InterceptorsWrapper(
  onRequest: _onRequest, // Adiciona o Token em cada chamada
  onError: _onError,     // Se o token expirar, tenta dar "Refresh"
));
```

**Como funciona o Refresh:**
1. O app tenta acessar a API com o `access_token`.
2. Se a API Go retornar `401 Unauthorized` (token expirou), o Interceptador intercepta o erro.
3. Ele chama automaticamente `/auth/refresh` usando o `refresh_token`.
4. Se conseguir um novo token, ele salva no celular e **repete** a chamada original sem o usuário perceber nada.

### Repositórios (Pattern)
Em vez de fazer chamadas espalhadas pelo app, usamos classes separadas:
- `AuthRepository`: Login e Registro.
- `LocationRepository`: Envia e busca localizações.
- `WifiRepository`: Atualiza status do WiFi.

---

## 3. `location_service.dart` — Rastreamento GPS

Este serviço transforma o celular em um rastreador.

```dart
_subscription = Geolocator.getPositionStream(
  locationSettings: locationSettings,
).listen((position) async {
  // 1. Pega Latitude e Longitude
  // 2. Converte coordenadas em Endereço (Geocoding)
  // 3. Envia para a API Go
});
```

**Conceitos Flutter:**
- **Stream**: É um fluxo constante de dados (o GPS mandando posições).
- **Listen**: O app "escuta" esse fluxo e executa uma ação toda vez que a posição muda.
- **Foreground Notification**: No Android, para o rastreamento não parar quando o app fecha, criamos uma notificação fixa.

---

## 4. `dashboard_page.dart` — A Interface (UI)

É a tela principal que você vê. Ela usa o widget `FlutterMap` para mostrar os familiares.

### Ciclo de Vida e Timer
```dart
@override
void initState() {
  _loadAll(); // Carrega os dados assim que abre
  _refreshTimer = Timer.periodic(const Duration(seconds: 30), (_) => _loadAll());
}
```
O `Timer.periodic` faz o app "pollear" (pedir novos dados) para a API a cada 30 segundos, mantendo o mapa sempre atualizado.

### Componentes de UI (Design)
- **Stats Cards**: Mostra quantos estão online e quantos alertas existem.
- **Markers**: Ícones personalizados no mapa com a foto/nome do familiar.
- **Timeago**: Transforma datas como `2024-05-01 10:00` em "há 5 minutos".

---

## 5. Conceitos Fundamentais de Dart/Flutter

Se você está vindo do Go, estas são as diferenças principais:

| Conceito | O que é? | Equivalente em Go |
|----------|----------|-------------------|
| **Future** | Uma tarefa que vai terminar depois | `chan` (canal) ou Goroutine |
| **async / await** | Espera uma tarefa terminar | Bloqueio de canal/wait group |
| **Widget** | Tudo na tela é um Widget | Structs de UI |
| **StatefulWidget** | Tela que pode mudar de visual | — |
| **Dio** | Cliente HTTP potente | `http.Client` |

---

## 6. Fluxo de Execução do App

1. **`main.dart`**: Verifica se existe um token salvo no `SecureStorage`.
   - Se SIM → Abre o `Dashboard`.
   - Se NÃO → Abre a `LoginPage`.
2. **Login**: O usuário digita dados -> `AuthRepository` envia para o Go -> Recebe e salva Tokens -> Abre `Dashboard`.
3. **Dashboard**: Inicia o `LocationService` (GPS) e o `WifiService`.
4. **Fundo**: O GPS envia a posição -> A API Go recebe -> API Go checa Geofences -> Se houver erro, a API cria um alerta.
5. **Dashboard**: Na próxima atualização de 30s, o app lê os alertas e mostra na tela.

---

## 7. Como Testar

1. **API**: Certifique-se que o servidor Go está rodando em `localhost:8080`.
2. **Emulador Android**: No `api_client.dart`, usamos o IP `10.0.2.2` porque, para o emulador, `localhost` é o próprio celular, não o seu computador.
3. **Permissões**: O app vai pedir permissão de "Localização o tempo todo" para o rastreamento funcionar.

---

Este projeto é um excelente exemplo de **Full Stack moderno**: Go para alta performance no backend e Flutter para uma UI fluida e nativa no mobile! 🚀
