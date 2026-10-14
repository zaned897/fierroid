import ListaEspera from "./ListaEspera.jsx";
import Marca from "./Marca.jsx";

export default function Cotizacion({ onEntrar, onInicio, sesionActiva }) {
  return (
    <div className="home-publica cotizacion-publica">
      <header className="home-encabezado">
        <a
          className="home-marca"
          href="/"
          aria-label="Fierro, inicio"
          onClick={(event) => {
            event.preventDefault();
            onInicio();
          }}
        >
          <Marca size={38} />
          <span>Fierro</span>
        </a>
        <nav className="home-navegacion" aria-label="Navegación principal">
          <a href="/">Inicio</a>
          <a href="/#beneficios">Beneficios</a>
          <a href="/#preguntas-frecuentes">Preguntas frecuentes</a>
        </nav>
        <button type="button" className="home-entrar home-entrar-cabecera" onClick={onEntrar}>
          {sesionActiva ? "Ir al panel" : "Iniciar sesión"}
        </button>
      </header>

      <main className="cotizacion-main">
        <section className="cotizacion-hero" aria-labelledby="cotizacion-titulo">
          <p className="home-lema">Cotización</p>
          <h1 id="cotizacion-titulo">Cuéntanos dónde estará tu estación.</h1>
          <p>
            Con tu estado y número aproximado de estaciones podemos preparar una
            respuesta más útil para tu rancho.
          </p>
        </section>
        <ListaEspera />
      </main>
    </div>
  );
}
