const now = new Date();
const minutesAgo = (minutes) => new Date(now.getTime() - minutes * 60000).toISOString();

export const demoUser = { id: "user-admin", username: "admin", is_active: true, created_at: "2026-01-12T09:00:00Z" };

export const demoServers = [
  { id: "server-prod", name: "bx-prod-01", address: "10.20.0.11", port: 22, username: "root", credential_type: "private_key", host_key_fingerprint: "SHA256:3b6f9c2d8a7e4d1c9a8f2a9b7c1d3e4f5a", enabled: true, capabilities_checked_at: minutesAgo(2), created_at: "2026-02-10T08:30:00Z", updated_at: minutesAgo(2), capabilities: { actions: {}, services: { nginx: "active", httpd: "active", mysql: "active", php_fpm: "inactive", memcached: "active", redis: "active", push_server: "active", cron: "active", bvat: "active" } } },
  { id: "server-stage", name: "bx-stage-01", address: "10.20.0.24", port: 22, username: "root", credential_type: "password", host_key_fingerprint: "SHA256:1a04d21e887c4a9f7dfb0ac65a104e1c01", enabled: true, capabilities_checked_at: minutesAgo(8), created_at: "2026-03-01T10:00:00Z", updated_at: minutesAgo(8), capabilities: { actions: {}, services: { nginx: "active", httpd: "active", mysql: "active", php_fpm: "active", memcached: "active", redis: "inactive", push_server: "active", cron: "active", bvat: "active" } } },
  { id: "server-backup", name: "bx-backup-01", address: "10.20.0.31", port: 22, username: "root", credential_type: "private_key", host_key_fingerprint: "SHA256:8b7c14da99f3e0871bc04ebd91928f3c21", enabled: true, capabilities_checked_at: minutesAgo(180), created_at: "2026-05-18T12:15:00Z", updated_at: minutesAgo(180), capabilities: { actions: {}, services: { nginx: "inactive", httpd: "inactive", mysql: "active", php_fpm: "inactive", memcached: "inactive", redis: "inactive", push_server: "inactive", cron: "active", bvat: "inactive" } } },
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

export const demoSnapshot = {
  hostname: "bx-prod-01",
  platform: "AlmaLinux 9.6 (Seafoam Grouper)",
  bitrixenv: "9.0.10",
  pool: {
    exit_status: 0,
    data: {
      status: "finished",
      params: [
        { hostname: "bx-prod-01", ip: "10.20.0.11", roles: ["web", "mysql", "push"], status: "online" },
        { hostname: "bx-stage-01", ip: "10.20.0.24", roles: ["web"], status: "online" }
      ]
    },
    stderr: ""
  },
  sites: {
    exit_status: 0,
    data: {
      status: "finished",
      params: [
        {
          SiteName: "default",
          ServerName: "shop.example.ru",
          DocumentRoot: "/home/bitrix/www",
          DBType: "mysql",
          DBName: "sitemanager",
          DBLogin: "bitrix0",
          HTTPS: "enable",
          Charset: "utf-8",
          CronTask: "enable",
          CompositeStatus: "enable",
          SiteStatus: "finished",
          NginxHTTPConfig: "/etc/nginx/bx/site_avaliable/bx_ext_default.conf",
          ApacheConf: "/etc/httpd/bx/conf/default.conf",
          error: 0,
          message: ""
        },
        {
          SiteName: "b24_crm",
          ServerName: "crm.example.ru",
          DocumentRoot: "/home/bitrix/ext_www/crm",
          DBType: "mysql",
          DBName: "crm_db",
          DBLogin: "bitrix0",
          HTTPS: "enable",
          Charset: "utf-8",
          CronTask: "enable",
          CompositeStatus: "disable",
          SiteStatus: "finished",
          NginxHTTPConfig: "/etc/nginx/bx/site_avaliable/bx_ext_crm.conf",
          ApacheConf: "/etc/httpd/bx/conf/crm.conf",
          error: 0,
          message: ""
        }
      ]
    },
    stderr: ""
  },
  tasks: {
    exit_status: 0,
    data: {
      status: "finished",
      params: [
        { id: "task-2814", pid: 14205, action: "site.create", status: "finished", percent: 100, errors: 0, message: "Site shop.example.ru configured" },
        { id: "task-2821", pid: 14580, action: "web.php.configure", status: "running", percent: 65, errors: 0, message: "Switching PHP version to 8.3" }
      ]
    },
    stderr: ""
  },
  mysql: {
    exit_status: 0,
    data: {
      status: "finished",
      params: {
        version: "8.0.36-28 Percona Server",
        role: "master",
        replication: "active",
        connections: 18,
        max_connections: 151,
        databases: ["sitemanager", "crm_db"]
      }
    },
    stderr: ""
  },
  memcached: {
    exit_status: 0,
    data: {
      status: "finished",
      params: [
        { host: "127.0.0.1", port: 11211, memory_limit: "256M", status: "running" }
      ]
    },
    stderr: ""
  },
  sphinx: {
    exit_status: 0,
    data: {
      status: "finished",
      params: {
        status: "running",
        port: 9306,
        indexes: ["bitrix"]
      }
    },
    stderr: ""
  },
  monitoring: {
    exit_status: 0,
    data: {
      status: "finished",
      params: {
        agent: "active",
        system_load: "0.24, 0.18, 0.15",
        disk_free: "42.8 GB / 60 GB"
      }
    },
    stderr: ""
  },
  network: {
    exit_status: 0,
    data: {
      status: "finished",
      params: [
        { interface: "eth0", ip: "10.20.0.11", mask: "255.255.255.0", gateway: "10.20.0.1" }
      ]
    },
    stderr: ""
  }
};

