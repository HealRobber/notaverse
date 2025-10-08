// src/App.jsx
import React from "react";
import { Routes, Route, NavLink } from "react-router-dom";
import PostRunner from "./components/PostRunner";
import PromptManager from "./components/PromptManager";
import PipelinesManager from "./components/PipelineManager";
import nav from "./styles/topnav.module.css"; // ★ 추가

export default function App() {
  return (
    <>
      <nav className={nav.topnav}>
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            [nav.link, isActive && nav.active].filter(Boolean).join(" ")
          }
        >
          Init Content
        </NavLink>
        <NavLink
          to="/prompt"
          className={({ isActive }) =>
            [nav.link, isActive && nav.active].filter(Boolean).join(" ")
          }
        >
          Prompts
        </NavLink>
        <NavLink
          to="/pipelines"
          className={({ isActive }) =>
            [nav.link, isActive && nav.active].filter(Boolean).join(" ")
          }
        >
          Pipelines
        </NavLink>
      </nav>

      <Routes>
        <Route path="/" element={<PostRunner />} />
        <Route path="/prompt" element={<PromptManager />} />
        <Route path="/pipelines" element={<PipelinesManager />} />
      </Routes>
    </>
  );
}
