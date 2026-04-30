# MyFamilySafe 🛡️

App Flutter + API Go para monitoramento familiar com localização em tempo real, status de WiFi e alertas de geofencing.

## Stack
| Camada | Tecnologia |
|--------|-----------|
| App mobile | Flutter (Android) |
| API backend | Go + Gin |
| Banco de dados | PostgreSQL via Supabase |
| Autenticação | JWT (access + refresh token) |
| Mapa | OpenStreetMap via flutter_map |

## Estrutura
```
myfamilysafe/
├── api/
│   ├── main.go
│   ├── go.mod
│   ├── .env.example
│   └── internal/
│       ├── models/models.go
│       ├── database/database.go
│       ├── middleware/middleware.go
│       └── handlers/
│           ├── handler.go
│           ├── auth.go
│           └── resources.go
└── flutter/
    ├── pubspec.yaml
    └── lib/
        ├── main.dart
        ├── core/
        │   ├── api_client.dart
        │   ├── location_service.dart
        │   └── wifi_service.dart
        └── screens/
            └── dashboard_page.dart
```

## Como rodar a API
```bash
cd api
cp .env.example .env  # configure com suas credenciais Supabase
go mod tidy
go run main.go        # http://localhost:8080
```

## Como rodar o Flutter
```bash
cd flutter
flutter pub get
flutter run
```

## Permissões Android necessárias (AndroidManifest.xml)
```xml
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_BACKGROUND_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_WIFI_STATE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
```
