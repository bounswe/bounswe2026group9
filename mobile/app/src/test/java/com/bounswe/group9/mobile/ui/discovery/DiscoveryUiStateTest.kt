package com.bounswe.group9.mobile.ui.discovery

import com.bounswe.group9.mobile.data.remote.EventListItemDto
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

/**
 * Pure-data tests for the Discovery state object — exercises the
 * client-side `displayedEvents` filter that hides bookmarked-/going-only
 * cards without re-querying the server, plus the accessibility-flag rollup.
 */
class DiscoveryUiStateTest {

    private fun event(
        id: String,
        bookmarked: Boolean? = null,
        attendance: String? = null
    ) = EventListItemDto(
        id = id,
        host_id = "h1",
        title = "Event $id",
        description = null,
        start_datetime = "2026-06-01T10:00:00+00:00",
        end_datetime = "2026-06-01T12:00:00+00:00",
        visibility = "public",
        is_age_restricted = false,
        attendee_limit = null,
        attendee_count = 0,
        status = "published",
        is_bookmarked = bookmarked,
        attendance_status = attendance,
        going_count = 0,
        bookmark_count = 0,
        is_full = false,
        categories = emptyList(),
        primary_location = null,
        primary_image_url = null
    )

    @Test
    fun `displayedEvents returns every item when no client-side filter is on`() {
        val state = DiscoveryUiState(
            events = listOf(event("a"), event("b", bookmarked = true), event("c", attendance = "going"))
        )

        assertEquals(3, state.displayedEvents.size)
    }

    @Test
    fun `displayedEvents keeps only bookmarked items when bookmarkedOnly is on`() {
        val state = DiscoveryUiState(
            events = listOf(event("a"), event("b", bookmarked = true), event("c")),
            bookmarkedOnly = true
        )

        assertEquals(listOf("b"), state.displayedEvents.map { it.id })
    }

    @Test
    fun `displayedEvents keeps only going items when goingOnly is on`() {
        val state = DiscoveryUiState(
            events = listOf(
                event("a"),
                event("b", attendance = "going"),
                event("c", attendance = "interested")
            ),
            goingOnly = true
        )

        assertEquals(listOf("b"), state.displayedEvents.map { it.id })
    }

    @Test
    fun `hasAccessibilityFilter true when any flag is on`() {
        assertFalse(DiscoveryUiState().hasAccessibilityFilter)
        assertTrue(DiscoveryUiState(wheelchair = true).hasAccessibilityFilter)
        assertTrue(DiscoveryUiState(captions = true).hasAccessibilityFilter)
        assertTrue(DiscoveryUiState(elevator = true, quietFriendly = true).hasAccessibilityFilter)
    }
}
