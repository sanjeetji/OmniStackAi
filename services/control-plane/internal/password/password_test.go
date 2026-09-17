package password

import (
	"strings"
	"testing"
)

// testIterations keeps most of these tests fast: they exercise the exact same code path as the
// real Hash/Verify, just with a lower, deterministic-for-testing iteration count. Exactly one
// test below (TestHashUsesTheRealDefaultIterationCount) calls the public Hash/Verify with the
// real production iteration count, so the actual default is verified at least once.
const testIterations = 1000

func TestHashAndVerifyRoundTrip(t *testing.T) {
	encoded, err := hashWithIterations("correct horse battery staple", testIterations)
	if err != nil {
		t.Fatalf("hashWithIterations() error = %v", err)
	}

	ok, err := Verify(encoded, "correct horse battery staple")
	if err != nil {
		t.Fatalf("Verify() error = %v", err)
	}
	if !ok {
		t.Fatal("Verify() = false, want true for the correct password")
	}
}

func TestVerifyRejectsWrongPassword(t *testing.T) {
	encoded, err := hashWithIterations("correct horse battery staple", testIterations)
	if err != nil {
		t.Fatalf("hashWithIterations() error = %v", err)
	}

	ok, err := Verify(encoded, "wrong password")
	if err != nil {
		t.Fatalf("Verify() error = %v", err)
	}
	if ok {
		t.Fatal("Verify() = true, want false for an incorrect password")
	}
}

func TestHashProducesDifferentSaltsEachCall(t *testing.T) {
	first, err := hashWithIterations("same password", testIterations)
	if err != nil {
		t.Fatalf("hashWithIterations() error = %v", err)
	}
	second, err := hashWithIterations("same password", testIterations)
	if err != nil {
		t.Fatalf("hashWithIterations() error = %v", err)
	}

	if first == second {
		t.Fatal("hashWithIterations() returned identical output for two independent calls")
	}

	for _, encoded := range []string{first, second} {
		ok, err := Verify(encoded, "same password")
		if err != nil || !ok {
			t.Fatalf("Verify(%q) = %v, %v, want true, nil", encoded, ok, err)
		}
	}
}

func TestHashEncodingFormat(t *testing.T) {
	encoded, err := hashWithIterations("plain", testIterations)
	if err != nil {
		t.Fatalf("hashWithIterations() error = %v", err)
	}

	parts := strings.Split(encoded, "$")
	if len(parts) != 4 {
		t.Fatalf("encoded hash has %d parts, want 4: %q", len(parts), encoded)
	}
	if parts[0] != algorithmName {
		t.Fatalf("algorithm = %q, want %q", parts[0], algorithmName)
	}
	if parts[1] != "1000" {
		t.Fatalf("iterations = %q, want \"1000\"", parts[1])
	}
}

func TestVerifyRejectsMalformedHash(t *testing.T) {
	cases := []string{
		"",
		"not-a-hash-at-all",
		"pbkdf2-sha256$not-a-number$c2FsdA$a2V5",
		"pbkdf2-sha256$1000$not-base64!!$a2V5",
		"unknown-algorithm$1000$c2FsdA$a2V5",
		"pbkdf2-sha256$1000$c2FsdA", // missing a field
	}
	for _, encoded := range cases {
		t.Run(encoded, func(t *testing.T) {
			ok, err := Verify(encoded, "anything")
			if err == nil {
				t.Fatalf("Verify(%q) error = nil, want an error", encoded)
			}
			if ok {
				t.Fatalf("Verify(%q) = true, want false", encoded)
			}
		})
	}
}

func TestHashAndVerifySupportUnicodeAndEmptyPasswords(t *testing.T) {
	for _, plain := range []string{"", "pässwörd-émoji-🔒", strings.Repeat("x", 200)} {
		encoded, err := hashWithIterations(plain, testIterations)
		if err != nil {
			t.Fatalf("hashWithIterations(%q) error = %v", plain, err)
		}
		ok, err := Verify(encoded, plain)
		if err != nil || !ok {
			t.Fatalf("Verify(%q) = %v, %v, want true, nil", plain, ok, err)
		}
	}
}

func TestHashUsesTheRealDefaultIterationCount(t *testing.T) {
	encoded, err := Hash("a real production password")
	if err != nil {
		t.Fatalf("Hash() error = %v", err)
	}
	parts := strings.Split(encoded, "$")
	if len(parts) != 4 || parts[1] != "210000" {
		t.Fatalf("Hash() iterations = %q, want \"210000\"", parts[1])
	}
	ok, err := Verify(encoded, "a real production password")
	if err != nil || !ok {
		t.Fatalf("Verify() = %v, %v, want true, nil", ok, err)
	}
}
