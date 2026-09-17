package auth

import "testing"

func TestGenerateTokenReturnsDistinctUnpredictableTokens(t *testing.T) {
	firstRaw, firstHash, err := generateToken()
	if err != nil {
		t.Fatalf("generateToken() error = %v", err)
	}
	secondRaw, secondHash, err := generateToken()
	if err != nil {
		t.Fatalf("generateToken() error = %v", err)
	}

	if firstRaw == secondRaw {
		t.Fatal("generateToken() returned the same raw token twice")
	}
	if firstHash == secondHash {
		t.Fatal("generateToken() returned the same hash twice")
	}
	if firstRaw == firstHash {
		t.Fatal("generateToken() hash must differ from the raw token")
	}
}

func TestHashTokenIsDeterministicAndDoesNotReturnTheRawToken(t *testing.T) {
	raw, hash, err := generateToken()
	if err != nil {
		t.Fatalf("generateToken() error = %v", err)
	}

	if hashToken(raw) != hash {
		t.Fatal("hashToken(raw) does not match the hash generateToken() returned for the same raw value")
	}
	if hashToken(raw) == raw {
		t.Fatal("hashToken(raw) must not equal raw")
	}
}
