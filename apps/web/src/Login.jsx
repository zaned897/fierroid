import { useCallback, useEffect, useRef, useState } from "react";

import { CowIcon } from "./icons/cows.jsx";

const GSI_SRC = "https://accounts.google.com/gsi/client";
const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

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
    if (!listo || !CLIENT_ID || !contenedor.current) return;

    window.google.accounts.id.initialize({
      client_id: CLIENT_ID,
      callback: alRecibirCredencial,
    });
    window.google.accounts.id.renderButton(contenedor.current, {
      theme: "filled_black",
      size: "large",
      shape: "pill",
      text: "signin_with",
      locale: "es",
    });
  }, [listo, alRecibirCredencial]);

  return (
    <div className="page login">
      <CowIcon variant="frente" size={72} className="cow" />
      <p className="brand">Fierro</p>
      <p className="lede">Pesajes de ganado, del corral a tu bolsillo.</p>

      {!CLIENT_ID && (
        <p className="error">
          Falta <code>VITE_GOOGLE_CLIENT_ID</code>. Configúralo en el <code>.env</code> de
          la raíz y reinicia el servidor de desarrollo.
        </p>
      )}

      <div ref={contenedor} className="gsi" />

      {entrando && <p className="muted">Entrando…</p>}
      {(error || errorScript) && <p className="error">{error || errorScript}</p>}

      <p className="muted fine">
        El acceso es por invitación: tu correo debe estar dado de alta.
      </p>
    </div>
  );
}
