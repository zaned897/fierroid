import { useEffect, useState } from "react";

import Marca from "./Marca.jsx";
import HomeNavigation from "./HomeNavigation.jsx";
import ListaEspera from "./ListaEspera.jsx";
import { PieHome } from "./PreguntasAcceso.jsx";
import Secciones from "./Secciones.jsx";
import VistaPesajesDemo from "./VistaPesajesDemo.jsx";
import "./home-animaciones.css";

/** Pixeles de desplazamiento que cuentan como cambio de dirección. */
const UMBRAL_PX = 8;

/**
 * La barra superior sigue al scroll: arriba del todo se ve sobre la portada,
 * al bajar se esconde para dejar la pantalla al contenido y al subir aparece
 * fija con fondo. Con el foco dentro (teclado) no se esconde.
 */
function useBarraConScroll() {
  const [estado, setEstado] = useState(() => ({ arriba: window.scrollY < 24, oculta: false }));

  useEffect(() => {
    let previo = window.scrollY;
    let pendiente = 0;
    const medir = () => {
      pendiente = 0;
      const y = window.scrollY;
      const arriba = y < 24;
      const delta = y - previo;
      if (Math.abs(delta) < UMBRAL_PX && !arriba) return;
      const enfocada = document.activeElement?.closest?.(".home-encabezado");
      const menuAbierto = document.querySelector(".home-menu[open]") ||
        ("popover" in HTMLElement.prototype && document.querySelector(".home-menu:popover-open"));
      setEstado({ arriba, oculta: !arriba && delta > 0 && !enfocada && !menuAbierto });
      previo = y;
    };
    const alScroll = () => {
      if (pendiente) return;
      pendiente = requestAnimationFrame(medir);
    };
    window.addEventListener("scroll", alScroll, { passive: true });
    medir();
    return () => {
      window.removeEventListener("scroll", alScroll);
      cancelAnimationFrame(pendiente);
    };
  }, []);

  return estado;
}

export default function Home({ onEntrar }) {
  const barra = useBarraConScroll();
  const claseBarra = `home-encabezado${barra.arriba ? "" : " fija"}${barra.oculta ? " oculta" : ""}`;

  return (
    <div className="home-publica">
      <a className="home-saltar" href="#contenido-home">
        Saltar al contenido
      </a>
      <header className={claseBarra}>
        <a className="home-marca" href="/" aria-label="Fierro, inicio">
          <Marca size={38} />
          <span>Fierro</span>
        </a>
        <HomeNavigation onEntrar={onEntrar} />
      </header>

      <main id="contenido-home">
        <section className="home-portada" aria-labelledby="home-titulo">
          <div className="home-portada-principal">
            <div className="home-portada-contenido">
              <p className="home-lema">Ganadería de siempre, tecnología de punta.</p>
              <h1 id="home-titulo">El peso de tu ganado, siempre a la mano.</h1>
              <p className="home-descripcion">
                La manga, el arete y el ojo del vaquero, con una báscula que no olvida.
                Registra cada pesaje y consulta el historial de tus animales desde tu celular.
              </p>
              <ul className="home-sellos" aria-label="Lo que distingue a Fierro">
                <li>Funciona sin señal</li>
                <li>Ningún pesaje se pierde</li>
                <li>Lecturas dudosas, marcadas</li>
              </ul>
              <div className="home-acciones">
                <a className="home-entrar" href="#lista-espera">
                  Unirme a la lista de espera <span aria-hidden="true">→</span>
                </a>
              </div>
              <p className="home-nota">
                ¿Tu rancho ya usa Fierro?{" "}
                <button type="button" className="home-nota-entrar" onClick={onEntrar}>
                  Inicia sesión
                </button>
              </p>
            </div>
            {/* La tarjeta se monta sobre el paisaje: juntos ocupan el lugar
                que antes ocupaban por separado. */}
            <div className="home-portada-vista">
              <figure className="home-paisaje">
                <img
                  src="/img/home-paisaje-ia.webp"
                  width="1536"
                  height="1024"
                  alt=""
                  loading="eager"
                  decoding="async"
                />
              </figure>
              <VistaPesajesDemo />
            </div>
          </div>
        </section>
        <Secciones />
        <ListaEspera onEntrar={onEntrar} />
      </main>
      <PieHome onEntrar={onEntrar} />
    </div>
  );
}
