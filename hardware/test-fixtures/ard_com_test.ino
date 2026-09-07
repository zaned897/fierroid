/*
 * Fierro — prototipo RFID, PARTE 2: pesaje por evento
 * ---------------------------------------------------
 * Presentar el tag ABRE una sesion. El peso se emite UNA vez cuando
 * se estabiliza (o al vencer el timeout). Linea muda entre eventos.
 *
 * Salida (una linea = un evento):
 *   W,<UID hex>,<ADC 0-1023>   pesaje completo: tag y peso ya emparejados
 *   H,<millis>                 latido de enlace (no es dato)
 *   # ...                      diagnostico human-readable, ignorable
 *
 * Este micro no sabe nada de Fierro: sin event_id, sin kg, sin proto:.
 * La sesion/estabilidad es acondicionamiento de senal (auto-hold),
 * como en cualquier indicador de bascula comercial.
 *
 * Serie: 115200, 8N1.
 */

#include <SPI.h>
#include <MFRC522.h>
#include <string.h>

// --- Pines (UNO / Nano) ---
const uint8_t PIN_RC522_SS = 10;
const uint8_t PIN_RC522_RST = 9;
const uint8_t PIN_POT = A0;

// --- Politica de sesion: afinar en el banco ---
const unsigned long MUESTREO_POT_MS = 50;     // muestreo interno (no sale por serie)
const unsigned long ESTABLE_MS = 800;         // quieto durante esto => peso valido
const int BANDA_ADC = 8;                      // +/- 8 cuentas (~39 mV) = "quieto"
const unsigned long TIMEOUT_SESION_MS = 8000; // si no estabiliza, se emite igual
const unsigned long AUSENCIA_MS = 400;        // sin tarjeta asi de largo => "se fue"
const unsigned long HEARTBEAT_MS = 10000;     // 0 => sin latido

MFRC522 lector(PIN_RC522_SS, PIN_RC522_RST);

enum Estado
{
    ESPERANDO_TAG,
    PESANDO
};
Estado estado = ESPERANDO_TAG;

// deteccion de tags
unsigned long tarjetaVistaMs = 0; // ultima vez que se vio una tarjeta
char ultimoEmitido[21];           // uid de la ultima W emitida
bool huboGap = true;              // hubo campo vacio desde la ultima W

// sesion de pesaje en curso
char uidSesion[21];
unsigned long inicioSesionMs = 0;
unsigned long estableDesdeMs = 0;
int cand = 0;  // referencia de la banda muerta
long suma = 0; // acumulador de la ventana estable
int nVentana = 0;

void setup()
{
    Serial.begin(115200);
    while (!Serial)
    {
        ;
    }

    SPI.begin();
    lector.PCD_Init();
    delay(50);

    Serial.println(F("== Fierro proto — pesaje por evento =="));
    Serial.println(F("lineas: W,<uid>,<adc> | H,<millis> | # diagnostico"));

    const byte v = lector.PCD_ReadRegister(MFRC522::VersionReg);
    Serial.print(F("RC522 version: 0x"));
    Serial.println(v, HEX);
    if (v != 0x91 && v != 0x92)
    {
        Serial.println(F("ERROR: lector no detectado. VCC a 3.3V; SS=D10 RST=D9 MOSI=D11 MISO=D12 SCK=D13"));
        while (true)
        {
            delay(1000);
        } // sin lector no seguimos: fallo ruidoso
    }

    // La configuracion va en el banner: toda captura queda autodescripta
    Serial.print(F("cfg estable_ms="));
    Serial.println(ESTABLE_MS);
    Serial.print(F("cfg banda_adc="));
    Serial.println(BANDA_ADC);
    Serial.print(F("cfg timeout_ms="));
    Serial.println(TIMEOUT_SESION_MS);
    Serial.print(F("cfg ausencia_ms="));
    Serial.println(AUSENCIA_MS);
    Serial.print(F("cfg heartbeat_ms="));
    Serial.println(HEARTBEAT_MS);

    ultimoEmitido[0] = '\0';
    tarjetaVistaMs = millis();
    Serial.println(F("Listo. Presenta una tarjeta..."));
}

