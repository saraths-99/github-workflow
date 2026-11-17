# Architecture

> Lines marked **TBD — conflict** are unresolved: two readings of the code disagree. Check them
> against the base branch (`base_branch` in `.github/copilot-instructions.md`), then delete the marker.

## Repositories

| Repository | Modules | Role |
|---|---|---|
| `repository_halo_android` | `app` | The Android app; its `settings.gradle.kts` pulls the other repositories' modules in as source when `isLocalBuild=true` |
| `repository_sdk_android` | `spectrumsdk`, `commonsdk` | Consumer lock SDK and the shared SDK under it |
| `android_common-ui` | `common-ui` | Shared UI components and reusable feature/screen infrastructure |
| `android_gdo_sdk` | `gdosdk`, `mcumgr-core`, `mcumgr-ble` | Garage-door-opener SDK and its mcumgr modules |
| `android_otau` | `otau_common_sdk`, `darwin-sdk`, `ti_otau_sdk`, `nordic_otau_sdk`, `mcumgr_core_sdk`, `sampleapp` | Vendor firmware-update SDKs and the common OTA contracts |

(`repository_sdk_android/settings.gradle`, `android_gdo_sdk/settings.gradle`,
`android_otau/settings.gradle`.) **TBD:** which repository the spec folder ships in —
`qatalyst-ticket-ship` needs it for a ticket that touches more than one repository.

## Layers

MVVM + Repository + Services. No use-case layer: zero `*UseCase.kt` files found anywhere in
`app`, `commonsdk`, or `spectrumsdk`. The app module has 104 `*ViewModel.kt` classes
(`app/src/main/java/.../feature/**`); `Repository`-suffixed classes (e.g.
`AnnouncementRepository`, `AccessCodeCrcRepository`, `RemoteAccessCodeCrcRepository`) and
`Service`-suffixed classes (18 found) live in `spectrumsdk`/`commonsdk`, not in `app`.

The SDKs add a `module/` layer below the services (`ble`, `caching`, `cloud`, `auth`, `firmware`,
`lock`, `modality`, `ota`, `stepsequences`) that separates orchestration from BLE, cloud, storage and
auth work. ViewModels use LiveData and Flow; login and add-lock are `callbackFlow` step sequences;
background work is WorkManager. The patterns are not uniform, so check the package you are in.

## Modules

The module graph, read directly from `repository_halo_android/settings.gradle.kts` and each
module's own `build.gradle(.kts)`. `api` means the dependency is exposed to consumers of the module;
`implementation` means it is not.

| Module | Repository | Role | Depends on |
|---|---|---|---|
| `app` | `repository_halo_android` | UI/presentation shell (`com.spectrum.halo`); kwikset/weiser brand flavors × 6 environment flavors | `commonsdk`, `spectrumsdk`, `common-ui`, `ti_otau_sdk`, `nordic_otau_sdk`, `gdosdk`, `mcumgr-core`, `mcumgr-ble` |
| `spectrumsdk` | `repository_sdk_android` | Halo lock BLE + cloud SDK: command queue, encrypted caching, REST, Matter/Wi-Fi provisioning | `api` `commonsdk`; `implementation` `darwin-sdk`, `mcumgr_core_sdk`, `nordic_otau_sdk`, `otau_common_sdk`, `ti_otau_sdk` |
| `commonsdk` | `repository_sdk_android` | Shared base: session management, lock model/capability interfaces, BLE queue module, REST interfaces, firmware orchestration. Its build also carries Room, BLE, networking, cryptography and WorkManager, so it is not a contracts-only module | `implementation` `darwin-sdk`, `mcumgr_core_sdk`, `nordic_otau_sdk`, `otau_common_sdk`, `ti_otau_sdk` |
| `common-ui` | `android_common-ui` | Shared Fragments/ViewModels for login & account flows, reused across both brands | `implementation` `commonsdk` |
| `gdosdk` | `android_gdo_sdk` | Garage-door-opener BLE SDK, with its own command queue (`GdoBleQueue`) | `implementation` `commonsdk`, `mcumgr-core`, `mcumgr-ble` |
| `otau_common_sdk` | `android_otau` | Vendor-neutral OTA (firmware update) abstraction | — |
| `darwin-sdk` | `android_otau` | Darwin-vendor OTA implementation | `api` `otau_common_sdk` |
| `ti_otau_sdk` | `android_otau` | TI-vendor OTA implementation | `api` `otau_common_sdk` |
| `nordic_otau_sdk` | `android_otau` | Nordic-vendor OTA implementation (Halo/OTAU side) | `implementation` `mcumgr_core_sdk`, `otau_common_sdk` |
| `mcumgr_core_sdk` | `android_otau` | Halo/OTAU-side mcumgr protocol implementation | — |
| `mcumgr-core` | `android_gdo_sdk` | GDO-side mcumgr protocol implementation (separate from `mcumgr_core_sdk`) | — |
| `mcumgr-ble` | `android_gdo_sdk` | GDO-side mcumgr BLE transport | — |

