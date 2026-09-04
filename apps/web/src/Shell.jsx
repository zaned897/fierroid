import Marca from "./Marca.jsx";

/**
 * Estructura de las pantallas públicas: marca a un lado, contenido al otro.
 *
 * El panel de marca desaparece bajo 900px en vez de encogerse. En un celular
 * en el corral, media pantalla de decoración es media pantalla menos de lo que
 * la persona vino a hacer.
 */
export default function Shell({ lema, children }) {
  return (
    <div className="shell">
      <aside className="marca" aria-hidden="true">
        <div className="marca-contenido">
          <Marca size={56} />
          <p className="marca-lema">{lema}</p>
        </div>
      </aside>

      <main className="shell-panel">
        <div className="shell-columna">{children}</div>
      </main>
    </div>
  );
}
