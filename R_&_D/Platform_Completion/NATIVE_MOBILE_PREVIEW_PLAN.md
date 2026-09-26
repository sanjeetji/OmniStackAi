# Native Mobile Preview: R&D and plan (PC-062)

Written 2026-09-26 for the founder and whoever builds PC-063..PC-066. The facts about open-source
projects were checked on 2026-09-26 (sources at the end); anything not verified is marked.

**Founder's direction:** open source first. Run the Android emulator and iOS Simulator without
the Android Studio or Xcode *apps* where possible. Android Studio, the Xcode GUI and paid
services come later.

---

## 1. The short answer

| | Android | iOS |
|---|---|---|
| Without the IDE? | **Yes.** The emulator is a separate SDK package driven from the command line (`sdkmanager`, `avdmanager`, `emulator -no-window`). Android Studio is not needed. | **Only half.** No open-source iOS simulator exists. The Simulator ships *inside* Xcode, and macOS may only run on Apple hardware. We can install Xcode headlessly and never open its GUI (`xcodes`, `xcrun simctl`, `idb`). Xcode is free; it needs a free Apple ID, not the paid developer programme. |
| Open source? | The AOSP system images are Apache-2.0. The emulator *binary* is under the Android SDK licence: free to use, but not open source. Fully open-source alternatives (Cuttlefish, Redroid) need Linux. | Control and streaming tools are open source (`idb` MIT, `xcodes` MIT). The simulator itself is Apple's. |
| On the founder's Mac (M2, 16 GB) | Works, accelerated by Apple's Hypervisor.framework. One or two emulators at a time. | Works once Xcode is installed (about 15-40 GB). |
| In the browser | Yes, by streaming the emulator's screen and sending taps back (section 4). | Yes, by streaming the simulator (section 5). There are small open-source examples; we build our own streamer. |
| Hosted for every user | Linux servers with KVM. Straightforward. | Needs Mac hardware, and Apple's licence restricts "service bureau / time-sharing" use. **Legal review before offering it publicly.** |

## 2. What this Mac has today (checked 2026-09-26)

- Apple **M2**, 16 GB RAM, macOS 26.1.
- Android SDK at `~/Library/Android/sdk`, 2.3 GB: emulator 37.1.11, platform-tools (`adb`),
  platforms 34-37, build-tools 34 and 36.
- **No Android virtual device right now:** `~/.android/avd` is empty and no system image is
  installed. The emulator mentioned earlier may have been deleted. PC-063 recreates it from the
  command line.
- **No Xcode:** only the Command Line Tools. The iOS Simulator is not available until Xcode is
  installed.
- Colima 0.10.3 (aarch64, stopped). **The M2 has no nested virtualization in Colima** (that needs
  M3 or later), so anything that needs KVM inside Colima (Cuttlefish, docker-android, Google's
  emulator containers) will not run here.

## 3. How a user previews a mobile app (the ladder)

The cheapest level that proves what the user needs comes first. Each level is opt-in above
level 2.

| Level | What the user does | React Native (default) | Native Kotlin | Native Swift |
|---|---|---|---|---|
| 0 | Nothing: automatic checks | typecheck, tests (R-560, R-561) | Gradle build + tests | xcodebuild + tests (Mac) |
| 1 | Browser preview of the web/PWA | PWA + QR (R-573) | same web/PWA | same web/PWA |
| 2 | **Scan a QR on their own phone** | Expo Go / dev build (exists, R-545) | QR -> signed test APK | TestFlight (needs Apple account, PC-070) |
| 3 | **Android emulator in the Studio** | Expo Go or dev build on the emulator | APK installed on the emulator | not applicable |
| 4 | **iOS Simulator in the Studio** | Expo Go on the simulator | not applicable | app installed on the simulator |

Levels 3 and 4 are what the founder asked for. Local first (PC-063, PC-064), then hosted (PC-065,
PC-066).

## 4. Android: the plan

### 4.1 Local, without Android Studio (PC-063)

1. **Bootstrap from the command line:**
   - install `cmdline-tools` (gives `sdkmanager` and `avdmanager`) and accept the licences
     (`sdkmanager --licenses`)
   - install an arm64 system image, for example `system-images;android-36;google_apis;arm64-v8a`
   - create the device with `avdmanager create avd -n omnistack-phone ...`
   - wrap all of it in one command (`task mobile:android:up`) and a `doctor` check
2. **Run headless:**
   ```
   emulator -avd omnistack-phone -no-window -no-audio -no-boot-anim -grpc 8554
   ```
   Save a snapshot after the first boot so later starts take seconds, not a minute.
