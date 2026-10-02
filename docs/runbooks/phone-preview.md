# Opening a generated app on your phone

A project with a mobile app shows a QR code in the preview. Scanning it with your phone's camera opens
the app in **Expo Go**, a free app from the App Store and Google Play. The app talks to the preview's
real API and database.

## Before you scan

1. Install or update **Expo Go** from your phone's store. Expo Go opens only the newest Expo SDK, and
   generated apps are built for it: SDK 57, shown under the QR. An older Expo Go says
   "Project is incompatible with this version of Expo Go". Updating it fixes that.
2. Choose how the phone reaches this computer. The two modes are in the next section.

## Same Wi-Fi (the default)

`OMNISTACKAI_PHONE_ACCESS=lan`. The QR is `exp://<this computer's address>:<port>`. It works when:

- the phone and this computer are on the **same Wi-Fi**;
- the phone is not on mobile data or a VPN;
- the Wi-Fi lets devices reach each other. Many office, hotel and guest networks do not
  ("client isolation"), and the scan then just spins.

Nothing leaves your network in this mode.

## From anywhere

`OMNISTACKAI_PHONE_ACCESS=anywhere` in `.env`, then restart the preview.

- It needs `cloudflared`: `brew install cloudflared`. It is free and needs no account.
- The preview opens a Cloudflare quick tunnel to the app's dev server and one to its API. The QR
  becomes `exps://<name>.trycloudflare.com`.
- It works on any network, mobile data included.
- The tunnel addresses are random and change each time the preview starts.
- The preview is then reachable from the internet, so it **requires sign-in**. It gets its own
  random JWT secret, and development mode is switched off; normally a request with no token is let in
  as an admin. Create an account in the app, or sign in with one you made in the web preview.
- The preview builds each app's bundle before you scan. A bundle built while the phone waits is a
  long stream, and a quick tunnel can drop its end ("Bundling 99%" forever). If that happens, reload in Expo Go.
- If `cloudflared` is missing or cannot connect, the preview falls back to the same-Wi-Fi QR, and its
  log says so.

## What does not work in Expo Go

- **Push notifications.** Expo Go has no remote push since SDK 53. The app skips push registration
  in Expo Go. Push works in a development or store build with the project's EAS id (see
  [notifications](notifications.md)).
- **Native code beyond Expo's modules.** Generated apps use only modules Expo Go includes.

## On the emulator

The preview's "Android emulator" panel installs the Expo Go that matches the app's SDK. It replaces an
older one it installed before, then opens the same link the QR encodes. See
[the emulator runbook](android-emulator.md).

## Moving to a new Expo SDK

When Expo releases a new SDK, the store's Expo Go moves to it within days, and older apps stop
opening. The SDK, and every package version it fixes, live in one file,
`services/agent-engine/src/omnistackai_agent_engine/codegen/expo_sdk.py`.

To move generated apps to the new SDK:

1. Take each version from the new `expo` package's `bundledNativeModules.json`.
2. Check the result with `expo install --check` in a generated app.
3. Add the new Expo Go APK to `EXPO_GO` in `mobile_device/android.py`.

`https://api.expo.dev/v2/versions/latest` reports the SDK the store's Expo Go opens, as
`expoGoSdkVersion`.
