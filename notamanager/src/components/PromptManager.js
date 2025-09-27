import React, { useEffect, useState } from "react";
import { getPrompts, createPrompt, updatePrompt, deletePrompt } from "../api/prompts";
import { getPipeline } from "../api/pipelines";
import { useSearchParams } from "react-router-dom"; // ★ 이미 추가되어 있다면 유지
import styles from "../styles/ui.module.css";

export default function PromptManager() {
  const [prompts, setPrompts] = useState([]);
  const [visiblePrompts, setVisiblePrompts] = useState([]);  // ★ pipeline 필터링용
  const [newPrompt, setNewPrompt] = useState("");
  const [editPrompts, setEditPrompts] = useState({});
  const [search] = useSearchParams();
  const pipelineId = search.get("pipelineId");               // ★ 파이프라인 진입 여부

  useEffect(() => {
    loadPrompts();
  }, [pipelineId]);

  async function loadPrompts() {
    const data = await getPrompts();
    data.sort((a, b) => Number(a.id) - Number(b.id));
    setPrompts(data);

    if (pipelineId) {
      const pipeline = await getPipeline(pipelineId);
      const ids = parseIds(pipeline?.prompt_array ?? []);
      const order = new Map(ids.map((id, idx) => [Number(id), idx]));
      const filtered = data
        .filter((p) => order.has(Number(p.id)))
        .sort((a, b) => order.get(Number(a.id)) - order.get(Number(b.id)));
      setVisiblePrompts(filtered);
    } else {
      setVisiblePrompts(data);
    }
  }

  function parseIds(val) {
    if (Array.isArray(val)) return val.map(Number).filter((n) => !Number.isNaN(n));
    if (typeof val === "string") {
      try {
        const j = JSON.parse(val);
        if (Array.isArray(j)) return j.map(Number).filter((n) => !Number.isNaN(n));
      } catch {}
      return val.split(",").map((s) => Number(s.trim())).filter((n) => !Number.isNaN(n));
    }
    if (val && typeof val === "object") {
      return Object.values(val).map((v) => Number(v)).filter((n) => !Number.isNaN(n));
    }
    return [];
  }

  async function handleAdd() {
    if (!newPrompt.trim()) return;
    await createPrompt(newPrompt);
    setNewPrompt("");
    await loadPrompts();
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
        await loadPrompts();
      }
    }
  }

  async function handleDelete(id) {
    if (window.confirm("Are you sure you want to delete this prompt?")) {
      await deletePrompt(id);
      await loadPrompts();
    }
  }

  return (
    <div className={styles.wrapper}>
      <h1 className={styles.title}>
        {pipelineId ? `Pipeline ${pipelineId}의 Prompts` : "Prompt Manager"}
      </h1>

      {/* ★ 파이프라인으로 진입한 경우에는 '추가' UI를 숨김 */}
      {!pipelineId && (
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
      )}

      {/* 목록은 visiblePrompts 사용 */}
      <ul className={styles.list}>
        {visiblePrompts.map((p) => (
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

        {!visiblePrompts.length && (
          <li className={styles.listItem}>
            <div className={styles.helper}>
              {pipelineId ? "해당 Pipeline에 연결된 Prompt가 없습니다." : "등록된 Prompt가 없습니다."}
            </div>
          </li>
        )}
      </ul>
    </div>
  );
}