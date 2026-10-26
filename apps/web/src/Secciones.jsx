import { useEffect, useRef } from "react";

import Beneficios from "./Beneficios.jsx";
import Diagrama from "./Diagrama.jsx";
import PreguntasAcceso from "./PreguntasAcceso.jsx";
import Referencias from "./Referencias.jsx";
import GraficaPeso from "./GraficaPeso.jsx";
import VisionPremium from "./VisionPremium.jsx";
import MasQueBascula from "./MasQueBascula.jsx";

/** Si el observador no respondió ni una vez para entonces, se revela todo. */
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
 * De ahí el temporizador de rescate: si en ese plazo el callback no llegó ni
 * una vez, se revela todo. No basta con "nada visible todavía": con la portada
 * ocupando la pantalla, ninguna sección está a la vista y el rescate apagaba
 * el revelado aunque el observador funcionara. Pasado el plazo se pierde
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

    // El observador entrega una primera llamada por cada objetivo apenas
    // empieza a observar, esté o no en pantalla. Si llegó, funciona; lo que
    // está debajo del pliegue se revela cuando la persona baje.
    let respondio = false;

    const observador = new IntersectionObserver(
      (entradas) => {
        respondio = true;
        entradas.forEach((entrada) => {
          if (!entrada.isIntersecting) return;
          entrada.target.classList.add("visible");
          // Una vez visible se deja en paz: no es un efecto que deba repetirse
          // cada vez que la persona sube y baja.
          observador.unobserve(entrada.target);
        });
      },
      { rootMargin: "0px 0px -10% 0px" },
    );

    objetivos.forEach((el) => observador.observe(el));

    const rescate = setTimeout(() => {
      if (respondio) return;
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

/** Secciones del home, sustituidas de forma incremental según la guía. */
export default function Secciones() {
  const raiz = useRevelar();

  return (
    <div className="secciones" ref={raiz}>
      {/* Justo después de la portada: es lo que vende (#94). */}
      <MasQueBascula />

      <section
        className="bloque banda-oscura como-funciona"
        id="como-funciona"
        aria-labelledby="como-funciona-titulo"
        data-revelar
      >
        <div className="bloque-cabeza">
          <h2 id="como-funciona-titulo">Del pesaje al historial, en tres pasos</h2>
        </div>
        <Diagrama />
      </section>

      <Beneficios />

      {/* 3. Dato. La gráfica manda y el texto la acompaña. */}
      <section className="bloque dato" data-revelar>
        <div className="dato-texto">
          <h2>El historial de cada animal</h2>
          <p>
            Del arete al peso, a lo largo del tiempo. Cuánto ganó entre una
            pasada y la siguiente, y cuándo dejó de ganar.
          </p>
          <p className="dato-apunte">
            Fíjate en el 27 de agosto: la báscula no se estabilizó y esa lectura
            queda marcada. Se guarda igual, señalada — un dato dudoso avisado es
            útil; uno maquillado, no.
          </p>
        </div>
        <GraficaPeso />
      </section>

      <Referencias />
      <VisionPremium />
      <PreguntasAcceso />
    </div>
  );
}
