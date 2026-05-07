package com.bounswe.group9.mobile.testing

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.TestDispatcher
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.setMain
import org.junit.jupiter.api.extension.AfterEachCallback
import org.junit.jupiter.api.extension.BeforeEachCallback
import org.junit.jupiter.api.extension.ExtensionContext

/**
 * JUnit 5 extension that swaps `Dispatchers.Main` for a `TestDispatcher` so
 * `viewModelScope.launch { ... }` can run synchronously inside unit tests.
 *
 * `UnconfinedTestDispatcher` runs eagerly until the first suspension; pair
 * with `runTest { advanceUntilIdle() }` for deterministic completion.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class MainDispatcherExtension(
    val testDispatcher: TestDispatcher = UnconfinedTestDispatcher()
) : BeforeEachCallback, AfterEachCallback {
    override fun beforeEach(context: ExtensionContext?) { Dispatchers.setMain(testDispatcher) }
    override fun afterEach(context: ExtensionContext?) { Dispatchers.resetMain() }
}
