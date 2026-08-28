import { useState } from "react";
import { api } from "../api/client";
import { Icon } from "./Icon";
import { Modal } from "./Modal";
import { OperationStatus } from "./ServerWorkspace";

export function OperationsView({ operations, setOperations, servers, notify }) {
  const [filter, setFilter] = useState("all");
  const [selected, setSelected] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const visible = filter === "all" ? operations : operations.filter((item) => item.status === filter);

  async function open(operation) { setSelected(operation); setLoading(true); try { setEvents(await api.events(operation.id)); } catch (error) { notify(error.message, "error"); } finally { setLoading(false); } }
  async function cancel() { try { const updated = await api.cancelOperation(selected.id); setOperations((items) => items.map((item) => item.id === updated.id ? updated : item)); setSelected(updated); notify("Операция отменена"); } catch (error) { notify(error.message, "error"); } }

  return <section className="page"><header className="page-header"><div><h1>Операции</h1><p>Очередь действий и журнал выполнения</p></div><button className="button" onClick={async () => { try { setOperations(await api.operations()); notify("Список операций обновлён"); } catch (error) { notify(error.message, "error"); } }}><Icon name="refresh"/>Обновить</button></header>
    <div className="filter-tabs">{[["all", "Все"], ["queued", "В очереди"], ["running", "Выполняются"], ["succeeded", "Завершены"], ["failed", "Ошибки"]].map(([id, label]) => <button key={id} className={filter === id ? "active" : ""} onClick={() => setFilter(id)}>{label}<span>{id === "all" ? operations.length : operations.filter((item) => item.status === id).length}</span></button>)}</div>
    <div className="data-table panel"><div className="operation-head operation-grid"><span>Операция</span><span>Сервер</span><span>Риск</span><span>Статус</span><span>Создана</span></div>{visible.map((operation) => <button className="operation-row operation-grid" key={operation.id} onClick={() => open(operation)}><span><code>{operation.action}</code><small>{operation.id.slice(0, 12)}</small></span><span>{servers.find((server) => server.id === operation.server_id)?.name || operation.server_id.slice(0, 8)}</span><span className={`risk risk--${operation.risk}`}><i/>{operation.risk}</span><OperationStatus status={operation.status}/><time>{new Date(operation.created_at).toLocaleString("ru-RU", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}</time></button>)}</div>
    {!visible.length ? <div className="empty-state empty-state--small"><h2>Операций нет</h2><p>Измените фильтр или запустите действие на странице сервера.</p></div> : null}
    {selected ? <Modal title={selected.action} subtitle={`Операция ${selected.id}`} onClose={() => setSelected(null)} size="large"><div className="modal__body operation-detail"><div className="operation-summary"><dl><dt>Статус</dt><dd><OperationStatus status={selected.status}/></dd><dt>Сервер</dt><dd>{servers.find((server) => server.id === selected.server_id)?.name || selected.server_id}</dd><dt>Параметры</dt><dd><code>{JSON.stringify(selected.args_redacted)}</code></dd><dt>Создана</dt><dd>{new Date(selected.created_at).toLocaleString("ru-RU")}</dd></dl>{selected.error_message ? <div className="form-error"><Icon name="alert"/>{selected.error_message}</div> : null}</div><div className="timeline"><h3>События</h3>{loading ? <div className="skeleton-list"><i/><i/><i/></div> : events.map((event) => <div className="timeline-item" key={event.id}><i/><div><b>{event.message}</b><span>{event.event} · {new Date(event.created_at).toLocaleTimeString("ru-RU")}</span></div></div>)}</div></div><footer className="modal__footer">{selected.status === "queued" ? <button className="button button--danger" onClick={cancel}>Отменить операцию</button> : null}<button className="button button--primary" onClick={() => setSelected(null)}>Закрыть</button></footer></Modal> : null}
  </section>;
}
