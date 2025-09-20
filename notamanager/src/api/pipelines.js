import { apiFetch, joinUrl } from "./client";

const PIPELINES_BASE = "/gemini-api/pipelines";

export async function getPipelines() {
  // GET /gemini-api/pipelines/
  return apiFetch(joinUrl(PIPELINES_BASE));
}

export async function getPipeline(id) {
  // GET /gemini-api/pipelines/:id
  return apiFetch(joinUrl(PIPELINES_BASE, String(id)));
}

export async function createPipeline({ description, prompt_array }) {
  // POST /gemini-api/pipelines/
  return apiFetch(joinUrl(PIPELINES_BASE), {
    method: "POST",
    body: JSON.stringify({ description, prompt_array }),
  });
}

export async function updatePipeline(id, payload) {
  // PUT /gemini-api/pipelines/:id
  return apiFetch(joinUrl(PIPELINES_BASE, String(id)), {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deletePipeline(id) {
  // DELETE /gemini-api/pipelines/:id
  return apiFetch(joinUrl(PIPELINES_BASE, String(id)), {
    method: "DELETE",
  });
}
