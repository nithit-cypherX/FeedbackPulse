# Cost per 1,000 predictions

**Prepared: 11 October 2026. Currency: USD. This is a scenario estimate, not an
Azure bill or a measured 1,000-request run.**

With the assumptions below, we estimate **$0.0653 for compute and requests**
per 1,000 successful predictions. Including the listed registry and monitoring
costs gives **about $5.43 for a 30-day period with 1,000 predictions**. The second
number is a subtotal of the main items, not an all-inclusive cost or spending cap.

## What we checked

The current Malaysia West deployment uses the Consumption plan, **1 vCPU and
2 GiB per replica**, with scaling from 0 to 3 replicas. The
[app template](../cloudlayer/containerapp.template.yaml) records the same sizing.
The Basic ACR and Log Analytics workspace are shared with coursework labs.

Our 11 October read-only check showed $1.91 in October resource-group costs,
including $1.72 for the shared ACR. There was no separate FeedbackPulse cost
line yet; that does not prove the App costs $0. Existing logs contained 13
successful `POST /predict` access-log entries that day. We cannot divide the
shared monthly bill by this small, possibly incomplete count and call it the
App's actual cost per 1,000 predictions.

## Scenario assumptions

These are planning choices, not measured usage:

| Input | Assumption |
|---|---|
| Period and output | 30 days; 1,000 successful predictions |
| Replica running time | 30 total replica-minutes (1,800 seconds), including startup/model loading and time before scale-to-zero |
| Traffic pattern | Short usage sessions; replicas scale to zero outside them, not continuous traffic throughout the month |
| External HTTP requests | 1,100: 1,000 successful predictions plus 100 other requests, such as status checks or failed attempts |
| Log ingestion | 0.1 GB attributable to FeedbackPulse in the period; this volume is carried over from the proposal, not measured |
| Registry allocation | Charge the whole Basic registry to this scenario for 30 days, as if the project paid for it alone |
| Monitoring | One traffic-alert time series, using the Portal's recorded $0.10/month estimate |

Two replicas running for 15 minutes each count as 30 replica-minutes. Azure
charges allocated resources while replicas run, not just model inference time.
With a minimum of zero, running replicas are above the minimum, so we use the
active rates. Platform health probes are not billable HTTP requests; the 100
extra requests above are external calls. See [Azure's billing rules](https://learn.microsoft.com/en-us/azure/container-apps/billing).

We do **not** derive the 30 minutes from the team's East Asia p95 or the three
Malaysia West browser timings. Neither measures total replica running time.
The scenario assumes 1,000 predictions fit within this time; we have not tested
that workload. More sessions, cold starts, retries or scale-out can increase it.

## Rates and calculation

Malaysia West USD retail rates checked on 11 October 2026, before free
allowances, student credits, discounts and tax:

| Item | Rate | Source |
|---|---:|---|
| Active CPU | $0.000028 per vCPU-second | [ACA rates](https://prices.azure.com/api/retail/prices?%24filter=serviceName%20eq%20%27Azure%20Container%20Apps%27%20and%20armRegionName%20eq%20%27malaysiawest%27) |
| Active memory | $0.000004 per GiB-second | Same ACA rates |
| External requests | $0.468 per million | Same ACA rates |
| Basic registry | $0.1666 per day | [ACR rates](https://prices.azure.com/api/retail/prices?%24filter=serviceName%20eq%20%27Container%20Registry%27%20and%20armRegionName%20eq%20%27malaysiawest%27%20and%20skuName%20eq%20%27Basic%27) |
| Analytics Logs ingestion | $2.691 per GB, paid tier | [Log Analytics rates](https://prices.azure.com/api/retail/prices?%24filter=serviceName%20eq%20%27Log%20Analytics%27%20and%20armRegionName%20eq%20%27malaysiawest%27) |
| Traffic alert | $0.10 per month, Portal estimate | [Recorded alert setup](../demo/README.md#traffic-alert--p05-t02-part-3) |

```text
Compute = replica-seconds x (vCPU x CPU rate + GiB x memory rate)
        = 1,800 x (1 x 0.000028 + 2 x 0.000004) = $0.0648
Requests = 1,100 / 1,000,000 x 0.468 = $0.0005148
Compute + requests = $0.0653148

Cost per 1,000 = costs for the period / successful predictions in that period x 1,000
```

| Main item | Calculation | Estimated cost |
|---|---|---:|
| Compute and requests | As above | $0.0653148 |
| Registry | 30 x $0.1666 | $4.9980 |
| Logs | 0.1 x $2.691 | $0.2691 |
| Traffic alert | One month | $0.1000 |
| **Main-items subtotal** | **Sum before rounding** | **$5.4324148 (about $5.43)** |

Because this scenario has exactly 1,000 successful predictions in the period,
the subtotal is also its main-items cost per 1,000. It is not a fixed price for
every additional 1,000 predictions: registry and alert costs are spread over
the period's volume. We do not claim the whole shared registry bill actually
belongs to FeedbackPulse.

## Limits and what could change the result

- **Running time matters.** Keeping requests at 1,100, compute plus requests is
  about $0.0329 at 15 replica-minutes, $0.0653 at 30, or $0.1301 at 60. These are
  sensitivity examples, not benchmark results or guaranteed bounds.
- **Free allowances can reduce the bill.** We leave them and student credits
  out so the estimate does not depend on unused benefits shared with other
  apps. We have not calculated the account's remaining allowance.
- **Some items are excluded, not claimed to be free:** network transfer,
  registry storage above the included capacity, extra log retention, CI/build,
  local development/evaluation, and tax. Basic ACR includes 10 GiB of storage;
  this scenario assumes it stays within that amount, not that we audited all
  shared registry storage. See [ACR limits](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-skus).
- **No separate model blob-storage charge is added.** This deployment ships
  the model inside its image. We do not copy the proposal's 5 GB blob-storage
  assumption into this serving estimate.
- **To report actual cost later**, use attributed costs and successful
  predictions from the same period, account for shared services explicitly,
  and allow billing data to arrive. No new load test was run for this report.

The calculation was checked in both seconds and hours. No Azure configuration
was changed to prepare this report.
