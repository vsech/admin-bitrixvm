import { Icon } from "./Icon";

const items = [
  ["overview", "overview", "Обзор"],
  ["servers", "servers", "Серверы"],
  ["operations", "operations", "Операции"],
  ["users", "users", "Пользователи"],
];

export function Sidebar({ view, user, onNavigate, onLogout, mobileOpen, onMobileToggle }) {
  return (
    <aside className={`sidebar ${mobileOpen ? "sidebar--open" : ""}`}>
      <div className="brand"><span>BitrixVM Control</span></div>
      <button className="mobile-close" onClick={() => onMobileToggle(false)} aria-label="Закрыть меню"><Icon name="close" /></button>
      <nav className="sidebar__nav" aria-label="Основная навигация">
        {items.map(([id, icon, label]) => (
          <button key={id} className={`nav-item ${view === id ? "nav-item--active" : ""}`} onClick={() => { onNavigate(id); onMobileToggle(false); }} aria-current={view === id ? "page" : undefined}>
            <Icon name={icon} /><span>{label}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar__account">
        <div className="account"><span className="account__avatar">{user?.username?.slice(0, 1).toUpperCase()}</span><span><b>{user?.username}</b></span></div>
        <button className="nav-item" onClick={onLogout}><Icon name="logout" /><span>Выйти</span></button>
      </div>
    </aside>
  );
}
