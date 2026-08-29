import { useState } from "react";
import { api } from "../api/client";
import { Icon } from "./Icon";
import { Modal } from "./Modal";

const riskLabels = { low: "Низкий риск", medium: "Средний риск", high: "Высокий риск", critical: "Критический риск" };

function initialValues(schema) {
  return Object.fromEntries(Object.entries(schema?.properties || {}).map(([key, definition]) => [key, definition.default ?? (definition.type === "boolean" ? false : "")]));
}

function fieldOptions(definition) {
  return definition.enum || definition["x-options"] || [];
}

export function ActionDialog({ server, capability, onClose, onExecuted, notify }) {
  const [values, setValues] = useState(() => initialValues(capability.request_schema));
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const confirmationRequired = ["high", "critical"].includes(capability.risk);
  const properties = Object.entries(capability.request_schema?.properties || {});

  function setValue(key, definition, raw) {
    const value = definition.type === "integer" ? (raw === "" ? "" : Number(raw)) : definition.type === "boolean" ? raw : raw;
    setValues((current) => ({ ...current, [key]: value })); setPreview(null);
  }

  async function previewAction() {
    setLoading(true);
    try { setPreview(await api.preview(server.id, capability.action, values)); }
    catch (error) { notify(error.message, "error"); } finally { setLoading(false); }
  }

  async function execute(event) {
    event.preventDefault();
    if (confirmationRequired && !preview) { await previewAction(); return; }
    setLoading(true);
    try { const operation = await api.execute(server.id, capability.action, values, preview?.confirmation_token); onExecuted(operation); notify("Операция добавлена в очередь"); onClose(); }
    catch (error) { notify(error.message, "error"); } finally { setLoading(false); }
  }

  return (
    <Modal title={capability.summary || capability.action} subtitle={`${server.name} · ${capability.action}`} onClose={onClose} size="large">
      <form onSubmit={execute}>
        <div className="modal__body action-layout">
          <div className="form-stack">
            <div className={`risk-callout risk-callout--${capability.risk}`}><span>{riskLabels[capability.risk]}</span><p>{confirmationRequired ? "Перед запуском API сформирует одноразовое подтверждение параметров." : "Действие можно поставить в очередь без дополнительного подтверждения."}</p></div>
            {properties.length === 0 ? <div className="empty-params">У действия нет параметров.</div> : properties.map(([key, definition]) => <label key={key}>{definition.description || key}{!capability.request_schema.required?.includes(key) ? <span className="optional">необязательно</span> : null}
              {definition.type === "boolean" ? <span className="switch-row"><input type="checkbox" checked={Boolean(values[key])} onChange={(event) => setValue(key, definition, event.target.checked)} /> Включено</span> : fieldOptions(definition).length ? <select value={values[key]} onChange={(event) => setValue(key, definition, event.target.value)} required={capability.request_schema.required?.includes(key)}><option value="">Выберите значение</option>{fieldOptions(definition).map((item) => <option key={item} value={item}>{item}</option>)}</select> : <input type={definition.format === "password" ? "password" : definition.type === "integer" ? "number" : "text"} value={values[key]} min={definition.minimum} max={definition.maximum} pattern={definition.pattern} onChange={(event) => setValue(key, definition, event.target.value)} required={capability.request_schema.required?.includes(key)} />}
              <small className="field-code">{key}</small>
            </label>)}
          </div>
          <aside className="action-preview"><h3>Проверка запуска</h3>{preview ? <><div className="preview-ok"><Icon name="check"/> Параметры проверены</div><p>{preview.summary}</p>{preview.warnings?.map((warning) => <div key={warning} className="preview-warning"><Icon name="alert" size={17}/>{warning}</div>)}<dl><dt>Подтверждение действует до</dt><dd>{new Date(preview.expires_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}</dd></dl></> : <p className="muted">{confirmationRequired ? "Заполните параметры и выполните предварительную проверку." : "Проверьте параметры перед постановкой операции в очередь."}</p>}</aside>
        </div>
        <footer className="modal__footer"><button type="button" className="button" onClick={onClose}>Отмена</button>{confirmationRequired && !preview ? <button type="button" className="button button--primary" onClick={previewAction} disabled={loading}>{loading ? "Проверяем…" : "Предварительный просмотр"}</button> : <button className={`button ${capability.risk === "critical" ? "button--danger" : "button--primary"}`} disabled={loading}>{loading ? "Отправляем…" : "Запустить операцию"}</button>}</footer>
      </form>
    </Modal>
  );
}