**Source versus artifact.** The other repositories' modules are included in the app build as source
only when `isLocalBuild=true`; the app's settings default it to false, where the same dependencies
resolve from catalog-defined artifacts. A module list read from `settings.gradle.kts` is therefore the
local-build graph, not the only one.

## Startup and SDK composition

- **App start** (`app/.../core/KwiksetApp.kt`): marks a fresh process start, then sets up Koin and
  `SpectrumSdk`. Environment and brand come from `BuildConfig.FLAVOR_environment`/`FLAVOR_brand`. The
  fresh-process flag tells process recreation apart from a configuration change such as fold/unfold;
  keep that distinction when touching startup or navigation recovery.
- **`SpectrumSdk.configure()`** (`spectrumsdk/.../SpectrumSdk.kt`) builds the SDK's `Dependencies`; an
  existing TODO says reconfiguring would mean recreating the services and clearing cached state, so
  **calling it again is not a way to switch environment at runtime.**
- **`GdoSdk`** (`gdosdk/.../sdk/GdoSdk.kt`) is built from the `CurrentSessionManager` and `HomeService`,
  so it shares the consumer session rather than having its own authentication.

## UI

View Binding (`buildFeatures.viewBinding = true`, `app/build.gradle.kts:135`). Single host
`HomeActivity` + `NavHostFragment` (`app/src/main/res/layout/activity_home.xml`) with Safe Args
(`androidx.navigation.safeargs.kotlin` plugin). Two standalone secondary activities:
`WebViewActivity` (tutorial web content) and Amplify's `HostedUIRedirectActivity` (Cognito
Hosted UI callback).

**TBD — conflict on Compose.** One reading found no Compose dependency anywhere in `app`; another says
the app build enables Compose, that there is a `compose/` package under
`app/src/main/java/com/spectrum/halo/`, and that the version catalog carries a Compose BOM. Check
`buildFeatures` in `app/build.gradle.kts` and that package. The "no Compose" rule in
`xml-ui.instructions.md` rests on the answer.

**Base classes.** `common-ui` has a shared `BaseFragment`
(`common-ui/src/main/java/com/spectrum/common/feature/common/BaseFragment.kt`): it observes
connectivity and provides the shared loading, success, retry and permission UI, and it expects its host
activity to be a `BaseActivity`. Per-feature bases also exist (e.g. `BaseLoginFragment`/
`BaseLoginViewModel`, `BaseAccountSettingsFragment`). **TBD:** whether every per-feature base extends
`BaseFragment`.

## Dependency injection

Koin (`koin-core`, `koin-android`, `koin-androidx-workmanager`). App-level wiring lives in
`app/src/main/java/com/spectrum/halo/di/AppModule.kt`, which binds SDK-level singletons
(`CurrentSessionManager`, `GdoSdk`, `SpectrumLock`) into feature ViewModels. Inside the SDKs, services
are assembled explicitly by each SDK's own `Dependencies` class (`SpectrumSdk` and `GdoSdk` each have
one), not by Koin: Koin covers the application layer and the SDK facades it hands to ViewModels.

## Networking

Three parallel channels:
- **Retrofit REST** — `*RestInterface.kt` under `commonsdk`/`spectrumsdk`'s
  `interfaces/rest/` packages (auth, token, user, device, history, home, upload-image,
  utility), built via `RestInterfaceBuilder.kt`. It uses separate converters for the general, token
  and history APIs, a separate refresh-token client, and token-expiry and authentication
  interceptors on the main client: add endpoints through the existing interfaces and do not reorder
  the interceptors or change a converter unless the change is about that.
- **AWS AppSync (GraphQL)** — real-time device/lock state (`aws-android-sdk-appsync`), with a regional
  client configuration.
