export function joinUrl(base, path = "") {
  const b = base.endsWith("/") ? base : base + "/";
  return path ? b + path : b;
}

export async function apiFetch(url, options = {}) {
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  // 실패 응답은 본문을 텍스트로 읽어 에러 메시지로 던집니다.
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${res.statusText} @ ${url}\n${text}`);
  }

  // 204/HTML 등 JSON이 아닐 수 있는 응답도 안전 처리
  const ct = res.headers.get("content-type") || "";
  if (res.status === 204 || !ct.includes("application/json")) {
    return null;
  }
  return res.json();
}
