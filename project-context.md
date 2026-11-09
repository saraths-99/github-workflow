# Project context

## What this app does

A Bluetooth (BLE) + Wi-Fi smart-lock companion app for Kwikset and Weiser electronic locks,
published as two white-labeled apps from one codebase (Gradle root project `SpectrumHalo`,
namespace `com.spectrum.halo`) — `com.kwikset.blewifi` and `com.weiser.blewifi`
(`app/build.gradle.kts:73-82`). It's part of the HHI (Hardware & Home Improvement) family of
Kwikset/Weiser apps (`android_common_ui/README.md`). Lets a homeowner pair, control and manage
their lock(s) — and, where enabled, a garage-door opener — over BLE, plus manage access codes,
firmware updates, account settings, and (optionally) Google Home / Matter and Android Auto
integration.

## Target platforms

Phone only — no `wear`/`tv` module in `settings.gradle.kts`. `minSdk = 29` (Android 10),
`compileSdk`/`targetSdk = 36` (`gradle/libs.versions.toml:16-17`). Android Auto is an in-app
integration (`androidx.car` dependency, `feature/car/` package), not a separate build target.

## Core features

One line per top-level package under `app/src/main/java/com/spectrum/halo/feature/`:

- `account` — account settings, change password/phone/username
- `app` — app shell / `HomeActivity`, the single nav host
- `banner` — in-app promotional/status banners
- `car` — Android Auto screens (`androidx.car.app`)
- `chatbot` — in-app support chatbot
- `choose_a_device` — device/lock pairing entry point, including QR-code pairing
  (`IS_QR_SCAN_LOCK_ENABLED` build flag, `journeyapps:zxing` dependency)
- `fcm` — push notifications (Firebase Cloud Messaging)
- `feedback` — in-app feedback / Play Store rating prompts (`APP_FEEDBACK_ENABLE` flag)
- `gdo` — garage-door-opener control, settings and diagnostics (`IS_GDO_FEATURE_ENABLED` flag)
- `home` — home/property management (naming, description, deletion)
- `landing` — splash/welcome screens
- `lock` — lock control, settings, access codes, and Matter pairing
  (`ALLOW_SEND_BLE_WHILE_MATTER_ENABLE` flag)
- `login` / `signup` / `resetpassword` — authentication flows (AWS Cognito, see Key integrations)
- `navigation` — shared nav graph/host wiring
- `newfeaturehighlight` — what's-new / feature-highlight UI
- `realtimevoidalert` / `home/automation/realtimevoicealert` — real-time voice alert automation
- `support` — in-app help/support

Google Home integration (`com.google.home.Home`, `IS_GOOGLE_HOME_API_ENABLED` flag) is wired
directly into `di/AppModule.kt` rather than living in its own `feature/` package.

## Users / personas

TBD — no explicit developer note on file; never inferred from code or package names.

## Key integrations

- **AWS Cognito, via Amplify** — sign-in/auth, including a Cognito Hosted UI redirect activity
  (`amplify-core-kotlin`, `aws-auth-cognito`, `AndroidManifest.xml`'s
  `HostedUIRedirectActivity`)
- **AWS AppSync** — real-time device/lock state (`aws-android-sdk-appsync` dependency,
  `gradle/libs.versions.toml`)
- **Retrofit REST APIs** — `*RestInterface.kt` under `commonsdk`/`spectrumsdk`'s
  `interfaces/rest/` packages (auth, token, user, device, history, home, upload-image, utility),
  built via `RestInterfaceBuilder.kt`
- **Nordic BLE** — lock/GDO communication (`ble.ktx`/`scanner` dependencies; see
  `ble-halo.instructions.md`/`ble-gdo.instructions.md`)
- **Firebase** — Crashlytics, Analytics, and Cloud Messaging (push notifications)
- **Google Maps SDK** — `play-services-maps` + `maps.ktx`, with a `GEO_MAP_API_KEY` resource per
  environment flavor
- **Google Home API** — `play-services-home`/`play-services-home-types`, imported as local
  `.aar` files because "the Home APIs used in this open beta are not yet available in Google's
  official libraries" (`app/build.gradle.kts:267-269`)
- **ZXing** — QR-code scanning for device pairing

## Business constraints

- **Local data at rest is encrypted** — `spectrumsdk`'s Room database
  (`module/caching/room/Database.kt`) is opened through a SQLCipher `SupportFactory` in
  `SpectrumCachingModuleImpl.kt` (`net.zetetic:sqlcipher-android`,
  `gradle/libs.versions.toml:23`).
- **Brand identity is a build-time constraint, not a runtime one** — `flavorDimensions +=
  listOf("environment", "brand")` with distinct `applicationId`s per brand
  (`com.kwikset.blewifi` / `com.weiser.blewifi`), enforced by Gradle, not a runtime switch
  (`app/build.gradle.kts:70-82`).

## Glossary

- **GDO** — garage-door opener (`gdosdk` module, `IS_GDO_FEATURE_ENABLED`)
- **OTAU** — over-the-air (firmware) update (`android_otau` repo, `*_otau_sdk` modules)
- **Halo** — the Kwikset/Weiser connected smart-lock product line (Gradle root project
  `SpectrumHalo`, namespace `com.spectrum.halo`)
- **HHI** — Hardware & Home Improvement, the Kwikset/Weiser product group
  (`android_common_ui/README.md`)
- **mcumgr** — Nordic's BLE firmware-update management protocol; implemented twice in this
  codebase — once for Halo/OTAU devices (`mcumgr_core_sdk`, in `android_otau`) and once for GDO
  (`mcumgr-core`/`mcumgr-ble`, in `android_gdo_sdk`) — see Known risks in `architecture.md`
- **Darwin** — `darwin-sdk`, one of three vendor-specific OTA implementations (alongside TI and
  Nordic) wrapped by `otau_common_sdk`

---
*Each fact is cited at the point it's stated; anything without a citation is `TBD`.*
