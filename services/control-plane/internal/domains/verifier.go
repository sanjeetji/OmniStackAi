package domains

import (
	"context"
	"errors"
	"net"
	"regexp"
	"strings"
	"time"
)

var (
	ErrInvalidHostname  = errors.New("domains: invalid hostname format (must follow RFC 1123)")
	ErrIPNotAllowed     = errors.New("domains: IP addresses cannot be used as custom domains")
	ErrSuffixOnly       = errors.New("domains: public suffix cannot be used as domain")
	ErrReservedHostname = errors.New("domains: platform and localhost domains cannot be used")
)

var (
	// RFC 1123 hostname regex
	hostnameRegex = regexp.MustCompile(`^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$`)

	reservedDomains = map[string]bool{
		"omnistackai.com": true,
		"omnistack.ai":    true,
		"localhost":       true,
		"example.com":     true,
	}

	// Common top-level or two-part public suffixes
	commonSuffixes = map[string]bool{
		"com": true, "org": true, "net": true, "edu": true, "gov": true,
		"io": true, "ai": true, "app": true, "dev": true, "co": true,
		"co.uk": true, "org.uk": true, "ac.uk": true,
		"com.au": true, "net.au": true, "org.au": true,
		"co.in": true, "net.in": true, "org.in": true,
	}
)

type DNSVerifier interface {
	LookupCNAME(ctx context.Context, host string) (string, error)
	LookupIP(ctx context.Context, network, host string) ([]net.IP, error)
}

type defaultDNSVerifier struct{}

func (d defaultDNSVerifier) LookupCNAME(ctx context.Context, host string) (string, error) {
	return net.DefaultResolver.LookupCNAME(ctx, host)
}

func (d defaultDNSVerifier) LookupIP(ctx context.Context, network, host string) ([]net.IP, error) {
	return net.DefaultResolver.LookupIP(ctx, network, host)
}

// CleanAndValidateHostname checks RFC 1123, public suffixes, and reserved domains.
func CleanAndValidateHostname(raw string) (string, error) {
	h := strings.ToLower(strings.TrimSpace(raw))
	h = strings.TrimSuffix(h, ".")

	if h == "" {
		return "", ErrInvalidHostname
	}

	// Check if IP address
	if net.ParseIP(h) != nil {
		return "", ErrIPNotAllowed
	}

	// Reject localhost and reserved domains
	if reservedDomains[h] || strings.HasSuffix(h, ".omnistackai.com") || strings.HasSuffix(h, ".omnistack.ai") || strings.HasSuffix(h, ".localhost") {
		return "", ErrReservedHostname
	}

	// Reject if raw suffix
	if commonSuffixes[h] {
		return "", ErrSuffixOnly
	}

	if !hostnameRegex.MatchString(h) {
		return "", ErrInvalidHostname
	}

	// Ensure at least one dot
	parts := strings.Split(h, ".")
	if len(parts) < 2 {
		return "", ErrInvalidHostname
	}

	return h, nil
}

// IsApexDomain returns true if the domain is an apex domain (e.g., example.com or example.co.uk)
func IsApexDomain(hostname string) bool {
	parts := strings.Split(hostname, ".")
	if len(parts) == 2 {
		return true
	}
	if len(parts) == 3 {
		twoPartSuffix := parts[1] + "." + parts[2]
		if commonSuffixes[twoPartSuffix] {
			return true
		}
	}
	return false
}

// CalculateExpectedRecord determines the record type, name, and default value.
func CalculateExpectedRecord(hostname, provider, providerSiteTarget string) (recordType, recordName, recordValue string) {
	isApex := IsApexDomain(hostname)

	switch strings.ToLower(provider) {
	case "netlify":
		if isApex {
			return "A", "@", "75.2.60.5"
		}
		parts := strings.Split(hostname, ".")
		sub := parts[0]
		target := providerSiteTarget
		if target == "" {
			target = "apex.netlify.app"
		}
		return "CNAME", sub, target

	default: // vercel
		if isApex {
			return "A", "@", "76.76.21.21"
		}
		parts := strings.Split(hostname, ".")
		sub := parts[0]
		return "CNAME", sub, "cname.vercel-dns.com"
	}
}

// VerifyDNS checks whether the hostname resolves according to expected record type and value.
func VerifyDNS(ctx context.Context, verifier DNSVerifier, hostname, recordType, expectedValue string) (resolved bool, details string) {
	if verifier == nil {
		verifier = defaultDNSVerifier{}
	}

	ctxTimeout, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	if strings.EqualFold(recordType, "CNAME") {
		cname, err := verifier.LookupCNAME(ctxTimeout, hostname)
		if err == nil {
			cnameTrimmed := strings.TrimSuffix(strings.ToLower(cname), ".")
			expectedTrimmed := strings.TrimSuffix(strings.ToLower(expectedValue), ".")
			if cnameTrimmed == expectedTrimmed || strings.Contains(cnameTrimmed, expectedTrimmed) {
				return true, "CNAME resolves to " + cnameTrimmed
			}
		}
		// Also check if CNAME host resolves to any valid IP
		if ips, err := verifier.LookupIP(ctxTimeout, "ip4", hostname); err == nil && len(ips) > 0 {
			return true, "Resolved to IP: " + ips[0].String()
		}
		return false, "CNAME not yet resolving to " + expectedValue
	}

	// A record check
	ips, err := verifier.LookupIP(ctxTimeout, "ip4", hostname)
	if err != nil || len(ips) == 0 {
		return false, "DNS A record not resolving"
	}
	for _, ip := range ips {
		if ip.String() == expectedValue {
			return true, "A record resolves to " + expectedValue
		}
	}
	return false, "A record resolves to " + ips[0].String() + ", expected " + expectedValue
}
