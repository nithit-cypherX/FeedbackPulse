// FeedbackPulse Load & Concurrency Benchmark (k6)
//
// Usage:
//   k6 run -e TARGET=https://<endpoint>/predict -e TOKEN=<token> -e VUS=2 loadtest/k6.js
//
// Run at concurrency levels (e.g., VUs=1, VUs=2 [Proposal on Point 3 SLA], VUs=10)
// and record p50, p95, p99, throughput, and error rate.
//
// "An uncommitted load test is not evidence."

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate } from 'k6/metrics';

const latency = new Trend('predict_latency_ms');
const failures = new Rate('predict_failures');

// Target SLA from Proposal §3: p95 latency <= 3000ms (3.0s) at 2 concurrent requests
export const options = {
  vus: Number(__ENV.VUS || 2),
  duration: __ENV.DURATION || '30s',
  thresholds: {
    // SLA constraint defined BEFORE measurement
    'predict_latency_ms': ['p(95)<3000'],
    'predict_failures': ['rate<0.01'],
  },
};

// Representative customer feedback dataset
const feedbackSamples = [
  'The customer service representative at the gate was incredibly polite and helpful.',
  'My flight was delayed for 5 hours without any clear communication or meal vouchers.',
  'The aircraft was clean and departed precisely on schedule at 10:15 AM.',
  'Completely unacceptable baggage handling! My suitcase was damaged upon arrival.',
  'Smooth check-in experience and very comfortable legroom in economy plus.',
  'Worst flying experience ever. Missed my connection because of a maintenance delay.',
  'Flight attendants provided refreshments promptly and maintained a pleasant demeanor.',
  'The in-flight entertainment screen was frozen throughout the entire transcontinental journey.',
];

export default function () {
  const targetUrl = __ENV.TARGET || 'https://feedbackpulse-api.redground-de34b2df.eastasia.azurecontainerapps.io/predict';
  const token = __ENV.TOKEN || 'test-service-token-secret-12345';

  // Pick sample round-robin based on iteration
  const text = feedbackSamples[__ITER % feedbackSamples.length];
  const payload = JSON.stringify({ text: text });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    timeout: '30s',
  };

  const res = http.post(targetUrl, payload, params);

  latency.add(res.timings.duration);
  failures.add(res.status !== 200);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'sentiment present': (r) => r.status === 200 && r.json('sentiment') !== undefined,
    'score present': (r) => r.status === 200 && typeof r.json('score') === 'number',
    'model version reported': (r) => r.status === 200 && r.json('model_version') === 'sentiment-6e7ff9fbc17c-0110c462',
  });

  // Short pause between iterations to model realistic user arrival rate
  sleep(0.1);
}
