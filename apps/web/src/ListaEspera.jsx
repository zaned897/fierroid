import { useRef, useState } from "react";
import { apiFetch } from "./auth.js";
import "./lista-espera.css";

const ESTADOS_MX = [
  "Aguascalientes",
  "Baja California",
  "Baja California Sur",
  "Campeche",
  "Chiapas",
  "Chihuahua",
  "Ciudad de México",
  "Coahuila",
  "Colima",
  "Durango",
  "Estado de México",
  "Guanajuato",
  "Guerrero",
  "Hidalgo",
  "Jalisco",
  "Michoacán",
  "Morelos",
  "Nayarit",
  "Nuevo León",
  "Oaxaca",
  "Puebla",
  "Querétaro",
  "Quintana Roo",
  "San Luis Potosí",
  "Sinaloa",
  "Sonora",
  "Tabasco",
  "Tamaulipas",
  "Tlaxcala",
  "Veracruz",
  "Yucatán",
  "Zacatecas",
];

export default function ListaEspera() {
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");
  const sending = useRef(false);
  async function submit(event) {
    event.preventDefault();
    if (sending.current) return;
    const data = new FormData(event.currentTarget);
    sending.current = true; setBusy(true); setError("");
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    try {
      const result = await apiFetch('/v1/waitlist', { method: 'POST', signal: controller.signal,
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
          name: data.get('name'), email: data.get('email'), state: data.get('state'),
          stations: Number(data.get('stations')),
          consent: data.get('consent') === 'on', website: data.get('website'),
        }) });
      if (!result.accepted) throw new Error('No confirmado');
      setStatus({
        confirmed: result.confirmed,
        emailSent: result.email_sent,
        confirmationUrl: result.confirmation_url || "",
      });
    } catch (err) {
      setError(err.status === 429 ? 'Hay muchas solicitudes. Inténtalo en una hora.' : 'No pudimos confirmar el registro. Tus datos siguen aquí; puedes reintentar.');
    } finally { clearTimeout(timer); sending.current = false; setBusy(false); }
  }
  return <section id="lista-espera" className="waitlist-section" aria-labelledby="waitlist-title">
    <div className="waitlist-intro"><p className="home-lema">Próximas estaciones</p>
      <h2 id="waitlist-title">Cotiza Fierro para tu rancho.</h2>
      <p>Déjanos tus datos y te contactamos con disponibilidad, alcance recomendado y siguientes pasos.</p>
      <p className="waitlist-note">Sin pago ni compromiso de compra. La cotización no reserva equipo ni garantiza una fecha de entrega.</p>
    </div>
    {status ? <div className="waitlist-card" role="status">
      <h3>{status.confirmed ? 'Tu correo ya estaba confirmado.' : 'Revisa tu correo para confirmar.'}</h3>
      {status.confirmed ? <p>Tu registro sigue activo en la lista de espera de Fierro.</p> :
        <p>{status.emailSent ? 'Te mandamos un enlace de confirmación. Después de abrirlo podremos contactarte sobre disponibilidad.' : 'Guardamos tu registro. Falta configurar el correo automático, pero en modo local puedes confirmar con el enlace de prueba.'}</p>}
      {status.confirmationUrl && <p className="waitlist-note"><a href={status.confirmationUrl}>Abrir enlace de confirmación de prueba</a></p>}
      <p>Este registro no crea una cuenta de acceso al panel.</p>
    </div> :
      <form className="waitlist-card" onSubmit={submit} aria-busy={busy}>
        <label>Nombre<input name="name" autoComplete="name" required maxLength={100} disabled={busy} /></label>
        <label>Correo electrónico<input name="email" type="email" autoComplete="email" required maxLength={254} disabled={busy} /></label>
        <label>Estado<select name="state" required defaultValue="" disabled={busy}>
          <option value="" disabled>Selecciona tu estado</option>
          {ESTADOS_MX.map((estado) => <option key={estado} value={estado}>{estado}</option>)}
        </select></label>
        <label>¿Cuántas estaciones te interesan?<input name="stations" type="number" min="1" max="1000" defaultValue="1" required disabled={busy} /><small>Una estimación; puedes decidirlo más adelante.</small></label>
        <div className="waitlist-trap" aria-hidden="true"><label>Sitio web<input name="website" tabIndex={-1} autoComplete="off" /></label></div>
        <label className="waitlist-consent"><input name="consent" type="checkbox" required disabled={busy} /><span>Autorizo a Fierro a usar estos datos para contactarme sobre la disponibilidad de sus estaciones.</span></label>
        <button className="home-entrar" type="submit" disabled={busy}>{busy ? 'Registrando…' : 'Unirme a la lista de espera'}</button>
        {error && <p className="error" role="alert">{error}</p>}
      </form>}
  </section>;
}
