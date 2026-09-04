import { useCallback, useEffect, useRef, useState } from "react";

import Shell from "./Shell.jsx";

const GSI_SRC = "https://accounts.google.com/gsi/client";
const ULTIMO = "fierro.ultimo-proveedor";

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
    const alFallar = () => setError("No se pudo cargar el inicio de sesión de Google.");
    script.addEventListener("load", alCargar);
    script.addEventListener("error", alFallar);
    return () => {
      script.removeEventListener("load", alCargar);
      script.removeEventListener("error", alFallar);
    };
  }, [listo]);

  return { listo, error };
}

/**
 * Rellena `providers` cuando la API todavía no lo manda.
 *
 * La PWA se despliega sola al mergear y la API a mano, así que siempre hay una
 * ventana con el front adelante. Sin esto, esa ventana deja a todo el mundo
 * fuera: la lista llega vacía y la pantalla dice que no hay proveedores, lo
 * cual es falso. Hay uno; la API es vieja.
 *
 * Se apoya en `google_enabled`, que es el mismo dato con el que el servidor
 * arma la lista. Se puede borrar cuando ninguna API desplegada conteste sin
 * `providers`.
 */
function normalizar(config) {
  if (Array.isArray(config.providers)) return config;
  return {
    ...config,
    providers: config.google_enabled ? [{ id: "google", name: "Google" }] : [],
  };
}

/**
 * Qué proveedores existen lo decide la API, no el bundle.
 *
 * Antes el client ID venía de una variable de build. Cuando el build no la
 * veía, el minificador eliminaba el efecto que dibuja el botón —podía probar
 * que siempre retornaba— y la página se veía bien, sin botón y sin error.
 * Pedirlo en tiempo de ejecución convierte ese fallo silencioso en una
 * petición que falla a la vista.
 */
function useProveedores() {
  const [estado, setEstado] = useState({ cargando: true, config: null, error: null });

  useEffect(() => {
    let vivo = true;
    fetch("/v1/auth/config")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((config) => {
        if (vivo) setEstado({ cargando: false, config: normalizar(config), error: null });
      })
      .catch((err) => {
        if (vivo) {
          setEstado({
            cargando: false,
            config: null,
            error: `No se pudo contactar la API: ${err.message}`,
          });
        }
      });
    return () => {
      vivo = false;
    };
  }, []);

  return estado;
}

function leerUltimo() {
  try {
    return localStorage.getItem(ULTIMO);
  } catch {
    return null;
  }
}

function guardarUltimo(id) {
  try {
    localStorage.setItem(ULTIMO, id);
  } catch {
    // Recordar el proveedor es una comodidad, no un requisito.
  }
}

/** Botón de Google, dibujado por Google. */
function BotonGoogle({ clientId, onCredencial, ancho }) {
  const contenedor = useRef(null);
  const { listo, error } = useGoogleScript();

  useEffect(() => {
    if (!listo || !clientId || !contenedor.current) return;

    window.google.accounts.id.initialize({ client_id: clientId, callback: onCredencial });
    // Lo dibuja Google y no nosotros: sus lineamientos de marca lo exigen, y un
    // botón propio se rompe cada vez que cambian el flujo por dentro.
    window.google.accounts.id.renderButton(contenedor.current, {
      theme: "filled_black",
      size: "large",
      shape: "rectangular",
      text: "continue_with",
      locale: "es",
      width: ancho,
    });
  }, [listo, clientId, onCredencial, ancho]);

  return (
    <>
      <div ref={contenedor} className="gsi" />
      {error && <p className="error">{error}</p>}
    </>
  );
}

export default function Login({ onSession, exchange, onInicio }) {
  const { cargando, config, error: errorConfig } = useProveedores();
  const [error, setError] = useState(null);
  const [entrando, setEntrando] = useState(false);
  const [ancho, setAncho] = useState(320);
  const columna = useRef(null);
  const ultimo = leerUltimo();

  // Google dibuja su botón con un ancho en píxeles, no con CSS.
  useEffect(() => {
    const medir = () => {
      const w = columna.current?.getBoundingClientRect().width;
      if (w) setAncho(Math.round(Math.min(Math.max(w, 200), 400)));
    };
    medir();
    window.addEventListener("resize", medir);
    return () => window.removeEventListener("resize", medir);
  }, [cargando]);

  const alRecibirCredencial = useCallback(
    async (respuesta) => {
      setEntrando(true);
      setError(null);
      try {
        const sesion = await exchange(respuesta.credential);
        guardarUltimo("google");
        onSession(sesion);
      } catch (err) {
        // El caso común no es un fallo técnico: es alguien sin invitación.
        setError(err.message);
      } finally {
        setEntrando(false);
      }
    },
    [exchange, onSession],
  );

  const proveedores = config?.providers ?? [];

  return (
    <Shell lema="Del corral a tu bolsillo.">
      <button type="button" className="volver" onClick={onInicio}>
        ← Inicio
      </button>

      <h1 className="titulo">Entrar a Fierro</h1>
      <p className="subtitulo">Continúa con:</p>

      <div className="proveedores" ref={columna}>
        {cargando && <p className="muted">Cargando…</p>}

        {proveedores.map((p) => (
          <div key={p.id} className="proveedor">
            {ultimo === p.id && <span className="ultimo">Última vez</span>}
            {p.id === "google" && (
              <BotonGoogle
                clientId={config.google_client_id}
                onCredencial={alRecibirCredencial}
                ancho={ancho}
              />
            )}
          </div>
        ))}

        {!cargando && proveedores.length === 0 && !errorConfig && (
          <p className="error">
            La API no tiene configurado ningún proveedor de inicio de sesión.
          </p>
        )}
      </div>

      {entrando && <p className="muted">Entrando…</p>}
      {(error || errorConfig) && <p className="error">{error || errorConfig}</p>}

      <p className="pie">El acceso es por invitación: tu correo debe estar dado de alta.</p>
    </Shell>
  );
}
