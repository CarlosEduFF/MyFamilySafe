# Build stage
FROM golang:1.22-alpine AS builder

WORKDIR /app

# Copy dependency files
COPY go.mod ./
# Note: go.sum will be copied if it exists, otherwise this will skip it
COPY go.sum* ./
RUN go mod download

# Copy the source code
COPY . .

# Build the application
# We use -ldflags="-s -w" to reduce binary size
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o server main.go

# Final stage
FROM alpine:latest

# Add certificates for HTTPS requests (e.g. to Supabase)
RUN apk --no-cache add ca-certificates tzdata

WORKDIR /root/

# Copy the binary from the builder stage
COPY --from=builder /app/server .

# Expose the default port
EXPOSE 8080

# Environment variables with defaults
ENV PORT=8080
ENV GIN_MODE=release

# Start the application
CMD ["./server"]
