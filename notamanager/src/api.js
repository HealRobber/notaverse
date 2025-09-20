// api.js
const PROMPTS_BASE = "/gemini-api/prompts";

function joinUrl(base, path = "") {
  const b = base.endsWith("/") ? base : base + "/";
  return path ? b + path : b;
}

async function apiFetch(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  // 실패 시 응답 본문을 텍스트로 읽어서 오류를 명확히 표시
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${res.statusText} @ ${url}\n${text}`);
  }

  const ct = res.headers.get("content-type") || "";
  if (res.status === 204 || !ct.includes("application/json")) return null;
  return res.json();
}

export async function getPrompts() {
  return apiFetch(joinUrl(PROMPTS_BASE));
}

export async function createPrompt(prompt) {
  return apiFetch(joinUrl(PROMPTS_BASE), {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
}

export async function updatePrompt(id, prompt) {
  try {
    // 일반형
    return await apiFetch(joinUrl(PROMPTS_BASE, String(id)), {
      method: "PUT",
      body: JSON.stringify({ prompt }),
    });
  } catch (e) {
    // 서버가 /:id/ (trailing slash)만 허용하는 경우 재시도
    if (String(e).includes("404") || String(e).includes("405")) {
      return apiFetch(joinUrl(PROMPTS_BASE, `${id}/`), {
        method: "PUT",
        body: JSON.stringify({ prompt }),
      });
    }
    throw e;
  }
}

export async function deletePrompt(id) {
  return apiFetch(joinUrl(PROMPTS_BASE, String(id)), { method: "DELETE" });
}
