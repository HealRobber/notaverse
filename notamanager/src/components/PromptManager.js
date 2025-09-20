import React, { useEffect, useState } from "react";
import { getPrompts, createPrompt, updatePrompt, deletePrompt } from "../api";
import styles from "./PromptManager.module.css";

export default function PromptManager() {
  const [prompts, setPrompts] = useState([]);
  const [newPrompt, setNewPrompt] = useState("");
  const [editPrompts, setEditPrompts] = useState({});

  useEffect(() => {
    loadPrompts();
  }, []);

  async function loadPrompts() {
    const data = await getPrompts();
    // id 오름차순
    data.sort((a, b) => Number(a.id) - Number(b.id));
    setPrompts(data);
  }

  async function handleAdd() {
    if (!newPrompt.trim()) return;
    await createPrompt(newPrompt);
    setNewPrompt("");
    loadPrompts();
  }

  function handleInputChange(id, newText) {
    setEditPrompts((prev) => ({ ...prev, [id]: newText }));
  }

  async function handleUpdate(id) {
    const newValue = editPrompts[id];
    if (newValue !== undefined) {
      if (window.confirm("Are you sure to update this prompt?")) {
        await updatePrompt(id, newValue);
        setEditPrompts((prev) => {
          const updated = { ...prev };
          delete updated[id];
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
    <div className={styles.wrapper}>
      <h1 className={styles.title}>Prompt Manager</h1>

      {/* 새 프롬프트 입력 */}
      <div className={styles.card} style={{ marginBottom: 14 }}>
        <div className={styles.row}>
          <textarea
            className={styles.textarea}
            value={newPrompt}
            onChange={(e) => setNewPrompt(e.target.value)}
            placeholder="Input new prompt"
            spellCheck={false}
          />
          <button onClick={handleAdd} className={`${styles.button} ${styles.buttonPrimary}`}>
            추가
          </button>
        </div>
        <div className={styles.helper}>
          길이가 긴 프롬프트를 붙여넣어도 상자가 세로로 확장되며, 내용이 더 길면 스크롤됩니다.
        </div>
      </div>

      {/* 프롬프트 목록 */}
      <ul className={styles.list}>
        {prompts.map((p) => (
          <li key={p.id} className={styles.listItem}>
            <div className={styles.header}>
              <span className={styles.idBadge}>ID: {p.id}</span>
              <span className={styles.meta}>
                {new Date(p.created_at).toLocaleString()} · {(editPrompts[p.id] ?? p.prompt)?.length.toLocaleString()} chars
              </span>
            </div>

            <div className={styles.row}>
              <textarea
                className={styles.textarea}
                value={editPrompts[p.id] ?? p.prompt}
                onChange={(e) => handleInputChange(p.id, e.target.value)}
                spellCheck={false}
              />
              <div className={styles.actions}>
                <button onClick={() => handleUpdate(p.id)} className={styles.button}>
                  수정
                </button>
                <button onClick={() => handleDelete(p.id)} className={styles.button}>
                  삭제
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
