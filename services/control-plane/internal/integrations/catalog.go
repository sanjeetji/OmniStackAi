package integrations

// Entry is one integration in the catalog, with an honest account of how it is verified.
type Entry struct {
	ID       string `json:"id"`
	Name     string `json:"name"`
	Category string `json:"category"` // email, analytics, payments, ai, hosting, source
	Scope    string `json:"scope"`    // project or account
	// Verification is "live" (the provider confirms the credentials), "format" (only their form
	// can be checked) or "on_use" (no free check; the first real use shows it).
	Verification string   `json:"verification"`
	HowChecked   string   `json:"how_checked"`
	Generates    []string `json:"generates,omitempty"`
	Where        string   `json:"where"` // where in the console it is connected
}

// Catalog is every integration a project or account can connect.
var Catalog = []Entry{
	{ID: "resend", Name: "Resend email", Category: "email", Scope: "project", Verification: "live",
		HowChecked: "Signs in to Resend with the key and checks the sender's domain is verified there. Sends nothing.",
		Generates:  []string{"lib/email.ts", "lib/email-templates.ts", "app/api/send/route.ts", "components/contact-form.tsx"},
		Where:      "Project → Connectors"},
	{ID: "smtp", Name: "Your own mail server (SMTP)", Category: "email", Scope: "project", Verification: "live",
		HowChecked: "Connects to the server, starts encryption and signs in with the username and password. Sends nothing.",
		Generates:  []string{"lib/email.ts", "lib/email-templates.ts", "app/api/send/route.ts", "components/contact-form.tsx"},
		Where:      "Project → Connectors"},
	{ID: "ga4", Name: "Google Analytics 4", Category: "analytics", Scope: "project", Verification: "format",
		HowChecked: "Checks the Measurement ID's form. Google cannot confirm it without your Google account; Realtime in Analytics shows the first visit.",
		Generates:  []string{"components/GoogleAnalytics.tsx", "app/layout.tsx (tag added)"},
		Where:      "Project → Connectors"},
	{ID: "stripe", Name: "Stripe payments", Category: "payments", Scope: "project", Verification: "live",
		HowChecked: "Reads the account balance with the secret key (nothing is charged) and checks the keys are all test or all live.",
		Generates:  []string{"lib/payments/stripe.ts", "app/api/checkout/route.ts", "app/api/webhooks/stripe/route.ts", "app/checkout/success|cancel"},
		Where:      "Project → Payments"},
	{ID: "razorpay", Name: "Razorpay payments", Category: "payments", Scope: "project", Verification: "live",
		HowChecked: "Lists one payment with the key pair (nothing is charged).",
		Generates:  []string{"lib/payments/razorpay.ts", "app/api/checkout/route.ts", "app/api/webhooks/razorpay/route.ts", "app/checkout/success|cancel"},
		Where:      "Project → Payments"},
	{ID: "ai:openai", Name: "OpenAI key", Category: "ai", Scope: "account", Verification: "live", HowChecked: "Lists models with the key. No model is run.", Where: "Settings → BYOK keys"},
	{ID: "ai:anthropic", Name: "Anthropic key", Category: "ai", Scope: "account", Verification: "live", HowChecked: "Lists models with the key. No model is run.", Where: "Settings → BYOK keys"},
	{ID: "ai:google-gemini", Name: "Google Gemini key", Category: "ai", Scope: "account", Verification: "live", HowChecked: "Lists models with the key. No model is run.", Where: "Settings → BYOK keys"},
	{ID: "ai:groq", Name: "Groq key", Category: "ai", Scope: "account", Verification: "live", HowChecked: "Lists models with the key. No model is run.", Where: "Settings → BYOK keys"},
	{ID: "ai:openrouter", Name: "OpenRouter key", Category: "ai", Scope: "account", Verification: "live", HowChecked: "Reads the key's own limits. No model is run.", Where: "Settings → BYOK keys"},
	{ID: "ai:deepseek", Name: "DeepSeek key", Category: "ai", Scope: "account", Verification: "live", HowChecked: "Reads the account balance. No model is run.", Where: "Settings → BYOK keys"},
	{ID: "ai:mistral", Name: "Mistral key", Category: "ai", Scope: "account", Verification: "live", HowChecked: "Lists models with the key. No model is run.", Where: "Settings → BYOK keys"},
	{ID: "ai:nvidia", Name: "NVIDIA key", Category: "ai", Scope: "account", Verification: "on_use",
		HowChecked: "NVIDIA has no free way to check a key; the first build that uses it shows whether it works.", Where: "Settings → BYOK keys"},
	{ID: "vercel", Name: "Vercel hosting", Category: "hosting", Scope: "account", Verification: "live", HowChecked: "Reads your Vercel user with the token when it is saved.", Where: "Settings → Hosting"},
	{ID: "netlify", Name: "Netlify hosting", Category: "hosting", Scope: "account", Verification: "live", HowChecked: "Reads your Netlify user with the token when it is saved.", Where: "Settings → Hosting"},
	{ID: "domain", Name: "Custom domain", Category: "hosting", Scope: "project", Verification: "live", HowChecked: "Looks up the domain's DNS record and asks the host to confirm it.", Where: "Project → Domains"},
	{ID: "github", Name: "GitHub", Category: "source", Scope: "account", Verification: "live", HowChecked: "GitHub confirms the app installation when you connect.", Where: "Project → Git"},
}

// envFields maps an integration's settings to the project secrets (environment variables) that
// hold them; the generated app reads the same names.
var envFields = map[string]map[string]string{
	"resend":   {"api_key": "RESEND_API_KEY", "from_email": "RESEND_FROM_EMAIL"},
	"smtp":     {"host": "SMTP_HOST", "port": "SMTP_PORT", "username": "SMTP_USER", "password": "SMTP_PASS", "from_email": "SMTP_FROM"},
	"stripe":   {"secret_key": "STRIPE_SECRET_KEY", "publishable_key": "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY", "webhook_secret": "STRIPE_WEBHOOK_SECRET"},
	"razorpay": {"key_id": "RAZORPAY_KEY_ID", "key_secret": "RAZORPAY_KEY_SECRET", "webhook_secret": "RAZORPAY_WEBHOOK_SECRET"},
}

// EnvFields returns the setting → environment variable map for an integration (nil if its
// settings are not secrets).
func EnvFields(integration string) map[string]string { return envFields[integration] }

// SettingsFromSecrets reads an integration's settings out of a project's secrets.
func SettingsFromSecrets(integration string, secrets map[string]string) map[string]string {
	out := map[string]string{}
	for field, env := range envFields[integration] {
		if v, ok := secrets[env]; ok {
			out[field] = v
		}
	}
	return out
}
