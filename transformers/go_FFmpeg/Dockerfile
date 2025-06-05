# Stage 1: Build the binary
FROM docker.io/library/golang:1.24-alpine AS builder

RUN apk add --no-cache git

WORKDIR /app

COPY src/go.mod src/go.sum ./
RUN go mod download

COPY src/ ./
RUN go build -o go_ffmpeg

# Stage 2: Minimal runtime image
FROM alpine:3.19

# Install ffmpeg
RUN apk add --no-cache ffmpeg

WORKDIR /app
COPY --from=builder /app/go_ffmpeg .

EXPOSE 8000

ENTRYPOINT ["./go_ffmpeg", "-l", "0.0.0.0", "-p", "8000"]