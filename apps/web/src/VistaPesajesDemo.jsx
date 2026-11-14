// Las cifras ilustran la estabilización sin consultar lecturas ni temporizadores.
export default function VistaPesajesDemo() {
  return (
    <div className="home-pesaje">
      <div className="home-pesaje-cabecera">
        <span>Pesaje demo</span>
        <span className="home-pesaje-guardado">Guardado</span>
      </div>
      <div className="home-pesaje-lectura">
        <strong>
          <span className="home-pesaje-sr">437.5 kilogramos</span>
          <span className="home-pesaje-numero" aria-hidden="true">
            <span className="home-pesaje-cifras">
              <span>437.5</span>
              <span>425.8</span>
              <span>442.1</span>
              <span>435.6</span>
              <span>437.5</span>
            </span>
          </span>
          <span className="home-pesaje-unidad" aria-hidden="true">kg</span>
        </strong>
      </div>
    </div>
  );
}
