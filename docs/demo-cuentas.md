# Rancho demo por cuenta

Cada cuenta real puede tener un **rancho demo aparte** con datos sintéticos
realistas, para que quien entra a la plataforma antes de conectar su báscula vea
un rancho vivo, y para hacer demos en cualquier entorno sin tocar lo real.

## Cómo funciona

- **Base (016):** el demo es otra organización, `<cuenta>-demo`, con
  `es_demo = true` y `demo_de_org_id` apuntando a la cuenta real. Nada sintético
  vive en la organización real.
- **API:** los usuarios de la cuenta lo abren con `?org=<cuenta>-demo` en
  cualquier ruta que ya acepte `org`. `/v1/auth/me` lo anuncia en `demo_org`. Un
  `org` ajeno se ignora, como siempre.
- **Web:** interruptor "Ver datos de demostración / Ver mis datos reales" bajo
  la barra superior. Encendido, un aviso fijo ámbar dice que son datos de
  ejemplo, y la organización se muestra como "(demostración)". Arranca
  encendido solo si la cuenta todavía no tiene ni un pesaje real.
- **Basculas reales:** sus pesajes llegan a la cuenta real por su estación, como
  siempre. No hay que borrar ni migrar nada: el demo queda al lado.

### Por qué no una marca "sintético" en cada fila

El libro de dinero (014) es de solo agregar, y los repartos de gasto de corral
y hato abarcan todos los animales de la organización. Mezclar exigiría un
filtro en cada consulta y borrar del libro para purgar; un filtro olvidado da
cifras falsas revueltas con las reales.

## Sembrar

Con la llave de un superusuario:

```bash
export FIERRO_TOKEN=...
python3 scripts/seed_demo_cuentas.py --api https://<api> --todas            # cuentas con usuarios
python3 scripts/seed_demo_cuentas.py --api https://<api> --org los-encinos --rehacer   # refrescar fechas
python3 scripts/seed_demo_cuentas.py --api https://<api> --org los-encinos --purgar    # borrar el demo
python3 scripts/seed_demo_cuentas.py --org los-encinos --out demo.json      # ver los datos sin red
```

En production se detiene salvo `--permitir-produccion`.

Por cuenta carga, en unas 14 semanas: 42 animales (la historia de
[`demo-asistente.md`](demo-asistente.md) más 4 novillos vendidos), ~470 pesajes
semanales en dos estaciones, ~97 movimientos de dinero (compras por embarque,
alimento por corral y mes, vaquero, luz, flete, vacunas, tratamientos ligados a
su nota, una reparación, una captura anulada y recapturada, ventas con destare
y precio de mercado semanal) y 10 notas del diario. Es determinista: repetirlo
no duplica nada.

## Purgar

`DELETE /v1/orgs/{cuenta}/demo` (o `--purgar`) borra el demo completo en una
transacción y dice cuántas filas salieron de cada tabla. Se niega si alguna
estación del demo tiene pesajes con `source` distinto de `demo` (una báscula
real asignada por error) o si el demo tiene usuarios propios.
