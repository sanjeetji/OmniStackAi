# File uploads and cloud file sources: accounts and keys

Generated apps store uploaded files in **Cloudflare R2** (development and production) or **AWS
S3** (production alternative). When no keys are set, they fall back to the **local disk**, so
nothing breaks without an account and `task verify` stays offline. Users pick files from their
device, camera or a link out of the box. Google Drive, Dropbox, OneDrive and Box appear once
their keys are set (through a self-hosted Uppy Companion). Every backend the platform generates -
Python, Go and Node (Express or Hono) - has the same upload checks and reads the same settings.

Put every value in `.env` only; it is git-ignored. Never paste keys into chat, issues or commits.
The key names are already in `.env` and `.env.example`.

## Whose keys these are

They are the **platform's** keys (yours, as the operator). The platform gives them to the apps it
previews and publishes; no key is written into a generated app's code. Every project gets its own
folder in the bucket (`projects/<project>/...`), and deleting a project deletes its folder.
Someone who downloads their app and runs it elsewhere sets their own storage in its `.env`
(`S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`), and a project's own keys
take precedence over the platform's when it is published.

## Which storage is used

| `OMNISTACKAI_STORAGE_TARGET` | Tried in order |
|---|---|
| `dev` (default) | R2 dev bucket, then local disk |
| `prod` | R2 prod bucket, then AWS S3, then local disk |

A store is used only when all of its keys are set. Switching to production later needs no code:
fill in the production keys and set `OMNISTACKAI_STORAGE_TARGET=prod`.

---

## 1. Cloudflare R2 (development, free tier)

1. Sign up at <https://dash.cloudflare.com/sign-up> and verify your email.
2. In the left menu open **R2 Object Storage** and click **Purchase R2 / Enable R2**. Cloudflare
   may ask for a card even for the free tier (10 GB storage, about 1M uploads and 10M reads a month,
   no download fees). You are not charged while you stay inside it.
3. Copy your **Account ID** from the R2 overview page (right-hand side)
   → `OMNISTACKAI_R2_DEV_ACCOUNT_ID`.
4. **Create bucket**: name `omnistackai-dev`, location *Automatic*, storage class *Standard*
   → `OMNISTACKAI_R2_DEV_BUCKET=omnistackai-dev`.
5. No CORS policy is needed: files reach the bucket through the app's API, and people open them
   through short-lived signed links (a plain redirect), so the browser never calls the bucket.
6. Back on the R2 overview: **Manage R2 API Tokens** (or **API** → **Manage API tokens**) →
   **Create API token**:
   - Permissions: **Object Read & Write**
   - Specify bucket: **Apply to specific buckets only** → `omnistackai-dev`
   - TTL: forever (or a date you will remember)
   - **Create**, then copy the two values at once (the secret is shown only once):
     - **Access Key ID** → `OMNISTACKAI_R2_DEV_ACCESS_KEY_ID`
     - **Secret Access Key** → `OMNISTACKAI_R2_DEV_SECRET_ACCESS_KEY`
7. Keep **Public access** off and `OMNISTACKAI_R2_DEV_PUBLIC_URL` empty. The apps never use a public
   address: every file is served through a signed link that expires, so a resume or an ID proof
   cannot be read by someone who only knows its address.
8. Run `bash scripts/omnistack.sh restart`.

## 2. Cloudflare R2 (production)

Same steps, with a separate bucket and token, so development can never touch production data:

- bucket `omnistackai-prod` → `OMNISTACKAI_R2_PROD_BUCKET`
- the same Account ID → `OMNISTACKAI_R2_PROD_ACCOUNT_ID`
- a token scoped to `omnistackai-prod` only → `OMNISTACKAI_R2_PROD_ACCESS_KEY_ID` and
  `OMNISTACKAI_R2_PROD_SECRET_ACCESS_KEY`
- public access off, `OMNISTACKAI_R2_PROD_PUBLIC_URL` empty (files are served through signed links)
- set `OMNISTACKAI_STORAGE_TARGET=prod`

Beyond the free tier, R2 costs about $0.015 per GB a month, with no download fees.

## 3. AWS S3 (production alternative)

Used when `OMNISTACKAI_STORAGE_TARGET=prod` and the R2 prod keys are empty.

1. AWS console → **S3** → **Create bucket**: a unique name (for example `omnistackai-prod-files`),
   your region (for example `ap-south-1`), keep **Block all public access** on
   → `OMNISTACKAI_S3_BUCKET` and `OMNISTACKAI_S3_REGION`.
