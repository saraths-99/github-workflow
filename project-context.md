# Project context

> Lines marked **TBD — conflict** are unresolved: two readings of the code disagree. Check them
> against the base branch (`base_branch` in `.github/copilot-instructions.md`), then delete the marker.
> Component behavior lives in `architecture.md`.

## What this app does

A Bluetooth (BLE) + Wi-Fi smart-lock companion app for Kwikset and Weiser electronic locks,
published as two white-labeled apps from one codebase (Gradle root project `SpectrumHalo`,
namespace `com.spectrum.halo`) — `com.kwikset.blewifi` and `com.weiser.blewifi`
(`app/build.gradle.kts:73-82`). It's part of the HHI (Hardware & Home Improvement) family of
Kwikset/Weiser apps (`android_common_ui/README.md`). Lets a homeowner pair, control and manage
their lock(s) — and, where enabled, a garage-door opener — over BLE, plus manage access codes,
firmware updates, account settings, and (optionally) Google Home / Matter and Android Auto
integration. The app is built from five repositories (see below).

## Target platforms

Phone only — no `wear`/`tv` module in `settings.gradle.kts`. `minSdk = 29` (Android 10),
`compileSdk`/`targetSdk = 36` (`gradle/libs.versions.toml:16-17`). Android Auto is an in-app
integration (`androidx.car` dependency, `feature/car/` package), not a separate build target.

## Repositories and local workspace

Bitbucket workspace `team_giga_zuul`; repositories and their modules are in `architecture.md`. The
existing citation `android_common_ui/README.md` spells that repository with an underscore, the
workspace's repository is `android_common-ui` — **TBD:** confirm the real name.

**Branch.** Which branch tickets branch from is `base_branch` in `.github/copilot-instructions.md`:
**TBD** until that is filled in. Do not infer behavior from another branch, from a similarly named
SDK, or from an old packaged artifact.

**Local source builds.** The app's `settings.gradle.kts` includes the other repositories' modules from
sibling directories — all five checked out side by side in one workspace folder, named as in the
repository table — but only when `isLocalBuild=true`; it defaults to false, which resolves them as
catalog artifacts instead. Being in the settings does not prove the app depends on a module directly.
(`repository_halo_android/settings.gradle.kts`)

## Build variants

(`app/build.gradle.kts`, `gradle/libs.versions.toml`, `gradle/wrapper/gradle-wrapper.properties`)

- **Flavor dimensions, in order:** `environment`, then `brand`. Environments: `integration`, `qa`,
  `production`, `beta`, `stability`, `stability2`. Brands: `kwikset`, `weiser`. Build types: `debug`,
  `release`. A variant is named like `IntegrationKwiksetDebug`.
- **Build features:** ViewBinding and BuildConfig are enabled. Compose: **TBD — conflict**, see
  `architecture.md`'s UI section.
- **Release build:** minification and resource shrinking on. The release-signing assignment is
  commented out in the file read, so do not assume release signing is configured.
- **BuildConfig flags,** filled from project properties: `ALLOW_SEND_BLE_WHILE_MATTER_ENABLE`,
  `APP_FEEDBACK_ENABLE`, `IS_GDO_FEATURE_ENABLED`, `IS_QR_SCAN_LOCK_ENABLED`,
  `IS_GOOGLE_HOME_API_ENABLED`. Their configured values are not recorded here; never invent them.
- **Toolchain:** Java/Kotlin target 17; Gradle wrapper 8.9 (the app catalog's separate `gradle`
  entry of 8.7.0 is not the wrapper version). Only the app's version catalog was read.
- The app has several distinct version numbers (app version, production override, version code,
  equivalent production app version, internal artifact versions); never collapse them into one.

## Build and test commands

**TBD — none of these has been run.** `qatalyst-developer` and `qatalyst-ticket-ship` are told to
build and test with `isLocalBuild=true`, and no file records how. These are candidates built from the
variant names above, run from `repository_halo_android`. A developer should run each once, keep the
ones that work, and replace this block:

```bash
./gradlew -PisLocalBuild=true :app:assembleIntegrationKwiksetDebug
./gradlew -PisLocalBuild=true :app:testIntegrationKwiksetDebugUnitTest
./gradlew -PisLocalBuild=true :commonsdk:testDebugUnitTest :spectrumsdk:testDebugUnitTest :gdosdk:testDebugUnitTest
```

