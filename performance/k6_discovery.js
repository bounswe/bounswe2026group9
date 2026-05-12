/**
 * k6 performance test — Event Discovery endpoint
 *
 * Tests the primary discovery flow under load:
 *   - unauthenticated listing
 *   - search query
 *   - category filter
 *   - quick filter (today / upcoming)
 *
 * Run:
 *   k6 run performance/k6_discovery.js
 *   k6 run --vus 20 --duration 30s performance/k6_discovery.js
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "https://api.thesocialeventmapper.social";

export const errorRate = new Rate("errors");

export const options = {
  stages: [
    { duration: "10s", target: 10 }, // ramp up
    { duration: "20s", target: 10 }, // steady
    { duration: "10s", target: 0  }, // ramp down
  ],
  thresholds: {
    http_req_duration: ["p(95)<1500"], // 95% of requests under 1.5 s
    errors: ["rate<0.05"],             // error rate below 5%
  },
};

export default function () {
  const headers = { "Content-Type": "application/json" };

  // 1. Plain listing
  let res = http.get(`${BASE_URL}/events?page=1&page_size=20`, { headers });
  check(res, { "listing 200": (r) => r.status === 200 });
  errorRate.add(res.status !== 200);
  sleep(0.5);

  // 2. Search
  res = http.get(`${BASE_URL}/events?search=music&page=1`, { headers });
  check(res, { "search 200": (r) => r.status === 200 });
  errorRate.add(res.status !== 200);
  sleep(0.5);

  // 3. Quick filter — today
  res = http.get(`${BASE_URL}/events?quick_filter=today&page=1`, { headers });
  check(res, { "quick filter 200": (r) => r.status === 200 });
  errorRate.add(res.status !== 200);
  sleep(0.5);

  // 4. Category filter
  res = http.get(`${BASE_URL}/events?quick_filter=upcoming&page=1`, { headers });
  check(res, { "upcoming 200": (r) => r.status === 200 });
  errorRate.add(res.status !== 200);
  sleep(0.5);
}
