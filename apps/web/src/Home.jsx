import Secciones from "./Secciones.jsx";
import Shell from "./Shell.jsx";

/**
 * Portada.
 *
 * Lo primero que se ve sigue siendo corto: quien llega recomendado viene a
 * entrar, y una portada larga se interpone entre esa persona y su trabajo. Lo
 * que explica el producto va debajo, para quien lo necesite.
 */
export default function Home({ onEntrar }) {
  const alInicio = () => {
    window.scrollTo({
      top: 0,
      // Respetar la preferencia también aquí: un salto instantáneo es lo que
      // pide quien apagó las animaciones, no un desplazamiento suave.
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "auto"
        : "smooth",
    });
  };

  return (
    <>
      <Shell lema="Del corral a tu bolsillo.">
        <h1 className="titulo">Fierro</h1>
        <p className="subtitulo">
          Pesaje de ganado que no pierde una lectura, aunque se caiga la señal.
        </p>

        <button type="button" className="primario" onClick={onEntrar}>
          Entrar
        </button>

        <p className="pie">
          El acceso es por invitación. Si tu rancho ya usa Fierro, pide que den
          de alta tu correo.
        </p>
      </Shell>

      <Secciones onEntrar={onEntrar} onArriba={alInicio} />
    </>
  );
}
