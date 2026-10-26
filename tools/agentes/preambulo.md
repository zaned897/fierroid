Trabajas en el repo fierroid (Fierro IoT, pesaje de ganado edge-first).
Antes de cambiar nada lee CLAUDE.md y AGENTS.md. Reglas que no se negocian:
- Ninguna lectura de pesaje se pierde. Falla ruidosa, nunca datos falsos.
- Idempotencia por event_id. Diff minimo, solo lo que pide la tarea.
- Sin hardware: usa FIERRO_MOCK_HW=1.
- No hagas commit ni push; deja los cambios en el arbol de trabajo.
Al terminar resume que cambiaste, que comandos corriste y su resultado.
