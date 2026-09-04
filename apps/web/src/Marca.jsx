/**
 * La marca de Fierro.
 *
 * El PNG es una silueta de un solo color, así que se usa como máscara CSS y no
 * como imagen: el trazo es exactamente el del archivo, pero el color lo pone la
 * paleta. El café original (#6c3d25) sobre el verde de fondo (#142018) queda
 * casi invisible, y un logotipo que no se ve no es un logotipo.
 *
 * En la pestaña del navegador sí va el archivo tal cual, con su café: ahí el
 * fondo lo pone el navegador, no nosotros.
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
