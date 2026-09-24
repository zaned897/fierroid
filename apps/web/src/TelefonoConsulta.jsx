import Marca from "./Marca.jsx";
import { CowIcon } from "./icons/cows.jsx";

/** Ilustración HTML, sin controles operativos ni consultas a datos privados. */
export default function TelefonoConsulta() {
  return (
    <figure className="home-telefono-escena" aria-label="Vista de ejemplo de consulta de pesajes en un teléfono">
      <div className="home-telefono">
        <div className="home-telefono-marca"><Marca size={26} /><span>FIERRO</span></div>
        <div className="home-telefono-pantalla">
          <span className="home-telefono-rancho">Los Encinos</span>
          <strong className="home-telefono-titulo">Pesajes</strong>
          <div className="home-telefono-peso">
            <span>Último pesaje</span><strong>437.5 kg</strong>
            <span><CowIcon variant="perfil" size={16} /> BEDE50D3</span>
          </div>
          <strong className="home-telefono-subtitulo">Lecturas recientes</strong>
          <div className="home-telefono-lectura"><span>Hoy, 19:42</span><strong>437.5 kg</strong></div>
          <div className="home-telefono-lectura"><span>Hoy, 19:27</span><strong>279.0 kg</strong></div>
          <div className="home-telefono-lectura"><span>Hoy, 19:26</span><strong>325.0 kg</strong></div>
        </div>
      </div>
      <figcaption>Vista de ejemplo · Fondo ilustrativo generado con IA</figcaption>
    </figure>
  );
}
