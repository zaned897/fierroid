import Marca from "./Marca.jsx";
import Secciones from "./Secciones.jsx";
import VistaPesajesDemo from "./VistaPesajesDemo.jsx";

export default function Home({ onEntrar }) {
  const alInicio = () => window.scrollTo({ top: 0, behavior: "auto" });

  return (
    <div className="home-publica">
      <a className="home-saltar" href="#contenido-home">
        Saltar al contenido
      </a>
      <header className="home-encabezado">
        <a className="home-marca" href="/" aria-label="Fierro, inicio">
          <Marca size={38} />
          <span>Fierro</span>
        </a>
        <nav className="home-navegacion" aria-label="Navegación principal">
          <a href="#como-funciona">Cómo funciona</a>
          <a href="#beneficios">Beneficios</a>
        </nav>
        <button type="button" className="home-entrar home-entrar-cabecera" onClick={onEntrar}>
          <span className="home-entrar-largo">Iniciar sesión</span>
          <span className="home-entrar-corto">Entrar</span>
        </button>
      </header>

      <main id="contenido-home">
        <section className="home-portada" aria-labelledby="home-titulo">
          <div className="home-portada-principal">
            <div className="home-portada-contenido">
              <p className="home-lema">Del corral a tu bolsillo.</p>
              <h1 id="home-titulo">El peso de tu ganado, siempre a la mano.</h1>
              <p className="home-descripcion">
                Registra cada pesaje y consulta el historial de tus animales desde tu celular.
              </p>
              <div className="home-acciones">
                <button type="button" className="home-entrar" onClick={onEntrar}>
                  Iniciar sesión <span aria-hidden="true">→</span>
                </button>
                <a className="home-conocer" href="#como-funciona">
                  Conocer Fierro
                </a>
              </div>
              <p className="home-nota">
                <span className="home-candado" aria-hidden="true" />
                Acceso por invitación.
              </p>
            </div>
            <VistaPesajesDemo />
          </div>
          <figure className="home-paisaje">
            <img
              src="/img/home-paisaje-ia.webp"
              width="1536"
              height="1024"
              alt=""
              loading="eager"
              decoding="async"
            />
            <figcaption>Imagen ilustrativa generada con IA</figcaption>
          </figure>
        </section>
        <Secciones onEntrar={onEntrar} onArriba={alInicio} />
      </main>
    </div>
  );
}
