/**
 * El invariante raíz, dibujado.
 *
 * Es la sección con más peso de la portada porque es la diferencia real contra
 * una hoja de cálculo, y un párrafo no la cuenta: hay que ver dónde se rompe el
 * enlace y que la lectura ya está a salvo antes de ese punto.
 *
 * Va en HTML y no en SVG a propósito. Un SVG con `viewBox` escala, pero un
 * diagrama horizontal escalado a 375px deja el texto ilegible; esto reflota a
 * una columna con la misma regla que el resto de la página. El ticket pedía
 * SVG pensando en "no una imagen rasterizada" — eso se cumple igual.
 */
const PASOS = [
  {
    titulo: "La báscula y el arete",
    texto: "La estación lee el peso y el arete en el corral.",
  },
  {
    titulo: "La outbox de la estación",
    texto: "Se guarda en el disco de la estación. Aquí ya está a salvo.",
    salvo: true,
  },
  {
    titulo: "La nube",
    texto: "Sube cuando vuelve la señal, y no antes.",
  },
];

export default function Diagrama() {
  return (
    <div className="diagrama">
      <ol className="pasos">
        {PASOS.map((paso, i) => (
          <li key={paso.titulo} className={paso.salvo ? "paso salvo" : "paso"}>
            <span className="paso-num" aria-hidden="true">
              {i + 1}
            </span>
            <div>
              <h3>{paso.titulo}</h3>
              <p>{paso.texto}</p>
            </div>
            {/* El corte va entre la outbox y la nube: es el único enlace que
                puede caerse sin que se pierda nada. */}
            {paso.salvo && <span className="corte">señal caída</span>}
          </li>
        ))}
      </ol>

      <p className="diagrama-pie">
        El éxito de la captura es el guardado local, no la subida. La nube puede
        fallar; el corral no.
      </p>
    </div>
  );
}
