/** Iconos decorativos de trazo uniforme para los pasos del home. */
export default function HomeIcon({ tipo }) {
  return (
    <svg viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      {tipo === "arete" && <><path d="M18 14V9a6 6 0 0 1 12 0v5l10 12v16H8V26Z" /><circle cx="24" cy="10" r="1.5" /></>}
      {tipo === "bascula" && <><path d="M12 6h24a4 4 0 0 1 4 4l4 30a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3l4-30a4 4 0 0 1 4-4Z" /><circle cx="24" cy="23" r="10" /><path d="m24 23 5-6M24 13v3" /></>}
      {tipo === "nube" && <><path d="M12 35a10 10 0 0 1-1-20 13 13 0 0 1 25-1 10 10 0 0 1 1 21M24 43V24m-8 8 8-8 8 8" /></>}
    </svg>
  );
}
