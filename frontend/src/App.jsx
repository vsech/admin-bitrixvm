import { useCallback, useEffect, useState } from "react";
import { api } from "./api/client";
import { Login } from "./components/Login";
import { OperationsView } from "./components/OperationsView";
import { Overview } from "./components/Overview";
import { ServerWorkspace } from "./components/ServerWorkspace";
import { Sidebar } from "./components/Sidebar";
import { Toast } from "./components/Toast";
import { UsersView } from "./components/UsersView";
import { Icon } from "./components/Icon";

export default function App() {
  const [user, setUser] = useState(null);
  const [initializing, setInitializing] = useState(api.authenticated);
  const [loginError, setLoginError] = useState("");
  const [view, setView] = useState("servers");
  const [servers, setServers] = useState([]);
  const [operations, setOperations] = useState([]);
  const [toast, setToast] = useState(null);
  const [mobileOpen, setMobileOpen] = useState(false);

  const notify = useCallback((message, type = "success") => { setToast({ message, type }); window.setTimeout(() => setToast(null), 4200); }, []);

  useEffect(() => {
    if (!api.authenticated) { setInitializing(false); return; }
    api.me().then(setUser).catch(() => api.clearTokens()).finally(() => setInitializing(false));
  }, []);

  useEffect(() => {
    if (!user) return;
    let active = true;
    Promise.all([api.servers(), api.operations()]).then(([serverItems, operationItems]) => { if (active) { setServers(serverItems); setOperations(operationItems); } }).catch((error) => notify(error.message, "error"));
    return () => { active = false; };
  }, [user, notify]);

  async function login(username, password) { setLoginError(""); try { setUser(await api.login(username, password)); } catch (error) { setLoginError(error.message); } }
  async function logout() { await api.logout(); setUser(null); setServers([]); setOperations([]); }

  if (initializing) return <div className="app-loading"><span className="brand__mark">B</span><p>Подключаемся к контроллеру…</p></div>;
  if (!user) return <Login onLogin={login} error={loginError} demo={api.isDemo}/>;

  return <div className="app-shell">
    <Sidebar view={view} user={user} onNavigate={setView} onLogout={logout} mobileOpen={mobileOpen} onMobileToggle={(value) => setMobileOpen(value ?? !mobileOpen)} />
    {mobileOpen ? <button className="mobile-overlay" aria-label="Закрыть меню" onClick={() => setMobileOpen(false)}/> : null}
    <div className="app-main">
      <div className="mobile-bar"><button className="icon-button" onClick={() => setMobileOpen(true)} aria-label="Открыть меню"><Icon name="menu"/></button><span>BitrixVM Control</span><span className="account__avatar">{user.username.slice(0, 1).toUpperCase()}</span></div>
      {view === "overview" ? <Overview servers={servers} operations={operations} onNavigate={setView}/> : null}
      {view === "servers" ? <ServerWorkspace servers={servers} setServers={setServers} operations={operations} setOperations={setOperations} notify={notify} navigateOperations={() => setView("operations")}/> : null}
      {view === "operations" ? <OperationsView operations={operations} setOperations={setOperations} servers={servers} notify={notify}/> : null}
      {view === "users" ? <UsersView currentUser={user} notify={notify}/> : null}
    </div>
    <Toast toast={toast} onClose={() => setToast(null)}/>
  </div>;
}
