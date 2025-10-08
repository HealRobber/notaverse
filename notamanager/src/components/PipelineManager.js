// src/components/PipelinesManager.jsx
import React, { useEffect, useState } from "react";
import { getPipelines, createPipeline, deletePipeline } from "../api/pipelines";
import { useNavigate } from "react-router-dom";
import styles from "../styles/ui.module.css";

export default function PipelinesManager() {
  const [pipelines, setPipelines] = useState([]);
  const [description, setDescription] = useState("");
  const [promptArrayText, setPromptArrayText] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    load();
  }, []);

  async function load() {
    try {
      const data = await getPipelines();
      console.debug("[PipelinesManager] getPipelines raw response:", data);

      // id 오름차순 정렬
      data.sort((a, b) => Number(a.id) - Number(b.id));
      setPipelines(data);
    } catch (e) {
      console.error("[PipelinesManager] load error:", e);
    }
  }

  function parsePromptArray(text) {
    if (!text.trim()) return [];
    return text
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .map((n) => Number(n))
      .filter((n) => !Number.isNaN(n));
  }

  async function handleCreate() {
    const arr = parsePromptArray(promptArrayText);
    if (!description.trim()) {
      alert("description을 입력해 주세요.");
      return;
    }
    try {
      await createPipeline({ description, prompt_array: arr });
      setDescription("");
      setPromptArrayText("");
      await load();
    } catch (e) {
      alert(`생성 중 오류: ${e?.message || e}`);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm("이 파이프라인을 삭제하시겠습니까?")) return;
    try {
      await deletePipeline(id);
      await load();
    } catch (e) {
      alert(`삭제 중 오류: ${e?.message || e}`);
    }
  }

  function goToPipeline(p) {
    navigate(`/prompt?pipelineId=${p.id}`);
  }

  function renderPromptArray(val) {
    if (Array.isArray(val)) return val.join(", ");
    if (typeof val === "string") {
      // "[1,2,3]" 같은 JSON 문자열 처리
      try {
        const parsed = JSON.parse(val);
        if (Array.isArray(parsed)) return parsed.join(", ");
      } catch {}
      // "1,2,3" 같은 CSV 처리
      return val;
    }
    if (val && typeof val === "object") {
      try { return Object.values(val).join(", "); } catch {}
    }
    return "";
  }

  return (
    <div className={styles.wrapper}>
      <h1 className={styles.title}>Pipelines</h1>

      {/* 생성 카드 */}
      <div className={styles.card} style={{ marginBottom: 14 }}>
        <div className={styles.row}>
          <input
            style={{ flex: 1, padding: 10, border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)" }}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Pipeline description (예: 기사요약 v2)"
          />
          <button onClick={handleCreate} className={`${styles.button} ${styles.buttonPrimary}`}>
            등록
          </button>
        </div>
        <div className={styles.row}>
          <input
            style={{ flex: 1, padding: 10, border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)" }}
            value={promptArrayText}
            onChange={(e) => setPromptArrayText(e.target.value)}
            placeholder="prompt_array: 쉼표로 구분된 id (예: 1,2,3,4)"
          />
        </div>
        <div className={styles.helper}>
          description·prompt id 목록을 등록합니다. 예: description=“기사요약v2”, prompt_array=“12,15,21”
        </div>
      </div>

      {/* 목록 */}
      <ul className={styles.list}>
        {pipelines.map((p) => {
          console.debug("[PipelinesManager] rendering pipeline:", p);

          return (
            <li key={p.id} className={styles.listItem}>
              <div className={styles.header}>
                <span className={styles.idBadge}>Pipeline ID: {p.id}</span>
                <span className={styles.meta}>{new Date(p.created_at).toLocaleString()}</span>
              </div>

              <div style={{ marginBottom: 8, fontWeight: 600 }}>
                {p.description || "(no description)"}
              </div>

              <div className={styles.helper} style={{ marginBottom: 8 }}>
                prompt_array: {renderPromptArray(p.prompt_array)}
              </div>

              <div className={styles.actions} style={{ flexDirection: "row", gap: 8 }}>
                <button
                  onClick={() => goToPipeline(p)}
                  className={`${styles.button} ${styles.buttonPrimary}`}
                >
                  이 파이프라인의 Prompt 보기
                </button>
                <button onClick={() => handleDelete(p.id)} className={`${styles.button} ${styles.buttonDanger}`}>
                  삭제
                </button>
              </div>
            </li>
          );
        })}

      </ul>
    </div>
  );
}