void loop()
{
    switch (estado)
    {
    case ESPERANDO_TAG:
        tareaTag();
        break;
    case PESANDO:
        tareaPeso();
        break;
    }
    tareaLatido();
}

/*
 * ESPERANDO_TAG: abrir sesion solo con tarjetas NUEVAS.
 * "Nueva" = uid distinto al ultimo emitido, o el mismo uid despues
 * de un hueco (se quito y volvio a poner). La misma tarjeta quieta
 * no abre nada: de ahi el silencio.
 */
void tareaTag()
{
    if (millis() - tarjetaVistaMs >= AUSENCIA_MS)
        huboGap = true;

    if (!lector.PICC_IsNewCardPresent())
        return;
    if (!lector.PICC_ReadCardSerial())
        return;
    lector.PICC_HaltA();
    tarjetaVistaMs = millis();

    char uid[21];
    uidHex(uid, lector.uid.uidByte, lector.uid.size);

    if (!huboGap && strcmp(uid, ultimoEmitido) == 0)
        return; // misma quieta

    strcpy(uidSesion, uid);
    Serial.print(F("# sesion "));
    Serial.print(uidSesion);
    Serial.println(F(" esperando peso..."));

    cand = analogRead(PIN_POT);
    suma = cand;
    nVentana = 1;
    inicioSesionMs = millis();
    estableDesdeMs = inicioSesionMs;
    estado = PESANDO;
}

/*
 * PESANDO: muestrear el pot cada 50 ms y esperar a que se asiente.
 * El lector no se consulta aqui: en el corral real, para cuando el
 * animal esta en la bascula ya salio del alcance de la antena.
 * Toda sesion termina en exactamente una W: estable o por timeout.
 */
void tareaPeso()
{
    static unsigned long ultimoMuestreoMs = 0;
    const unsigned long ahora = millis();
    if (ahora - ultimoMuestreoMs < MUESTREO_POT_MS)
        return;
    ultimoMuestreoMs = ahora;

    if (ahora - inicioSesionMs >= TIMEOUT_SESION_MS)
    {
        emitir(false);
        return;
    }

    const int adc = analogRead(PIN_POT);

    if (abs(adc - cand) > BANDA_ADC)
    {
        // el peso se esta moviendo: nueva referencia, reloj de estabilidad a cero
        cand = adc;
        suma = adc;
        nVentana = 1;
        estableDesdeMs = ahora;
        return;
    }

    suma += adc;
    nVentana++;

    if (ahora - estableDesdeMs >= ESTABLE_MS)
        emitir(true);
}

/*
 * Una W por sesion, ni una mas. ADC = media de la ventana estable,
 * crudo (0-1023): convertir a kg es cosa del lado PC.
 */
void emitir(const bool estable)
{
    const int adc = (int)((suma + nVentana / 2) / nVentana);

    Serial.print(F("W,"));
    Serial.print(uidSesion);
    Serial.print(F(","));
    Serial.println(adc);
    if (!estable)
        Serial.println(F("# emitido por timeout: no estabilizo"));

    strcpy(ultimoEmitido, uidSesion);
    huboGap = false;
    estado = ESPERANDO_TAG;
}

/* Latido de enlace: distingue "no hay eventos" de "cable muerto".
 * No es dato. HEARTBEAT_MS = 0 y desaparece. */
void tareaLatido()
{
    if (HEARTBEAT_MS == 0)
        return;
    static unsigned long ultimoMs = 0;
    if (millis() - ultimoMs < HEARTBEAT_MS)
        return;
    ultimoMs = millis();
    Serial.print(F("H,"));
    Serial.println(ultimoMs);
}

void uidHex(char *out, const byte *uid, const uint8_t len)
{
    static const char tablaHex[] = "0123456789ABCDEF";
    for (uint8_t i = 0; i < len; i++)
    {
        out[2 * i] = tablaHex[uid[i] >> 4];
        out[2 * i + 1] = tablaHex[uid[i] & 0x0F];
    }
    out[2 * len] = '\0';
}
