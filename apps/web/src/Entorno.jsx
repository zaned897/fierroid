import { useEffect, useState } from "react";
import { apiFetch } from "./auth.js";
import "./entorno.css";

export default function Entorno() {
  const [entorno, setEntorno] = useState("comprobando");

  useEffect(() => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    let activo = true;
    apiFetch("/health", { signal: controller.signal, cache: "no-store" })
      .then((health) => {
        if (!health.ok || !["stage", "production", "local", "dev"].includes(health.env)) {
          throw new Error("Entorno desconocido");
        }
        if (activo) setEntorno(health.env);
      })
      .catch(() => {
        if (activo) setEntorno("desconocido");
      })
      .finally(() => clearTimeout(timeout));
    return () => {
      activo = false;
      clearTimeout(timeout);
      controller.abort();
    };
  }, []);

  if (entorno === "production") return null;

  const mensajes = {
    comprobando: "Comprobando entorno…",
    desconocido: "No se pudo confirmar el entorno. Recarga antes de registrar cambios.",
    stage: "STAGE · Entorno de pruebas · Datos separados de producción",
    local: "LOCAL · Entorno de desarrollo",
    dev: "DEV · Entorno de desarrollo",
  };

  return <div className="entorno-aviso" role="status">{mensajes[entorno]}</div>;
}
