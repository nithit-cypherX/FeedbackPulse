"use strict";

const feedback = document.querySelector("#feedback");
const form = document.querySelector("#feedback-form");
const analyse = document.querySelector("#analyse");
const resultPanel = document.querySelector("#result-panel");
const resultMessage = document.querySelector("#result-message");
const sentiment = document.querySelector("#sentiment");
const score = document.querySelector("#score");
const responseTime = document.querySelector("#response-time");
const modelVersion = document.querySelector("#model-version");
const checkApi = document.querySelector("#check-api");
const apiStatus = document.querySelector("#api-status");
const apiDetail = document.querySelector("#api-detail");
const examples = {
  praise: "The support team was friendly and solved my problem quickly. Thank you!",
  complaint: "My order arrived late and the package was damaged. I am disappointed.",
  other: "I placed an order yesterday and received the confirmation email."
};
let prediction = null;

function resetResult(message = "Your result will appear here after the API responds.") {
  for (const output of [sentiment, score, responseTime, modelVersion]) output.textContent = "—";
  delete sentiment.dataset.value;
  delete resultMessage.dataset.state;
  resultMessage.textContent = message;
}

function invalidateResult() {
  prediction?.abort();
  prediction = null;
  resetResult();
  resultPanel.setAttribute("aria-busy", "false");
  analyse.textContent = "Analyse feedback →";
  analyse.disabled = !feedback.value.trim();
}

async function request(path, options, controller) {
  const timeout = setTimeout(() => controller.abort(), 65000);
  try {
    const response = await fetch(path, {
      ...options, signal: controller.signal, credentials: "omit", cache: "no-store"
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.error?.message || "The request failed. Try again later.");
    return body;
  } catch (error) {
    if (controller.signal.aborted) throw new Error("The request took too long. Try again later.");
    if (error instanceof TypeError) throw new Error("Cannot reach the local relay. Check that it is running.");
    if (error instanceof SyntaxError) throw new Error("The local relay returned an invalid response.");
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

feedback.addEventListener("input", invalidateResult);
document.querySelector("#clear").addEventListener("click", () => {
  feedback.value = "";
  invalidateResult();
  feedback.focus();
});
for (const button of document.querySelectorAll("[data-example]")) {
  button.addEventListener("click", () => {
    feedback.value = examples[button.dataset.example];
    invalidateResult();
    feedback.focus();
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (prediction || !feedback.value.trim()) return;
  const controller = new AbortController();
  prediction = controller;
  resetResult("Waiting for the API… A cold start may take up to a minute.");
  resultMessage.dataset.state = "loading";
  resultPanel.setAttribute("aria-busy", "true");
  analyse.disabled = true;
  analyse.textContent = "Analysing…";
  const started = performance.now();
  try {
    const body = await request("/api/predict", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: feedback.value })
    }, controller);
    if (prediction !== controller) return;
    sentiment.textContent = body.sentiment;
    sentiment.dataset.value = body.sentiment;
    score.textContent = body.score.toFixed(3);
    responseTime.textContent = `${Math.round(performance.now() - started).toLocaleString()} ms`;
    modelVersion.textContent = body.model_version;
    resultMessage.textContent = "Analysis complete. These values came from the API.";
    delete resultMessage.dataset.state;
  } catch (error) {
    if (prediction !== controller) return;
    resetResult(error.message);
    resultMessage.dataset.state = "error";
  } finally {
    if (prediction === controller) {
      prediction = null;
      analyse.disabled = !feedback.value.trim();
      analyse.textContent = "Analyse feedback →";
      resultPanel.setAttribute("aria-busy", "false");
    }
  }
});

checkApi.addEventListener("click", async () => {
  if (checkApi.disabled) return;
  checkApi.disabled = true;
  checkApi.textContent = "Checking…";
  apiStatus.textContent = "Checking";
  apiStatus.dataset.state = "unchecked";
  apiDetail.textContent = "Checking readiness. A cold start may take up to a minute.";
  let detail;
  try {
    await request("/api/ready", { method: "GET" }, new AbortController());
    apiStatus.textContent = "Ready";
    apiStatus.dataset.state = "ready";
    detail = "Ready at this check; this is not continuous monitoring.";
  } catch (error) {
    apiStatus.textContent = "Check failed";
    apiStatus.dataset.state = "error";
    detail = error.message;
  } finally {
    apiDetail.textContent = `Last checked ${new Date().toLocaleTimeString()}. ${detail}`;
    checkApi.disabled = false;
    checkApi.textContent = "Check API";
  }
});
