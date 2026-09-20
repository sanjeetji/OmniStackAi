package connectors

type ConnectorCategory string

const (
	CategoryAnalytics     ConnectorCategory = "analytics"
	CategoryCommunication ConnectorCategory = "communication"
	CategoryProductivity  ConnectorCategory = "productivity"
)

type ConfigField struct {
	Key         string `json:"key"`
	Label       string `json:"label"`
	Type        string `json:"type"` // "text", "password", "number"
	Required    bool   `json:"required"`
	Placeholder string `json:"placeholder"`
	HelpText    string `json:"help_text"`
}

type ConnectorDefinition struct {
	ID          string            `json:"id"`
	Name        string            `json:"name"`
	Description string            `json:"description"`
	Category    ConnectorCategory `json:"category"`
	AuthType    string            `json:"auth_type"` // "none", "api_key", "oauth2"
	Icon        string            `json:"icon"`
	DocsURL     string            `json:"docs_url"`
	Fields      []ConfigField     `json:"fields"`
	Generated   []string          `json:"generated"`
}

var Catalog = []ConnectorDefinition{
	{
		ID:          "ga4",
		Name:        "Google Analytics 4",
		Description: "Track visitor traffic, screen views, and conversion events directly in Google Analytics.",
		Category:    CategoryAnalytics,
		AuthType:    "none",
		Icon:        "google-analytics",
		DocsURL:     "https://support.google.com/analytics/answer/9539598",
		Fields: []ConfigField{
			{
				Key:         "measurement_id",
				Label:       "Measurement ID",
				Type:        "text",
				Required:    true,
				Placeholder: "G-XXXXXXXXXX",
				HelpText:    "Your Google Analytics 4 Measurement ID starting with G-",
			},
		},
		Generated: []string{
			"app/layout.tsx: Injects Google tag script with your measurement ID",
		},
	},
	{
		ID:          "resend",
		Name:        "Resend Email",
		Description: "Send transactional emails (welcome emails, receipts, verification codes) via Resend API.",
		Category:    CategoryCommunication,
		AuthType:    "api_key",
		Icon:        "mail",
		DocsURL:     "https://resend.com/docs/send-with-nextjs",
		Fields: []ConfigField{
			{
				Key:         "api_key",
				Label:       "API Key",
				Type:        "password",
				Required:    true,
				Placeholder: "re_...",
				HelpText:    "Your Resend API key starting with re_",
			},
			{
				Key:         "from_email",
				Label:       "Sender Email (From)",
				Type:        "text",
				Required:    true,
				Placeholder: "onboarding@resend.dev or notifications@yourdomain.com",
				HelpText:    "Verified sender email address",
			},
		},
		Generated: []string{
			"lib/email.ts: Typed sendEmail helper using Resend REST API (zero npm dependencies)",
			"app/api/send/route.ts: Example server action for sending emails",
		},
	},
	{
		ID:          "smtp",
		Name:        "Custom SMTP",
		Description: "Connect standard SMTP email server (Gmail SMTP, SendGrid, Amazon SES, Mailgun, Postmark).",
		Category:    CategoryCommunication,
		AuthType:    "api_key",
		Icon:        "server",
		DocsURL:     "https://nodemailer.com/smtp/",
		Fields: []ConfigField{
			{
				Key:         "host",
				Label:       "SMTP Host",
				Type:        "text",
				Required:    true,
				Placeholder: "smtp.example.com",
				HelpText:    "Server hostname",
			},
			{
				Key:         "port",
				Label:       "SMTP Port",
				Type:        "number",
				Required:    true,
				Placeholder: "587",
				HelpText:    "Usually 587 (TLS/STARTTLS) or 465 (SSL)",
			},
			{
				Key:         "username",
				Label:       "SMTP Username",
				Type:        "text",
				Required:    true,
				Placeholder: "user@example.com",
				HelpText:    "Authentication username",
			},
			{
				Key:         "password",
				Label:       "SMTP Password",
				Type:        "password",
				Required:    true,
				Placeholder: "••••••••",
				HelpText:    "Authentication password or app password",
			},
			{
				Key:         "from_email",
				Label:       "Sender Email (From)",
				Type:        "text",
				Required:    true,
				Placeholder: "noreply@yourdomain.com",
				HelpText:    "Email address to appear in the From header",
			},
		},
		Generated: []string{
			"lib/email.ts: SMTP client configuration and sendEmail helper",
		},
	},
}

func GetDefinition(id string) (ConnectorDefinition, bool) {
	for _, c := range Catalog {
		if c.ID == id {
			return c, true
		}
	}
	return ConnectorDefinition{}, false
}
