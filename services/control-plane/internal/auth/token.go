package auth

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"fmt"
)

const tokenBytes = 32

// generateToken returns a new opaque bearer token (raw, to hand to the caller exactly once) and
// its SHA-256 hash (the only form ever persisted). Storing only the hash means a database
// compromise does not hand out usable session tokens, mirroring how this project already treats
// model-provider API keys as capabilities that must never be stored or logged raw.
func generateToken() (raw string, hash string, err error) {
	buf := make([]byte, tokenBytes)
	if _, err := rand.Read(buf); err != nil {
		return "", "", fmt.Errorf("auth: generate token: %w", err)
	}
	raw = base64.RawURLEncoding.EncodeToString(buf)
	return raw, hashToken(raw), nil
}

func hashToken(raw string) string {
	sum := sha256.Sum256([]byte(raw))
	return hex.EncodeToString(sum[:])
}
