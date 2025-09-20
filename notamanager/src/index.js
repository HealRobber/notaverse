import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles/tokens.css";     // 전역 토큰 import (이미 하셨다면 생략)

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter basename="/notamanager">
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
