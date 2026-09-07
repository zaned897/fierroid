import { useCallback, useEffect, useState } from "react";

import { apiFetch } from "./auth.js";

/**
 * Panel de administración: la cadena organización → rancho → estación, y usuarios.
 *
 * Sólo se monta para superusuarios, y quien decide eso es `App.jsx`: aquí no
 * hay comprobación de permisos porque esconder controles no protege nada. Quien
 * mande la petición sin serlo recibe un 403 de la API, que es donde el permiso
 * se decide de verdad.
 *
 * **Un animal no se asigna a una organización.** Pertenece a la dueña de la
 * estación que lo pesó. Por eso este panel administra la cadena y no ofrece
 * ningún desplegable de organización en la ficha del animal: sería mentir sobre
 * el modelo.
 */

function Campo({ etiqueta, valor, onChange, placeholder, ...resto }) {
  return (
    <label className="campo">
      {etiqueta}
      <input
        value={valor}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        {...resto}
      />
    </label>
  );
}

function NuevaOrg({ onHecho, onError }) {
  const [slug, setSlug] = useState("");
  const [name, setName] = useState("");
  const [ocupado, setOcupado] = useState(false);

  const crear = async () => {
    setOcupado(true);
    try {
      await onHecho({ slug, name });
      setSlug("");
      setName("");
    } catch (err) {
      onError(err.message);
    } finally {
      setOcupado(false);
    }
  };

  return (
    <div className="alta">
      <Campo etiqueta="Slug" valor={slug} onChange={setSlug} placeholder="los-encinos" />
      <Campo etiqueta="Nombre" valor={name} onChange={setName} placeholder="Ganadera Los Encinos" />
      <button type="button" onClick={crear} disabled={ocupado || !slug || !name}>
        {ocupado ? "Creando…" : "Crear organización"}
      </button>
    </div>
  );
}

function NuevoRancho({ org, onHecho, onError }) {
  const [slug, setSlug] = useState("");
  const [name, setName] = useState("");
  const [ocupado, setOcupado] = useState(false);

  const crear = async () => {
    setOcupado(true);
    try {
      await onHecho(org.slug, { slug, name });
      setSlug("");
      setName("");
    } catch (err) {
      onError(err.message);
    } finally {
      setOcupado(false);
    }
  };

  return (
    <div className="alta compacta">
      <Campo etiqueta="Slug del rancho" valor={slug} onChange={setSlug} placeholder="san-jose" />
      <Campo etiqueta="Nombre" valor={name} onChange={setName} placeholder="San José" />
      <button type="button" onClick={crear} disabled={ocupado || !slug || !name}>
        {ocupado ? "Creando…" : "Añadir rancho"}
      </button>
    </div>
  );
}

/**
 * Registrar una estación suelta.
 *
 * Es la pantalla más importante del panel: una estación sin rancho acepta
 * pesajes que después no aparecen en ninguna vista, sin dar ningún error. Por
 * eso las sueltas salen arriba y en rojo, no escondidas al final.
 */
function Registrar({ device, orgs, onHecho, onError }) {
  const [destino, setDestino] = useState("");
  const [ocupado, setOcupado] = useState(false);

  const opciones = orgs.flatMap((o) =>
    o.ranches.map((r) => ({ valor: `${o.slug}|${r.slug}`, texto: `${o.slug} · ${r.slug}` })),
  );

  const registrar = async () => {
    const [org, ranch] = destino.split("|");
    setOcupado(true);
    try {
      await onHecho(device.device_id, { org, ranch });
    } catch (err) {
      onError(err.message);
    } finally {
      setOcupado(false);
    }
  };

  return (
    <li className="suelta">
      <div>
        <span className="tag">{device.device_id}</span>
        <span className="meta">
          {device.readings} {device.readings === 1 ? "pesaje" : "pesajes"} sin organización
        </span>
      </div>
      <div className="suelta-accion">
        <label className="campo">
          Asignar a
          <select value={destino} onChange={(e) => setDestino(e.target.value)}>
            <option value="">Elige un rancho…</option>
            {opciones.map((o) => (
              <option key={o.valor} value={o.valor}>
                {o.texto}
              </option>
            ))}
          </select>
        </label>
        <button type="button" onClick={registrar} disabled={ocupado || !destino}>
          {ocupado ? "Registrando…" : "Registrar"}
        </button>
      </div>
    </li>
  );
}

function NuevoUsuario({ orgs, onHecho, onError }) {
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [org, setOrg] = useState("");
  const [superusuario, setSuperusuario] = useState(false);
  const [ocupado, setOcupado] = useState(false);

  const crear = async () => {
    setOcupado(true);
    try {
      await onHecho({
        email,
        full_name: fullName || null,
        org: superusuario ? null : org || null,
        is_superuser: superusuario,
      });
      setEmail("");
      setFullName("");
    } catch (err) {
      onError(err.message);
    } finally {
      setOcupado(false);
    }
  };

  return (
    <div className="alta">
      <Campo
        etiqueta="Correo"
        valor={email}
        onChange={setEmail}
        placeholder="alguien@rancho.mx"
        type="email"
      />
      <Campo etiqueta="Nombre" valor={fullName} onChange={setFullName} placeholder="Opcional" />

      <label className="campo">
        Organización
        <select
          value={org}
          onChange={(e) => setOrg(e.target.value)}
          disabled={superusuario}
        >
          <option value="">Sin organización</option>
          {orgs.map((o) => (
            <option key={o.slug} value={o.slug}>
              {o.slug}
            </option>
          ))}
        </select>
      </label>

      <label className="marca-check">
        <input
          type="checkbox"
          checked={superusuario}
          onChange={(e) => setSuperusuario(e.target.checked)}
        />
        Superusuario — ve todas las organizaciones
      </label>

      <button type="button" onClick={crear} disabled={ocupado || !email}>
        {ocupado ? "Dando de alta…" : "Dar de alta"}
      </button>
    </div>
  );
}

