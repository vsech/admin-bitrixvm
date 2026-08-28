import { Icon } from "./Icon";
import { OperationStatus } from "./ServerWorkspace";

export function Overview({ servers, operations, onNavigate }) {
  const running = operations.filter((item) => ["queued", "running"].includes(item.status));
  return <section className="page"><header className="page-header"><div><h1>Обзор</h1><p>Состояние контура управления BitrixVM</p></div><button className="button button--primary" onClick={() => onNavigate("servers")}><Icon name="servers"/>Открыть серверы</button></header>
    <div className="overview-lead"><div><span>Контроллер готов</span><h2>{servers.length ? `${servers.length} ${servers.length === 1 ? "сервер" : "сервера"} подключено` : "Серверы ещё не добавлены"}</h2><p>Опасные действия проходят предварительную проверку, все операции сохраняются в журнале аудита.</p></div><Icon name="shield" size={54}/></div>
    <div className="overview-columns"><section className="panel overview-section"><header><h2>Инфраструктура</h2><button onClick={() => onNavigate("servers")}>Все серверы <Icon name="chevron" size={16}/></button></header>{servers.map((server) => <button className="overview-server" key={server.id} onClick={() => onNavigate("servers")}><span className="server-name"><Icon name="servers" size={18}/><span><b>{server.name}</b><small>{server.address}</small></span></span><span className="status status--ok"><i/>Доступен</span></button>)}</section>
      <section className="panel overview-section"><header><h2>Активные операции</h2><button onClick={() => onNavigate("operations")}>Журнал <Icon name="chevron" size={16}/></button></header>{running.length ? running.map((operation) => <button className="overview-operation" key={operation.id} onClick={() => onNavigate("operations")}><span><code>{operation.action}</code><small>{servers.find((item) => item.id === operation.server_id)?.name}</small></span><OperationStatus status={operation.status}/></button>) : <div className="inline-empty">Активных операций нет</div>}</section></div>
  </section>;
}
