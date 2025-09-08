import React, { useEffect, useState } from "react";
import { getPrompts, createPrompt, updatePrompt, deletePrompt } from "../api";

export default function PromptManager() {
  const [prompts, setPrompts] = useState([]);
  const [newPrompt, setNewPrompt] = useState("");
  const [editPrompts, setEditPrompts] = useState({});

  useEffect(() => {
    loadPrompts();
  }, []);

  async function loadPrompts() {
    const data = await getPrompts();
    setPrompts(data);
  }

  async function handleAdd() {
    if (!newPrompt.trim()) return;
    await createPrompt(newPrompt);
    setNewPrompt("");
    loadPrompts();
  }

  async function handleInputChange(id, newText) {
    setEditPrompts((prev) => ({ ...prev, [id]: newText }));
  }

  async function handleUpdate(id) {
    const newValue = editPrompts[id];
    if (newValue !== undefined) {
      if (window.confirm("Are you sure to update this prompt?")) {
        await updatePrompt(id, newValue);
        setEditPrompts((prev) => {
        const updated = { ...prev };
        delete updated[id]; // 업데이트 후 편집 상태 삭제
        return updated;
      });
      loadPrompts();
      }
    }
  }

  async function handleDelete(id) {
    if (window.confirm("Are you sure you want to delete this prompt?")) {
        await deletePrompt(id);
        loadPrompts();
    }
  }

  return (
    <div>
      <h1>Prompt Manager</h1>
      <div style={{ marginBottom: "10px" }}>
        <input
          style={{ padding: "5px", width: "300px" }}
          value={newPrompt}
          onChange={(e) => setNewPrompt(e.target.value)}
          placeholder="Input new prompt"
        />
        <button onClick={handleAdd} style={{ marginLeft: "10px" }}>
          추가
        </button>
      </div>
      <ul style={{ listStyle: "none", padding: 0 }}>
        {prompts.map((p) => (
          <li key={p.id} style={{ marginBottom: "8px" }}>
            <input
              style={{ width: "300px", padding: "5px" }}
              value={editPrompts[p.id] ?? p.prompt} // 편집 중 값 있으면 우선 표시
              onChange={(e) => handleInputChange(p.id, e.target.value)}
            />
            <button
              onClick={() => handleUpdate(p.id)}
              style={{ marginLeft: "10px" }}
            >
              수정
            </button>
            <button
              onClick={() => handleDelete(p.id)}
              style={{ marginLeft: "10px" }}
            >
              삭제
            </button>
            <span style={{ marginLeft: "10px", fontSize: "12px", color: "#555" }}>
              {new Date(p.created_at).toLocaleString()}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
