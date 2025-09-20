import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import PromptManager from "./components/PromptManager";

export default function App() {
  return (
    <Routes>
      <Route path="/prompt" element={<PromptManager />} />
      {/* / 에 오면 /prompt로 보내기 */}
      <Route path="/" element={<Navigate to="/prompt" replace />} />
      {/* 기타 경로도 /prompt로 리다이렉트 */}
      <Route path="*" element={<Navigate to="/prompt" replace />} />
    </Routes>
  );
}
