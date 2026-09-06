import { useEffect, useRef } from "react";

import Diagrama from "./Diagrama.jsx";
import Foto from "./Foto.jsx";
import GraficaPeso from "./GraficaPeso.jsx";

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

    const observador = new IntersectionObserver(
      (entradas) => {
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

/**
 * Cinco secciones, cinco registros distintos.
 *
 * Antes eran el mismo bloque cinco veces —foto a un lado, texto al otro, misma
 * altura— y la página se leía como una lista. Ahora ninguna repite el patrón de
 * la anterior: declaración, diagrama, dato, contraste invertido, y una a sangre
 * para cerrar.
 */
export default function Secciones({ onEntrar, onArriba }) {
  const raiz = useRevelar();

  return (
    <div className="secciones" ref={raiz}>
      {/* 1. Declaración. Abre con una frase, no con una imagen. */}
      <section className="bloque declaracion" data-revelar>
        <p className="declaracion-texto">
          El peso se apunta a mano, el arete se lee mal, la hoja se traspapela.
          Cuando alguien pregunta cuánto pesaba ese animal hace tres meses, la
          respuesta es un cálculo de memoria.
        </p>
      </section>

      {/* 2. Diagrama sobre banda más oscura. */}
      <section className="bloque banda-oscura" data-revelar>
        <div className="bloque-cabeza">
          <h2>Sigue funcionando sin señal</h2>
          <p>
            Es lo que separa a Fierro de una hoja de cálculo. La estación no
            necesita internet para pesar: lo necesita para <em>contarlo</em>, y
            eso puede esperar.
          </p>
        </div>
        <Diagrama />
      </section>

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

      {/* 4. Contraste invertido. Es el golpe de la página. */}
      <section className="bloque banda-clara" data-revelar>
        <div className="bloque-cabeza">
          <h2>Cada rancho ve lo suyo</h2>
          <p>
            Organizaciones, ranchos y estaciones. Quien entra ve el hato de su
            organización y nada más — el aislamiento no es una vista filtrada,
            es una condición en cada consulta.
          </p>
        </div>

        {/* Tira con scroll en vez de carrusel: mismo recorrido, sin quitarle
            el control a quien lee ni romper el teclado. */}
        <div className="tira" tabIndex={0} role="group" aria-label="El trabajo de rancho">
          <Foto nombre="seccion-corral" />
          <Foto nombre="seccion-manga" />
          <Foto nombre="seccion-arete" />
          <Foto nombre="seccion-hato" />
        </div>
      </section>

      {/* 5. Cierre a sangre. La única foto que llega a 1600px. */}
      <section className="bloque cierre-hero" data-revelar>
        <div className="cierre-contenido">
          <h2>El acceso es por invitación</h2>
          <p>
            No hay registro abierto. Damos de alta los correos de cada rancho uno
            por uno, porque cada cuenta ve datos de un negocio real y preferimos
            saber de quién es cada una.
          </p>
          <div className="cierre-acciones">
            <button type="button" className="contraste" onClick={onEntrar}>
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
