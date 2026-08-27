import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import Documentation from "./pages/Documentation";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Documentation />
  </StrictMode>,
);

