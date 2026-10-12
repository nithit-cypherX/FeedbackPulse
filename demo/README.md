# Local demo — P05

A single HTML/CSS/JavaScript page served by the local Python relay. It does not
load a model, create Azure resources or change the API/CD. There is no frontend
build step or extra dependency.

From `/home/nirvana/feedbackpulse`, use the existing Python 3.13 `.venv`:

```bash
# Set this to the HTTPS origin of the API you intend to demonstrate.
export FEEDBACKPULSE_API_URL='https://<your-app>.<your-environment>.azurecontainerapps.io'
# Enter that API's SERVICE_TOKEN without echoing it or putting it in shell history.
read -rsp 'Service token: ' SERVICE_TOKEN; echo
export SERVICE_TOKEN
.venv/bin/python -m demo.server
# Press Ctrl+C to stop, then remove the token from this shell.
unset SERVICE_TOKEN
```

While the server is running, open **http://127.0.0.1:8080** in your browser.

- Type English feedback or choose an example, then click **Analyse feedback**.
  Examples only fill the input; they do not contain preset predictions.
- Results show the API's sentiment, score (0–1) and model version. Response time
  measures this page's round trip, not p95 or model inference alone.
- Editing the input or clicking **Clear** removes the old result. If a request
  is pending, its response is ignored; the server may already have sent it upstream.
- **Check API** makes one readiness request and records the check time. It does
  not poll or claim that the service stays healthy after that check.
- The page starts with no result and **Not checked**. Errors and timeouts never
  become sample results. A browser request has a 65-second deadline, allowing the
  relay's 60-second timeout to return first.

No feedback history or token is stored in browser storage. Avoid personal data;
submitted text is still sent to the configured API. Only `demo/static/` is served
as static content, not the repository or its environment files.

## Open monitoring — P05-T02, part 2

