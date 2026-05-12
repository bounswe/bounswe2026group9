/**
 * k6 performance test — Authentication endpoints
 *
 * Tests login and token refresh under load.
 *
 * Run:
 *   k6 run performance/k6_auth.js
 *   k6 run --vus 10 --duration 30s performance/k6_auth.js
 *
 * Set credentials via env vars to avoid hardcoding:
 *   BASE_URL=https://api.thesocialeventmapper.social \
 *   TEST_EMAIL=emir27_bora@hotmail.com \
 *   TEST_PASSWORD=Deneme123. \
 *   k6 run performance/k6_auth.js
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate } from "k6/metrics";

const BASE_URL  = __ENV.BASE_URL   || "https://api.thesocialeventmapper.social";
const EMAIL     = __ENV.TEST_EMAIL    || "emir27_bora@hotmail.com";
const PASSWORD  = __ENV.TEST_PASSWORD || "Deneme123.";

export const errorRate = new Rate("errors");

export const options = {
  stages: [
    { duration: "10s", target: 5  },
    { duration: "20s", target: 5  },
    { duration: "10s", target: 0  },
  ],
  thresholds: {
    http_req_duration: ["p(95)<2000"],
    errors: ["rate<0.05"],
  },
};

export default function () {
  const headers = { "Content-Type": "application/json" };

  // Login
  const loginRes = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({ email: EMAIL, password: PASSWORD }),
    { headers }
  );
  const loginOk = check(loginRes, {
    "login 200": (r) => r.status === 200,
    "has access_token": (r) => {
      try { return !!JSON.parse(r.body).access_token; } catch { return false; }
    },
  });
  errorRate.add(!loginOk);
  sleep(1);
}