- **AWS Cognito, via Amplify** — authentication, including a Hosted UI redirect flow. **TBD:** whether
  this is the consumer sign-in. Another reading has consumer login running through step sequences and a
  regional REST token API (`commonsdk/.../module/auth/`); confirm where `Amplify.configure` is called.

`AuthTokenManagerImpl` (`commonsdk/.../module/auth/`) stores tokens per region and keeps the existing
refresh token when a refresh response omits one; keep region identity intact on every token update.

## BLE

Two independent Nordic BLE stacks, deliberately kept apart (see
`ble-halo.instructions.md`/`ble-gdo.instructions.md`):
- **Halo stack** (`commonsdk` + `spectrumsdk`) — command queue in
  `module/ble/BleQueueModule(Impl).kt` / `module/ble/model/BleQueue.kt`.
- **GDO stack** (`gdosdk`) — its own queue in `ble/queue/GdoBleQueue(Module).kt`.

Neither shares connection state, queues, or secure-channel code with the other.

The Halo queue is keyed by lock ID and times out per command type; whether queues for different locks
run concurrently was not established.

**GDO modality** (`gdosdk/.../utility/modality/ModalityCommandExecutionHelper.kt` — the
`ModalityCommandExecutionHelperImpl` class is declared in this file, not its own): determine BLE and
cloud reachability, then:

```text
cloud reachable:
    run the cloud command; on success return it
    if BLE was not reachable -> return the cloud error
    else run the BLE command and return its result
BLE reachable only -> run the BLE command
neither            -> GeneralError
```

Cloud is preferred and may fall back to BLE; the BLE-selected path does not fall back to cloud. Cloud
uses the Matter code, BLE reachability a derived BLE name. Do not assume the consumer lock's
fallback, retry or idempotency matches this; the consumer toggle path was not read.

Lock onboarding is `AddLockStepSequence` (`spectrumsdk/.../service/addlock/`), with separate start and
resume entry points and pending-lock persistence. Its checkpoint transitions were not read; read them
before reordering any step.

## Firmware updates

`FirmwareUpdateModuleFactory` (`commonsdk/.../module/firmware/`) picks the module from the product ID
and, for some products, the cached bundle's file extension:

| Product | Module |
|---|---|
| `Aura`, `HaloKeypad`, `HaloTouchscreen`, `HaloFingerprint`, `AuraReach` | TI for a `BIN` bundle, otherwise Darwin |
| `HaloSelectPlus`, `HaloSelect` | Nordic |
| `HaloPuck`, `SparkKeypad`, `SparkTouchPanel` | Wi-Fi OTA module |
| Other recognized product IDs | Mostly Darwin — read the factory for exceptions |
| No product ID | No module |

`OnFirmwareFlashListener` (`otau_common_sdk/.../OTAInterfaces.java`) reports progress as 0–100; keep
that scale. BLE firmware update and Wi-Fi OTA are separate paths, and `WifiOtaServiceImpl`
(`spectrumsdk/.../service/ota/wifiota/`) confirms a settings change against the database or one API
read, not on the request being accepted.

## Storage

**Consumer database.** Room (`spectrumsdk/src/main/.../module/caching/room/Database.kt`), schema
version 55, opened through a SQLCipher `SupportFactory` in `SpectrumCachingModuleImpl.kt` — encrypted
at rest (`net.zetetic:sqlcipher-android`) — **except** when the lowercased configuration name
contains the integration or stability configuration string. That is a substring check, so it also
matches names containing `stability`, not just an exact environment. The builder enables
`allowMainThreadQueries()` although its comment says to use IO, and it deletes and recreates the
database on the one unreadable/wrong-key error it checks. A legacy `OldDatabase.kt`/
`OldDatabaseModule.kt` pair exists for migrating off a prior schema. The migration chain was not read.

**GDO database.** Room, schema version 23, name `spectrum.gdosdk.database`
(`gdosdk/src/main/java/com/spectrum/gdosdk/data/caching/room/Database.kt`; the `GdoDatabase` class is
declared in `Database.kt`). Auto-migrations plus an explicit 16 → 17 migration; the inspected builder
configures **no SQLCipher factory**. Do not carry the consumer database's encryption assumptions over
to it.

`commonsdk` declares a Room dependency in its build file but owns no `@Database` of its own — noted as
"Room present, no database confirmed there" per `docs/field-sources.md`'s own rule, rather than
assumed to share `spectrumsdk`'s schema.