export default function Admin({ session, onExpired }) {
  const [arbol, setArbol] = useState({ orgs: [], unassigned_devices: [] });
  const [usuarios, setUsuarios] = useState([]);
  const [error, setError] = useState(null);
  const [aviso, setAviso] = useState(null);
  const [cargando, setCargando] = useState(true);

  const recargar = useCallback(async () => {
    try {
      const [o, u] = await Promise.all([
        apiFetch("/v1/orgs", { session }),
        apiFetch("/v1/users", { session }),
      ]);
      setArbol(o);
      setUsuarios(u.users || []);
      setError(null);
    } catch (err) {
      if (err.unauthorized) onExpired();
      else setError(err.message);
    } finally {
      setCargando(false);
    }
  }, [session, onExpired]);

  useEffect(() => {
    recargar();
  }, [recargar]);

  const enviar = useCallback(
    async (ruta, cuerpo, metodo = "POST") => {
      const r = await apiFetch(ruta, {
        session,
        method: metodo,
        headers: { "Content-Type": "application/json" },
        ...(cuerpo ? { body: JSON.stringify(cuerpo) } : {}),
      });
      await recargar();
      return r;
    },
    [session, recargar],
  );

  const crearOrg = (cuerpo) => enviar("/v1/orgs", cuerpo);
  const crearRancho = (slug, cuerpo) => enviar(`/v1/orgs/${slug}/ranches`, cuerpo);
  const altaUsuario = (cuerpo) => enviar("/v1/users", cuerpo);

  const registrar = async (deviceId, destino) => {
    const r = await enviar(`/v1/devices/${encodeURIComponent(deviceId)}`, destino, "PUT");
    // Mover una estación arrastra su historia. Decirlo no es cortesía: quien
    // administra tiene que saber que le cambió los datos a alguien.
    if (r.readings_moved > 0) {
      const n = r.readings_moved;
      setAviso(
        `${deviceId}: ${n} ${n === 1 ? "pesaje pasó" : "pesajes pasaron"} ` +
          `${r.previous_org ? `de ${r.previous_org} ` : ""}a ${r.org}.`,
      );
    }
  };

  const desactivar = async (email) => {
    const r = await enviar(`/v1/users/${encodeURIComponent(email)}`, null, "DELETE");
    setAviso(`${email} desactivado. Llaves revocadas: ${r.keys_revoked}.`);
  };

  if (cargando) return <p className="muted">Cargando…</p>;

  return (
    <>
      {error && <p className="error">{error}</p>}
      {aviso && <p className="aviso">{aviso}</p>}

      {arbol.unassigned_devices.length > 0 && (
        <section className="panel" aria-label="Estaciones sin registrar">
          <h2>Estaciones sin rancho</h2>
          <p className="muted">
            Sus pesajes entran a la base y <strong>no aparecen en ninguna vista</strong>. No dan
            error: hay que registrarlas para que se vean.
          </p>
          <ul className="sueltas">
            {arbol.unassigned_devices.map((d) => (
              <Registrar
                key={d.device_id}
                device={d}
                orgs={arbol.orgs}
                onHecho={registrar}
                onError={setError}
              />
            ))}
          </ul>
        </section>
      )}

      <section className="panel" aria-label="Organizaciones">
        <h2>Organizaciones</h2>
        {arbol.orgs.map((org) => (
          <div key={org.slug} className="org">
            <h3>
              {org.name} <span className="tag">{org.slug}</span>
            </h3>
            {org.ranches.length === 0 && <p className="muted">Sin ranchos todavía.</p>}
            <ul className="ranchos">
              {org.ranches.map((r) => (
                <li key={r.slug}>
                  <span className="animal-nombre">{r.name}</span>
                  <span className="meta">
                    {r.devices.length === 0
                      ? "sin estaciones"
                      : r.devices
                          .map((d) => `${d.device_id} (${d.readings})`)
                          .join(" · ")}
                  </span>
                </li>
              ))}
            </ul>
            <NuevoRancho org={org} onHecho={crearRancho} onError={setError} />
          </div>
        ))}

        <h3>Nueva organización</h3>
        <NuevaOrg onHecho={crearOrg} onError={setError} />
      </section>

      <section className="panel" aria-label="Usuarios">
        <h2>Usuarios</h2>
        <ul className="usuarios">
          {usuarios.map((u) => (
            <li key={u.email} className={u.is_active ? "" : "inactivo"}>
              <div>
                <span className="animal-nombre">{u.full_name || u.email}</span>
                <span className="meta">
                  <span className="tag">{u.email}</span>
                  <span>
                    {u.is_superuser ? "todas las organizaciones" : u.org || "sin organización"}
                    {!u.is_active && " · desactivado"}
                  </span>
                </span>
              </div>
              {u.is_active && (
                <button type="button" className="ghost" onClick={() => desactivar(u.email)}>
                  Desactivar
                </button>
              )}
            </li>
          ))}
        </ul>

        <h3>Dar de alta</h3>
        <NuevoUsuario orgs={arbol.orgs} onHecho={altaUsuario} onError={setError} />
      </section>
    </>
  );
}
