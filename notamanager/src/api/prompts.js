import { apiFetch, joinUrl } from "./client";

const PROMPTS_BASE = "/gemini-api/prompts";

export async function getPrompts() {
  // GET /gemini-api/prompts/
  return apiFetch(joinUrl(PROMPTS_BASE));
}

export async function createPrompt(prompt) {
  // POST /gemini-api/prompts/
  return apiFetch(joinUrl(PROMPTS_BASE), {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
}

export async function updatePrompt(id, prompt) {
  // PUT /gemini-api/prompts/:id  (trailing slash 강제 시 재시도 로직을 여기에 추가해도 됨)
  return apiFetch(joinUrl(PROMPTS_BASE, String(id)), {
    method: "PUT",
    body: JSON.stringify({ prompt }),
  });
}

export async function deletePrompt(id) {
  // DELETE /gemini-api/prompts/:id
  return apiFetch(joinUrl(PROMPTS_BASE, String(id)), {
    method: "DELETE",
  });
}
