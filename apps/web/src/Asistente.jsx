import { useState } from "react";
import { apiFetch } from "./auth.js";
import "./asistente.css";

const SUGERIDAS = [
  "¿Qué vaca tiene problemas?",
  "¿Cuántas vacas tengo registradas?",
  "¿Cuál es el peso total hasta hoy?",
];

function Chips({ consultas }) {
  if (!consultas || consultas.length === 0) return null;

  let animales = null;
  let pesajes = null;
  let incompleta = false;

  for (const c of consultas) {
    if (c.animales != null) {
      animales = animales == null ? c.animales : Math.max(animales, c.animales);
    }
    if (c.pesajes_revisados != null) {
      pesajes = pesajes == null ? c.pesajes_revisados : Math.max(pesajes, c.pesajes_revisados);
    }
    if (c.lectura_incompleta) {
      incompleta = true;
    }
  }

  if (animales == null && pesajes == null && !incompleta) return null;

  return (
    <div className="asistente-chips" aria-label="Datos revisados">
      {animales != null && <span className="asistente-chip">Revisé {animales} animales</span>}
      {pesajes != null && <span className="asistente-chip">{pesajes} pesajes</span>}
      {incompleta && (
        <span className="asistente-chip asistente-chip-incompleta">Solo pesajes recientes</span>
      )}
    </div>
  );
}

function enlazarAretes(linea, aretes, onAbrir) {
  const validos = (aretes || []).filter(Boolean);
  if (validos.length === 0 || !onAbrir) return linea;

  const ordenados = [...new Set(validos)].sort((a, b) => b.length - a.length);
  const patron = new RegExp(
    `(${ordenados.map((a) => a.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`,
    "g",
  );
  const conjunto = new Set(ordenados);

  return linea.split(patron).map((parte, indice) =>
    conjunto.has(parte) ? (
      <button
        key={indice}
        type="button"
        className="asistente-arete"
        onClick={() => onAbrir(parte)}
      >
        {parte}
      </button>
    ) : (
      parte
    ),
  );
}

function CuerpoRespuesta({ texto, aretes, onAbrir }) {
  const lineas = (texto || "").split("\n");
  const bloques = [];
  let listaActual = null;

  for (let i = 0; i < lineas.length; i += 1) {
    const linea = lineas[i];
    if (linea.startsWith("- ")) {
      if (!listaActual) {
        listaActual = [];
        bloques.push({ tipo: "ul", items: listaActual, key: i });
      }
      listaActual.push(linea.slice(2));
    } else {
      listaActual = null;
      if (linea.trim() !== "") {
        bloques.push({ tipo: "p", texto: linea, key: i });
      }
    }
  }

  return (
    <div className="asistente-cuerpo">
      {bloques.map((bloque) =>
        bloque.tipo === "ul" ? (
          <ul key={bloque.key} className="asistente-lista">
            {bloque.items.map((item, j) => (
              <li key={j}>{enlazarAretes(item, aretes, onAbrir)}</li>
            ))}
          </ul>
        ) : (
          <p key={bloque.key}>{enlazarAretes(bloque.texto, aretes, onAbrir)}</p>
        ),
      )}
    </div>
  );
}

export default function Asistente({ session, onExpired, onAbrir }) {
  const [turnos, setTurnos] = useState([]);
  const [pregunta, setPregunta] = useState("");
  const [esperando, setEsperando] = useState(false);
  const [error, setError] = useState(null);

  const enviar = async (textoPregunta) => {
    const limpio = (textoPregunta ?? pregunta).trim();
    if (!limpio || esperando) return;

    const previos = turnos.map(({ rol, texto }) => ({ rol, texto }));
    setTurnos((actuales) => [...actuales, { rol: "usuario", texto: limpio }]);
    setPregunta("");
    setError(null);
    setEsperando(true);

    try {
      const data = await apiFetch("/v1/asistente", {
        session,
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pregunta: limpio, previos }),
      });
      setTurnos((actuales) => [
        ...actuales,
        {
          rol: "asistente",
          texto: data.respuesta || "",
          consultas: data.consultas || [],
          aretes: data.aretes || [],
        },
      ]);
    } catch (err) {
      if (err.unauthorized) {
        onExpired();
      } else {
        setError(err.message || "El asistente no pudo contestar. Intenta de nuevo.");
      }
    } finally {
      setEsperando(false);
    }
  };

  const alEnviarFormulario = (evento) => {
    evento.preventDefault();
    enviar(pregunta);
  };

  return (
    <section className="panel asistente" aria-label="Pregúntale a Fierro">
      <div className="asistente-encabezado">
        <h2>Pregúntale a Fierro</h2>
        <p className="muted">
          Respuestas calculadas sobre los pesajes y las fichas de tu rancho.
        </p>
      </div>

      <div className="asistente-sugeridas" role="group" aria-label="Preguntas sugeridas">
        {SUGERIDAS.map((sugerida) => (
          <button
            key={sugerida}
            type="button"
            className="asistente-sugerida"
            disabled={esperando}
            onClick={() => enviar(sugerida)}
          >
            {sugerida}
          </button>
        ))}
      </div>

      {turnos.length > 0 && (
        <ol className="asistente-hilo" aria-label="Conversación">
          {turnos.map((turno, indice) => (
            <li
              key={indice}
              className={`asistente-turno asistente-turno-${turno.rol}`}
            >
              {turno.rol === "usuario" ? (
                <div className="asistente-burbuja-usuario">
                  <p>{turno.texto}</p>
                </div>
              ) : (
                <div className="asistente-tarjeta">
                  <Chips consultas={turno.consultas} />
                  <CuerpoRespuesta
                    texto={turno.texto}
                    aretes={turno.aretes}
                    onAbrir={onAbrir}
                  />
                </div>
              )}
            </li>
          ))}
        </ol>
      )}

      {esperando && (
        <p className="asistente-estado" role="status">
          Revisando tus pesajes…
        </p>
      )}

      {error && (
        <div className="asistente-alerta" role="alert">
          {error}
        </div>
      )}

      <form className="asistente-formulario" onSubmit={alEnviarFormulario}>
        <label className="campo asistente-campo">
          <span>Escribe tu pregunta</span>
          <input
            type="text"
            value={pregunta}
            onChange={(e) => setPregunta(e.target.value)}
            placeholder="Ej. ¿Qué vaca tiene problemas?"
            maxLength={1000}
            disabled={esperando}
          />
        </label>
        <button
          type="submit"
          className="asistente-enviar"
          disabled={esperando || !pregunta.trim()}
        >
          Enviar
        </button>
      </form>
    </section>
  );
}
