import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { LandingPage } from "./components/LandingPage";
import "./index.css";

const isWorkspace = window.location.pathname === "/app" || window.location.pathname.startsWith("/app/");

createRoot(document.getElementById("root")!).render(
  <StrictMode>{isWorkspace ? <App /> : <LandingPage />}</StrictMode>,
);
