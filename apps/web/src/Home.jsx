import Shell from "./Shell.jsx";

/**
 * Portada. Deliberadamente corta.
 *
 * Quien llega aquí ya sabe qué es Fierro —se lo dijo quien le pasó el enlace—
 * y viene a entrar. Una portada larga se interpone entre esa persona y su
 * trabajo.
 */
export default function Home({ onEntrar }) {
  return (
    <Shell lema="Del corral a tu bolsillo.">
      <h1 className="titulo">Fierro</h1>
      <p className="subtitulo">
        Pesaje de ganado que no pierde una lectura, aunque se caiga la señal.
      </p>

      <button type="button" className="primario" onClick={onEntrar}>
        Entrar
      </button>

      <p className="pie">
        El acceso es por invitación. Si tu rancho ya usa Fierro, pide que den de
        alta tu correo.
      </p>
    </Shell>
  );
}
