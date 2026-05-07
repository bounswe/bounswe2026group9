package com.bounswe.group9.mobile

import io.mockk.every
import io.mockk.mockk
import io.mockk.verify
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test

/**
 * Boots the unit-test stack: JUnit 5 (jupiter) + MockK. Every PR following
 * issue #227 will lean on this configuration, so a single canary test here
 * means CI flips red the moment the test toolchain drifts.
 */
class SmokeUnitTest {

    private interface Greeter {
        fun greet(name: String): String
    }

    @Test
    fun jupiter_runs_and_asserts() {
        assertEquals(4, 2 + 2)
    }

    @Test
    fun mockk_records_and_verifies_calls() {
        val greeter = mockk<Greeter>()
        every { greeter.greet(any()) } returns "hi"

        val result = greeter.greet("ada")

        assertEquals("hi", result)
        verify(exactly = 1) { greeter.greet("ada") }
    }
}
