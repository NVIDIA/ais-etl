FROM docker.io/library/golang:1.24-alpine AS builder

RUN apk add --no-cache git gcc musl-dev

WORKDIR /app

COPY src/go.mod src/go.sum ./
RUN go mod download

COPY src/ ./
RUN go build -o parquet-parser

FROM alpine:3.19

RUN apk add --no-cache libc6-compat libstdc++ libgcc strace procps htop

WORKDIR /app
COPY --from=builder /app/parquet-parser .

EXPOSE 8000
ENTRYPOINT ["./parquet-parser", "-l", "0.0.0.0", "-p", "8000"] 