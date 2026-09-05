import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
// La tipografia viaja en el bundle, no se pide a Google Fonts: es una
// peticion a un tercero en la portada, y el corral tiene mala senal.
// Cada @font-face trae su unicode-range, asi que el navegador solo baja
// el subconjunto que usa: 47 KB para latino.
import "@fontsource-variable/inter";

import App from "./App.jsx";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
