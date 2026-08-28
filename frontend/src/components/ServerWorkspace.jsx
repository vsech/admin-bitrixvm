import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { Icon } from "./Icon";
import { ActionDialog } from "./ActionDialog";
import { AddServerDialog } from "./AddServerDialog";
import { Modal } from "./Modal";

const riskLabels = { low: "Низкий", medium: "Средний", high: "Высокий", critical: "Критический" };
const categoryLabels = { pool: "Пул", hosts: "Хосты", local: "Система", runtime: "Платформа", mysql: "MySQL", memcached: "Memcached", tasks: "Задачи", sites: "Сайты", site: "Сайты", sphinx: "Sphinx", web: "Web / PHP", monitoring: "Мониторинг", push: "Push", transformer: "Трансформер" };
const summaryTranslations = { "Create the native Bitrix server pool": "Создать пул Bitrix", "Remove the native Bitrix server pool": "Удалить пул Bitrix", "Reboot the BitrixVM server": "Перезагрузить сервер", "Power off the BitrixVM server": "Выключить сервер", "Update all EL9 packages": "Обновить системные пакеты", "Create memcached instance": "Создать экземпляр Memcached", "Stop a Bitrix background task": "Остановить фоновую задачу", "Create a Bitrix kernel site": "Создать сайт с ядром Bitrix", "Configure Node.js push service": "Настроить Push-сервис" };

const relativeTime = (date) => {
  if (!date) return "Не проверялся";
  const minutes = Math.max(0, Math.round((Date.now() - new Date(date).getTime()) / 60000));
  if (minutes < 1) return "только что";
  if (minutes < 60) return `${minutes} мин назад`;
  if (minutes < 1440) return `${Math.round(minutes / 60)} ч назад`;
  return new Date(date).toLocaleDateString("ru-RU");
};

