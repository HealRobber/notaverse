import React from "react";
import { Link, useLocation } from "react-router-dom";

export default function Header() {
  const loc = useLocation();
  const tab = (path) =>
    ({
      borderBottom: loc.pathname.startsWith(path) ? "2px solid #2563eb" : "2px solid transparent",
      padding: "8px 12px",
      textDecoration: "none",
      color: "#111827",
    });

  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center", padding: 12, borderBottom: "1px solid #eee" }}>
      <Link to="/pipelines" style={tab("/pipelines")}>Pipelines</Link>
      <Link to="/prompt" style={tab("/prompt")}>All Prompts</Link>
    </div>
  );
}
