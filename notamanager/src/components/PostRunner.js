import React, { useEffect, useMemo, useRef, useState } from "react";
import { runPostAsync } from "../api/post";      // 실행 등록(accepted + job_id 반환)
import { apiFetch } from "../api/client";        // 상태/결과는 템플릿 문자열로 직접 호출
import styles from "../styles/ui.module.css";

const POST_BASE = "/gemini-api/post";

/** 상태 조회: /gemini-api/post/status/:job_id */
async function fetchJobStatus(jobId) {
  if (!jobId) throw new Error("jobId is required");
  const url = `${POST_BASE}/status/${encodeURIComponent(jobId)}`;
  return apiFetch(url);
}

/** 결과 조회: /gemini-api/post/result/:job_id */
async function fetchJobResult(jobId) {
  if (!jobId) throw new Error("jobId is required");
  const url = `${POST_BASE}/result/${encodeURIComponent(jobId)}`;
  return apiFetch(url);
}

export default function PostRunner() {
  const [topic, setTopic] = useState("");
  const [photoCount, setPhotoCount] = useState(1);
  const [llmModel, setLlmModel] = useState("");
  const [targetChars, setTargetChars] = useState(1200);

  const [jobId, setJobId] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [clientLogs, setClientLogs] = useState([]);
  const pollRef = useRef(null);

  const log = (line) =>
    setClientLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${line}`]);

  async function handleRun() {
    setError("");
    setResult(null);
    setClientLogs([]);
    setJobId("");

    if (!topic.trim()) {
      setError("topic을 입력해 주세요.");
      return;
    }
    const n = Number(photoCount);
    if (Number.isNaN(n) || n < 0) {
      setError("photo_count는 0 이상의 숫자여야 합니다.");
      return;
    }
    const tc = Number(targetChars);
    if (Number.isNaN(tc) || tc < 100 || tc > 20000) {
      setError("글자수는 100~20000 사이의 숫자여야 합니다.");
      return;
    }

    setRunning(true);
    log("작업 등록 요청");
    try {
      const resp = await runPostAsync({
        topic: topic.trim(),
        photo_count: n,
        llm_model: llmModel.trim() || null,
        target_chars: tc,
      });

      if (resp && resp.status === "accepted" && resp.job_id) {
        setJobId(resp.job_id);
        log(`작업 수락됨: job_id=${resp.job_id}`);
      } else {
        const msg = (resp && resp.detail) || "작업 등록에 실패했습니다.";
        setError(msg);
        setRunning(false);
      }
    } catch (e) {
      const msg = e?.message || String(e);
      setError(msg);
      setRunning(false);
    }
  }

  useEffect(() => {
    async function poll() {
      if (!jobId) return;
      try {
        const st = await fetchJobStatus(jobId);

        // step 로그 갱신
        if (st && st.steps) {
          const lines = Object.keys(st.steps)
            .sort((a, b) => Number(a) - Number(b))
            .map((k) => `Step ${k}: ${st.steps[k]}`);
          setClientLogs((prev) => {
            const base = prev.filter((line) => !line.startsWith("Step "));
            return base.concat(lines);
          });
        }

        if (st.status === "done") {
          const r = await fetchJobResult(jobId);
          if (r && r.status === "ok") setResult(r.result || null);
          setRunning(false);
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
          log("작업 완료");
        } else if (st.status === "error") {
          setError(st.error || "서버에서 오류가 발생했습니다.");
          setRunning(false);
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
          log("작업 실패");
        }
      } catch (e) {
        // 일시적 네트워크 오류는 폴링 유지
        // console.warn("[poll] error (jobId:", jobId, ")", e);
      }
    }

    if (jobId && !pollRef.current) {
      pollRef.current = setInterval(poll, 2000); // 2초 간격
      poll(); // 즉시 1회
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [jobId]);

  const stepLogs = useMemo(() => {
    const onlySteps = clientLogs.filter((l) => l.startsWith("Step "));
    return onlySteps.map((msg, i) => ({ key: i, msg }));
  }, [clientLogs]);

  return (
    <div className={styles.wrapper}>
      <h1 className={styles.title}>Init Content Runner</h1>

      {/* 입력 */}
      <div className={`${styles.card} ${styles.mb14}`}>
        <div className={styles.row}>
          {/* 왼쪽: Topic textarea */}
          <textarea
            className={`${styles.textarea} ${styles.flexGrow}`}
            placeholder="Topic을 입력하세요"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            spellCheck={false}
          />

          {/* 오른쪽: 설정 박스 */}
          <div className={styles.minCol}>
            <input
              type="number"
              min={0}
              max={10}
              value={photoCount}
              onChange={(e) => setPhotoCount(e.target.value)}
              placeholder="photo_count (0~10)"
              className={`${styles.input} ${styles.mb8}`}
            />
            <input
              type="text"
              value={llmModel}
              onChange={(e) => setLlmModel(e.target.value)}
              placeholder="llm_model (선택)"
              className={`${styles.input} ${styles.mb8}`}
            />
            <input
              type="number"
              min={100}
              max={20000}
              value={targetChars}
              onChange={(e) => setTargetChars(e.target.value)}
              placeholder="글자수(예: 1200)"
              className={`${styles.input} ${styles.mb8}`}
            />
            <button
              className={`${styles.button} ${styles.buttonPrimary}`}
              onClick={handleRun}
              disabled={running}
            >
              {running ? "실행 중…" : "실행"}
            </button>
          </div>
        </div>

        <div className={styles.helper}>
          호출 흐름: <code>POST /gemini-api/post/run-async</code> →{" "}
          <code>GET /gemini-api/post/status/:job_id</code> →{" "}
          <code>GET /gemini-api/post/result/:job_id</code>
        </div>
        {error ? (
          <div
            className={styles.helper}
            style={{ color: "var(--color-danger)", marginTop: 8 }}
          >
            오류: {error}
          </div>
        ) : null}
      </div>

      {/* 상태 & 로그 */}
      <div className={`${styles.card} ${styles.mb14}`}>
        <div className={styles.header}>
          <span className={styles.idBadge}>실행 상태</span>
          <span className={styles.meta}>
            {running
              ? jobId
                ? `실행 중 · job=${jobId.slice(0, 8)}…`
                : "작업 등록 중"
              : result
              ? "완료"
              : error
              ? "실패"
              : "대기"}
          </span>
        </div>

        <div className={styles.helper} style={{ marginBottom: 8 }}>
          Client Logs
        </div>
        <pre className={styles.pre}>
          {clientLogs.length ? clientLogs.join("\n") : "(로그 없음)"}
        </pre>

        <div className={styles.helper} style={{ margin: "12px 0 6px" }}>
          Step Logs
        </div>
        <ul className={styles.list}>
          {stepLogs.length ? (
            stepLogs.map(({ key, msg }) => (
              <li key={key} className={styles.listItem}>
                <div className={styles.helper}>{msg}</div>
              </li>
            ))
          ) : (
            <li className={styles.listItem}>
              <div className={styles.helper}>(결과 수신 후 표시됩니다)</div>
            </li>
          )}
        </ul>
      </div>

      {/* 결과 요약 */}
      <div className={styles.card}>
        <div className={styles.header}>
          <span className={styles.idBadge}>결과 요약</span>
        </div>
        {result ? (
          <>
            <div className={styles.row}>
              <div className={styles.helper}>
                pipeline_id: <b>{result.pipeline_id}</b>
              </div>
              <div className={styles.helper}>
                uploaded_images: <b>{result.uploaded_images}</b>
              </div>
              {result.llm_model ? (
                <div className={styles.helper}>
                  llm_model: <b>{result.llm_model}</b>
                </div>
              ) : null}
              {result.target_chars ? (
                <div className={styles.helper}>
                  target_chars: <b>{result.target_chars}</b>
                </div>
              ) : null}
            </div>

            {(result.tags && result.tags.length) ||
            (result.categories && result.categories.length) ? (
              <div className={styles.row}>
                <div className={styles.helper}>
                  tags: {Array.isArray(result.tags) ? result.tags.join(", ") : ""}
                </div>
                <div className={styles.helper}>
                  categories:{" "}
                  {Array.isArray(result.categories)
                    ? result.categories.join(", ")
                    : ""}
                </div>
              </div>
            ) : null}

            {result.post ? (
              <div className={styles.row}>
                <div className={styles.helper}>
                  post:{" "}
                  {result.post.link ? (
                    <a href={result.post.link} target="_blank" rel="noreferrer">
                      {result.post.link}
                    </a>
                  ) : (
                    JSON.stringify(result.post)
                  )}
                </div>
              </div>
            ) : null}

            <div className={styles.helper} style={{ marginTop: 10 }}>
              Raw 결과(JSON)
            </div>
            <pre className={styles.pre} style={{ minHeight: 120 }}>
              {JSON.stringify(result, null, 2)}
            </pre>
          </>
        ) : (
          <div className={styles.helper}>(아직 결과가 없습니다)</div>
        )}
      </div>
    </div>
  );
}
