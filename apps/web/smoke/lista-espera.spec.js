import { expect, test } from "./fixtures.js";

const datos = {
  name: "Raquel de Prueba",
  email: "raquel@example.test",
  stations: 3,
  consent: true,
  website: "",
};

for (const status of [202, 409, 500]) {
  test(`la lista de espera muestra el resultado de HTTP ${status}`, async ({ page }) => {
    const solicitudes = [];
    await page.route("/v1/waitlist", async (route) => {
      const request = route.request();
      solicitudes.push({ method: request.method(), body: request.postDataJSON() });
      const json = status === 202 ? { accepted: true } : { detail: "Error simulado" };
      await route.fulfill({ status, json });
    });
    await page.goto("/#lista-espera");

    const lista = page.locator("#lista-espera");
    const nombre = lista.getByRole("textbox", { name: "Nombre", exact: true });
    const correo = lista.getByLabel("Correo electrónico");
    const estaciones = lista.getByRole("spinbutton");
    const consentimiento = lista.getByRole("checkbox", { name: /Autorizo a Fierro/ });
    const enviar = lista.getByRole("button", { name: "Unirme a la lista de espera" });
    await nombre.fill(datos.name);
    await correo.fill(datos.email);
    await estaciones.fill(String(datos.stations));
    await consentimiento.check();
    await enviar.click();

    if (status === 202) {
      await expect(lista.getByRole("status")).toContainText("Tu interés quedó registrado.");
      await expect(enviar).toBeHidden();
    } else {
      await expect(lista.getByRole("alert")).toContainText("No pudimos confirmar el registro");
      await expect(lista.getByText("Tu interés quedó registrado.")).toBeHidden();
      await expect(nombre).toHaveValue(datos.name);
      await expect(correo).toHaveValue(datos.email);
      await expect(estaciones).toHaveValue(String(datos.stations));
      await expect(consentimiento).toBeChecked();
      await expect(enviar).toBeEnabled();
    }

    expect(solicitudes).toEqual([{ method: "POST", body: datos }]);
  });
}