export function ServerWorkspace({ servers, setServers, operations, setOperations, notify, navigateOperations }) {
  const [selectedId, setSelectedId] = useState(servers[0]?.id || null);
  const [capabilities, setCapabilities] = useState([]);
  const [search, setSearch] = useState("");
  const [actionSearch, setActionSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [loadingCapabilities, setLoadingCapabilities] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [activeAction, setActiveAction] = useState(null);
  const [snapshot, setSnapshot] = useState(null);
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const selected = servers.find((item) => item.id === selectedId) || servers[0];

  useEffect(() => {
    if (!selected) { setCapabilities([]); return; }
    let active = true; setLoadingCapabilities(true);
    api.capabilities(selected.id).then((items) => { if (active) setCapabilities(items); }).catch((error) => notify(error.message, "error")).finally(() => active && setLoadingCapabilities(false));
    return () => { active = false; };
  }, [selected?.id]);

  const visibleServers = useMemo(() => servers.filter((server) => `${server.name} ${server.address}`.toLowerCase().includes(search.toLowerCase())), [servers, search]);
  const categories = useMemo(() => [...new Set(capabilities.map((item) => item.category))], [capabilities]);
  const visibleCapabilities = useMemo(() => capabilities.filter((item) => (category === "all" || item.category === category) && `${item.action} ${item.summary || ""}`.toLowerCase().includes(actionSearch.toLowerCase())), [capabilities, category, actionSearch]);

  async function refreshCapabilities() {
    if (!selected) return; setLoadingCapabilities(true);
    try { setCapabilities(await api.refreshCapabilities(selected.id)); notify("Возможности сервера обновлены"); setServers((items) => items.map((item) => item.id === selected.id ? { ...item, capabilities_checked_at: new Date().toISOString() } : item)); }
    catch (error) { notify(error.message, "error"); } finally { setLoadingCapabilities(false); }
  }

  async function loadSnapshot() {
    setSnapshotLoading(true);
    try { setSnapshot(await api.snapshot(selected.id)); } catch (error) { notify(error.message, "error"); } finally { setSnapshotLoading(false); }
  }

  if (!servers.length) return <section className="page"><PageHeader search={search} setSearch={setSearch} onAdd={() => setAddOpen(true)} /><div className="empty-state"><div className="empty-state__icon"><Icon name="servers" size={30}/></div><h2>Добавьте первый сервер</h2><p>Контроллер проверит SSH fingerprint и совместимость BitrixEnv перед сохранением.</p><button className="button button--primary" onClick={() => setAddOpen(true)}><Icon name="plus"/> Добавить сервер</button></div>{addOpen ? <AddServerDialog onClose={() => setAddOpen(false)} onCreated={(server) => { setServers([server]); setSelectedId(server.id); }} notify={notify}/> : null}</section>;

  return <section className="page page--servers">
    <PageHeader search={search} setSearch={setSearch} onAdd={() => setAddOpen(true)} />
    <div className="server-workspace">
      <div className="server-list panel">
        <div className="table-head server-grid"><span>Сервер</span><span>Адрес</span><span>Состояние</span><span>Проверка</span></div>
        <div className="server-rows">{visibleServers.map((server) => <button key={server.id} className={`server-row server-grid ${selected?.id === server.id ? "selected" : ""}`} onClick={() => setSelectedId(server.id)}><span className="server-name"><Icon name="servers" size={18}/><b>{server.name}</b></span><code>{server.address}</code><span className={Date.now() - new Date(server.capabilities_checked_at).getTime() > 7200000 ? "status status--warn" : "status status--ok"}><i/>{Date.now() - new Date(server.capabilities_checked_at).getTime() > 7200000 ? "Проверить" : "Доступен"}</span><span>{relativeTime(server.capabilities_checked_at)}</span></button>)}</div>
        {!visibleServers.length ? <div className="inline-empty">Серверы не найдены</div> : null}
      </div>
      <div className="server-detail panel">
        <header className="detail-header"><div><h2>{selected.name}</h2><span className="status status--ok"><i/>Доступен</span></div><div className="button-group"><button className="button button--small" onClick={refreshCapabilities} disabled={loadingCapabilities}><Icon name="refresh"/>{loadingCapabilities ? "Обновляем…" : "Обновить"}</button><button className="button button--small" onClick={loadSnapshot} disabled={snapshotLoading}><Icon name="snapshot"/>{snapshotLoading ? "Собираем…" : "Снимок"}</button></div></header>
        <dl className="server-meta"><dt>Адрес</dt><dd><code>{selected.address}:{selected.port}</code></dd><dt>Пользователь</dt><dd>{selected.username}</dd><dt>SSH fingerprint</dt><dd><code title={selected.host_key_fingerprint}>{selected.host_key_fingerprint.slice(0, 29)}…</code></dd><dt>Возможности получены</dt><dd>{relativeTime(selected.capabilities_checked_at)}</dd></dl>
        <div className="tabs" role="tablist"><button className="active">Возможности <span>{capabilities.filter((item) => item.available).length}</span></button><button onClick={loadSnapshot}>Состояние</button><button onClick={navigateOperations}>История</button></div>
        <div className="capability-tools"><div className="search search--compact"><Icon name="search"/><input value={actionSearch} onChange={(event) => setActionSearch(event.target.value)} placeholder="Найти действие" aria-label="Найти действие" /></div><select value={category} onChange={(event) => setCategory(event.target.value)} aria-label="Категория"><option value="all">Все категории</option>{categories.map((item) => <option value={item} key={item}>{categoryLabels[item] || item}</option>)}</select></div>
        <div className="capability-table"><div className="capability-head"><span>Действие</span><span>Описание</span><span>Риск</span><span>Доступность</span><span/></div>{loadingCapabilities ? <div className="skeleton-list"><i/><i/><i/><i/></div> : visibleCapabilities.map((item) => <div className={`capability-row ${!item.available ? "disabled" : ""}`} key={item.action}><code>{item.action}</code><span>{summaryTranslations[item.summary] || item.summary || categoryLabels[item.category] || "Системное действие"}{item.reason ? <small>Причина: {item.reason}</small> : null}</span><span className={`risk risk--${item.risk}`}><i/>{riskLabels[item.risk]}</span><span className={item.available ? "available" : "unavailable"}>{item.available ? "Доступно" : "Недоступно"}</span><button className="button button--outline button--tiny" disabled={!item.available} onClick={() => setActiveAction({ ...item, summary: summaryTranslations[item.summary] || item.summary || item.action })}>Открыть</button></div>)}</div>
        {!loadingCapabilities && !visibleCapabilities.length ? <div className="inline-empty">Подходящие действия не найдены</div> : null}
      </div>
    </div>
    <section className="recent panel"><header><h2>Последние операции</h2><button onClick={navigateOperations}>Все операции <Icon name="chevron" size={17}/></button></header>{operations.slice(0, 3).map((operation) => <div className="recent-row" key={operation.id}><code>{operation.action}</code><span>{servers.find((server) => server.id === operation.server_id)?.name || "—"}</span><OperationStatus status={operation.status}/><time>{new Date(operation.created_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}</time></div>)}</section>
    {addOpen ? <AddServerDialog onClose={() => setAddOpen(false)} onCreated={(server) => { setServers((items) => [...items, server]); setSelectedId(server.id); }} notify={notify}/> : null}
    {activeAction ? <ActionDialog server={selected} capability={activeAction} onClose={() => setActiveAction(null)} onExecuted={(operation) => setOperations((items) => [operation, ...items])} notify={notify}/> : null}
    {snapshot ? <Modal title="Снимок состояния" subtitle={`${selected.name} · получен только что`} onClose={() => setSnapshot(null)}><div className="modal__body snapshot"><pre>{JSON.stringify(snapshot, null, 2)}</pre></div><footer className="modal__footer"><button className="button button--primary" onClick={() => setSnapshot(null)}>Готово</button></footer></Modal> : null}
  </section>;
}

function PageHeader({ search, setSearch, onAdd }) { return <header className="page-header"><div><h1>Серверы</h1><p>Управление инфраструктурой BitrixEnv</p></div><div className="page-actions"><div className="search"><Icon name="search"/><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Поиск по серверам" aria-label="Поиск по серверам" /></div><button className="button button--primary" onClick={onAdd}><Icon name="plus"/>Добавить сервер</button></div></header>; }

export function OperationStatus({ status }) { const labels = { queued: "В очереди", running: "Выполняется", succeeded: "Выполнено", failed: "Ошибка", canceled: "Отменено", unknown: "Неизвестно" }; return <span className={`op-status op-status--${status}`}><i/>{labels[status] || status}</span>; }
