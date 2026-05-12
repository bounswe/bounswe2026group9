/**
 * k6 performance test — Health & Categories (lightweight smoke)
 *
 * Verifies the API stays responsive under light concurrent load.
 * Good baseline to run before/after deployments.
 *
 * Run:
 *   k6 run performance/k6_health.js
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "https://api.thesocialeventmapper.social";

export const errorRate = new Rate("errors");

export const options = {
  vus: 20,
  duration: "30s",
  thresholds: {
    http_req_duration: ["p(95)<500"], // health + categories must be fast
    errors: ["rate<0.01"],
  },
};

export default function () {
  // Health check
  let res = http.get(`${BASE_URL}/health`);
  check(res, {
    "health 200": (r) => r.status === 200,
    "database connected": (r) => {
      try { return JSON.parse(r.body).database === "connected"; } catch { return false; }
    },
  });
  errorRate.add(res.status !== 200);
  sleep(0.3);

  // Categories listing
  res = http.get(`${BASE_URL}/categories`);
  check(res, {
    "categories 200": (r) => r.status === 200,
    "returns array": (r) => {
      try { return Array.isArray(JSON.parse(r.body)); } catch { return false; }
    },
  });
  errorRate.add(res.status !== 200);
  sleep(0.3);
}
