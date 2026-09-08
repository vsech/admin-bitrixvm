import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Icon } from "./Icon";

function toLocalDatetimeString(date) {
  const d = new Date(date);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function LogViewer({ server, notify }) {
  const [services, setServices] = useState([]);
  const [service, setService] = useState("");
  const [source, setSource] = useState("journal");
  const [dateFrom, setDateFrom] = useState(() => {
    const d = new Date(Date.now() - 3600000);
    return toLocalDatetimeString(d);
  });
  const [dateTo, setDateTo] = useState(() => toLocalDatetimeString(new Date()));
  const [filePath, setFilePath] = useState("");
  const [grep, setGrep] = useState("");
  const [lines, setLines] = useState([]);
  const [total, setTotal] = useState(0);
  const [truncated, setTruncated] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    api.logServices().then((items) => { if (active) setServices(items); }).catch((err) => { if (active) notify(err.message, "error"); });
    return () => { active = false; };
  }, [notify]);

  const selectedService = services.find((s) => s.id === service);

  useEffect(() => {
    if (selectedService && selectedService.files.length > 0) {
      setFilePath(selectedService.files[0]);
    } else {
      setFilePath("");
    }
  }, [selectedService]);

  useEffect(() => {
    if (selectedService) {
      setSource(selectedService.journal_unit ? "journal" : "file");
    }
  }, [selectedService]);

  async function fetchLogs() {
    if (!service) {
      notify("Выберите сервис", "error");
      return;
    }
    setLoading(true);
    setLoaded(false);
    try {
      const result = await api.logs(server.id, {
        service,
        source,
        date_from: new Date(dateFrom).toISOString(),
        date_to: new Date(dateTo).toISOString(),
        file_path: source === "file" ? filePath : null,
        grep: grep || null,
        limit: 5000,
      });
      setLines(result.lines);
      setTotal(result.total);
      setTruncated(result.truncated);
      setLoaded(true);
    } catch (err) {
      notify(err.message, "error");
    } finally {
      setLoading(false);
    }
  }

  function downloadLogs() {
    if (!lines.length) return;
    const blob = new Blob([lines.join("\n")], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${server.name}_${service}_${new Date().toISOString().slice(0, 10)}.log`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="log-viewer">
      <div className="log-controls">
        <label>
          Сервис
          <select value={service} onChange={(e) => setService(e.target.value)} required>
            <option value="">Выберите сервис</option>
            {services.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </label>

        <label>
          Источник
          <select value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="journal" disabled={!selectedService?.journal_unit}>journalctl</option>
            <option value="file">Файл лога</option>
          </select>
        </label>

        {source === "file" && selectedService?.files?.length > 0 && (
          <label>
            Файл
            <select value={filePath} onChange={(e) => setFilePath(e.target.value)}>
              {selectedService.files.map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
          </label>
        )}

        <label>
          С
          <input
            type="datetime-local"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
          />
        </label>

        <label>
          По
          <input
            type="datetime-local"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
          />
        </label>

        <label>
          Фильтр
          <input
            type="text"
            value={grep}
            onChange={(e) => setGrep(e.target.value)}
            placeholder="grep шаблон"
          />
        </label>

        <div className="log-controls__actions">
          <button className="button button--primary" onClick={fetchLogs} disabled={loading || !service}>
            {loading ? "Загружаем…" : "Загрузить логи"}
          </button>
          {loaded && lines.length > 0 && (
            <button className="button" onClick={downloadLogs}>
              <Icon name="snapshot" size={16} /> Скачать
            </button>
          )}
        </div>
      </div>

      {loaded && (
        <div className="log-info">
          <span>Строк: {total}</span>
          {truncated && <span className="log-info__warn"> (ограничено 5000 строк)</span>}
          <span> · Источник: {lines[0]?.includes("journalctl") ? "journalctl" : source}</span>
        </div>
      )}

      <div className="log-output">
        {loading ? (
          <div className="log-loading">
            <div className="skeleton-list"><i/><i/><i/><i/><i/></div>
          </div>
        ) : loaded && lines.length > 0 ? (
          <pre className="log-pre">{lines.join("\n")}</pre>
        ) : loaded ? (
          <div className="log-empty">Логи не найдены за выбранный период</div>
        ) : (
          <div className="log-empty">Выберите сервис и период для загрузки логов</div>
        )}
      </div>
    </div>
  );
}
