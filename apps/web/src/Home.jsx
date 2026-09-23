import Marca from "./Marca.jsx";
import Secciones from "./Secciones.jsx";

/**
 * Home público.
 *
 * Esta primera unidad solo cambia encabezado y portada. Las secciones
 * existentes permanecen debajo hasta sustituirse en ciclos posteriores.
 */
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
        <button type="button" className="home-entrar home-entrar-cabecera" onClick={onEntrar}>
          Iniciar sesión
        </button>
      </header>

      <main id="contenido-home">
        <section className="home-portada" aria-labelledby="home-titulo">
          <div className="home-portada-contenido">
            <p className="home-lema">Del corral a tu bolsillo.</p>
            <h1 id="home-titulo">El peso de tu ganado, siempre a la mano.</h1>
            <p className="home-descripcion">
              Registra cada pesaje y consulta el historial de tus animales desde tu celular.
            </p>
            <div className="home-acciones">
              <button type="button" className="home-entrar" onClick={onEntrar}>
                Iniciar sesión
              </button>
            </div>
            <p className="home-nota">Acceso por invitación.</p>
          </div>
        </section>

        <Secciones onEntrar={onEntrar} onArriba={alInicio} />
      </main>
    </div>
  );
}
