import { useEffect, useRef } from "react";

import Diagrama from "./Diagrama.jsx";
import Foto from "./Foto.jsx";

/** Si el observador no ha revelado nada para entonces, se revela todo. */
const RESCATE_MS = 1500;

/**
 * Aparición al entrar en viewport, con dos redes debajo.
 *
 * **Ocultar lo hace JavaScript**, no el CSS: la clase `con-revelado` la pone
 * este efecto. Sin JS —o sin `IntersectionObserver`, o con movimiento
 * reducido— nadie oculta nada y las secciones se leen tal cual. Al revés, con
 * `opacity: 0` por defecto y JS que lo quita, un script que no dispara deja la
 * página vacía sin un solo error en consola.
 *
 * Eso no basta, y lo descubrí midiendo: hay entornos donde `IntersectionObserver`
 * existe, acepta `observe()` y **nunca entrega el callback**. La comprobación de
 * soporte no los cubre, y el contenido se quedaría en `opacity: 0` para siempre.
 * De ahí el temporizador de rescate: pasado ese plazo se revela todo, se pierde
 * el escalonado y no se pierde la página. La animación es un adorno; el texto no.
 */
function useRevelar() {
  const raiz = useRef(null);

  useEffect(() => {
    const nodo = raiz.current;
    if (!nodo) return undefined;
    if (!("IntersectionObserver" in window)) return undefined;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return undefined;

    nodo.classList.add("con-revelado");

    const objetivos = [...nodo.querySelectorAll("[data-revelar]")];
    const revelar = (el) => el.classList.add("visible");

    const observador = new IntersectionObserver(
      (entradas) => {
        entradas.forEach((entrada) => {
          if (!entrada.isIntersecting) return;
          revelar(entrada.target);
          // Una vez visible se deja en paz: no es un efecto que deba repetirse
          // cada vez que la persona sube y baja.
          observador.unobserve(entrada.target);
        });
      },
      { rootMargin: "0px 0px -10% 0px" },
    );

    objetivos.forEach((el) => observador.observe(el));

    const rescate = setTimeout(() => {
      if (objetivos.some((el) => el.classList.contains("visible"))) return;
      // Se quita el ocultamiento en vez de animar hacia visible. Marcar cada
      // sección dependería de que la transición corra, y hay entornos donde no
      // corre: entonces la opacidad se quedaría clavada en 0, que es justo lo
      // que este rescate existe para impedir. Sin la clase, la regla que
      // esconde no aplica y no hay nada que animar.
      nodo.classList.remove("con-revelado");
      observador.disconnect();
    }, RESCATE_MS);

    return () => {
      clearTimeout(rescate);
      observador.disconnect();
    };
  }, []);

  return raiz;
}

function Seccion({ titulo, children, foto, invertida = false }) {
  return (
    <section className={invertida ? "seccion invertida" : "seccion"} data-revelar>
      <div className="seccion-texto">
        <h2>{titulo}</h2>
        {children}
      </div>
      {foto && <Foto nombre={foto} />}
    </section>
  );
}

export default function Secciones({ onEntrar, onArriba }) {
  const raiz = useRevelar();

  return (
    <div className="secciones" ref={raiz}>
      <Seccion titulo="La libreta se moja" foto="seccion-corral">
        <p>
          El peso se apunta a mano, el arete se lee mal, la hoja se traspapela.
          Cuando alguien pregunta cuánto pesaba ese animal hace tres meses, la
          respuesta es un cálculo de memoria.
        </p>
      </Seccion>

      <section className="seccion seccion-ancha" data-revelar>
        <div className="seccion-texto">
          <h2>Sigue funcionando sin señal</h2>
          <p>
            Es lo que separa a Fierro de una hoja de cálculo. La estación no
            necesita internet para pesar: lo necesita para <em>contarlo</em>, y
            eso puede esperar.
          </p>
        </div>
        <Diagrama />
      </section>

      <Seccion titulo="Cada rancho ve lo suyo" foto="seccion-hato" invertida>
        <p>
          Organizaciones, ranchos y estaciones. Quien entra ve el hato de su
          organización y nada más — el aislamiento no es una vista filtrada, es
          una condición en cada consulta.
        </p>
      </Seccion>

      <Seccion titulo="El historial de cada animal" foto="seccion-arete">
        <p>
          Del arete al peso, a lo largo del tiempo. Cuántas veces pasó por la
          manga, cuánto ganó entre una y otra, cuándo dejó de ganar. Eso es lo
          que la libreta no da.
        </p>
      </Seccion>

      <section className="seccion cierre" data-revelar>
        <div className="seccion-texto">
          <h2>El acceso es por invitación</h2>
          <p>
            No hay registro abierto. Damos de alta los correos de cada rancho
            uno por uno, porque cada cuenta ve datos de un negocio real y
            preferimos saber de quién es cada una.
          </p>
          <div className="cierre-acciones">
            <button type="button" className="primario" onClick={onEntrar}>
              Entrar
            </button>
            <button type="button" className="volver" onClick={onArriba}>
              ↑ Volver arriba
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
