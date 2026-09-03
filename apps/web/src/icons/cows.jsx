/**
 * Iconos ilustrativos de ganado.
 *
 * Son siluetas geometricas a proposito, no dibujos realistas: se leen a 20px en
 * una lista y no compiten con el dato importante, que es el peso.
 *
 * Todo usa `currentColor`, asi que heredan el color del contenedor. Los detalles
 * (manchas, hocico, ubre) usan `--cow-detail`, que por defecto es el fondo del
 * panel para que parezcan recortes.
 */

const DETAIL = "var(--cow-detail, rgba(0, 0, 0, 0.35))";

// Cada variante corresponde a un tipo de animal reconocible en un hato mexicano.
export const COW_VARIANTS = ["perfil", "cebu", "becerro", "toro", "frente", "lechera"];

export const COW_LABELS = {
  perfil: "Vaca de perfil",
  cebu: "Cebu con giba",
  becerro: "Becerro",
  toro: "Toro",
  frente: "Cabeza de frente",
  lechera: "Vaca lechera",
};

/** Hash djb2: el mismo arete siempre recibe el mismo icono. */
export function cowVariantForTag(tagId) {
  const text = String(tagId ?? "");
  let hash = 5381;
  for (let i = 0; i < text.length; i += 1) {
    hash = ((hash << 5) + hash + text.charCodeAt(i)) | 0;
  }
  return COW_VARIANTS[Math.abs(hash) % COW_VARIANTS.length];
}

/**
 * Piezas compartidas de los perfiles laterales.
 *
 * La clave para que una silueta se lea como bovino y no como un bulto es el
 * cuello: una cuna inclinada del hombro a la cabeza, con el hocico afilado
 * hacia adelante. Sin eso, cabeza y cuerpo se funden en un cacahuate.
 */
function Legs({ xs, y = 36, w = 5, h = 16 }) {
  return (
    <g>
      {xs.map((x) => (
        <rect key={x} x={x} y={y} width={w} height={h} rx={w / 2} />
      ))}
    </g>
  );
}

function Tail({ x = 54, y = 21 }) {
  return (
    <g>
      <path
        d={`M${x} ${y}q5 3 2 12`}
        fill="none"
        stroke="currentColor"
        strokeWidth="2.1"
        strokeLinecap="round"
      />
      <circle cx={x + 2} cy={y + 13} r="1.9" />
    </g>
  );
}

/** Cuello + cabeza + hocico, mirando a la izquierda. */
function HeadLeft({ top = 24, drop = 0 }) {
  const y = top + drop;
  return (
    <g>
      <path d={`M25 ${y - 3}L10 ${y + 2}L10 ${y + 12}L27 ${y + 13}Z`} />
      <path
        d={`M12 ${y}L4 ${y + 3}Q0 ${y + 4.5} 0 ${y + 8}Q0 ${y + 12.5} 4 ${y + 13}L12 ${y + 14}Z`}
      />
      <ellipse
        cx="12.5"
        cy={y}
        rx="4.2"
        ry="2.5"
        transform={`rotate(-30 12.5 ${y})`}
      />
      <ellipse cx="3.5" cy={y + 9} rx="3" ry="2.6" fill={DETAIL} />
    </g>
  );
}

function Horn({ x = 14, y = 22 }) {
  return (
    <path
      d={`M${x} ${y}Q${x + 1} ${y - 5} ${x + 5} ${y - 6}`}
      fill="none"
      stroke="currentColor"
      strokeWidth="2.3"
      strokeLinecap="round"
    />
  );
}

function Perfil() {
  return (
    <g>
      <Legs xs={[22, 30, 42, 49]} />
      <rect x="18" y="19" width="37" height="18" rx="8" />
      <Tail />
      <HeadLeft top={24} />
      <Horn x={14} y={23} />
      <ellipse cx="32" cy="25" rx="6" ry="4.2" fill={DETAIL} />
      <ellipse cx="46" cy="31" rx="4.6" ry="3.2" fill={DETAIL} />
    </g>
  );
}

function Cebu() {
  return (
    <g>
      <Legs xs={[22, 30, 42, 49]} />
      <rect x="18" y="20" width="37" height="17" rx="8" />
      {/* La giba sobre la cruz: la marca de la raza. */}
      <path d="M21 24C24 10 40 11 42 23z" />
      <Tail y={22} />
      <HeadLeft top={26} />
      {/* Oreja larga y caida en vez de parada. */}
      <ellipse cx="11" cy="33" rx="3" ry="6" transform="rotate(24 11 33)" />
      {/* Papada. */}
      <path d="M12 38c1 7 8 8 11 2z" />
    </g>
  );
}

