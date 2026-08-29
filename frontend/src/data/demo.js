const now = new Date();
const minutesAgo = (minutes) => new Date(now.getTime() - minutes * 60000).toISOString();

export const demoUser = { id: "user-admin", username: "admin", is_active: true, created_at: "2026-01-12T09:00:00Z" };

export const demoServers = [
  { id: "server-prod", name: "bx-prod-01", address: "10.20.0.11", port: 22, username: "root", credential_type: "private_key", host_key_fingerprint: "SHA256:3b6f9c2d8a7e4d1c9a8f2a9b7c1d3e4f5a", enabled: true, capabilities_checked_at: minutesAgo(2), created_at: "2026-02-10T08:30:00Z", updated_at: minutesAgo(2), capabilities: { actions: {} } },
  { id: "server-stage", name: "bx-stage-01", address: "10.20.0.24", port: 22, username: "root", credential_type: "password", host_key_fingerprint: "SHA256:1a04d21e887c4a9f7dfb0ac65a104e1c01", enabled: true, capabilities_checked_at: minutesAgo(8), created_at: "2026-03-01T10:00:00Z", updated_at: minutesAgo(8), capabilities: { actions: {} } },
  { id: "server-backup", name: "bx-backup-01", address: "10.20.0.31", port: 22, username: "root", credential_type: "private_key", host_key_fingerprint: "SHA256:8b7c14da99f3e0871bc04ebd91928f3c21", enabled: true, capabilities_checked_at: minutesAgo(180), created_at: "2026-05-18T12:15:00Z", updated_at: minutesAgo(180), capabilities: { actions: {} } },
];

export const demoCapabilities = [
  { action: "pool.status", available: true, reason: null, risk: "low", category: "pool", summary: "Состояние пула", request_schema: { type: "object", properties: {}, required: [] } },
  { action: "site.create", available: true, reason: null, risk: "medium", category: "sites", summary: "Создать сайт", request_schema: { type: "object", properties: { site: { type: "string", description: "Имя сайта" }, root: { type: "string", description: "Корневая директория" } }, required: ["site", "root"] } },
  { action: "web.php.configure", available: true, reason: null, risk: "high", category: "web", summary: "Настроить PHP", request_schema: { type: "object", properties: { host: { type: "string", description: "Bitrix pool hostname", "x-options-source": "pool_hosts", "x-options": ["bx-prod-01", "bx-stage-01"] }, version: { type: "string", enum: ["8.2", "8.3", "8.4"], description: "Версия PHP" } }, required: ["host", "version"] } },
  { action: "mysql.root_password", available: true, reason: null, risk: "critical", category: "mysql", summary: "Сменить пароль MySQL", request_schema: { type: "object", properties: { host: { type: "string", description: "Сервер MySQL" }, password: { type: "string", format: "password", writeOnly: true, description: "Новый пароль" } }, required: ["host", "password"] } },
  { action: "transformer.configure", available: false, reason: "Модуль не установлен", risk: "high", category: "transformer", summary: "Настроить трансформер документов", request_schema: { type: "object", properties: {}, required: [] } },
  { action: "local.reboot", available: true, reason: null, risk: "critical", category: "local", summary: "Перезагрузить сервер", request_schema: { type: "object", properties: {}, required: [] } },
];

export const demoOperations = [
  { id: "op-1", server_id: "server-prod", user_id: "user-admin", action: "site.create", category: "sites", risk: "high", status: "succeeded", args_redacted: { site: "shop.example.ru" }, idempotency_key: "demo-site-create", remote_task_id: "task-2814", result: { status: "ok" }, error_code: null, error_message: null, created_at: minutesAgo(17), started_at: minutesAgo(16), finished_at: minutesAgo(13), updated_at: minutesAgo(13) },
  { id: "op-2", server_id: "server-prod", user_id: "user-admin", action: "web.php.configure", category: "web", risk: "high", status: "running", args_redacted: { version: "8.3" }, idempotency_key: "demo-php-config", remote_task_id: "task-2821", result: null, error_code: null, error_message: null, created_at: minutesAgo(20), started_at: minutesAgo(19), finished_at: null, updated_at: minutesAgo(1) },
  { id: "op-3", server_id: "server-stage", user_id: "user-admin", action: "pool.status", category: "pool", risk: "low", status: "queued", args_redacted: {}, idempotency_key: "demo-pool-status", remote_task_id: null, result: null, error_code: null, error_message: null, created_at: minutesAgo(3), started_at: null, finished_at: null, updated_at: minutesAgo(3) },
];

export const demoEvents = [
  { id: "ev-1", operation_id: "op-1", level: "info", event: "queued", message: "Операция добавлена в очередь", data: {}, created_at: minutesAgo(17) },
  { id: "ev-2", operation_id: "op-1", level: "info", event: "started", message: "Выполнение начато", data: {}, created_at: minutesAgo(16) },
  { id: "ev-3", operation_id: "op-1", level: "info", event: "succeeded", message: "Операция успешно завершена", data: {}, created_at: minutesAgo(13) },
];
