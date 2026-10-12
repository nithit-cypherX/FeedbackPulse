# FeedbackPulse — Model Card

Updated: 11 October 2026. Summarises the existing P02 evaluation; no new evaluation
was run for this card.

## 1. Intended use

Help people group short English customer feedback for human review. The API
returns `negative`, `neutral` or `positive`, a score and a model version.
It does not write replies or decide how urgent a message is.

## 2. Model

| Item | Value |
|---|---|
| Source | CardiffNLP's `cardiffnlp/twitter-roberta-base-sentiment-latest` |
| Pinned revision | `3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7` |
| Registered model version | `sentiment-6e7ff9fbc17c-0110c462` |

We use pretrained weights. Our pipeline evaluates, packages and registers the
model; it does not train or fine-tune it. The [registry entry](reports/registry/sentiment-6e7ff9fbc17c-0110c462.json)
links this version to the artifact hashes, code commit, data and evaluation run.

## 3. Evaluation data

CrowdFlower's **Twitter US Airline Sentiment**, Kaggle dataset
`crowdflower/twitter-airline-sentiment/versions/4`: **14,640 labelled tweets**.
We used all rows, skipped none and made no train/test split because we did not
train on this dataset. It is evaluation data, not our training data.

## 4. Recorded results

The registered run finished on **7 October 2026 (UTC)**.

| Metric | Result |
|---|---:|
| Accuracy | 0.8100 |
| Macro F1 | 0.7606 |
| Negative F1 | 0.8867 |
| Neutral F1 | 0.6150 |
| Positive F1 | 0.7800 |

Neutral is the weakest class. About 62.7% of the dataset is negative, so we use
macro F1 to avoid letting the largest class dominate the summary.

These results came from the pinned upstream snapshot on macOS 15.5 ARM64 with
Python 3.13.11, not an Azure evaluation. P02 also checked the packaged model
against that snapshot on 300 rows and reported matching logits and labels.
See the [recorded evaluation](reports/registry/run-20261007T192531Z-d36357-evaluation.json)
and [P02 evidence](reports/P02-evidence.md) for the full results and environment.

## 5. Limits and safe use

- Results cover short English airline feedback, not every industry or language.
  Crowdsourced labels also contain disagreement.
- The API accepts at most **510 content tokens**, not 510 characters. Longer
  input is rejected rather than silently cut off.
- `score` is the chosen class's softmax score (0–1). A score of 0.9 does not
  establish that the answer has a 90% chance of being correct.
- Keep a person responsible for interpreting results. Avoid submitting personal
  or sensitive data: the local demo sends text to the deployed API.

## 6. Credits and licences

As recorded in P02: the **CardiffNLP model** uses **CC BY 4.0**, and the
**CrowdFlower dataset** uses **CC BY-NC-SA 4.0**. These are separate licences,
not a single licence for the whole project. Source links are in the
[proposal](PROPOSAL.md#2-model-and-dataset); version pins and hashes are in the
registry entry above.
