import "./referencias.css";

/**
 * Por qué pesar, con fuentes.
 *
 * Cada dato cita la fuente de la que sale, y cada fuente se verificó contra
 * su página original el 2026-10-24 (título, autores, revista, DOI). Nada de
 * esto es una afirmación de Fierro sobre su propio desempeño: son hallazgos
 * de terceros y se presentan así. Si una fuente cambia o desaparece, se
 * corrige aquí; no se parafrasea de memoria.
 */
const DATOS = [
  {
    icono: "alimento",
    titulo: "El alimento es el mayor costo",
    texto:
      "Extensión de Penn State recuerda que el alimento suele ser el gasto más alto de un productor de carne. Saber cuánto pesa cada animal ayuda a no dar de más ni de menos.",
    fuente: "penn-state",
  },
  {
    icono: "dosis",
    titulo: "La dosis depende del peso",
    texto:
      "La misma guía señala que, cuando un animal enferma, la dosis correcta del medicamento depende de conocer su peso real.",
    fuente: "penn-state",
  },
  {
    icono: "camara",
    titulo: "Las cámaras ya estiman el peso",
    texto:
      "En un estudio con ganado de carne en Brasil, un sistema de visión estimó el peso con un error típico de 7.7 a 11.4 kg según la etapa. La báscula sigue siendo la referencia.",
    fuente: "cominotte-2020",
  },
];

const LECTURAS = [
  {
    id: "penn-state",
    tipo: "Extensión universitaria",
    titulo: "Benefits of Weighing Beef Cattle",
    autores: "Taylor Zahn",
    medio: "Penn State Extension, 2025",
    url: "https://extension.psu.edu/benefits-of-weighing-beef-cattle",
  },
  {
    id: "cominotte-2020",
    tipo: "Artículo científico",
    titulo:
      "Automated computer vision system to predict body weight and average daily gain in beef cattle during growing and finishing phases",
    autores: "Cominotte, Fernandes, Dorea, Rosa, Ladeira y col.",
    medio: "Livestock Science 232, 2020",
    url: "https://doi.org/10.1016/j.livsci.2019.103904",
  },
  {
    id: "wang-2021",
    tipo: "Revisión científica",
    titulo: "Applications of machine learning for livestock body weight prediction from digital images",
    autores: "Wang, Shadpour, Chan, Rotondo, Wood y Tulpan",
    medio: "Journal of Animal Science 99(2), 2021",
    url: "https://doi.org/10.1093/jas/skab022",
  },
  {
    id: "grandin",
    tipo: "Guía de manejo",
    titulo: "Understanding Flight Zone and Point of Balance for Low Stress Handling of Cattle, Sheep, and Pigs",
    autores: "Temple Grandin, Colorado State University",
    medio: "grandin.com, actualizado 2022",
    url: "https://www.grandin.com/behaviour/principles/flight.zone.html",
  },
  {
    id: "iso-11784",
    tipo: "Norma internacional",
    titulo: "ISO 11784:2024 Radio frequency identification of animals — Code structure",
    autores: "Organización Internacional de Normalización",
    medio: "ISO, 2024",
    url: "https://www.iso.org/standard/83944.html",
  },
  {
    id: "senasica-2023",
    tipo: "Noticia del sector",
    titulo: "Establece Senasica nuevo esquema de trazabilidad de la ganadería",
    autores: "Redacción de BM Editores",
    medio: "noviembre de 2023",
    url: "https://bmeditores.mx/ganaderia/establece-senasica-nuevo-esquema-de-trazabilidad-de-la-ganaderia/",
  },
];

const numeroDe = Object.fromEntries(LECTURAS.map((lectura, indice) => [lectura.id, indice + 1]));

function IconoDato({ tipo }) {
  return (
    <svg viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      {tipo === "alimento" && <><path d="M8 40h32M12 40V22l12-8 12 8v18" /><path d="M19 40v-9h10v9M18 24h12" /></>}
      {tipo === "dosis" && <><path d="m30 8 10 10M35 13 17 31l-6 1 1-6 18-18" /><path d="m22 18 8 8M8 40l6-6" /></>}
      {tipo === "camara" && <><rect x="6" y="14" width="36" height="24" rx="4" /><circle cx="24" cy="26" r="7" /><path d="M17 14l3-5h8l3 5" /></>}
    </svg>
  );
}

export default function Referencias() {
  return (
    <section className="bloque home-referencias" id="por-que-pesar" aria-labelledby="por-que-pesar-titulo" data-revelar>
      <div className="home-referencias-contenido">
        <h2 id="por-que-pesar-titulo">Por qué pesar seguido</h2>
        <p className="home-referencias-intro">
          Lo que dicen la investigación y la extensión ganadera sobre conocer el peso de cada animal.
        </p>

        <ul className="home-datos">
          {DATOS.map((dato) => (
            <li className="home-dato" key={dato.titulo}>
              <span className="home-dato-icono"><IconoDato tipo={dato.icono} /></span>
              <h3>{dato.titulo}</h3>
              <p>
                {dato.texto}{" "}
                <a className="home-cita" href={`#lectura-${dato.fuente}`} aria-label={`Fuente ${numeroDe[dato.fuente]}`}>
                  [{numeroDe[dato.fuente]}]
                </a>
              </p>
            </li>
          ))}
        </ul>

        <h3 className="home-lecturas-titulo" id="lecturas">Lecturas recomendadas</h3>
        <ol className="home-lecturas">
          {LECTURAS.map((lectura) => (
            <li className="home-lectura" key={lectura.id} id={`lectura-${lectura.id}`}>
              <span className="home-lectura-tipo">{lectura.tipo}</span>
              <a href={lectura.url} target="_blank" rel="noopener noreferrer">
                {lectura.titulo}
              </a>
              <span className="home-lectura-medio">
                {lectura.autores} · {lectura.medio}
              </span>
            </li>
          ))}
        </ol>
        <p className="home-referencias-nota">
          Enlaces a sitios externos, en inglés salvo la nota de BM Editores. Fierro no está afiliado a estas fuentes.
        </p>
      </div>
    </section>
  );
}
