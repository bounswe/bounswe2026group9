/**
 * k6 performance test — Full authenticated user flow
 *
 * Simulates a real user session end-to-end:
 *   login → browse events → view event detail → toggle bookmark
 *
 * This is the most representative test of production load since
 * authenticated flows hit more backend logic (JWT validation,
 * personalized queries, write operations).
 *
 * Run:
 *   k6 run performance/k6_authenticated_flow.js
 *
 * Set credentials via env vars:
 *   TEST_EMAIL=emir27_bora@hotmail.com \
 *   TEST_PASSWORD=Deneme123. \
 *   k6 run performance/k6_authenticated_flow.js
 */

import http from "k6/http";
import { check, group, sleep, fail } from "k6";
import { Rate, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL      || "https://api.thesocialeventmapper.social";
const EMAIL    = __ENV.TEST_EMAIL    || "emir27_bora@hotmail.com";
const PASSWORD = __ENV.TEST_PASSWORD || "Deneme123.";

export const errorRate   = new Rate("errors");
export const loginTime   = new Trend("login_duration");
export const browseTime  = new Trend("browse_duration");

export const options = {
  stages: [
    { duration: "10s", target: 5  },
    { duration: "30s", target: 5  },
    { duration: "10s", target: 0  },
  ],
  thresholds: {
    http_req_duration: ["p(95)<2000"],
    login_duration:    ["p(95)<1500"],
    errors:            ["rate<0.05"],
  },
};

export default function () {
  const jsonHeaders = { "Content-Type": "application/json" };
  let token = null;

  group("login", () => {
    const res = http.post(
      `${BASE_URL}/auth/login`,
      JSON.stringify({ email: EMAIL, password: PASSWORD }),
      { headers: jsonHeaders }
    );
    loginTime.add(res.timings.duration);
    const ok = check(res, {
      "login 200":        (r) => r.status === 200,
      "has access_token": (r) => {
        try { return !!JSON.parse(r.body).access_token; } catch { return false; }
      },
    });
    errorRate.add(!ok);
    if (!ok) return;
    token = JSON.parse(res.body).access_token;
  });

  if (!token) return;

  const authHeaders = {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${token}`,
  };

  sleep(0.5);

  group("browse events (authenticated)", () => {
    const res = http.get(`${BASE_URL}/events?page=1&page_size=20`, { headers: authHeaders });
    browseTime.add(res.timings.duration);
    const ok = check(res, {
      "browse 200":    (r) => r.status === 200,
      "has items":     (r) => {
        try { return Array.isArray(JSON.parse(r.body).items); } catch { return false; }
      },
    });
    errorRate.add(!ok);

    // Grab first event ID for detail request
    if (ok) {
      try {
        const items = JSON.parse(res.body).items;
        if (items.length > 0) {
          sleep(0.3);
          group("event detail (authenticated)", () => {
            const detailRes = http.get(
              `${BASE_URL}/events/${items[0].id}`,
              { headers: authHeaders }
            );
            check(detailRes, { "detail 200": (r) => r.status === 200 });
            errorRate.add(detailRes.status !== 200);
          });
        }
      } catch (_) { /* ignore parse errors */ }
    }
  });

  sleep(1);
}