Confirm each task exists first (`./gradlew -PisLocalBuild=true :app:tasks --all`). A green task is not
proof that tests passed — see `architecture.md`'s Testing conventions.

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
- `login` / `signup` / `resetpassword` — authentication flows (see Key integrations)
- `navigation` — shared nav graph/host wiring
- `newfeaturehighlight` — what's-new / feature-highlight UI
- `realtimevoidalert` / `home/automation/realtimevoicealert` — real-time voice alert automation
- `support` — in-app help/support

Outside `feature/`: `geofencing/` (geofence-triggered operations, `GeofenceToggleWorker`), plus
`core/`, `di/`, `compose/`, `extension/` and `utilities/`
(`app/src/main/java/com/spectrum/halo/`). The names above are spelled as they are in the source.

Google Home integration (`com.google.home.Home`, `IS_GOOGLE_HOME_API_ENABLED` flag) is wired
directly into `di/AppModule.kt` rather than living in its own `feature/` package.

## Users / personas

TBD — no explicit developer note on file; never inferred from code or package names.

## Key integrations

- **AWS Cognito, via Amplify** — sign-in/auth, including a Cognito Hosted UI redirect activity
  (`amplify-core-kotlin`, `aws-auth-cognito`, `AndroidManifest.xml`'s
  `HostedUIRedirectActivity`). **TBD:** confirm what Amplify is used for; see `architecture.md`,
  Networking.
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

- **Local data at rest is encrypted for the consumer database only, and not in every configuration** —
  `spectrumsdk`'s Room database (`module/caching/room/Database.kt`) is opened through a SQLCipher
  `SupportFactory` in `SpectrumCachingModuleImpl.kt` (`net.zetetic:sqlcipher-android`,
  `gradle/libs.versions.toml:23`), except when the configuration name contains the integration or
  stability string. The GDO database has no SQLCipher factory in its builder
  (`gdosdk/.../data/caching/room/Database.kt`). Details in `architecture.md`'s Storage section.
- **Brand identity is a build-time constraint, not a runtime one** — `flavorDimensions +=
  listOf("environment", "brand")` with distinct `applicationId`s per brand
  (`com.kwikset.blewifi` / `com.weiser.blewifi`), enforced by Gradle, not a runtime switch
  (`app/build.gradle.kts:70-82`).
- **Release automation is out of bounds** — the root `build.gradle.kts` registers a `releaseApp` task
  (a custom `ReleaseTask`) that coordinates versions across all five repositories' artifacts and
  documents an auto-push option. Do not run it without the developer's explicit say-so. Its code and
  the `Jenkinsfile` were not fully read, so nothing here describes CI behavior.

## Other documentation in the app repo

The Halo app repository already lists `.github/copilot/architecture.md`,
`.github/copilot/project-context.md`, `.github/prompts/workflow.prompt.md` and
`.github/docs/workflows/add-lock.md`. Their contents were not read. **TBD:** decide whether this file
and `architecture.md` replace the first two or sit beside them, and review the other two before an
install touches `.github/prompts/`.

## Glossary

- **GDO** — garage-door opener (`gdosdk` module, `IS_GDO_FEATURE_ENABLED`)
- **OTAU** — over-the-air (firmware) update (`android_otau` repo, `*_otau_sdk` modules)
- **Wi-Fi OTA** — a firmware-update path for some products that runs through the cloud rather than
  BLE (`WifiOtaServiceImpl`); not the same as a BLE firmware update
- **Halo** — the Kwikset/Weiser connected smart-lock product line (Gradle root project
  `SpectrumHalo`, namespace `com.spectrum.halo`)
- **HHI** — Hardware & Home Improvement, the Kwikset/Weiser product group
  (`android_common_ui/README.md`)
- **mcumgr** — Nordic's BLE firmware-update management protocol; implemented twice in this
  codebase — once for Halo/OTAU devices (`mcumgr_core_sdk`, in `android_otau`) and once for GDO
  (`mcumgr-core`/`mcumgr-ble`, in `android_gdo_sdk`) — see Known risks in `architecture.md`
- **Darwin** — `darwin-sdk`, one of three vendor-specific OTA implementations (alongside TI and
  Nordic) wrapped by `otau_common_sdk`
- **Modality** — how a lock command reaches the device: over the cloud or over BLE
  (`Modality.Cloud` is the consumer app's preferred one; GDO picks per command, see `architecture.md`)
- **Step sequence** — a Flow-based, callback-driven interactive workflow such as login or add-lock
- **Identifiers** — lock ID, home ID, cloud device ID, Matter code, BLE name and region are six
  different things; none stands in for another

---
*Each fact is cited at the point it's stated; anything without a citation is `TBD`.*
