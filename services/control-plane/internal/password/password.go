// Package password hashes and verifies user passwords using PBKDF2-HMAC-SHA256 (RFC 8018),
// implemented directly on the Go standard library (crypto/hmac, crypto/sha256, crypto/subtle).
// This repository keeps dependencies minimal by convention (the agent-engine is Python-stdlib
// only; the control-plane has exactly one direct dependency, pgx, added out of necessity because
// there is no standard-library Postgres driver) — golang.org/x/crypto/bcrypt was considered and
// rejected for that reason, not because it is insecure.
package password

import (
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"crypto/subtle"
	"encoding/base64"
	"encoding/binary"
	"errors"
	"fmt"
	"strconv"
	"strings"
)

const (
	algorithmName     = "pbkdf2-sha256"
	defaultIterations = 210_000 // OWASP 2023 minimum recommendation for PBKDF2-HMAC-SHA256.
	saltLength        = 16
	keyLength         = 32
)

// ErrMalformedHash is returned by Verify when encoded is not a hash this package produced.
var ErrMalformedHash = errors.New("password: malformed hash")

// Hash derives a salted PBKDF2-HMAC-SHA256 hash of plain and encodes it, together with the
// algorithm parameters used, into a single self-describing string safe to store in a database
// column. Calling Hash twice for the same password returns different strings (independent random
// salts); both verify successfully against plain.
func Hash(plain string) (string, error) {
	return hashWithIterations(plain, defaultIterations)
}

// Verify reports whether plain matches the previously produced encoded hash, comparing the
// derived keys in constant time.
func Verify(encoded, plain string) (bool, error) {
	iterations, salt, expected, err := parse(encoded)
	if err != nil {
		return false, err
	}
	actual := deriveKey([]byte(plain), salt, iterations, len(expected))
	return subtle.ConstantTimeCompare(actual, expected) == 1, nil
}

func hashWithIterations(plain string, iterations int) (string, error) {
	salt := make([]byte, saltLength)
	if _, err := rand.Read(salt); err != nil {
		return "", fmt.Errorf("password: generate salt: %w", err)
	}
	derived := deriveKey([]byte(plain), salt, iterations, keyLength)
	return fmt.Sprintf(
		"%s$%d$%s$%s",
		algorithmName,
		iterations,
		base64.RawStdEncoding.EncodeToString(salt),
		base64.RawStdEncoding.EncodeToString(derived),
	), nil
}

func parse(encoded string) (iterations int, salt, key []byte, err error) {
	parts := strings.Split(encoded, "$")
	if len(parts) != 4 || parts[0] != algorithmName {
		return 0, nil, nil, ErrMalformedHash
	}
	iterations, err = strconv.Atoi(parts[1])
	if err != nil || iterations <= 0 {
		return 0, nil, nil, ErrMalformedHash
	}
	salt, err = base64.RawStdEncoding.DecodeString(parts[2])
	if err != nil {
		return 0, nil, nil, ErrMalformedHash
	}
	key, err = base64.RawStdEncoding.DecodeString(parts[3])
	if err != nil {
		return 0, nil, nil, ErrMalformedHash
	}
	return iterations, salt, key, nil
}

// deriveKey implements the PBKDF2 key-derivation function (RFC 8018 section 5.2) using
// HMAC-SHA256 as the pseudorandom function.
func deriveKey(password, salt []byte, iterations, keyLen int) []byte {
	hashSize := sha256.Size
	blockCount := (keyLen + hashSize - 1) / hashSize
	derived := make([]byte, 0, blockCount*hashSize)
	for block := uint32(1); block <= uint32(blockCount); block++ {
		derived = append(derived, deriveBlock(password, salt, iterations, block)...)
	}
	return derived[:keyLen]
}

func deriveBlock(password, salt []byte, iterations int, block uint32) []byte {
	mac := hmac.New(sha256.New, password)
	blockIndex := make([]byte, 4)
	binary.BigEndian.PutUint32(blockIndex, block)
	mac.Write(salt)
	mac.Write(blockIndex)

	u := mac.Sum(nil)
	result := append([]byte(nil), u...)
	for i := 1; i < iterations; i++ {
		mac.Reset()
		mac.Write(u)
		u = mac.Sum(nil)
		for j := range result {
			result[j] ^= u[j]
		}
	}
	return result
}
