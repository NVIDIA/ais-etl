# Stage 1: Build the binary
FROM golang:1.24-alpine AS builder

RUN apk add --no-cache git

WORKDIR /app

COPY src/go.mod src/go.sum ./
RUN go mod download

COPY src/ ./
RUN go build -o echo

# Stage 2: Minimal runtime image
FROM alpine:3.19

WORKDIR /app
COPY --from=builder /app/echo .

EXPOSE 80
CMD ["./echo"]
