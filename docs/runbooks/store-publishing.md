# Publishing a mobile app to Google Play and the App Store

A project's Expo app is built in Expo's cloud (EAS), so an iOS build needs no Mac, and it is uploaded
with the app owner's own store accounts. Everything runs from **Publish -> App stores** in the Studio.
The credentials are the project's secrets (**Manage -> Secrets**): the platform creates none, logs
none and keeps no key file after a command.

## What each step needs

| Secret | Needed for | Where to get it |
| --- | --- | --- |
| `EXPO_TOKEN` | every build and upload | expo.dev -> Account settings -> Access tokens |
| `EAS_PROJECT_ID` | every build and upload | expo.dev -> Projects -> Create a project -> its ID |
| `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` | Android upload | Google Cloud -> IAM -> Service accounts -> Keys -> Add key (JSON); invite the account in Play Console as a release manager |
| `ASC_API_KEY_P8` | iOS build and upload | App Store Connect -> Users and Access -> Integrations -> App Store Connect API -> Generate key (App Manager); paste the .p8 contents |
| `ASC_API_KEY_ID` | iOS build and upload | shown beside the key |
| `ASC_API_ISSUER_ID` | iOS build and upload | shown above the keys list |
| `APPLE_TEAM_ID` | iOS build and upload | developer.apple.com -> Account -> Membership |
| `ASC_APP_ID` | iOS upload | App Store Connect -> Apps -> the app -> App Information -> Apple ID |

The App Store upload uses an App Store Connect API key: an Apple ID password with two-factor codes
cannot be entered by a server.

## The steps

1. **Check** (runs when the panel opens): lists the missing secrets per store and the warnings the
   stores would refuse on - a bundle identifier not under a domain you own, an empty privacy policy
   URL in `apps/mobile/store.config.json`.
2. **Build for Google Play / App Store**: `eas build --platform <p> --profile production
   --non-interactive --no-wait`. The request returns once the build is queued; the panel links to it
   on expo.dev.
3. **Upload the latest build**: `eas submit --platform <p> --profile production --non-interactive
   --latest --no-wait`. For iOS the App Store Connect IDs are written into `eas.json` for this one
   command and the file is restored afterwards.

The same calls are available as `POST /projects/{id}/stores` with `{"platform": "android"|"ios",
"action": "check"|"build"|"submit"}`. `check` works for any owner; `build` and `submit` need a
verified email.

## When it fails

- **"Expo did not accept EXPO_TOKEN"**: the token was revoked or mistyped. Create a new one.
- **"Expo has no project with this EAS_PROJECT_ID"**: the ID belongs to another account.
- Anything else is eas-cli's own message, with secrets replaced by `[redacted]`.

The eas-cli version is pinned in `publish/store_release.py` (`EAS_CLI`), and its settings were
checked against that version's code. Re-check them when the pin changes.
