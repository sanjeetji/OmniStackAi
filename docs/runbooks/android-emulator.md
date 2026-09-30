# The Android emulator in the Studio

A project's mobile (Expo) app can run on an Android emulator shown inside the Studio, with no
Android Studio. Open the project's preview and pick the **Mobile app (Expo)** tab: the left side has
the QR code for your own phone (Expo Go, same Wi-Fi), and the right side has the emulator.

## First time: Set up (about 1.5 GB, once)

**Set up the emulator** does these steps, and each one is skipped if it has already been done:

1. Downloads Google's Android command-line tools (pinned in `mobile_device/android.py`) and checks
   their SHA-1 against the value Google publishes. An archive that doesn't match is deleted and
   nothing from it runs.
2. Accepts the SDK licences and installs `platform-tools`, `emulator` and
   `system-images;android-34;google_apis;arm64-v8a` (x86_64 on Intel and Linux).
3. Creates the virtual device `omnistack-phone`: a Pixel 6 profile at 720x1560, so each
   screenshot stays small.

The SDK goes where Android Studio would put it (`ANDROID_HOME`, else `~/Library/Android/sdk` on a
Mac), so an existing SDK is reused. Nothing is downloaded until someone presses the button.

## Using it

- **Start the emulator**: it boots headless (`-no-window`). The first boot takes about 30
  seconds, and later ones about 10 seconds, from the snapshot saved on Stop.
- **Open this app**: installs Expo Go for the app's Expo SDK (from Expo's versions API, pinned
  for SDK 51), marks Expo Go's developer-menu introduction as seen, and opens the running
  preview's `exp://` link.
- **Using the phone**: click to tap, drag to swipe, the ← and ○ buttons for Back and Home, and the
  box to type text. The screen refreshes about once a second.
- **Stop**: shuts the emulator down (`adb emu kill`).

The same steps are available from a terminal:
`PYTHONPATH=services/agent-engine/src python3 -m omnistackai_agent_engine.mobile_device.android status|setup|boot|stop`.
`scripts/omnistack.sh status` shows the emulator's state.

## One account at a time

There is one emulator per machine. The control plane lends it to one account for 30 minutes after
that account's last action, or until it presses Stop. Other accounts see "in use" and never see
the screen. A hosted device per session is PC-065.

## What was found making it work

- **Opening a link while Expo Go is closed crashes it.** Expo Go 2.31 fails with "Unable to attach a
  rootView to ReactInstance when UIManager is not properly initialized". Expo Go's home screen is
  started first, then the link is sent.
- **The app ignored every touch until Back was pressed.** On its first app, Expo Go opens a
  developer-menu introduction that this headless emulator never draws. The fix sets
  `is_onboarding_finished` in Expo Go's preferences. This needs root, which the `google_apis` image
  allows. On an image without root, pressing Back once does the same.
- **Every data call failed with "Network request failed".** The mobile app calls the preview API at
  this machine's LAN address, but the API listened only on 127.0.0.1. A project with a mobile app
  now runs its preview API on all interfaces; other projects still listen only on loopback.

## Limits

- Each emulator needs about 2-4 GB of RAM. On a 16 GB Mac, run one at a time and stop it when
  you're done.
- The screen is sent as PNG screenshots (about 0.4 s each). A video stream (scrcpy, or the
  emulator's gRPC) is a later improvement.
- iOS is PC-064: it needs Xcode, and it only runs on a Mac.
