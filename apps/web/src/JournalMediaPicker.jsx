import { useEffect, useRef, useState } from "react";
import { reducirImagen } from "./photo.js";
import { attachment, audioFormat, LIMITS, MAX_AUDIO_SECONDS, MAX_BYTES } from "./journalMedia.js";

function Preview({ item, index, disabled, onRemove }) {
  const [url, setUrl] = useState(null);
  useEffect(() => {
    const next = URL.createObjectURL(item.file);
    setUrl(next);
    return () => URL.revokeObjectURL(next);
  }, [item.file]);
  return <li>
    {item.kind === "photo"
      ? <img src={url || undefined} alt={`Foto adjunta ${index + 1}`} />
      : <audio controls preload="metadata" src={url || undefined} aria-label={`Nota de voz adjunta ${index + 1}`} />}
    <button type="button" disabled={disabled} onClick={onRemove}
      aria-label={`Quitar ${item.kind === "photo" ? "foto" : "nota de voz"} ${index + 1}`}>Quitar</button>
  </li>;
}

export default function JournalMediaPicker({ files, onChange, disabled, onWorking }) {
  const [error, setError] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const gallery = useRef(null);
  const camera = useRef(null);
  const active = useRef(null);
  const mounted = useRef(false);
  const values = useRef({ files, onChange, onWorking });
  values.current = { files, onChange, onWorking };

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      const current = active.current;
      active.current = null;
      if (current) {
        clearInterval(current.clock); clearTimeout(current.limit);
        if (current.recorder?.state === "recording") current.recorder.stop();
        current.stream?.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  async function photos(event) {
    const selected = [...event.target.files];
    event.target.value = "";
    setError(null); setProcessing(true); onWorking(true);
    try {
      let next = [...values.current.files];
      for (const file of selected) {
        if (next.filter((item) => item.kind === "photo").length >= LIMITS.photo) {
          throw new Error("Puedes agregar hasta 6 fotos por nota.");
        }
        const reduced = await reducirImagen(file, { forceJPEG: true });
        next = [...next, attachment(reduced, "photo", next)];
        if (!mounted.current) return;
        onChange(next);
      }
    } catch (err) {
      if (mounted.current) setError(err.message);
    } finally {
      if (mounted.current) { setProcessing(false); onWorking(false); }
    }
  }

  async function start() {
    if (active.current) return;
    const format = audioFormat();
    if (!format || !navigator.mediaDevices?.getUserMedia) {
      setError("La grabación no está disponible aquí. Usa HTTPS o localhost y un navegador actualizado. Puedes guardar texto y fotos.");
      return;
    }
    const current = {};
    active.current = current;
    setError(null); setProcessing(true); onWorking(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      current.stream = stream;
      if (!mounted.current || active.current !== current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      const recorder = new MediaRecorder(stream, { mimeType: format, audioBitsPerSecond: 32000 });
      current.recorder = recorder;
      const chunks = [];
      let bytes = 0;
      recorder.ondataavailable = (event) => {
        if (event.data.size) { chunks.push(event.data); bytes += event.data.size; }
        if (bytes > MAX_BYTES && recorder.state === "recording") recorder.stop();
      };
      recorder.onerror = () => {
        current.failed = true;
        if (mounted.current) setError("La grabación falló. Puedes volver a grabar o guardar texto y fotos.");
        if (recorder.state === "recording") recorder.stop();
      };
      recorder.onstop = () => {
        clearInterval(current.clock); clearTimeout(current.limit);
        stream.getTracks().forEach((track) => track.stop());
        if (active.current !== current || !mounted.current) return;
        active.current = null;
        setRecording(false); values.current.onWorking(false);
        if (current.failed) return;
        try {
          const file = new Blob(chunks, { type: recorder.mimeType || format });
          values.current.onChange([...values.current.files, attachment(file, "audio", values.current.files)]);
        } catch (err) { setError(err.message); }
      };
      recorder.start(1000);
      setRecording(true); setProcessing(false); setSeconds(0);
      const started = performance.now();
      current.clock = setInterval(() => setSeconds(Math.min(MAX_AUDIO_SECONDS, Math.floor((performance.now() - started) / 1000))), 250);
      // Reservar 250 ms para el último bloque del codificador (sobre todo AAC).
      current.limit = setTimeout(() => { if (recorder.state === "recording") recorder.stop(); }, MAX_AUDIO_SECONDS * 1000 - 250);
    } catch (err) {
      current.stream?.getTracks().forEach((track) => track.stop());
      if (!mounted.current) return;
      active.current = null; setProcessing(false); onWorking(false);
      setError(err.name === "NotAllowedError"
        ? "No hay permiso para usar el micrófono. Puedes habilitarlo en el navegador o guardar texto y fotos."
        : "No se pudo iniciar el micrófono. Puedes guardar texto y fotos.");
    }
  }

  const photoCount = files.filter((item) => item.kind === "photo").length;
  const audioCount = files.filter((item) => item.kind === "audio").length;
  return <div className="journal-media-picker">
    <p className="journal-media-label">Fotos y notas de voz <span>(opcional)</span></p>
    <div className="journal-media-actions">
      <button type="button" disabled={disabled || processing || recording || photoCount >= LIMITS.photo} onClick={() => gallery.current.click()}>Foto</button>
      <button type="button" disabled={disabled || processing || recording || photoCount >= LIMITS.photo} onClick={() => camera.current.click()}>Tomar foto</button>
      <button type="button" disabled={disabled || processing || recording || audioCount >= LIMITS.audio} onClick={start}>Nota de voz</button>
      <input ref={gallery} type="file" accept="image/jpeg,image/png,image/webp" multiple hidden onChange={photos} aria-label="Elegir fotos" />
      <input ref={camera} type="file" accept="image/*" capture="environment" hidden onChange={photos} aria-label="Tomar foto con cámara" />
    </div>
    <p className="muted journal-media-help">Hasta 6 fotos y 2 audios de 2 minutos. Máximo 2 MB por archivo.</p>
    {processing && <p role="status">Preparando adjunto…</p>}
    {recording && <div className="journal-recording">
      <p role="timer" aria-label="Tiempo de grabación">Grabando · {Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, "0")} / 2:00</p>
      <button type="button" onClick={() => active.current?.recorder?.stop()}>Detener grabación</button>
    </div>}
    {error && <p className="error" role="alert">{error}</p>}
    {files.length > 0 && <ul className="journal-media-previews" aria-label="Adjuntos por guardar">
      {files.map((item, index) => <Preview key={item.attachment_id} item={item}
        index={files.slice(0, index).filter((other) => other.kind === item.kind).length}
        disabled={disabled || processing || recording} onRemove={() => onChange(files.filter((file) => file.attachment_id !== item.attachment_id))} />)}
    </ul>}
  </div>;
}
