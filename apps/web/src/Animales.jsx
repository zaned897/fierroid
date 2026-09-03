import { useCallback, useEffect, useRef, useState } from "react";

import { apiFetch } from "./auth.js";
import { CowForTag } from "./icons/cows.jsx";
import { fetchPhotoUrl, reducirImagen } from "./photo.js";

function formatKg(kg) {
  return kg == null ? "—" : `${Number(kg).toFixed(1)} kg`;
}

/** Miniatura: la foto real si existe, el icono determinista si no. */
function Retrato({ animal, session, size = 56, recarga }) {
  const [url, setUrl] = useState(null);

  useEffect(() => {
    if (!animal.has_photo) {
      setUrl(null);
      return undefined;
    }
    let vivo = true;
    let actual = null;

    fetchPhotoUrl(animal.tag_id, session).then((nueva) => {
      if (!vivo) {
        if (nueva) URL.revokeObjectURL(nueva);
        return;
      }
      actual = nueva;
      setUrl(nueva);
    });

    return () => {
      vivo = false;
      // Sin revocar, cada re-render filtra un blob en memoria.
      if (actual) URL.revokeObjectURL(actual);
    };
  }, [animal.has_photo, animal.tag_id, session, recarga]);

  if (url) {
    return <img className="retrato" src={url} alt="" width={size} height={size} />;
  }
  return <CowForTag tagId={animal.tag_id} size={size} className="cow" />;
}

function Ficha({ animal, session, onCerrar, onCambio }) {
  const archivo = useRef(null);
  const [alias, setAlias] = useState(animal.alias || "");
  const [notes, setNotes] = useState(animal.notes || "");
  const [error, setError] = useState(null);
  const [ocupado, setOcupado] = useState(null);
  const [recarga, setRecarga] = useState(0);

  const guardar = useCallback(async () => {
    setOcupado("datos");
    setError(null);
    try {
      await apiFetch(`/v1/animals/${encodeURIComponent(animal.tag_id)}`, {
        session,
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ alias: alias || null, notes: notes || null }),
      });
      onCambio();
    } catch (err) {
      setError(err.message);
    } finally {
      setOcupado(null);
    }
  }, [alias, notes, animal.tag_id, session, onCambio]);

  const subirFoto = useCallback(
    async (evento) => {
      const elegido = evento.target.files?.[0];
      if (!elegido) return;

      setOcupado("foto");
      setError(null);
      try {
        const cuerpo = new FormData();
        cuerpo.append("file", await reducirImagen(elegido));

        const res = await fetch(`/v1/animals/${encodeURIComponent(animal.tag_id)}/photo`, {
          method: "POST",
          headers: { Authorization: `Bearer ${session.api_key}` },
          body: cuerpo,
        });
        if (!res.ok) {
          const detalle = await res.json().catch(() => ({}));
          throw new Error(detalle.detail || "No se pudo subir la foto");
        }
        setRecarga((n) => n + 1);
        onCambio();
      } catch (err) {
        setError(err.message);
      } finally {
        setOcupado(null);
        // Permite volver a elegir el mismo archivo tras un error.
        evento.target.value = "";
      }
    },
    [animal.tag_id, session, onCambio],
  );

  return (
    <section className="panel ficha" aria-label={`Ficha de ${animal.tag_id}`}>
      <div className="row">
        <h2>{animal.alias || "Sin nombre"}</h2>
        <button type="button" className="ghost" onClick={onCerrar}>
          Cerrar
        </button>
      </div>

      <div className="ficha-retrato">
        <Retrato animal={animal} session={session} size={160} recarga={recarga} />
      </div>

      <dl className="datos">
        <dt>Arete</dt>
        <dd className="tag">{animal.tag_id}</dd>
        <dt>Último peso</dt>
        <dd>{formatKg(animal.last_weight_kg)}</dd>
        <dt>Pesajes</dt>
        <dd>{animal.readings ?? 0}</dd>
      </dl>

      <label className="campo">
        Nombre
        <input value={alias} onChange={(e) => setAlias(e.target.value)} placeholder="La Pinta" />
      </label>

      <label className="campo">
        Notas
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
      </label>

      <div className="acciones">
        <button type="button" onClick={guardar} disabled={ocupado !== null}>
          {ocupado === "datos" ? "Guardando…" : "Guardar"}
        </button>
        <button type="button" onClick={() => archivo.current?.click()} disabled={ocupado !== null}>
          {ocupado === "foto" ? "Subiendo…" : animal.has_photo ? "Cambiar foto" : "Subir foto"}
        </button>
        {/* capture: en el celular abre la cámara directo, que es el caso de uso. */}
        <input
          ref={archivo}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          capture="environment"
          onChange={subirFoto}
          hidden
        />
      </div>

      {error && <p className="error">{error}</p>}
    </section>
  );
}

export default function Animales({ session, onExpired }) {
  const [animales, setAnimales] = useState([]);
  const [abierto, setAbierto] = useState(null);
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(true);

  const recargar = useCallback(async () => {
    try {
      const body = await apiFetch("/v1/animals", { session });
      setAnimales(body.animals || []);
      setError(null);
    } catch (err) {
      if (err.unauthorized) onExpired();
      else setError(err.message);
    } finally {
      setCargando(false);
    }
  }, [session, onExpired]);

  useEffect(() => {
    recargar();
  }, [recargar]);

  const seleccionado = animales.find((a) => a.tag_id === abierto);

  if (seleccionado) {
    return (
      <Ficha
        animal={seleccionado}
        session={session}
        onCerrar={() => setAbierto(null)}
        onCambio={recargar}
      />
    );
  }

  return (
    <section className="panel" aria-label="Animales">
      <h2>Animales</h2>
      {cargando && <p className="muted">Cargando…</p>}
      {error && <p className="error">{error}</p>}
      {!cargando && animales.length === 0 && (
        <p className="muted">
          Todavía no hay animales. Aparecen solos en cuanto pasan por la manga.
        </p>
      )}
      <ul className="animal-list">
        {animales.map((animal) => (
          <li key={`${animal.org}-${animal.tag_id}`}>
            <button type="button" className="animal" onClick={() => setAbierto(animal.tag_id)}>
              <Retrato animal={animal} session={session} />
              <span className="animal-body">
                <span className="animal-nombre">{animal.alias || "Sin nombre"}</span>
                <span className="meta">
                  <span className="tag">{animal.tag_id}</span>
                  <span>{formatKg(animal.last_weight_kg)}</span>
                </span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
