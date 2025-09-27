import { apiFetch } from "./client";

const POST_BASE = "/gemini-api/post";

export async function runPostAsync(payload) {
  const url = `${POST_BASE}/run-async`;
  console.debug("[runPostAsync] POST", url, payload);
  return apiFetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function getJobStatus(jobId) {
  if (!jobId) throw new Error("jobId is required for getJobStatus");
  const url = `${POST_BASE}/status/${encodeURIComponent(jobId)}`;
  console.debug("[getJobStatus] GET", url);
  return apiFetch(url);
}

export async function getJobResult(jobId) {
  if (!jobId) throw new Error("jobId is required for getJobResult");
  const url = `${POST_BASE}/result/${encodeURIComponent(jobId)}`;
  console.debug("[getJobResult] GET", url);
  return apiFetch(url);
}
