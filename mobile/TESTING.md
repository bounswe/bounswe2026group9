# Android testing & CI

Quick reference for the mobile test suite introduced in issue #227. Use this
page (or a copy on the repo wiki) when triaging a red CI run or onboarding a
new feature with tests.

## Running locally

All commands assume you are inside `mobile/`.

| Goal | Command |
|---|---|
| JVM unit tests (JUnit 5 + MockK + MockWebServer) | `./gradlew testDebugUnitTest` |
| Compose UI / instrumented tests (needs an emulator or device) | `./gradlew connectedDebugAndroidTest` |
| Static analysis | `./gradlew detekt` |
| Regenerate the detekt baseline (after deliberate code-style changes) | `./gradlew detektBaseline` |
| Everything the `fast` CI job runs | `./gradlew assembleDebug detekt testDebugUnitTest` |

Reports land under `app/build/reports/`:

- `tests/testDebugUnitTest/index.html` — unit-test HTML report
- `androidTests/connected/debug/index.html` — instrumented-test HTML report
- `detekt/detekt.html` — static-analysis findings
- `app/build/test-results/**/*.xml` — JUnit XML for CI consumption

## CI (`.github/workflows/android-ci.yml`)

Triggered on every pull request that touches `mobile/**`. Two parallel jobs:

| Job | Steps | Typical wall time |
|---|---|---|
| `fast` | `assembleDebug` → `detekt` → `testDebugUnitTest` | ~3–5 min |
| `instrumented` | AVD cache hydrate → `connectedDebugAndroidTest` (API 30, x86_64) | ~8–15 min |

Both upload their HTML and JUnit XML reports as 30-day artifacts:

- `android-fast-reports` — detekt + unit
- `android-instrumented-reports` — Compose UI / Espresso

Download from the run page → **Artifacts**, or pin a stable URL in the wiki's
Test Reports page after each Final-Milestone review.

## Test-coverage matrix

| Feature area | Tests | Where |
|---|---:|---|
| Auth (ViewModel) | 11 | [`ui/auth/AuthViewModelTest.kt`](app/src/test/java/com/bounswe/group9/mobile/ui/auth/AuthViewModelTest.kt) |
| Auth (repository, friendly errors) | 4 | [`data/repository/AuthRepositoryTest.kt`](app/src/test/java/com/bounswe/group9/mobile/data/repository/AuthRepositoryTest.kt) |
| Auth (HTTP contract) | 2 | [`data/remote/AuthApiContractTest.kt`](app/src/test/java/com/bounswe/group9/mobile/data/remote/AuthApiContractTest.kt) |
| Auth (Compose UI) | 3 | [`androidTest/.../ui/auth/LoginScreenTest.kt`](app/src/androidTest/java/com/bounswe/group9/mobile/ui/auth/LoginScreenTest.kt) |
| Profile (ViewModel) | 4 | [`ui/profile/ProfileViewModelTest.kt`](app/src/test/java/com/bounswe/group9/mobile/ui/profile/ProfileViewModelTest.kt) |
| Profile (Compose UI) | 3 | [`androidTest/.../ui/profile/ProfileScreenTest.kt`](app/src/androidTest/java/com/bounswe/group9/mobile/ui/profile/ProfileScreenTest.kt) |
| Discovery (state) | 4 | [`ui/discovery/DiscoveryUiStateTest.kt`](app/src/test/java/com/bounswe/group9/mobile/ui/discovery/DiscoveryUiStateTest.kt) |
| Discovery (ViewModel) | 13 | [`ui/discovery/DiscoveryViewModelTest.kt`](app/src/test/java/com/bounswe/group9/mobile/ui/discovery/DiscoveryViewModelTest.kt) |
| Discovery (Compose UI) | 4 | [`androidTest/.../ui/discovery/DiscoveryScreenTest.kt`](app/src/androidTest/java/com/bounswe/group9/mobile/ui/discovery/DiscoveryScreenTest.kt) |
| Events (repository, MockWebServer) | 9 | [`data/repository/EventRepositoryTest.kt`](app/src/test/java/com/bounswe/group9/mobile/data/repository/EventRepositoryTest.kt) |
| Event detail (ViewModel) | 9 | [`ui/eventdetail/EventDetailViewModelTest.kt`](app/src/test/java/com/bounswe/group9/mobile/ui/eventdetail/EventDetailViewModelTest.kt) |
| Event creation (ViewModel) | 11 | [`ui/createevent/CreateEventViewModelTest.kt`](app/src/test/java/com/bounswe/group9/mobile/ui/createevent/CreateEventViewModelTest.kt) |
| Event creation (Compose UI) | 4 | [`androidTest/.../ui/createevent/CreateEventScreenTest.kt`](app/src/androidTest/java/com/bounswe/group9/mobile/ui/createevent/CreateEventScreenTest.kt) |
| Notifications (ViewModel) | 5 | [`ui/notifications/NotificationViewModelTest.kt`](app/src/test/java/com/bounswe/group9/mobile/ui/notifications/NotificationViewModelTest.kt) |
| Notifications (HTTP contract) | 2 | [`data/remote/NotificationApiContractTest.kt`](app/src/test/java/com/bounswe/group9/mobile/data/remote/NotificationApiContractTest.kt) |
| Navigation route templates | 4 | [`ui/navigation/RoutesTest.kt`](app/src/test/java/com/bounswe/group9/mobile/ui/navigation/RoutesTest.kt) |
| Toolchain smoke | 2 + 1 | [`SmokeUnitTest.kt`](app/src/test/java/com/bounswe/group9/mobile/SmokeUnitTest.kt), [`SmokeUiTest.kt`](app/src/androidTest/java/com/bounswe/group9/mobile/SmokeUiTest.kt) |

