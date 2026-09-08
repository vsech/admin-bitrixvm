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

  const [editingUser, setEditingUser] = useState(null);
  const [editUsername, setEditUsername] = useState("");
  const [editPassword, setEditPassword] = useState("");

  const [changingUser, setChangingUser] = useState(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  useEffect(() => { api.users().then(setUsers).catch((error) => notify(error.message, "error")).finally(() => setLoading(false)); }, []);

  async function create(event) {
    event.preventDefault();
    setLoading(true);
    try {
      const user = await api.createUser({ username, password });
      setUsers((items) => [...items, user]);
      setCreateOpen(false);
      setUsername("");
      setPassword("");
      notify(`Пользователь ${user.username} создан`);
    } catch (error) {
      notify(error.message, "error");
    } finally {
      setLoading(false);
    }
  }

  async function disable(user) {
    if (!window.confirm(`Отключить пользователя ${user.username}?`)) return;
    try {
      await api.disableUser(user.id);
      setUsers((items) => items.map((item) => item.id === user.id ? { ...item, is_active: false } : item));
      notify(`Пользователь ${user.username} отключён`);
    } catch (error) {
      notify(error.message, "error");
    }
  }

  function openEdit(user) {
    setEditingUser(user);
    setEditUsername(user.username);
    setEditPassword("");
  }

  async function saveEdit(event) {
    event.preventDefault();
    setLoading(true);
    try {
      const updated = await api.updateUser(editingUser.id, { username: editUsername, current_password: editPassword });
      setUsers((items) => items.map((item) => item.id === updated.id ? updated : item));
      setEditingUser(null);
      setEditPassword("");
      notify(`Пользователь ${updated.username} обновлён`);
    } catch (error) {
      notify(error.message, "error");
    } finally {
      setLoading(false);
    }
  }

  function openPasswordChange(user) {
    setChangingUser(user);
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
  }

  async function savePassword(event) {
    event.preventDefault();
    if (newPassword !== confirmPassword) {
      notify("Пароли не совпадают", "error");
      return;
    }
    setLoading(true);
    try {
      await api.changePassword(changingUser.id, { current_password: currentPassword, new_password: newPassword, confirm_password: confirmPassword });
      setChangingUser(null);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      notify("Пароль изменён");
    } catch (error) {
      notify(error.message, "error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page">
      <header className="page-header">
        <div><h1>Пользователи</h1><p>Доступ администраторов к консоли</p></div>
        <button className="button button--primary" onClick={() => setCreateOpen(true)}><Icon name="plus" />Добавить пользователя</button>
      </header>
      <div className="data-table panel">
        <div className="user-head user-grid">
          <span>Пользователь</span><span>Статус</span><span>Создан</span><span />
        </div>
        {loading ? <div className="skeleton-list"><i /><i /></div> : users.map((user) => (
          <div className="user-row user-grid" key={user.id}>
            <span className="user-cell"><b>{user.username}</b>{user.id === currentUser.id ? <small>Текущая учётная запись</small> : null}</span>
            <span className={user.is_active ? "status status--ok" : "status status--muted"}><i />{user.is_active ? "Активен" : "Отключён"}</span>
            <time>{new Date(user.created_at).toLocaleDateString("ru-RU")}</time>
            <span className="user-actions">
              <button className="icon-button" onClick={() => openEdit(user)} disabled={!user.is_active} aria-label={`Редактировать ${user.username}`}><Icon name="pencil" size={18} /></button>
              <button className="icon-button" onClick={() => openPasswordChange(user)} disabled={!user.is_active} aria-label={`Сменить пароль ${user.username}`}><Icon name="key" size={18} /></button>
              <button className="icon-button" onClick={() => disable(user)} disabled={user.id === currentUser.id || !user.is_active} aria-label={`Отключить ${user.username}`}><Icon name="trash" size={18} /></button>
            </span>
          </div>
        ))}
      </div>

      {createOpen ? (
        <Modal title="Новый пользователь" subtitle="Доступ к управлению всей инфраструктурой" onClose={() => setCreateOpen(false)}>
          <form onSubmit={create}>
            <div className="modal__body form-stack">
              <label>Логин<input value={username} onChange={(event) => setUsername(event.target.value)} minLength="3" maxLength="64" pattern="[A-Za-z0-9_.\\-]+" autoComplete="username" required autoFocus /></label>
              <label>Пароль<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength="12" maxLength="256" autoComplete="new-password" required /><small>Не менее 12 символов</small></label>
              <div className="info-box"><Icon name="shield" /><p>Новый пользователь получит полный административный доступ к серверам и операциям.</p></div>
            </div>
            <footer className="modal__footer"><button type="button" className="button" onClick={() => setCreateOpen(false)}>Отмена</button><button className="button button--primary" disabled={loading}>Создать</button></footer>
          </form>
        </Modal>
      ) : null}

      {editingUser ? (
        <Modal title="Редактирование пользователя" subtitle={editingUser.username} onClose={() => setEditingUser(null)}>
          <form onSubmit={saveEdit}>
            <div className="modal__body form-stack">
              <label>Логин<input value={editUsername} onChange={(event) => setEditUsername(event.target.value)} minLength="3" maxLength="64" pattern="[A-Za-z0-9_.\\-]+" autoComplete="username" required autoFocus /></label>
              <label>Текущий пароль<input type="password" value={editPassword} onChange={(event) => setEditPassword(event.target.value)} minLength="12" maxLength="256" autoComplete="current-password" required /><small>Введите текущий пароль для подтверждения</small></label>
            </div>
            <footer className="modal__footer"><button type="button" className="button" onClick={() => setEditingUser(null)}>Отмена</button><button className="button button--primary" disabled={loading}>Сохранить</button></footer>
          </form>
        </Modal>
      ) : null}

      {changingUser ? (
        <Modal title="Смена пароля" subtitle={changingUser.username} onClose={() => setChangingUser(null)}>
          <form onSubmit={savePassword}>
            <div className="modal__body form-stack">
              <label>Текущий пароль<input type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} minLength="12" maxLength="256" autoComplete="current-password" required autoFocus /></label>
              <label>Новый пароль<input type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} minLength="12" maxLength="256" autoComplete="new-password" required /><small>Не менее 12 символов</small></label>
              <label>Подтверждение пароля<input type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} minLength="12" maxLength="256" autoComplete="new-password" required /></label>
            </div>
            <footer className="modal__footer"><button type="button" className="button" onClick={() => setChangingUser(null)}>Отмена</button><button className="button button--primary" disabled={loading}>Изменить</button></footer>
          </form>
        </Modal>
      ) : null}
    </section>
  );
}
