import { imagenes } from "./img/index.js";

/**
 * Una imagen del catálogo, con su crédito cuando la licencia lo exige.
 *
 * El crédito no se decide al maquetar. Tres de las fotos son CC BY 2.0 y la
 * atribución tiene que **verse en la página**, no solo en `CREDITOS.md`.
 * Poniéndolo aquí y no en cada sección, nadie puede copiar un `<img>` y
 * llevarse la imagen sin el crédito: la única forma de mostrarla es esta.
 *
 * `width` y `height` salen del índice y son las medidas reales del archivo.
 * Sin ellas el navegador no reserva el hueco y el texto salta cuando la
 * imagen carga — que en el corral, con señal mala, es todo el rato.
 */
export default function Foto({ nombre, className = "" }) {
  const img = imagenes[nombre];

  if (!img) {
    // En desarrollo revienta, porque un nombre mal escrito es un error de
    // programación y quiero verlo ya. En producción no: una foto que falta no
    // justifica tumbar la portada.
    if (import.meta.env.DEV) throw new Error(`Foto desconocida: "${nombre}"`);
    return null;
  }

  return (
    <figure className={`foto ${className}`.trim()}>
      <img
        src={img.src}
        width={img.width}
        height={img.height}
        alt={img.alt}
        loading="lazy"
        decoding="async"
      />
      {img.requiereAtribucion && (
        <figcaption className="credito">
          {img.autor} ·{" "}
          <a href={img.fuente} target="_blank" rel="noreferrer noopener">
            {img.licencia}
          </a>
        </figcaption>
      )}
    </figure>
  );
}