2. No CORS rules are needed (see step 5 above).
3. **IAM** → **Users** → **Create user** (for example `omnistackai-uploads`, no console access) →
   **Attach policies directly** → **Create policy** → JSON:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject", "s3:ListBucket"],
       "Resource": ["arn:aws:s3:::omnistackai-prod-files", "arn:aws:s3:::omnistackai-prod-files/*"]
     }]
   }
   ```

4. The user → **Security credentials** → **Create access key** → *Application running outside
   AWS* → copy **Access key** → `OMNISTACKAI_S3_ACCESS_KEY_ID` and **Secret access key**
   → `OMNISTACKAI_S3_SECRET_ACCESS_KEY`.

## 4. Local disk (fallback, no account)

Nothing to do. Files go to `~/.omnistackai/uploads` unless `OMNISTACKAI_LOCAL_STORAGE_DIR` says
otherwise. Good for offline work and tests; not for production (one machine, no CDN).

---

## 5. Cloud file sources (Google Drive, Dropbox, OneDrive, Box)

A small companion service (Uppy Companion) signs users in to their drive and copies the chosen
file straight into your storage. Locally it runs at `OMNISTACKAI_COMPANION_URL`
(`http://localhost:3020`). Every provider below needs the same redirect address pattern:
`<COMPANION_URL>/<provider>/redirect`.

First set `OMNISTACKAI_COMPANION_SECRET` to a long random string, for example the output of
`openssl rand -hex 32`.

### Google Drive

1. <https://console.cloud.google.com/> → project picker → **New project** (for example
   `omnistackai-uploads`).
2. **APIs & Services** → **Library** → enable **Google Drive API**.
3. **APIs & Services** → **OAuth consent screen** (Google Auth Platform) → **Get started**:
   - App name, support email; audience **External**; contact email → **Create**
   - **Data access** → **Add or remove scopes** → add
     `https://www.googleapis.com/auth/drive.readonly` → **Update** → **Save**
   - **Audience** → **Test users** → add the Google accounts you will test with (up to 100 while
     the app is in *Testing*)
4. **Clients** (or **Credentials** → **Create credentials** → **OAuth client ID**):
   - Application type **Web application**
   - Authorised redirect URI: `http://localhost:3020/drive/redirect`
   - **Create** → copy **Client ID** → `OMNISTACKAI_GOOGLE_DRIVE_CLIENT_ID` and **Client secret**
     → `OMNISTACKAI_GOOGLE_DRIVE_CLIENT_SECRET`
5. For production: add `https://<your-companion-domain>/drive/redirect`. `drive.readonly` is a
   *restricted* scope, so before opening Drive to more than your test users, Google requires app
   verification (a privacy policy, a demo video, and possibly a security assessment). Plan a few
   weeks for it.

### Dropbox

1. <https://www.dropbox.com/developers/apps> → **Create app** → **Scoped access** → **Full
   Dropbox** → name it.
2. **Permissions** tab → tick `files.metadata.read` and `files.content.read` → **Submit**.
3. **Settings** tab → **Redirect URIs** → add `http://localhost:3020/dropbox/redirect`.
4. **App key** → `OMNISTACKAI_DROPBOX_APP_KEY`; **App secret** (Show) → `OMNISTACKAI_DROPBOX_APP_SECRET`.
5. Production: add the production redirect URI and **Apply for production** (while in
   development, up to 500 users can connect).

### OneDrive (Microsoft)

1. <https://portal.azure.com/> → **Microsoft Entra ID** → **App registrations** → **New
   registration**:
   - Supported account types: **Accounts in any organizational directory and personal Microsoft
     accounts**
   - Redirect URI: **Web** → `http://localhost:3020/onedrive/redirect` → **Register**
2. **Overview** → **Application (client) ID** → `OMNISTACKAI_ONEDRIVE_CLIENT_ID`.
3. **Certificates & secrets** → **New client secret** → copy the **Value** (not the ID)
   → `OMNISTACKAI_ONEDRIVE_CLIENT_SECRET`. Note its expiry date.
4. **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated** →
   `Files.Read.All`, `offline_access`, `User.Read` → **Add permissions**.

### Box

1. <https://app.box.com/developers/console> → **Create Platform App** → **Custom App** →
   authentication **User Authentication (OAuth 2.0)** → name it → **Create App**.
2. **Configuration** → **Redirect URIs** → add `http://localhost:3020/box/redirect`; application
   scopes: **Read all files and folders stored in Box** → **Save Changes**.
3. **OAuth 2.0 Credentials** → **Client ID** → `OMNISTACKAI_BOX_CLIENT_ID`; **Client Secret**
   → `OMNISTACKAI_BOX_CLIENT_SECRET`.

After adding any keys: `bash scripts/omnistack.sh restart`. A source with empty keys is simply
not offered; device, camera and link always are.