Click **Open monitoring ↗** next to **Check API** to open
[FeedbackPulse — API Monitoring](https://portal.azure.com/#@student.mahidol.ac.th/dashboard/private/ad763481-176e-4f6f-a279-f4ebbdec412f)
in a new tab. It is a **private Azure dashboard**: use the owner's Azure account.
The link does not grant access or send the API token. It always points to our
Malaysia West `feedbackpulse-api`, even if the local relay is configured for a
different API. There is no new monitoring page or automatic polling in the demo.

| Chart | What it shows |
|---|---|
| Requests — total | Azure `Requests`, Sum: number of requests in each time bucket |
| Average response time — ms | Azure `ResponseTime`, Avg (Preview): average response time, not p95 or the browser round trip |
| HTTP errors — 4xx / 5xx | `Requests`, Sum, filtered to and split by `statusCodeCategory`: 4xx and 5xx counts, not error percentages |

All charts cover the **whole App**, not just `/predict`, and inherit the dashboard
time range (default **Past 24 hours, UTC**). Use **Refresh** manually; Azure metrics
can arrive after a delay. An absent series means Azure returned no data for that
category; we do not turn it into a measured zero. No alert was created in this step.

The exported [dashboard JSON](../cloudlayer/azure-dashboard.json) preserves the
layout and metric settings. In Azure Portal's Dashboard view, use **Upload** to
import it as a private dashboard; uploading does not deploy or change the App.
It references the current Azure resource ID, contains no credential, and still
requires access to that resource. The portal export's `INSERT LOCATION` field
is unchanged: this is a dashboard import file, not an ARM deployment template.

Evidence: [Azure dashboard](../reports/screenshots/p05-t02-part2-azure-dashboard-2026-10-11.jpg)
and [demo monitoring button](../reports/screenshots/p05-t02-part2-demo-monitoring-2026-10-11.jpg).
The demo screenshot is a local UI check with fake configuration, not a new live
API test. Opening the link was checked against the real Azure dashboard.

The server binds to `127.0.0.1:8080` only. Do not expose it to a network or tunnel:
it uses the operator's API token, not per-user login. It accepts same-origin web
requests and local command-line requests; other browser origins/hosts are rejected.
Configuration comes only from environment variables. It does not read `.env`
files automatically, and it never sends the token to the browser.

| Local request | Azure request | Input / result |
|---|---|---|
| `POST /api/predict` | `POST /predict`, with server-side Bearer token | JSON containing only a non-empty `text`; returns `sentiment`, `score`, `model_version` |
| `GET /api/ready` | `GET /ready`, without token | Returns `status` and `model_version` only when upstream reports ready |

The Azure API still enforces its 510-token limit; the relay does not tokenize text.
There is one upstream attempt with a 60-second total deadline (10-second connect
timeout), no automatic retry and no redirect following. A slow/cold API can time
out; a later attempt must be explicit. TLS verification stays enabled and the
HTTP client ignores environment proxies. Browser headers/cookies/query parameters
and arbitrary destinations are not forwarded. Upstream errors become short,
fixed JSON messages; raw HTML, response headers and exception details are not
returned. Responses use `Cache-Control: no-store`; request bodies and tokens are
not logged by the relay, and its supported entrypoint disables access logs.

## Traffic alert — P05-T02, part 3

`feedbackpulse-traffic-spike` watches the existing Malaysia West App. It alerts
when **Total Requests >= 20 over one minute**, checked every minute, at severity
**2 — Warning**. The `feedbackpulse-traffic-email` action group has one email
receiver, chosen by the owner. Automatic resolution is enabled.

This is a small-demo threshold, not the App's measured capacity. The seven-day
query before setup returned 24 requests with a peak of 6 in one minute. The rule
counts the whole App, not only `/predict` or one caller. It can flag unexpected
client retries, but it neither blocks requests nor proves an outage or attack.
When notified, open the dashboard and compare request volume, latency and errors.

Azure Portal estimated **USD 0.10/month** for this one monitored time series,
before any applicable free allowance; this is not an actual cost report. The
test also uses the existing App's compute. No new App, role, model, API/CD change
or log-query alert was needed.

On 2026-10-11, one readiness preflight returned HTTP 200 in 41.591 seconds. Then
25 sequential `GET /ready` requests all returned HTTP 200 between
**15:36:05 and 15:36:34 UTC**, taking 28.874 seconds in total. No token or prediction
was sent. The one-shot burst stopped after 25 requests and did not retry.
This checks a request-volume alert, not inference performance or model failure.

**Verified:** Azure recorded 25 requests in its `15:37:00 UTC` one-minute metric
bucket. The actual alert evaluated Total = 25 against >= 20 and was recorded as
**Fired at 15:39:43 UTC (22:39:43 Asia/Bangkok)**, about three minutes after the
burst ended. The owner confirmed receiving the alert email, not a welcome or
action-group test email. Email receipt is a user confirmation; we did not inspect
the mailbox or save an email screenshot.

At the end of the 11 October 2026 check, the rule was enabled with automatic
resolution configured. A Resolved transition was not verified. No additional
traffic was sent as part of that check after the one-shot burst. This is not a
live status check. Evidence: [rule configuration](../reports/screenshots/p05-t02-part3-traffic-rule-2026-10-11.jpg)
and [actual alert](../reports/screenshots/p05-t02-part3-traffic-fired-2026-10-11.jpg).

## Offline checks

```bash
.venv/bin/python -m pytest -q tests/test_demo.py
.venv/bin/ruff check demo/server.py tests/test_demo.py
```

These tests use a mock HTTP transport and fake credentials. Passing them does
not prove a live Azure round trip. The separate live check is recorded below.

## Live check — 2026-10-11 (P05-T01, part 3)

The browser page called the normal local relay, which called the existing
Malaysia West API at
`https://feedbackpulse-api.happybay-6ab85ce1.malaysiawest.azurecontainerapps.io`.
The relay used the existing token from ignored `cloud.env`; no token was put in
the browser or evidence. No mock transport was used in this check.

**Check API** returned Ready at 21:00:34 Asia/Bangkok. Each built-in example was
then submitted once. All three returned model version
`sentiment-6e7ff9fbc17c-0110c462`.

| Example | API sentiment | Displayed score | Browser round trip | Screenshot |
|---|---|---:|---:|---|
| Praise | positive | 0.934 | 1,195 ms | [Live positive](../reports/screenshots/p05-t01-part3-live-positive-2026-10-11.jpg) |
| Complaint | negative | 0.936 | 642 ms | [Live negative](../reports/screenshots/p05-t01-part3-live-negative-2026-10-11.jpg) |
| Other | neutral | 0.746 | 767 ms | [Live neutral](../reports/screenshots/p05-t01-part3-live-neutral-2026-10-11.jpg) |

These are three individual UI requests, not an accuracy evaluation, p95 benchmark
or cold-start measurement. Scores are rounded to three decimals by the page.
The earlier part-2 screenshots remain explicitly labelled as mock evidence.
The local test server was stopped after verification; the Azure app was not
changed. API/CD, dependencies and cloud resources were left untouched.
