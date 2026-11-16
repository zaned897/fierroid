import { expect, test } from "./fixtures.js";

const animal = {
  org: "rancho-prueba",
  tag_id: "SMOKE-001",
  alias: "La Pinta",
  readings: 0,
  has_photo: false,
};
const sesion = {
  id: "sesion-simulada",
  api_key: "token-simulado",
  user: {
    email: "ganadera@example.test",
    full_name: "Ganadera de prueba",
    org: animal.org,
    is_superuser: false,
  },
};
const nota = {
  body: "Cambió al corral de observación.",
  category: "manejo",
  occurred_at: "2026-09-01T09:30:00.000Z",
};
const fechaLocal = "2026-09-01T09:30";
const uuidV4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

async function simularRancho(page, { perderPrimerAck = false } = {}) {
  await page.addInitScript((session) => {
    localStorage.setItem("fierro.session", JSON.stringify(session));
  }, sesion);

  const historialVacio = (route) => route.fulfill({ json: { readings: [], next_cursor: null } });
  await page.route("/v1/devices", (route) => route.fulfill({ json: { devices: [] } }));
  await page.route("/v1/animals", (route) => route.fulfill({ json: { animals: [animal] } }));
  await page.route("/v1/readings?*", historialVacio);
  await page.route(`/v1/animals/${animal.tag_id}/readings?*`, historialVacio);

  const solicitudes = [];
  const entradas = new Map();
  await page.route(`/v1/animals/${animal.tag_id}/journal?*`, async (route) => {
    const request = route.request();
    expect(new URL(request.url()).searchParams.get("org")).toBe(animal.org);
    expect(request.headers().authorization).toBe(`Bearer ${sesion.api_key}`);
    if (request.method() === "GET") {
      await route.fulfill({ json: { entries: [...entradas.values()], next_cursor: null } });
      return;
    }

    expect(request.method()).toBe("POST");
    const entrada = request.postDataJSON();
    solicitudes.push(entrada);
    if (!entradas.has(entrada.entry_id)) {
      entradas.set(entrada.entry_id, {
        ...entrada,
        author: sesion.user.full_name,
        created_at: "2026-09-01T09:31:00.000Z",
      });
    }
    // El servidor ya guardó la nota cuando falla la entrega de la respuesta.
    if (perderPrimerAck && solicitudes.length === 1) {
      await route.abort("failed");
      return;
    }
    await route.fulfill({ json: entradas.get(entrada.entry_id) });
  });

  return solicitudes;
}

async function abrirBitacora(page) {
  await page.getByRole("navigation", { name: "Secciones del panel" })
    .getByRole("button", { name: "Animales", exact: true }).click();
  await page.getByRole("button", { name: /La Pinta.*SMOKE-001/ }).click();
  const seccion = page.getByRole("region", { name: "Bitácora del animal" });
  await expect(seccion.getByRole("button", { name: "Actualizar bitácora" })).toBeEnabled();
  return seccion;
}

async function llenarNota(seccion) {
  await seccion.getByLabel("Fecha del evento (hora local)").fill(fechaLocal);
  await seccion.getByLabel("Categoría").selectOption(nota.category);
  await seccion.getByRole("textbox", { name: "Anotación" }).fill(nota.body);
}

function guardar(seccion) {
  return seccion.getByRole("button", { name: "Guardar anotación" }).click();
}

function notaEnHistorial(seccion) {
  return seccion.getByRole("list").getByText(nota.body, { exact: true });
}

async function comprobarGuardado(seccion) {
  await expect(seccion.getByRole("status").filter({ hasText: "Anotación guardada." })).toBeVisible();
  await expect(notaEnHistorial(seccion)).toHaveCount(1);
  await expect(seccion.getByRole("textbox", { name: "Anotación" })).toHaveValue("");
}

test("guarda una anotación y la muestra en el historial", async ({ page }) => {
  const solicitudes = await simularRancho(page);
  await page.goto("/");
  const bitacora = await abrirBitacora(page);
  await expect(bitacora.getByText("Todavía no hay anotaciones.")).toBeVisible();
  await llenarNota(bitacora);
  await guardar(bitacora);
  await comprobarGuardado(bitacora);

  expect(solicitudes).toEqual([{ ...nota, entry_id: expect.stringMatching(uuidV4) }]);
});

test("reintenta después de recargar con el mismo UUID si se perdió el ACK", async ({ page }) => {
  const solicitudes = await simularRancho(page, { perderPrimerAck: true });
  await page.goto("/");
  let bitacora = await abrirBitacora(page);
  await llenarNota(bitacora);
  await guardar(bitacora);
  await expect(bitacora.getByRole("alert")).toContainText("No se confirmó el guardado");
  await expect(bitacora.getByRole("textbox", { name: "Anotación" })).toHaveValue(nota.body);
  expect(solicitudes).toHaveLength(1);
  const primerEnvio = solicitudes[0];
  expect(primerEnvio).toEqual({ ...nota, entry_id: expect.stringMatching(uuidV4) });

  await page.reload();
  bitacora = await abrirBitacora(page);
  await expect(bitacora.getByRole("textbox", { name: "Anotación" })).toHaveValue(nota.body);
  await expect(bitacora.getByLabel("Categoría")).toHaveValue(nota.category);
  await expect(bitacora.getByLabel("Fecha del evento (hora local)")).toHaveValue(fechaLocal);
  await expect(notaEnHistorial(bitacora)).toHaveCount(1);
  await guardar(bitacora);
  await comprobarGuardado(bitacora);
  expect(solicitudes).toEqual([primerEnvio, primerEnvio]);

  await page.reload();
  bitacora = await abrirBitacora(page);
  await expect(bitacora.getByRole("textbox", { name: "Anotación" })).toHaveValue("");
  await expect(notaEnHistorial(bitacora)).toHaveCount(1);
});
