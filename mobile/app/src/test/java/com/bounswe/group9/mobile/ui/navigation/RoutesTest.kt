package com.bounswe.group9.mobile.ui.navigation

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test

/**
 * Pins the path templates produced by `Routes.*` against their declared
 * `composable(route = ...)` patterns. If the navigation argument names ever
 * drift between the route declaration and the helper, these tests fail
 * loudly instead of silently breaking deep links and `popBackStack`.
 */
class RoutesTest {

    @Test
    fun `eventDetail returns the path that matches its route template`() {
        // Route template: "eventDetail/{eventId}"
        val path = Routes.eventDetail("evt-1")
        assertEquals("eventDetail/evt-1", path)
        // Sanity: the static template ends with the same prefix.
        assertEquals("eventDetail/{eventId}", Routes.EVENT_DETAIL)
    }

    @Test
    fun `hostProfile returns the path that matches its route template`() {
        val path = Routes.hostProfile("user-7")
        assertEquals("hostProfile/user-7", path)
        assertEquals("hostProfile/{userId}", Routes.HOST_PROFILE)
    }

    @Test
    fun `editEvent returns the path that matches its route template`() {
        val path = Routes.editEvent("evt-9")
        assertEquals("editEvent/evt-9", path)
        assertEquals("editEvent/{eventId}", Routes.EDIT_EVENT)
    }

    @Test
    fun `inviteAccept route encodes both eventId and inviteToken in order`() {
        // Critical for the sem://invite/{eventId}/{inviteToken} deep link in
        // AndroidManifest.xml — argument order in the helper must mirror the route.
        val path = Routes.inviteAccept(eventId = "evt-1", inviteToken = "tok-abc")
        assertEquals("inviteAccept/evt-1/tok-abc", path)
        assertEquals("inviteAccept/{eventId}/{inviteToken}", Routes.INVITE_ACCEPT)
    }
}
