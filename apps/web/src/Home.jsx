import BarraHome from "./BarraHome.jsx";
import ListaEspera from "./ListaEspera.jsx";
import { PieHome } from "./PreguntasAcceso.jsx";
import Secciones from "./Secciones.jsx";
import VistaPesajesDemo from "./VistaPesajesDemo.jsx";
import { imagenes } from "./img/index.js";
import "./home-animaciones.css";
import "./home-barra.css";
import "./home-portada.css";

const paisaje = imagenes["portada-campo-ia"];

export default function Home({ onEntrar }) {
  return (
    <div className="home-publica">
      <a className="home-saltar" href="#contenido-home">
        Saltar al contenido
      </a>
      <BarraHome onEntrar={onEntrar} />

      <main id="contenido-home" tabIndex={-1}>
        <section className="home-portada" aria-labelledby="home-titulo">
          <picture className="home-portada-foto">
            <source media="(max-width: 40rem)" type="image/avif" srcSet={paisaje.srcSetVerticalAvif} sizes="100vw" />
            <source media="(max-width: 40rem)" srcSet={paisaje.srcSetVertical} sizes="100vw" />
            <img
              src={paisaje.src}
              srcSet={paisaje.srcSet}
              sizes="100vw"
              width={paisaje.width}
              height={paisaje.height}
              alt=""
              fetchPriority="high"
            />
          </picture>
          <div className="home-portada-principal">
            <div className="home-portada-contenido">
              <h1 id="home-titulo">El peso de tu ganado, a la mano.</h1>
              <p>Registra en el corral. Consulta desde tu celular.</p>
              <a className="home-cta" href="#lista-espera">
                Unirme a la lista <span aria-hidden="true">→</span>
              </a>
            </div>
            <VistaPesajesDemo />
          </div>
        </section>
        <div className="home-franja">
          <ul className="home-sellos" aria-label="Lo que distingue a Fierro">
            <li><span aria-hidden="true" />Funciona sin señal</li>
            <li><span aria-hidden="true" />Ningún pesaje se pierde</li>
            <li><span aria-hidden="true" />Lecturas dudosas, marcadas</li>
          </ul>
          <small>Imagen de portada generada con IA</small>
        </div>
        <Secciones />
        <ListaEspera onEntrar={onEntrar} />
      </main>
      <PieHome onEntrar={onEntrar} />
    </div>
  );
}
