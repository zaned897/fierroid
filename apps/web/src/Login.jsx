import { useCallback, useEffect, useRef, useState } from "react";

import { CowIcon } from "./icons/cows.jsx";

const GSI_SRC = "https://accounts.google.com/gsi/client";

/**
 * El client ID lo sirve la API, no lo inyecta el build.
 *
 * Antes venía de `import.meta.env.VITE_GOOGLE_CLIENT_ID`, que Vite resuelve al
 * construir. Eso significaba el mismo valor configurado en dos lugares, y que
 * un despliegue del front sin esa variable produce un bundle donde el botón
 * ni siquiera se intenta dibujar — el minificador elimina el efecto entero
 * porque puede probar que siempre retorna. Falla en silencio y solo se ve
 * leyendo el bundle compilado.
 *
 * Pidiéndolo en tiempo de ejecución hay una sola fuente y el error, si lo hay,
 * es visible: una petición que falla.
 */
function useClientId() {
  const [estado, setEstado] = useState({ cargando: true, clientId: null, error: null });

  useEffect(() => {
    let vivo = true;
    fetch("/v1/auth/config")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((cfg) => {
        if (!vivo) return;
        setEstado({
          cargando: false,
          clientId: cfg.google_client_id || null,
          error: cfg.google_client_id ? null : "La API no tiene configurado el inicio de sesión con Google.",
        });
      })
      .catch((err) => {
        if (vivo) setEstado({ cargando: false, clientId: null, error: `No se pudo contactar la API: ${err.message}` });
      });
    return () => {
      vivo = false;
    };
  }, []);

  return estado;
}

/** Carga el script de Google una sola vez, aunque el componente se remonte. */
function useGoogleScript() {
  const [listo, setListo] = useState(() => Boolean(window.google?.accounts?.id));
  const [error, setError] = useState(null);

  useEffect(() => {
    if (listo) return undefined;

    let script = document.querySelector(`script[src="${GSI_SRC}"]`);
    if (!script) {
      script = document.createElement("script");
      script.src = GSI_SRC;
      script.async = true;
      document.head.appendChild(script);
    }

    const alCargar = () => setListo(true);
    const alFallar = () =>
      setError("No se pudo cargar el inicio de sesión de Google. Revisa tu conexión.");

    script.addEventListener("load", alCargar);
    script.addEventListener("error", alFallar);
    return () => {
      script.removeEventListener("load", alCargar);
      script.removeEventListener("error", alFallar);
    };
  }, [listo]);

  return { listo, error };
}

export default function Login({ onSession, exchange }) {
  const contenedor = useRef(null);
  const { listo, error: errorScript } = useGoogleScript();
  const { cargando, clientId, error: errorConfig } = useClientId();
  const [error, setError] = useState(null);
  const [entrando, setEntrando] = useState(false);

  const alRecibirCredencial = useCallback(
    async (respuesta) => {
      setEntrando(true);
      setError(null);
      try {
        onSession(await exchange(respuesta.credential));
      } catch (err) {
        // El caso más común no es un fallo técnico: es alguien que no está
        // dado de alta. El mensaje del servidor ya lo explica.
        setError(err.message);
      } finally {
        setEntrando(false);
      }
    },
    [exchange, onSession],
  );

  useEffect(() => {
    if (!listo || !clientId || !contenedor.current) return;

    window.google.accounts.id.initialize({
      client_id: clientId,
      callback: alRecibirCredencial,
    });
    window.google.accounts.id.renderButton(contenedor.current, {
      theme: "filled_black",
      size: "large",
      shape: "pill",
      text: "signin_with",
      locale: "es",
    });
  }, [listo, clientId, alRecibirCredencial]);

  return (
    <div className="page login">
      <CowIcon variant="frente" size={72} className="cow" />
      <p className="brand">Fierro</p>
      <p className="lede">Pesajes de ganado, del corral a tu bolsillo.</p>

      <div ref={contenedor} className="gsi" />

      {cargando && <p className="muted">Cargando…</p>}
      {entrando && <p className="muted">Entrando…</p>}
      {(error || errorScript || errorConfig) && (
        <p className="error">{error || errorScript || errorConfig}</p>
      )}

      <p className="muted fine">
        El acceso es por invitación: tu correo debe estar dado de alta.
      </p>
    </div>
  );
}
