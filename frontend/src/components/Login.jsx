import { useState } from "react";
import { Icon } from "./Icon";

export function Login({ onLogin, error, demo }) {
  const [username, setUsername] = useState(demo ? "admin" : "");
  const [password, setPassword] = useState(demo ? "demo-password" : "");
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    try { await onLogin(username, password); } finally { setLoading(false); }
  }

  return (
    <main className="login-shell">
      <section className="login-panel">
        <div className="login-brand"><span className="brand__mark">B</span><span>BitrixVM Control</span></div>
        <div className="login-copy">
          <h1>Управление BitrixVM<br/>под контролем</h1>
          <p>Единая безопасная консоль для серверов, операций и аудита инфраструктуры BitrixEnv.</p>
        </div>
        <div className="login-security"><Icon name="shield"/><span>SSH-ключи и пароли зашифрованы.<br/>Опасные действия требуют подтверждения.</span></div>
      </section>
      <section className="login-form-wrap">
        <form className="login-form" onSubmit={submit}>
          <div><h2>Вход в консоль</h2><p>Используйте учётную запись администратора</p></div>
          {demo ? <div className="notice">Демонстрационный режим — запросы к серверу не отправляются.</div> : null}
          {error ? <div className="form-error"><Icon name="alert" size={18}/>{error}</div> : null}
          <label>Логин<input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required autoFocus /></label>
          <label>Пароль<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required /></label>
          <button className="button button--primary button--wide" disabled={loading}>{loading ? "Проверяем…" : "Войти"}</button>
          <small>Сессия защищена короткоживущим access-токеном</small>
        </form>
      </section>
    </main>
  );
}
