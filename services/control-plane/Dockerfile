FROM golang:1.27.1-alpine3.24 AS build

WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY cmd ./cmd
COPY internal ./internal
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/control-plane ./cmd/control-plane

FROM alpine:3.24.1

RUN addgroup -S omnistackai && adduser -S -G omnistackai omnistackai
COPY --from=build /out/control-plane /usr/local/bin/control-plane
USER omnistackai
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/control-plane"]