**Totals:** 80 unit tests + 15 instrumented tests = **95 automated tests**.

## Maestro E2E flows

Native end-to-end flows live in [`mobile/maestro/`](../maestro/). They run against the real app on a running emulator or device — no mocking.

| Flow | File | What it covers |
|---|---|---|
| Login | [`01_login.yaml`](../maestro/01_login.yaml) | Valid credentials → lands on discovery screen |
| Discovery search & filter | [`02_discovery_search_and_filter.yaml`](../maestro/02_discovery_search_and_filter.yaml) | Search input → filter sheet open/apply |
| Register tab | [`03_register.yaml`](../maestro/03_register.yaml) | Tab switch → registration form fields visible |
| Create event auth guard | [`04_create_event_auth_guard.yaml`](../maestro/04_create_event_auth_guard.yaml) | Login → create event form accessible |
| Discovery list/map toggle | [`05_discovery_list_view.yaml`](../maestro/05_discovery_list_view.yaml) | Toggle between map and list view |
| Profile navigation | [`06_profile_navigation.yaml`](../maestro/06_profile_navigation.yaml) | Login → open profile → verify stats visible |
| Filter category & sort | [`07_filter_category_and_sort.yaml`](../maestro/07_filter_category_and_sort.yaml) | Open filters → select category + sort → apply |

**These flows are manual-only — they are not part of CI.** Reasons: they require a live network connection to the production backend, and `clearState` timing on headless emulators is unreliable without real device warm-up.

Run all flows locally (emulator or device must be running with the app installed):

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 17)   # macOS — Java 17 required
maestro test mobile/maestro/
```

Run a single flow:

```bash
maestro test mobile/maestro/01_login.yaml
```

Offline / error UX is covered indirectly by:

- typed `EventDetailError` mapping in [`EventRepositoryTest.kt`](app/src/test/java/com/bounswe/group9/mobile/data/repository/EventRepositoryTest.kt) (404 → `NotFound`, 403 + age message → `Underage`)
- generic 5xx → `Result.failure` in the same file
- ViewModel-level rollback assertions in `EventDetailViewModelTest` and
  `DiscoveryViewModelTest`

The dedicated NotFound / AccessDenied / Underage screens are private composables
inside `EventDetailScreen.kt`; the typed error contract above is the stable
seam being verified rather than the Compose tree itself.

## Adding a new test

1. Pick the slice — most ViewModel / repository tests live in `app/src/test/`
   (JVM, JUnit 5 + MockK), Compose UI tests in `app/src/androidTest/` (JUnit 4
   + `createComposeRule`).
2. ViewModel tests use the [`MainDispatcherExtension`](app/src/test/java/com/bounswe/group9/mobile/testing/MainDispatcherExtension.kt)
   to swap `Dispatchers.Main` for an `UnconfinedTestDispatcher`. Pair with
   `runTest { ... advanceUntilIdle() }`.
3. Repository / HTTP-contract tests should stand up a `MockWebServer` and use
   `mockkObject(RetrofitProvider) { every { apiService } returns realApi }`
   so the production singleton stays untouched.
4. New code introduces no detekt regressions because of the
   [`baseline.xml`](config/detekt/baseline.xml) snapshot. Touching legacy code
   that is in the baseline can clear entries — re-run `./gradlew detektBaseline`
   only after fixing the underlying issue.

## Updating the wiki Test Reports page

After a Final-Milestone CI run on `main`:

1. Open the run page in GitHub → **Artifacts** → copy the artifact URL for
   `android-fast-reports` and `android-instrumented-reports`.
2. Edit the wiki's Test Reports page; replace the previous links with the new
   artifact URLs and the run's commit SHA.
3. Optionally include a screenshot of the green CI summary.