## Background work

`GeofenceToggleWorker` (`app/.../geofencing/`) manages BLE session state and keeps proximity retries
inside one worker execution (a code comment says re-enqueuing them used to interrupt BLE
verification). Keep its cleanup of the service scope and the connected-device service session, and do
not add parallel scans or retry workers without checking who owns the session. WorkManager's
foreground service type is `connectedDevice` (`app/src/main/AndroidManifest.xml`); the merged manifest
per variant was not read.

## Error handling

`kotlin-result` (`com.github.michaelbull.result`) is the dominant pattern — found in 309 files
across `commonsdk`/`spectrumsdk`. The app module opts in to its unsafe-access annotations
(`UnsafeResultValueAccess`/`UnsafeResultErrorAccess`) at the Kotlin compiler level
(`app/build.gradle.kts:148-149`), consistent with the "no bare GATT callbacks" rule in
`ble-halo.instructions.md`/`ble-gdo.instructions.md`.

## Testing conventions

Unit tests run on JUnit 5 (`junit-jupiter-api`/`params`/`engine`, `useJUnitPlatform()` in
`app/build.gradle.kts:291-293`), with MockK for mocking and `kotlinx-coroutines-test` for
coroutine dispatchers. Instrumented tests use AndroidX JUnit4 + Espresso + UiAutomator
(`androidTestImplementation`). Tests live alongside their own module's existing `src/test`/
`src/androidTest` trees (e.g. `gdosdk/src/test/.../ble/queue/GdoBleQueueImplTest.kt`,
`commonsdk/src/test/.../module/ble/model/BleQueueTest.kt`) — no separate top-level test
source set found. The SDK builds between them also use JUnit 4, Mockito and Kover; **TBD:** which
module uses which mocking library.

**A passing Gradle task is not a passing test run.** `commonsdk` sets `ignoreFailures = true` on its
debug and release unit-test tasks, several library builds set lint `abortOnError = false`, and the GDO
Kover configuration excludes selected packages and classes. Read the test reports for these modules.
(`commonsdk/build.gradle.kts`, `gdosdk/build.gradle.kts`)

## Rationale: TBD

Several instruction files say "see `architecture.md` for why". No reason can be recovered from code,
and none is to be guessed. A developer needs to supply, in a sentence each: why the UI stays on View
Binding (or, if Compose is in use, where it is allowed); why there is no use-case layer; why the SDKs
assemble services through `Dependencies` instead of Koin, and why `GdoSdk` is kept apart; and why the
Halo and GDO BLE stacks are kept separate.

## Known risks / deviations from the above

- **Two independent mcumgr (BLE firmware-update) implementations** exist side by side:
  `mcumgr_core_sdk`/`nordic_otau_sdk` (`android_otau` repo, used for Halo-side OTA) and
  `mcumgr-core`/`mcumgr-ble` (`android_gdo_sdk` repo, used for GDO OTA) — not shared, per each
  module's own `build.gradle`. Their interchangeability is not established.
- **`:ekey` is referenced then commented out** in `repository_halo_android/settings.gradle.kts`
  — not currently part of the build.
- **The Google Home integration imports local `.aar` files directly** (`app/build.gradle.kts:
  267-289`) because, per its own comment, "the Home APIs used in this open beta are not yet
  available in Google's official libraries" — a temporary dependency mechanism, not a published
  artifact.
- **`commonsdk` carries a Room dependency without owning an `@Database`** — see Storage above.
- **Sensitive values in logs and config** (review concerns, not proof of exposure): the login step
  sequence (`commonsdk/.../module/auth/stepsequences/login/LogInStepSequence.kt`) logs
  password/key-related values; debug HTTP logging is BODY level; debug builds plant a file-logging
  tree; the app build config has API-key literals; keystore files are in the repository listings. Do
  not repeat these patterns or copy any value out of them.
- **Encryption is not uniform** (see Storage). The consumer cache also allows main-thread queries and
  recreates the database on one error; neither is a pattern to extend.
- **`NordicFirmwareUpdateWorker.doWork()` always ends in `Result.success()`**
  (`nordic_otau_sdk/.../module/otau/`; a reading of the source, not a reproduced failure) — a
  `Result.failure()` in the missing-lock-ID path is not returned, and a missing discovery lock or
  firmware file returns without failing the worker.

---
*Each fact is cited at the point it's stated; anything without a citation is `TBD`.*
