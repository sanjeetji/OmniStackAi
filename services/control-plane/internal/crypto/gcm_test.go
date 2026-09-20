package crypto

import (
	"bytes"
	"crypto/rand"
	"testing"
)

func TestEncryptDecrypt_Roundtrip(t *testing.T) {
	key := make([]byte, 32)
	if _, err := rand.Read(key); err != nil {
		t.Fatalf("rand.Read key: %v", err)
	}

	plaintext := []byte("ghp_secret_access_token_1234567890")
	aad := []byte("user-123-github")

	blob, err := Encrypt(key, plaintext, aad)
	if err != nil {
		t.Fatalf("Encrypt failed: %v", err)
	}

	if len(blob) <= len(plaintext) {
		t.Fatalf("blob length %d should be greater than plaintext length %d (nonce + tag)", len(blob), len(plaintext))
	}

	decrypted, err := Decrypt(key, blob, aad)
	if err != nil {
		t.Fatalf("Decrypt failed: %v", err)
	}

	if !bytes.Equal(plaintext, decrypted) {
		t.Fatalf("got %q, want %q", string(decrypted), string(plaintext))
	}
}

func TestEncryptDecrypt_InvalidKey(t *testing.T) {
	shortKey := make([]byte, 16)
	_, err := Encrypt(shortKey, []byte("hello"), nil)
	if err != ErrInvalidKey {
		t.Fatalf("expected ErrInvalidKey, got %v", err)
	}

	_, err = Decrypt(shortKey, []byte("someblobthatislongerthan12bytes"), nil)
	if err != ErrInvalidKey {
		t.Fatalf("expected ErrInvalidKey, got %v", err)
	}
}

func TestEncryptDecrypt_WrongAAD(t *testing.T) {
	key := make([]byte, 32)
	blob, err := Encrypt(key, []byte("secret"), []byte("correct-aad"))
	if err != nil {
		t.Fatalf("Encrypt: %v", err)
	}

	_, err = Decrypt(key, blob, []byte("wrong-aad"))
	if err != ErrDecryptionFailed {
		t.Fatalf("expected ErrDecryptionFailed on wrong AAD, got %v", err)
	}
}

func TestDecrypt_TamperedCiphertext(t *testing.T) {
	key := make([]byte, 32)
	blob, err := Encrypt(key, []byte("secret"), []byte("aad"))
	if err != nil {
		t.Fatalf("Encrypt: %v", err)
	}

	// Tamper with last byte
	blob[len(blob)-1] ^= 0x01

	_, err = Decrypt(key, blob, []byte("aad"))
	if err != ErrDecryptionFailed {
		t.Fatalf("expected ErrDecryptionFailed on tampered ciphertext, got %v", err)
	}
}

func TestDecrypt_TooShort(t *testing.T) {
	key := make([]byte, 32)
	_, err := Decrypt(key, []byte("short"), nil)
	if err != ErrCiphertextTooShort {
		t.Fatalf("expected ErrCiphertextTooShort, got %v", err)
	}
}
