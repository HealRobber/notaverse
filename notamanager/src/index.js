// src/main.jsx  (Vite 기준. CRA면 index.js 형태)
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles/tokens.css";  // 전역 토큰
import "./styles/base.css"

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter basename="/notamanager">
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
