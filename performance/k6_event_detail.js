/**
 * k6 performance test — Event Detail endpoint
 *
 * Event detail is the highest-traffic read path: every event card tap
 * triggers GET /events/{id} plus GET /events/{id}/comments.
 * Tests both endpoints under concurrent load.
 *
 * Run:
 *   k6 run performance/k6_event_detail.js
 *   k6 run --vus 30 --duration 30s performance/k6_event_detail.js
 *
 * Override the event ID:
 *   EVENT_ID=<uuid> k6 run performance/k6_event_detail.js
 */

import http from "k6/http";
import { check, group, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const BASE_URL  = __ENV.BASE_URL  || "https://api.thesocialeventmapper.social";
const EVENT_ID  = __ENV.EVENT_ID  || "4670bef0-75c5-4d3e-821b-f01138140be3";

export const errorRate  = new Rate("errors");
export const detailTime = new Trend("event_detail_duration");
export const commentTime = new Trend("event_comments_duration");

export const options = {
  stages: [
    { duration: "10s", target: 20 },
    { duration: "30s", target: 20 },
    { duration: "10s", target: 0  },
  ],
  thresholds: {
    http_req_duration:    ["p(95)<1000"],
    event_detail_duration: ["p(95)<800"],
    errors:               ["rate<0.05"],
  },
};

export default function () {
  group("event detail page load", () => {
    // Event detail
    const detailRes = http.get(`${BASE_URL}/events/${EVENT_ID}`);
    detailTime.add(detailRes.timings.duration);
    check(detailRes, {
      "event detail 200": (r) => r.status === 200,
      "has event id":     (r) => {
        try { return !!JSON.parse(r.body).id; } catch { return false; }
      },
    });
    errorRate.add(detailRes.status !== 200);
    sleep(0.3);

    // Comments for the same event
    const commentsRes = http.get(`${BASE_URL}/events/${EVENT_ID}/comments?page=1&page_size=20`);
    commentTime.add(commentsRes.timings.duration);
    check(commentsRes, {
      "comments 200": (r) => r.status === 200,
    });
    errorRate.add(commentsRes.status !== 200);
    sleep(0.3);
  });
}
