# Final Demo Structure and User Scenarios

## 1. Source Review: Open Issues and PRs Considered

This demo plan is updated from the previous private-event scenario after reviewing the current open GitHub work. The new flow puts the newest product features first instead of spending most of the demo on the earlier invite/access-request story.

### Open PRs that should shape the demo

- [PR #307](https://github.com/bounswe/bounswe2026group9/pull/307): Web "Suggested for you" discovery filter.
- [PR #309](https://github.com/bounswe/bounswe2026group9/pull/309): Web multi-location route mapper and itinerary timeline.
- [PR #310](https://github.com/bounswe/bounswe2026group9/pull/310): Mobile text reviews on host profile.
- [PR #312](https://github.com/bounswe/bounswe2026group9/pull/312): Backend testing roadmap, dependency injection, and faster unit coverage. This is not a main user-facing demo beat, but it can be mentioned briefly as quality/readiness work.

### Open issues that should shape the demo

- [Issue #275](https://github.com/bounswe/bounswe2026group9/issues/275): Notification-based event recommendations from past attended events.
- [Issue #276](https://github.com/bounswe/bounswe2026group9/issues/276): Similar event suggestions under each event detail page.
- [Issue #277](https://github.com/bounswe/bounswe2026group9/issues/277): Suggested discovery filter based on past attended events.
- [Issue #224](https://github.com/bounswe/bounswe2026group9/issues/224) / [Issue #207](https://github.com/bounswe/bounswe2026group9/issues/207): Location search and human-readable address storage.
- [Issue #231](https://github.com/bounswe/bounswe2026group9/issues/231) / [Issue #233](https://github.com/bounswe/bounswe2026group9/issues/233): QR code check-in and host capacity enforcement.
- [Issue #230](https://github.com/bounswe/bounswe2026group9/issues/230) / [Issue #237](https://github.com/bounswe/bounswe2026group9/issues/237): Written post-event reviews alongside star ratings.
- [Issue #157](https://github.com/bounswe/bounswe2026group9/issues/157): Multi-location route mapper and itinerary timeline on web.
- [Issue #152](https://github.com/bounswe/bounswe2026group9/issues/152): Final non-functional requirements around logging, performance, security, and measurable readiness.

## 2. Updated Demo Overview

The updated demo tells a full event lifecycle story with the newest features at the front:

1. Mehmet creates a polished multi-stop bird observation event on web using location search, human-readable addresses, route mapping, stop timing, required/optional equipment badges, and an itinerary preview.
2. Publishing the event triggers a personalized recommendation notification for Emir because Emir previously attended similar nature and bird observation events.
3. Emir uses the mobile app to follow the recommendation, checks the "Suggested for you" discovery path, opens the event detail page, and sees similar event suggestions.
4. Emir joins the event and receives a QR code that proves his attendance eligibility.
5. On event day, Mehmet verifies capacity control from the host side by checking Emir in with the QR flow.
6. After the event, Emir submits a written review with a star rating. Mehmet's host profile shows the new textual review as social proof.

The old private-event access-request scenario is now a short optional fallback, not the main story. The final demo should emphasize personalization, route richness, capacity enforcement, and post-event trust.

## 3. Demo Users

### Mehmet Kaya

Mehmet is the host and primarily uses the web application. He creates the event, reviews the route and itinerary, manages attendee check-in, and later verifies that written feedback appears on his host profile.

### Emir Demir

Emir is the attendee and primarily uses the mobile application. He has a history of attending nature and bird observation events, so he receives personalized recommendations. He joins Mehmet's event, shows his QR code for check-in, and writes a post-event review.

## 4. User Scenarios

### Scenario 1: Web Host Creates a Multi-Stop Event

Mehmet starts already authenticated on the web application. He creates a new bird observation event called **Belgrad Forest Bird Observation Route**. In the location step, he searches for real places instead of manually entering coordinates. He adds multiple stops, reorders them, and shows that the route line and numbered pins update. He adds stop timing and an itinerary note, marks binoculars as required equipment, and marks water/snacks as optional equipment. After publishing, he opens the event detail page to show the itinerary timeline, route map, formatted addresses, and equipment badges.

Main features shown:

- Location search and address display.
- Multi-location route mapper.
- Drag-and-drop stop ordering.
- Itinerary timeline.
- Required/optional equipment badges.
- Publish action that can trigger recommendations.

### Scenario 2: Mobile Attendee Discovers the Event Through Personalization

Emir starts already authenticated on the mobile application. He opens notifications and sees a new recommendation for Mehmet's event, explained as being based on his past bird observation attendance. He taps the notification to open the event. Then he briefly returns to discovery and enables **Suggested for you** to show that the same event appears through personalized browsing as well. On the event detail page, he sees the itinerary and a **Similar events** section that helps him continue exploring related activities.

Main features shown:

- Recommendation notification.
- Tappable notification routing to event detail.
- Suggested discovery filter.
- Similar event suggestions.
- Mobile event detail parity.

### Scenario 3: Mobile RSVP and QR-Based Check-In

Emir taps **Going** on the mobile event detail page. The app shows his attendee QR code. Mehmet switches to the host-side attendee/check-in view and scans Emir's QR code from the mobile device. The system validates that Emir is actually going to this event, marks him as checked in, and prevents duplicate or invalid check-in attempts.

Main features shown:

- QR generation after Going.
- Attendee QR display on mobile.
- Host-side scan/check-in flow.
- Attendee list check-in status.
- Capacity enforcement beyond simply disabling Going.

### Scenario 4: Post-Event Written Review and Host Profile Trust

The demo jumps to a pre-prepared completed version of the event. Emir opens Mehmet's host profile from the completed event and submits a star rating plus this written review:

> Mehmet planned the route clearly, the meeting points were easy to find, and the check-in process made the group feel organized.

Mehmet then opens his host profile on web and shows that the new review appears in the reviews section with the rating, reviewer identity, and timestamp.

Main features shown:

- Written review text alongside star rating.
- Review list on host profile.
- Post-event trust and accountability.

### Optional Fallback Scenario: Private Access Request

If the personalized recommendation or QR check-in flow is not stable enough on demo day, use the previous private-event access request story as a fallback:

- Mehmet creates or opens a private bird observation event.
- Emir sees a limited preview and requests access.
- Mehmet approves Emir after recognizing him.
- Emir refreshes and sees the full event details.

This fallback should not replace the main final demo unless needed.

## 5. Presentation Script

### 0:00 - 0:20: Introduction

**Speaker: Can Emir**

Start with Mehmet already authenticated on web and Emir already authenticated on mobile. Explain the story:

"Today we will show the complete lifecycle of a richer event experience: creating a multi-stop route, recommending it to the right attendee, joining with QR-based capacity control, and closing the loop with a written host review."

**Action:** Keep both apps ready. Web starts on Mehmet's create-event or dashboard page. Mobile starts on Emir's notifications or home screen.

### 0:20 - 1:50: Web Event Creation with Route and Address Features

**Speaker: Can Emir**  
**Controller: Ibrahim**

Mehmet creates **Belgrad Forest Bird Observation Route**.

**Actions:**

1. Open create-event page.
2. Enter title, category, date/time, and description.
3. In the location step, search for **Bogazici University / Hisarustu** or **M6 Bogazici University Metro** as the meeting point.
4. Add at least two Belgrad Forest stops.
5. Reorder one stop and show numbered pins updating.
6. Show the route polyline redrawing on the map.
7. Add stop timing and a short itinerary note.
8. Add equipment:
   - Required: Binoculars.
   - Optional: Water, snacks.

**Narration point:** This replaces plain coordinate entry with a route that is understandable before the event starts.

### 1:50 - 2:30: Web Publish and Detail Verification

**Speaker: Can Emir**  
**Controller: Ibrahim**

Publish the event, then open the event detail page.

**Actions:**

1. Click publish.
2. Open the created event detail page.
3. Show formatted addresses instead of raw coordinates.
4. Show itinerary timeline and route map.
5. Show required/optional equipment badges.

**Narration point:** Mehmet can verify that attendees will see the exact route, timing, and preparation requirements.

### 2:30 - 3:20: Mobile Recommendation Notification

**Speaker: Muhittin**  
**Controller: Ihsan**

Switch to Emir's mobile app.

**Actions:**

1. Open notifications.
2. Show the **event recommended** notification for Mehmet's bird observation event.
3. Tap the notification.
4. Land on the event detail page.

**Narration point:** Emir did not need to manually search. The system recommended the event because his past attended events include similar nature or bird observation categories.

### 3:20 - 4:00: Mobile Suggested Discovery and Similar Events

**Speaker: Muhittin**  
**Controller: Ihsan**

Show that personalization also works from discovery.

**Actions:**

1. Go to discovery.
2. Enable **Suggested for you**.
3. Show Mehmet's event in the personalized result list or map.
4. Re-open the event detail page.
5. Scroll to **Similar events** and point out one related nature event.

**Narration point:** Notifications are proactive, while Suggested discovery and Similar events support active browsing.

### 4:00 - 4:50: Mobile Join and Attendee QR

**Speaker: Muhittin**  
**Controller: Ihsan**

Emir joins the event.

**Actions:**

1. Tap **Going**.
2. Open the attendee QR code sheet or QR section.
3. Show the QR code fullscreen if available.

**Narration point:** Going now creates verifiable attendance, not just a label in the UI.

### 4:50 - 5:50: Host QR Check-In

**Speaker: Can Emir**  
**Controller: Ibrahim or Ihsan, depending on where scanning is available**

Use Mehmet's host-side check-in screen.

**Actions:**

1. Open Mehmet's attendee list/check-in page.
2. Show Emir as Going but not yet checked in.
3. Open scan screen.
4. Scan Emir's QR code from the mobile device.
5. Show successful check-in status.
6. Optionally scan again to show duplicate check-in prevention.

**Narration point:** This demonstrates capacity enforcement at the physical event, not only in the RSVP button.

### 5:50 - 6:40: Mobile Written Review After Event

**Speaker: Muhittin**  
**Controller: Ihsan**

Switch to a pre-prepared completed version of the same event.

**Actions:**

1. Open completed event or Mehmet's host profile from the completed event.
2. Open rate-host section.
3. Select a star rating.
4. Paste this review:

   "Mehmet planned the route clearly, the meeting points were easy to find, and the check-in process made the group feel organized."

5. Submit the rating and review.

**Narration point:** The review is more useful than a number alone because future attendees can understand what Mehmet did well.

### 6:40 - 7:20: Web Host Profile Review Verification

**Speaker: Can Emir**  
**Controller: Ibrahim**

Return to web as Mehmet or a public viewer.

**Actions:**

1. Open Mehmet's host profile.
2. Show aggregate rating.
3. Show the new written review in the reviews section.

**Narration point:** The event lifecycle now ends with visible trust signals on the host profile.

### 7:20 - 8:00: Closing

**Speaker: Can Emir**

Summarize the covered features:

- Web event creation with location search, route mapping, itinerary timeline, and equipment badges.
- Recommendation notification and Suggested discovery on mobile.
- Similar event discovery from event detail.
- QR-based attendee verification.
- Written host reviews after completion.

Close with one sentence:

"Together, these features make the platform more personalized before the event, more organized during the event, and more trustworthy after the event."

## 6. Demo Data Strategy

### Required users

- **Mehmet Kaya**: authenticated web user, host.
- **Emir Demir**: authenticated mobile user, attendee.

### Pre-populated attendance history

Emir must have at least one ended event attendance in categories such as:

- Bird Observation
- Nature
- Hiking

This is required for:

- Recommendation notification eligibility.
- Suggested for you filter behavior.

### Pre-populated recommendation path

Prepare either:

- A live publish path that reliably emits an `event_recommended` notification for Emir, or
- A seeded notification already visible in Emir's notification feed.

The notification should point to Mehmet's event and include a short reason such as:

"Based on bird observation events you attended."

### Event creation data

Prepare Mehmet's event details in advance so the controller can paste quickly:

- **Title:** Belgrad Forest Bird Observation Route
- **Category:** Bird Observation / Nature
- **Visibility:** Public, unless private access fallback is needed.
- **Meeting point:** M6 Bogazici University Metro / Hisarustu.
- **Route stops:** At least two Belgrad Forest locations.
- **Equipment required:** Binoculars.
- **Equipment optional:** Water, snacks.
- **Description:** A small, guided bird observation route with clear meeting points and a planned itinerary.

### QR check-in data

Make sure:

- Emir can mark himself Going.
- QR code appears after Going.
- Mehmet can access host attendee list/check-in screen.
- Scanner works on the demo device, or a manual QR payload fallback is available.
- Duplicate scan behavior is either stable enough to show or skipped.

### Completed event and review data

Prepare a completed event associated with Mehmet where Emir is eligible to rate Mehmet. This avoids waiting for real event completion during the live demo.

Review text to paste:

"Mehmet planned the route clearly, the meeting points were easy to find, and the check-in process made the group feel organized."

## 7. Role Assignments

- **Web Controller:** Ibrahim
- **Web Presenter:** Can Emir
- **Mobile Presenter:** Muhittin
- **Mobile Controller:** Ihsan
- **Time Keeper:** Battal
- **Customer Observer:** Mustafa

Presenter means the person talks and explains the value of the feature. Controller means the person operates the web or mobile app and performs the clicks, taps, scans, and form entries.

## 8. Demo-Day Checklist

- Mehmet and Emir are already logged in before the demo starts.
- Web app has create-event form data ready to paste.
- Mobile app has notification feed ready and map/list discovery stable.
- Emir has past attended events so Suggested for you is meaningful.
- Mehmet's event appears in mobile discovery after publishing.
- Similar events section has at least one result.
- QR check-in works on the selected devices.
- Completed event is available for rating.
- Host profile displays written reviews.
- Private access-request fallback is prepared only if recommendation/check-in is unstable.
