import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Icon } from "./Icon";
import { Modal } from "./Modal";

export function UsersView({ currentUser, notify }) {
  const [users, setUsers] = useState([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.users().then(setUsers).catch((error) => notify(error.message, "error")).finally(() => setLoading(false)); }, []);
  async function create(event) { event.preventDefault(); setLoading(true); try { const user = await api.createUser({ username, password }); setUsers((items) => [...items, user]); setCreateOpen(false); setUsername(""); setPassword(""); notify(`Пользователь ${user.username} создан`); } catch (error) { notify(error.message, "error"); } finally { setLoading(false); } }
  async function disable(user) { if (!window.confirm(`Отключить пользователя ${user.username}?`)) return; try { await api.disableUser(user.id); setUsers((items) => items.map((item) => item.id === user.id ? { ...item, is_active: false } : item)); notify(`Пользователь ${user.username} отключён`); } catch (error) { notify(error.message, "error"); } }
  return <section className="page"><header className="page-header"><div><h1>Пользователи</h1><p>Доступ администраторов к консоли</p></div><button className="button button--primary" onClick={() => setCreateOpen(true)}><Icon name="plus"/>Добавить пользователя</button></header>
    <div className="data-table panel"><div className="user-head user-grid"><span>Пользователь</span><span>Статус</span><span>Создан</span><span/></div>{loading ? <div className="skeleton-list"><i/><i/></div> : users.map((user) => <div className="user-row user-grid" key={user.id}><span className="user-cell"><b>{user.username}</b>{user.id === currentUser.id ? <small>Текущая учётная запись</small> : null}</span><span className={user.is_active ? "status status--ok" : "status status--muted"}><i/>{user.is_active ? "Активен" : "Отключён"}</span><time>{new Date(user.created_at).toLocaleDateString("ru-RU")}</time><button className="icon-button" onClick={() => disable(user)} disabled={user.id === currentUser.id || !user.is_active} aria-label={`Отключить ${user.username}`}><Icon name="trash" size={18}/></button></div>)}</div>
    {createOpen ? <Modal title="Новый пользователь" subtitle="Доступ к управлению всей инфраструктурой" onClose={() => setCreateOpen(false)}><form onSubmit={create}><div className="modal__body form-stack"><label>Логин<input value={username} onChange={(event) => setUsername(event.target.value)} minLength="3" maxLength="64" pattern={"[A-Za-z0-9_.\\-]+"} autoComplete="username" required autoFocus /></label><label>Пароль<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength="12" maxLength="256" autoComplete="new-password" required /><small>Не менее 12 символов</small></label><div className="info-box"><Icon name="shield"/><p>Новый пользователь получит полный административный доступ к серверам и операциям.</p></div></div><footer className="modal__footer"><button type="button" className="button" onClick={() => setCreateOpen(false)}>Отмена</button><button className="button button--primary" disabled={loading}>Создать</button></footer></form></Modal> : null}
  </section>;
}
