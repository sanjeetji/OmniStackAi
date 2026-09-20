package crypto

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"errors"
	"fmt"
	"io"
)

var (
	// ErrInvalidKey is returned when the encryption key is not 32 bytes (256 bits).
	ErrInvalidKey = errors.New("crypto: encryption key must be exactly 32 bytes for AES-256")
	// ErrCiphertextTooShort is returned when ciphertext is shorter than the GCM nonce size.
	ErrCiphertextTooShort = errors.New("crypto: ciphertext too short")
	// ErrDecryptionFailed is returned when authentication tag validation fails.
	ErrDecryptionFailed = errors.New("crypto: decryption failed")
)

// Encrypt encrypts plaintext using AES-256-GCM with additional authenticated data (AAD).
// It returns a blob containing the 12-byte nonce followed by the ciphertext and authentication tag.
func Encrypt(key []byte, plaintext []byte, aad []byte) ([]byte, error) {
	if len(key) != 32 {
		return nil, ErrInvalidKey
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, fmt.Errorf("crypto: new cipher: %w", err)
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, fmt.Errorf("crypto: new gcm: %w", err)
	}

	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return nil, fmt.Errorf("crypto: generate nonce: %w", err)
	}

	// Seal appends ciphertext and tag onto the destination slice (initialized with nonce).
	return gcm.Seal(nonce, nonce, plaintext, aad), nil
}

// Decrypt decrypts a blob produced by Encrypt using AES-256-GCM and verifies the AAD.
func Decrypt(key []byte, blob []byte, aad []byte) ([]byte, error) {
	if len(key) != 32 {
		return nil, ErrInvalidKey
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, fmt.Errorf("crypto: new cipher: %w", err)
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, fmt.Errorf("crypto: new gcm: %w", err)
	}

	nonceSize := gcm.NonceSize()
	if len(blob) < nonceSize {
		return nil, ErrCiphertextTooShort
	}

	nonce, ciphertext := blob[:nonceSize], blob[nonceSize:]
	plaintext, err := gcm.Open(nil, nonce, ciphertext, aad)
	if err != nil {
		return nil, ErrDecryptionFailed
	}

	return plaintext, nil
}