3. **Install the generated app:**
   - React Native: install Expo Go on the emulator and open the project's `exp://` URL, or use
     a dev build (`expo run:android`)
   - Native Kotlin: `./gradlew assembleDebug`, then `adb install`
4. **Stream it into the Studio.** Two candidates, decided by a one-day spike:
   - **A. ya-webadb / Tango** (MIT, active). ADB and the scrcpy protocol running in the browser.
     A small local bridge exposes `adb` over a WebSocket; the Studio renders the screen and sends
     taps, swipes and keys. Maintained and license-clean.
   - **B. The emulator's own gRPC endpoint** (`-grpc`), which Google's WebRTC gateway uses. Most
     direct, but *unverified* against a macOS-hosted emulator.
   - Fallback: screenshots every few hundred ms over `adb exec-out screencap`. Simple, and good
     enough for a first demo.

   Not chosen: `ws-scrcpy` is built on a 2021 scrcpy fork (last release 2024-03), and
   desktop `scrcpy` has no web output.
5. **The Studio "Device" tab:** boot/stop, pick a device profile, rotate, screenshot, logs
   (`adb logcat`), reinstall on every build, and a clear "emulator not installed; set it up?"
   state.
6. **Limits on this Mac:** each emulator needs roughly 2-4 GB RAM. Cap at two, and stop them when
   the Studio is idle.

`task verify` stays offline and fast: it tests the command generation and the bridge protocol
with fakes, never a real emulator. A separate opt-in check (`task mobile:android:smoke`) boots
a real one.

### 4.2 Hosted, for every user (PC-065)

This needs **Linux hosts with KVM**: bare metal, or cloud VMs that allow nested virtualization.
Candidates in order:

| Option | Licence | Why / why not |
|---|---|---|
| **Cuttlefish** (AOSP virtual device) | Apache-2.0 | **First choice.** Google's own virtual device; WebRTC browser UI built in; x86_64 and arm64 hosts; host packages active (v1.57, 2026-08). |
| Google `android-emulator-container-scripts` | Apache-2.0 | Emulator in Docker with a WebRTC gateway and web client. Maintained (last push 2026-07), no tagged releases, x86_64 + KVM only. |
| Redroid | Apache-2.0 (+ GPL-2.0 kernel modules) | No KVM and the highest density, because it shares the host kernel. That is also its weakness: weaker isolation between users. Only acceptable inside a per-tenant VM. |
| budtmo/docker-android | Custom Apache-2.0 with extra terms | Active and easy (noVNC), but its terms add usage telemetry that forks must disable. **Legal review before hosting it.** |

**How the sandbox works.** This is the part that was hard to see before.

```
Studio (browser)
   │  short-lived signed stream URL (per session)
   ▼
Control plane ── Preview broker ── picks a free device from a warm pool
                        │
                        ▼
              Device host (Linux + KVM)
              ┌──────────────────────────────────────┐
              │ session container / microVM          │
              │   Android device (Cuttlefish)        │
              │   WebRTC stream  ◄── to the browser  │
              │   network: ONLY this project's       │
              │   preview API (egress policy, R-071) │
              └──────────────────────────────────────┘
                        │ per-session tunnel
                        ▼
              The app's backend + database run in the existing
              build sandbox (R-486..R-490), as they do for web preview
```

- One device per session. It is wiped when the session ends: no data from one user reaches the
  next.
- The device can only reach its own project's preview API. Everything else is blocked.
- Time on a device is metered against credits (PC-010), with a hard cap per session.
- A warm pool of booted snapshots makes "open emulator" take seconds.
- It is built and proven on a local Linux VM first. The server account is plugged in at PC-070
  (keys last).

## 5. iOS: the plan

### 5.1 Local, without opening Xcode (PC-064)

1. Install Xcode headlessly: `xcodes install --latest` (MIT; asks for a free Apple ID), then
   `xcodebuild -downloadPlatform iOS` for the simulator runtime. One-time, about 15-40 GB.
2. Drive everything from the command line:
   - `xcrun simctl create / boot / install / launch / openurl / io screenshot / io recordVideo`
   - taps, swipes and text through **idb** (Meta, MIT, active: v1.6.2, 2026-09)
3. Install the generated app:
   - React Native: open the `exp://` URL in Expo Go on the simulator
   - Native Swift: `xcodebuild -sdk iphonesimulator`, then `simctl install`
4. Stream to the Studio with a small streamer of our own:
   - read frames from the simulator (video stream or fast screenshots) and send them as H.264 or
     MJPEG over a WebSocket
   - send input back through idb

   Small open-source projects show it works: `joshdholtz/simmer` (MIT), `EliotAndres/SimStream`
   and `himanshkukreja/ios-bridge` (MIT). They are young and small, so we use them as references,
   not dependencies.
