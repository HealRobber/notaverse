const API_URL = "/gemini-api/prompts/";

export async function getPrompts() {
  const res = await fetch(API_URL);
  return res.json();
}

export async function createPrompt(prompt) {
  const res = await fetch(API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
  return res.json();
}

export async function updatePrompt(id, prompt) {
  const res = await fetch(`${API_URL}${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
  return res.json();
}

export async function deletePrompt(id) {
  await fetch(`${API_URL}${id}`, {
    method: "DELETE",
  });
}