function Becerro() {
  return (
    <g>
      {/* Patas largas y finas bajo un cuerpo corto: proporcion de cria. */}
      <Legs xs={[26, 33, 44, 50]} y={36} w={4} h={17} />
      <rect x="24" y="23" width="31" height="14" rx="7" />
      <Tail x={54} y={25} />
      {/* Cabeza grande respecto al cuerpo y sin cuernos todavia. */}
      <g transform="translate(6 3) scale(1.08)">
        <HeadLeft top={22} />
      </g>
      <ellipse cx="40" cy="29" rx="5" ry="3.4" fill={DETAIL} />
    </g>
  );
}

function Toro() {
  return (
    <g>
      {/* Patas gruesas y cuerpo profundo: masa, no estatura. */}
      <Legs xs={[22, 31, 43, 50]} y={37} w={6} h={15} />
      <rect x="19" y="16" width="37" height="21" rx="9" />
      <Tail x={55} y={19} />
      <HeadLeft top={23} />
      {/* Cuernos en lira. Sin giba: esa es la marca del cebu, no la del toro. */}
      <path
        d="M11 21Q6 16 7 10"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.9"
        strokeLinecap="round"
      />
      <path
        d="M14 21Q19 16 18 10"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.9"
        strokeLinecap="round"
      />
      {/* Argolla nasal. */}
      <circle cx="3.5" cy="32" r="1.7" fill="currentColor" />
    </g>
  );
}

function Frente() {
  return (
    <g>
      <ellipse cx="12" cy="26" rx="8.5" ry="5" transform="rotate(-18 12 26)" />
      <ellipse cx="52" cy="26" rx="8.5" ry="5" transform="rotate(18 52 26)" />
      <path
        d="M19 14Q13 5 21 4"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.8"
        strokeLinecap="round"
      />
      <path
        d="M45 14Q51 5 43 4"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.8"
        strokeLinecap="round"
      />
      <rect x="16" y="13" width="32" height="35" rx="15" />
      {/* Copete entre los cuernos. */}
      <path d="M26 15q6-6 12 0z" fill={DETAIL} />
      <ellipse cx="32" cy="42" rx="10" ry="7" fill={DETAIL} />
      <ellipse cx="28" cy="41" rx="1.7" ry="2.3" fill="currentColor" />
      <ellipse cx="36" cy="41" rx="1.7" ry="2.3" fill="currentColor" />
      <circle cx="25" cy="26" r="2.5" fill={DETAIL} />
      <circle cx="39" cy="26" r="2.5" fill={DETAIL} />
    </g>
  );
}

function Lechera() {
  return (
    <g>
      <Legs xs={[23, 31, 43, 50]} />
      {/* Cuerpo largo y poco profundo: conformacion lechera. */}
      <rect x="18" y="20" width="38" height="17" rx="7.5" />
      {/* Ubre. */}
      <ellipse cx="37" cy="37" rx="7.5" ry="5" />
      <Tail x={55} y={22} />
      <HeadLeft top={25} />
      <Horn x={14} y={24} />
      {/* Manchas irregulares tipo Holstein. */}
      <path d="M26 22c6-2 9 3 7 7-2 4-9 4-11 0-1-3 0-6 4-7z" fill={DETAIL} />
      <ellipse cx="47" cy="29" rx="5.2" ry="3.8" fill={DETAIL} />
      <ellipse cx="36" cy="37" rx="4" ry="2.4" fill={DETAIL} />
    </g>
  );
}

const SHAPES = {
  perfil: Perfil,
  cebu: Cebu,
  becerro: Becerro,
  toro: Toro,
  frente: Frente,
  lechera: Lechera,
};

export function CowIcon({ variant = "perfil", size = 28, title, className, ...rest }) {
  const Shape = SHAPES[variant] ?? Perfil;
  const labelled = Boolean(title);

  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      className={className}
      fill="currentColor"
      role={labelled ? "img" : undefined}
      aria-hidden={labelled ? undefined : "true"}
      focusable="false"
      {...rest}
    >
      {labelled && <title>{title}</title>}
      <Shape />
    </svg>
  );
}

/** Icono para un animal concreto: mismo arete, mismo dibujo, siempre. */
export function CowForTag({ tagId, ...rest }) {
  const variant = cowVariantForTag(tagId);
  return <CowIcon variant={variant} title={COW_LABELS[variant]} {...rest} />;
}