5. **Without a Mac there is no local iOS Simulator.** Those users get level 2 (Expo Go on their
   iPhone) or a hosted simulator (5.2).

### 5.2 Hosted (PC-066, last)

- Needs real Apple hardware: our own Mac minis, AWS EC2 Mac (24-hour minimum lease) or
  MacStadium.
- **Tart** runs macOS VMs on Apple Silicon, two per Mac. It moved to OpenAI when Cirrus Labs
  joined in April 2026, and a more permissive licence was announced. *Confirm the licence before
  relying on it.*
- **Apple's licence** allows macOS VMs for development and testing but forbids "service bureau /
  time-sharing" use. Offering iOS simulators to the public as a service needs **legal review
  first**. Until then, iOS preview comes from:
  - Expo Go on the user's own iPhone
  - the simulator on the user's own Mac, through the Local Mac agent (PC-046)
  - a third-party service (section 6)

## 6. Later options (paid or third party, behind the same "device provider" interface)

- **EAS Simulator** (Expo, announced 2026-09-14, waitlist, no public price): cloud iOS Simulator
  and Android Emulator in the browser, driven by an API, and it accepts any build, including
  SwiftUI and Kotlin apps. The closest to what we want; worth joining the waitlist.
- **Appetize:** iOS and Android embedded in a web page. Small free tier, then roughly
  $40-400/month plus per-minute.
- **Genymotion SaaS:** Android only, roughly $0.05/device-minute.
- **AWS Device Farm:** real devices, $0.17/device-minute.
- **BrowserStack App Live:** real devices, per-user subscription.
- **Corellium:** virtual iOS and Android for enterprise, quote-based.
- **Firebase Test Lab:** automated tests only, not interactive.
- Android Studio and the Xcode GUI stay available for anyone who prefers them.

Prices are from third-party listings. Confirm with each vendor before choosing one.

Every provider sits behind one `DeviceProvider` interface (boot, install, stream, input, stop,
meter), the same pattern the sandbox drivers use (R-486..R-490). Adding a paid service is then
a key in `.env`, not a rewrite.

## 7. Work breakdown

| Task | What | Where it runs | Priority |
|---|---|---|---|
| PC-063 | Android: spike (boot + stream on this Mac) → `task mobile:android:up` + doctor → Studio Device tab → install RN/Kotlin builds | founder's Mac, then any Mac/Linux | P1, Phase 1 |
| PC-064 | iOS: `xcodes` + runtime install → simctl/idb control → own streamer → Studio Device tab | any Mac | P2, Phase 2 |
| PC-065 | Hosted Android: Cuttlefish pool on Linux + KVM, per-session isolation, WebRTC, metering | Linux servers (account at PC-070) | P2, Phase 4 |
| PC-066 | Hosted iOS on Mac hosts, after legal review | Mac hosts (account at PC-070) | P3, Phase 5 |
| PC-046 | Local Mac agent: a user's own Mac runs simulators and builds for the platform | user's Mac | P3, Phase 5 |
| R-574 | EAS build + submit to both stores (React Native) | Expo EAS (accounts at PC-070) | P1, Phase 1 |

## 8. Risks and unverified points

- The emulator's gRPC streaming from a *macOS-hosted* emulator is unverified; the PC-063 spike
  decides between it and Tango.
- Whether Colima's Linux kernel includes binder (needed by Redroid) is unverified, and there are
  open reports of it failing on arm64. Treated as out of scope on this M2.
- Tart's new licence and DeviceFarmer/stf's licence are reported as "Other" by GitHub; check both
  before use.
- Apple's licence terms for hosted simulators need a lawyer, not an engineer.

## Sources

- Android emulator from the command line: https://developer.android.com/studio/run/emulator-commandline
- Google emulator containers: https://github.com/google/android-emulator-container-scripts
- docker-android: https://github.com/budtmo/docker-android
- Redroid: https://github.com/remote-android/redroid-doc
- Cuttlefish: https://source.android.com/docs/devices/cuttlefish/get-started
- Colima nested virtualization: https://colima.run/docs/configuration
- ya-webadb / Tango: https://github.com/yume-chan/ya-webadb
- scrcpy: https://github.com/Genymobile/scrcpy
- idb: https://github.com/facebook/idb
- xcodes: https://github.com/XcodesOrg/xcodes
- EC2 Mac (24-hour minimum, Apple licence): https://aws.amazon.com/ec2/instance-types/mac/faqs/
- Cirrus Labs / Tart: https://cirruslabs.org/
- EAS Simulator: https://expo.dev/blog/build-ios-apps-on-windows-with-cloud-simulators
