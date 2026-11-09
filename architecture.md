# Architecture

## Layers

MVVM + Repository + Services. No use-case layer: zero `*UseCase.kt` files found anywhere in
`app`, `commonsdk`, or `spectrumsdk`. The app module has 104 `*ViewModel.kt` classes
(`app/src/main/java/.../feature/**`); `Repository`-suffixed classes (e.g.
`AnnouncementRepository`, `AccessCodeCrcRepository`, `RemoteAccessCodeCrcRepository`) and
`Service`-suffixed classes (18 found) live in `spectrumsdk`/`commonsdk`, not in `app`.

## Modules

The module graph, read directly from `repository_halo_android/settings.gradle.kts` and each
module's own `build.gradle(.kts)`:

| Module | Role | Depends on |
|---|---|---|
| `app` | UI/presentation shell (`com.spectrum.halo`); kwikset/weiser brand flavors × 6 environment flavors | `commonsdk`, `spectrumsdk`, `common-ui`, `ti_otau_sdk`, `nordic_otau_sdk`, `gdosdk`, `mcumgr-core`, `mcumgr-ble` |
| `spectrumsdk` | Halo lock BLE + cloud SDK: command queue, encrypted caching, REST, Matter/Wi-Fi provisioning | `commonsdk`, `darwin-sdk`, `mcumgr_core_sdk`, `nordic_otau_sdk`, `otau_common_sdk`, `ti_otau_sdk` |
| `commonsdk` | Shared base: session management, lock model/capability interfaces, BLE queue module, REST interfaces | `darwin-sdk`, `mcumgr_core_sdk`, `nordic_otau_sdk`, `otau_common_sdk`, `ti_otau_sdk` |
| `common-ui` | Shared Fragments/ViewModels for login & account flows, reused across both brands | `commonsdk` |
| `gdosdk` | Garage-door-opener BLE SDK, with its own command queue (`GdoBleQueue`) | `commonsdk`, `mcumgr-core`, `mcumgr-ble` |
| `otau_common_sdk` | Vendor-neutral OTA (firmware update) abstraction | — |
| `darwin-sdk` | Darwin-vendor OTA implementation | `otau_common_sdk` |
| `ti_otau_sdk` | TI-vendor OTA implementation | `otau_common_sdk` |
| `nordic_otau_sdk` | Nordic-vendor OTA implementation (Halo/OTAU side) | `mcumgr_core_sdk`, `otau_common_sdk` |
| `mcumgr_core_sdk` | Halo/OTAU-side mcumgr protocol implementation | — |
| `mcumgr-core` | GDO-side mcumgr protocol implementation (separate from `mcumgr_core_sdk`) | — |
| `mcumgr-ble` | GDO-side mcumgr BLE transport | — |

## UI

View Binding (`buildFeatures.viewBinding = true`, `app/build.gradle.kts:135`); no Compose
dependency found anywhere in `app`. Single host `HomeActivity` + `NavHostFragment`
(`app/src/main/res/layout/activity_home.xml`) with Safe Args
(`androidx.navigation.safeargs.kotlin` plugin). Two standalone secondary activities:
`WebViewActivity` (tutorial web content) and Amplify's `HostedUIRedirectActivity` (Cognito
Hosted UI callback). Shared UI logic is factored into per-feature base classes in `common-ui`
(e.g. `BaseLoginFragment`/`BaseLoginViewModel`, `BaseAccountSettingsFragment`) — there's no
single universal `BaseFragment`/`BaseActivity`.

## Dependency injection

Koin (`koin-core`, `koin-android`, `koin-androidx-workmanager`). App-level wiring lives in
`app/src/main/java/com/spectrum/halo/di/AppModule.kt`, which binds SDK-level singletons
(`CurrentSessionManager`, `GdoSdk`, `SpectrumLock`) into feature ViewModels.

## Networking

Three parallel channels:
- **Retrofit REST** — `*RestInterface.kt` under `commonsdk`/`spectrumsdk`'s
  `interfaces/rest/` packages (auth, token, user, device, history, home, upload-image,
  utility), built via `RestInterfaceBuilder.kt`.
- **AWS AppSync (GraphQL)** — real-time device/lock state (`aws-android-sdk-appsync`).
- **AWS Cognito, via Amplify** — authentication, including a Hosted UI redirect flow.

## BLE

Two independent Nordic BLE stacks, deliberately kept apart (see
`ble-halo.instructions.md`/`ble-gdo.instructions.md`):
- **Halo stack** (`commonsdk` + `spectrumsdk`) — command queue in
  `module/ble/BleQueueModule(Impl).kt` / `module/ble/model/BleQueue.kt`.
- **GDO stack** (`gdosdk`) — its own queue in `ble/queue/GdoBleQueue(Module).kt`.

Neither shares connection state, queues, or secure-channel code with the other.

## Storage

Room (`spectrumsdk/src/main/.../module/caching/room/Database.kt`), opened through a SQLCipher
`SupportFactory` in `SpectrumCachingModuleImpl.kt` — encrypted at rest
(`net.zetetic:sqlcipher-android`). A legacy `OldDatabase.kt`/`OldDatabaseModule.kt` pair exists
for migrating off a prior schema. `commonsdk` declares a Room dependency in its build file but
owns no `@Database` of its own — noted as "Room present, no database confirmed there" per
`docs/field-sources.md`'s own rule, rather than assumed to share `spectrumsdk`'s schema.

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
source set found.

## Known risks / deviations from the above

- **Two independent mcumgr (BLE firmware-update) implementations** exist side by side:
  `mcumgr_core_sdk`/`nordic_otau_sdk` (`android_otau` repo, used for Halo-side OTA) and
  `mcumgr-core`/`mcumgr-ble` (`android_gdo_sdk` repo, used for GDO OTA) — not shared, per each
  module's own `build.gradle`.
- **`:ekey` is referenced then commented out** in `repository_halo_android/settings.gradle.kts`
  — not currently part of the build.
- **The Google Home integration imports local `.aar` files directly** (`app/build.gradle.kts:
  267-289`) because, per its own comment, "the Home APIs used in this open beta are not yet
  available in Google's official libraries" — a temporary dependency mechanism, not a published
  artifact.
- **`commonsdk` carries a Room dependency without owning an `@Database`** — see Storage above.

---
*Each fact is cited at the point it's stated; anything without a citation is `TBD`.*
