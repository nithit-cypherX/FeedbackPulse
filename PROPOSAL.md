# FeedbackPulse — Capstone Proposal

**Team:** 3D team 
6688033 Jinnapat Jaiphoom
6688124 Nithit Teeraworawit
6688166 Supawit Sirikulpiboon

## 1. Problem and users

Customer support teams receive complaints, praise, and general comments.
FeedbackPulse is a backend API that classifies short English feedback as
**negative, neutral, or positive**, helping a calling system group messages for
human review. It does not reply to customers or decide urgency. A frontend and
CRM integration are outside the scope.

## 2. Model and dataset

We will use a pinned revision of
[CardiffNLP's Twitter RoBERTa sentiment model](https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest),
published under **CC BY 4.0**. Following the instructor's guidance on pretrained
models, we will not train or fine-tune it.

[Twitter US Airline Sentiment](https://www.kaggle.com/datasets/crowdflower/twitter-airline-sentiment),
version 4, under **CC BY-NC-SA 4.0**, will provide evaluation and demonstration
data. We will credit the sources and follow their licence terms. Results will
describe performance on airline feedback, not prove equal performance across
all industries.

## 3. Serving pattern and requirements

We will deploy an access-controlled online API on **Azure Container Apps,
Consumption plan**, because callers need a result for each submitted message.
Responses will contain sentiment, score, and model version. Invalid inputs and
model unavailability will return clear errors.

We target **end-to-end p95 latency <= 3 seconds at two concurrent requests**,
with the model loaded, using a versioned test set. Error rates and cold-start
time will be reported separately. Feedback is analysed when submitted; model
updates happen through checked releases. The service will scale to zero when
idle.

## 4. MLOps scope

We will version the code, evaluation data, model revision, and environment. An
automated evaluation and packaging pipeline will produce a registered model
with lineage. Reproducibility covers our integration workflow, not the original
model's training.

CI/CD will run meaningful tests before deployment. A dashboard will show
request counts, latency, and errors, with at least one working alert.
Deliverables include rollback and teardown instructions, a reproducible README,
a one-page model card, and cost per 1,000 predictions.

## 5. Planned failure

In a test deployment, we will make the model artifact unavailable. The service
should fail its readiness check, avoid misleading predictions, and trigger an
alert for the model-loading failure. We will restore the working version,
verify recovery, and add a regression test based on the incident.

## 6. Cost estimate

Our planning budget is **USD 15 for 30 days**, using Southeast Asia pricing and
excluding free grants. Assumptions are 20 total replica-hours at 2 vCPU and
4 GiB RAM, one Basic container registry, 5 GB of blob storage, and 0.1 GB of log
ingestion.

Estimated main charges are **$11.45**, with **$3.55** reserved for alerts,
requests, network, operations, and uncertainty. This is not a guaranteed
spending cap. Development will mainly run locally; resource sizing and actual
costs will be checked during implementation.

## 7. Team responsibilities

- Model integration and evaluation: **[Name]**
- API, deployment, and CI/CD: **[Name]**
- Monitoring, failure demonstration, and cost documentation: **[Name]**

Responsibilities may be shared between members.
