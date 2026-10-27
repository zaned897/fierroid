/**
 * La marca de Fierro.
 *
 * El PNG es una silueta de un solo color, así que se usa como máscara CSS y no
 * como imagen: el trazo es exactamente el del archivo, pero el color lo pone la
 * paleta. El café original (#6c3d25) sobre el verde de fondo (#142018) queda
 * casi invisible, y un logotipo que no se ve no es un logotipo.
 *
 * La pestaña del navegador no usa este archivo: el favicon (favicon.svg) es la
 * cabeza de toro en un sello verde con filo dorado, que trae su propio fondo.
 */
export default function Marca({ size = 48, className = "" }) {
  return (
    <span
      className={`marca-fierro ${className}`.trim()}
      style={{ width: size, height: size }}
      role="img"
      aria-label="Fierro"
    />
  );
}
