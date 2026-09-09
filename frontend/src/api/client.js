import { demoCapabilities, demoEvents, demoOperations, demoServers, demoSnapshot, demoUser } from "../data/demo";

const DEMO = new URLSearchParams(window.location.search).get("demo") === "1";
const wait = (value, delay = 180) => new Promise((resolve) => window.setTimeout(() => resolve(structuredClone(value)), delay));

class ApiError extends Error {
  constructor(message, status = 0, code = "request_failed") {
    super(message);
    this.status = status;
    this.code = code;
  }
}

class ApiClient {
  constructor() {
    this.accessToken = sessionStorage.getItem("bitrixvm_access");
    this.refreshToken = localStorage.getItem("bitrixvm_refresh");
    this.demoOperations = structuredClone(demoOperations);
  }

  get isDemo() { return DEMO; }
  get authenticated() { return DEMO || Boolean(this.accessToken); }

  setTokens(tokens) {
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;
    sessionStorage.setItem("bitrixvm_access", this.accessToken);
    localStorage.setItem("bitrixvm_refresh", this.refreshToken);
  }

  clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    sessionStorage.removeItem("bitrixvm_access");
    localStorage.removeItem("bitrixvm_refresh");
  }

  async request(path, options = {}, allowRefresh = true) {
    const headers = new Headers(options.headers);
    if (options.body && !(options.body instanceof URLSearchParams)) headers.set("Content-Type", "application/json");
    if (this.accessToken) headers.set("Authorization", `Bearer ${this.accessToken}`);
    const response = await fetch(path, { ...options, headers });
    if (response.status === 401 && allowRefresh && this.refreshToken) {
      const refreshed = await this.refresh();
      if (refreshed) return this.request(path, options, false);
    }
    if (!response.ok) {
      let payload = {};
      try { payload = await response.json(); } catch { /* empty response */ }
      throw new ApiError(payload.detail || payload.title || `Ошибка запроса (${response.status})`, response.status, payload.code);
    }
    return response.status === 204 ? null : response.json();
  }

  async login(username, password) {
    if (DEMO) return wait(demoUser);
    const form = new URLSearchParams({ username, password });
    const tokens = await this.request("/api/v1/auth/login", { method: "POST", body: form }, false);
    this.setTokens(tokens);
    return this.me();
  }

  async refresh() {
    try {
      const tokens = await this.request("/api/v1/auth/refresh", { method: "POST", body: JSON.stringify({ refresh_token: this.refreshToken }) }, false);
      this.setTokens(tokens);
      return true;
    } catch {
      this.clearTokens();
      return false;
    }
  }

  async logout() {
    if (!DEMO && this.refreshToken) {
      try { await this.request("/api/v1/auth/logout", { method: "POST", body: JSON.stringify({ refresh_token: this.refreshToken }) }, false); } catch { /* local logout still succeeds */ }
    }
    this.clearTokens();
  }

  me() { return DEMO ? wait(demoUser) : this.request("/api/v1/users/me"); }
  users() { return DEMO ? wait([demoUser, { id: "user-ops", username: "operator", is_active: true, created_at: "2026-06-04T11:30:00Z" }]) : this.request("/api/v1/users"); }
  createUser(payload) { return DEMO ? wait({ id: crypto.randomUUID(), username: payload.username, is_active: true, created_at: new Date().toISOString() }) : this.request("/api/v1/users", { method: "POST", body: JSON.stringify(payload) }); }
  disableUser(id) { return DEMO ? wait(null) : this.request(`/api/v1/users/${id}`, { method: "DELETE" }); }
  updateUser(id, payload) { return DEMO ? wait({ id, username: payload.username, is_active: true, created_at: new Date().toISOString() }) : this.request(`/api/v1/users/${id}`, { method: "PATCH", body: JSON.stringify(payload) }); }
  changePassword(id, payload) { return DEMO ? wait(null) : this.request(`/api/v1/users/${id}/password`, { method: "POST", body: JSON.stringify(payload) }); }
  servers() { return DEMO ? wait(demoServers) : this.request("/api/v1/servers"); }
  probe(payload) { return DEMO ? wait({ id: crypto.randomUUID(), ...payload, fingerprint: "SHA256:V3k8PjX2m7A4vT9nQ5rL1cD6sW0yB8uE", host_key_algorithm: "ssh-ed25519", expires_at: new Date(Date.now() + 600000).toISOString() }, 420) : this.request("/api/v1/servers/probes", { method: "POST", body: JSON.stringify(payload) }); }
  createServer(payload) { return DEMO ? wait({ id: crypto.randomUUID(), name: payload.name, address: "10.20.0.42", port: 22, username: "root", credential_type: payload.credential.type, host_key_fingerprint: payload.confirmed_fingerprint, enabled: true, capabilities: { actions: {} }, capabilities_checked_at: new Date().toISOString(), created_at: new Date().toISOString(), updated_at: new Date().toISOString() }, 500) : this.request("/api/v1/servers", { method: "POST", body: JSON.stringify(payload) }); }
  deleteServer(id) { return DEMO ? wait(null) : this.request(`/api/v1/servers/${id}`, { method: "DELETE" }); }
  capabilities(id) { return DEMO ? wait(demoCapabilities) : this.request(`/api/v1/servers/${id}/capabilities`); }
  refreshCapabilities(id) { return DEMO ? wait(demoCapabilities, 500) : this.request(`/api/v1/servers/${id}/capabilities/refresh`, { method: "POST" }); }
  snapshot(id) { return DEMO ? wait(demoSnapshot, 500) : this.request(`/api/v1/servers/${id}/snapshot`); }
  servicesStatus(id) {
    if (DEMO) {
      return wait({
        nginx: "active",
        httpd: "active",
        mysql: "active",
        php_fpm: "inactive",
        memcached: "active",
        redis: "active",
        push_server: "active",
        cron: "active",
        bvat: "active",
      }, 400);
    }
    return this.request(`/api/v1/servers/${id}/services-status`);
  }
  logServices(serverId) {
    if (DEMO) {
      return wait([
        { id: "nginx", name: "Nginx (HTTP/HTTPS)", journal_unit: "nginx", files: ["/var/log/nginx/error.log", "/var/log/nginx/access.log"], active: true },
        { id: "httpd", name: "Apache (httpd / PHP)", journal_unit: "httpd", files: ["/var/log/httpd/error_log", "/var/log/httpd/access_log"], active: true },
        { id: "bitrix-manager", name: "BitrixVM Управление", journal_unit: null, files: ["/opt/webdir/logs/wrapper.log", "/opt/webdir/logs/bvat.log"], active: true },
        { id: "push-server", name: "Bitrix Push Server (RTC)", journal_unit: "push-server", files: ["/var/log/push-server/error.log", "/var/log/push-server/info.log"], active: true },
        { id: "mysql", name: "MySQL / Percona / MariaDB", journal_unit: "mysqld", files: ["/var/log/mysqld.log", "/var/log/mysql/error.log"], active: true },
        { id: "redis", name: "Redis", journal_unit: "redis", files: ["/var/log/redis/redis.log"], active: true },
        { id: "memcached", name: "Memcached", journal_unit: "memcached", files: [], active: true },
        { id: "cron", name: "Cron (Задачи Bitrix)", journal_unit: "crond", files: ["/var/log/cron"], active: true },
        { id: "bvat", name: "Bitrix-Env Auto-tuning (BVAT)", journal_unit: "bvat", files: ["/opt/webdir/logs/bvat.log"], active: true },
        { id: "php-fpm", name: "PHP-FPM", journal_unit: "php-fpm", files: ["/var/log/php-fpm/www-error.log"], active: false },
        { id: "mail", name: "Почта (msmtp / maillog)", journal_unit: null, files: ["/var/log/maillog"], active: null },
        { id: "system", name: "Система (syslog / auth)", journal_unit: "_system", files: ["/var/log/messages", "/var/log/secure", "/var/log/dnf.log"], active: null },
        { id: "custom", name: "Пользовательский файл", journal_unit: null, files: [], active: null },
      ]);
    }
    const url = serverId ? `/api/v1/servers/${serverId}/log-services` : "/api/v1/servers/log-services";
    return this.request(url);
  }
  logs(serverId, params) {
    if (DEMO) {
      return wait({
        lines: [
          "2026-09-08T10:15:01+03:00 nginx[1234]: 192.168.1.1 GET /bitrix/tools.php 200",
          "2026-09-08T10:15:02+03:00 nginx[1234]: 192.168.1.2 POST /api/v1/auth/login 401",
          "2026-09-08T10:15:03+03:00 nginx[1234]: 192.168.1.1 GET /local/templates/.default/header.php 200",
          "2026-09-08T10:15:04+03:00 nginx[1234]: 192.168.1.3 GET /bitrix/cache/site1/main.js 304",
        ],
        total: 4,
        truncated: false,
        source_used: "journal",
      });
    }
    return this.request(`/api/v1/servers/${serverId}/logs`, { method: "POST", body: JSON.stringify(params) });
  }
  operations() { return DEMO ? wait(this.demoOperations) : this.request("/api/v1/operations"); }
  events(id) { return DEMO ? wait(demoEvents.map((event) => ({ ...event, operation_id: id }))) : this.request(`/api/v1/operations/${id}/events`); }
  preview(serverId, action, parameters) { return DEMO ? wait({ action, risk: demoCapabilities.find((item) => item.action === action)?.risk || "high", summary: demoCapabilities.find((item) => item.action === action)?.summary || action, warnings: action.includes("reboot") ? ["SSH-соединение будет прервано."] : [], normalized_parameters: parameters, confirmation_token: crypto.randomUUID(), expires_at: new Date(Date.now() + 300000).toISOString() }, 400) : this.request(`/api/v1/servers/${serverId}/actions/${action}/preview`, { method: "POST", body: JSON.stringify({ parameters }) }); }
  execute(serverId, action, parameters, confirmationToken) {
    if (DEMO) {
      const operation = { id: crypto.randomUUID(), server_id: serverId, user_id: demoUser.id, action, category: action.split(".")[0], risk: demoCapabilities.find((item) => item.action === action)?.risk || "low", status: "queued", args_redacted: parameters, idempotency_key: crypto.randomUUID(), remote_task_id: null, result: null, error_code: null, error_message: null, created_at: new Date().toISOString(), started_at: null, finished_at: null, updated_at: new Date().toISOString() };
      this.demoOperations.unshift(operation);
      return wait(operation, 450);
    }
    return this.request(`/api/v1/servers/${serverId}/actions/${action}`, { method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify({ parameters, confirmation_token: confirmationToken || null }) });
  }
  cancelOperation(id) {
    if (DEMO) {
      const operation = this.demoOperations.find((item) => item.id === id);
      if (operation) operation.status = "canceled";
      return wait(operation);
    }
    return this.request(`/api/v1/operations/${id}/cancel`, { method: "POST" });
  }
}

export const api = new ApiClient();
export { ApiError };
