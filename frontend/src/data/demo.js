const now = new Date();
const minutesAgo = (minutes) => new Date(now.getTime() - minutes * 60000).toISOString();

export const demoUser = { id: "user-admin", username: "admin", is_active: true, created_at: "2026-01-12T09:00:00Z" };

export const demoServers = [
  { id: "server-prod", name: "bx-prod-01", address: "10.20.0.11", port: 22, username: "root", credential_type: "private_key", host_key_fingerprint: "SHA256:3b6f9c2d8a7e4d1c9a8f2a9b7c1d3e4f5a", enabled: true, capabilities_checked_at: minutesAgo(2), created_at: "2026-02-10T08:30:00Z", updated_at: minutesAgo(2), capabilities: { actions: {}, services: { nginx: "active", httpd: "active", mysql: "active", php_fpm: "inactive", memcached: "active", redis: "active", push_server: "active", cron: "active", bvat: "active" } } },
  { id: "server-stage", name: "bx-stage-01", address: "10.20.0.24", port: 22, username: "root", credential_type: "password", host_key_fingerprint: "SHA256:1a04d21e887c4a9f7dfb0ac65a104e1c01", enabled: true, capabilities_checked_at: minutesAgo(8), created_at: "2026-03-01T10:00:00Z", updated_at: minutesAgo(8), capabilities: { actions: {}, services: { nginx: "active", httpd: "active", mysql: "active", php_fpm: "active", memcached: "active", redis: "inactive", push_server: "active", cron: "active", bvat: "active" } } },
  { id: "server-backup", name: "bx-backup-01", address: "10.20.0.31", port: 22, username: "root", credential_type: "private_key", host_key_fingerprint: "SHA256:8b7c14da99f3e0871bc04ebd91928f3c21", enabled: true, capabilities_checked_at: minutesAgo(180), created_at: "2026-05-18T12:15:00Z", updated_at: minutesAgo(180), capabilities: { actions: {}, services: { nginx: "inactive", httpd: "inactive", mysql: "active", php_fpm: "inactive", memcached: "inactive", redis: "inactive", push_server: "inactive", cron: "active", bvat: "inactive" } } },
];

import { ACTIONS_META } from "./capabilitiesMeta";

const disabledUpstream = {
  "host.repository": "Переключение канала репозитория отключено в BitrixEnv 9.0.10",
  "mysql.create_replica": "Настройка репликации MySQL временно отключена в upstream BitrixEnv 9.0.10",
  "mysql.promote_master": "Назначение мастера временно отключено в upstream BitrixEnv 9.0.10",
  "mysql.remove_replica": "Удаление реплики временно отключено в upstream BitrixEnv 9.0.10",
  "web.add_node": "Добавление web-ноды отключено в BitrixEnv 9.0.10",
  "web.remove_node": "Удаление web-ноды отключено в BitrixEnv 9.0.10",
  "monitoring.enable": "Модуль мониторинга Nagios/Munin отключен в BitrixEnv 9.0.10",
  "monitoring.update": "Модуль мониторинга Nagios/Munin отключен в BitrixEnv 9.0.10",
  "monitoring.disable": "Модуль мониторинга Nagios/Munin отключен в BitrixEnv 9.0.10",
  "transformer.configure": "Служба трансформатора документов не установлена на хосте",
  "transformer.remove": "Служба трансформатора документов не установлена на хосте",
};

const actionRiskMap = {
  "local.reboot": "critical",
  "local.halt": "critical",
  "site.delete": "critical",
  "pool.delete": "critical",
  "host.delete": "critical",
  "host.forget": "critical",
  "mysql.change_password": "critical",
  "mysql.remove_replica": "critical",
  "memcached.remove": "critical",
  "push.remove": "critical",
  "transformer.remove": "critical",
  "monitoring.disable": "critical",
  "site.ntlm_delete": "critical",
  "sphinx.delete": "critical",
};

const sampleSchemas = {
  "site.create_kernel": {
    type: "object",
    properties: {
      site: { type: "string", description: "Имя сайта (домен или имя папки)", default: "newsite.example.com" },
      root: { type: "string", description: "Корневая директория (DocumentRoot)", default: "/home/bitrix/ext_www/newsite" },
      charset: { type: "string", enum: ["utf-8", "windows-1251"], default: "utf-8", description: "Кодировка сайта" },
      database: { type: "string", description: "Имя базы данных (будет создана)", default: "sitemanager2" },
      dbuser: { type: "string", description: "Пользователь базы данных", default: "bitrix0" },
    },
    required: ["site", "root"],
  },
  "site.delete": {
    type: "object",
    properties: {
      site: { type: "string", description: "Имя удаляемого сайта", default: "b24_crm" },
    },
    required: ["site"],
  },
  "site.https_enable": {
    type: "object",
    properties: {
      site: { type: "string", description: "Имя сайта", default: "default" },
    },
    required: ["site"],
  },
  "site.email": {
    type: "object",
    properties: {
      site: { type: "string", description: "Имя сайта", default: "default" },
      smtp_host: { type: "string", description: "Адрес SMTP-сервера", default: "smtp.yandex.ru" },
      smtp_port: { type: "integer", description: "Порт SMTP", default: 465 },
      smtp_user: { type: "string", description: "Логин / Email" },
      smtp_password: { type: "string", format: "password", writeOnly: true, description: "Пароль SMTP" },
      tls: { type: "boolean", description: "Использовать TLS/SSL", default: true },
    },
    required: ["site", "smtp_host", "smtp_port", "smtp_user"],
  },
  "host.add": {
    type: "object",
    properties: {
      host: { type: "string", description: "IP-адрес или домен добавляемого сервера" },
      password: { type: "string", format: "password", writeOnly: true, description: "Пароль пользователя root" },
    },
    required: ["host", "password"],
  },
  "mysql.change_password": {
    type: "object",
    properties: {
      host: { type: "string", description: "Хост базы данных (обычно localhost)", default: "localhost" },
      password: { type: "string", format: "password", writeOnly: true, description: "Новый пароль root СУБД" },
    },
    required: ["password"],
  },
  "local.network_static": {
    type: "object",
    properties: {
      interface: { type: "string", description: "Сетевой интерфейс", default: "eth0" },
      ip: { type: "string", description: "IPv4 адрес", default: "10.20.0.11" },
      netmask: { type: "string", description: "Маска подсети", default: "255.255.255.0" },
      gateway: { type: "string", description: "Основной шлюз", default: "10.20.0.1" },
      dns: { type: "string", description: "DNS-сервер", default: "77.88.8.8" },
    },
    required: ["interface", "ip", "netmask", "gateway"],
  },
};

export const demoCapabilities = Object.entries(ACTIONS_META).map(([actionName, meta]) => {
  const isBlocked = actionName in disabledUpstream;
  let risk = actionRiskMap[actionName];
  if (!risk) {
    if (actionName.includes("upgrade") || actionName.includes("rollback") || actionName.includes("create") || actionName.includes("add") || actionName.includes("ntlm") || actionName.includes("static")) {
      risk = "high";
    } else if (actionName.includes("enable") || actionName.includes("disable") || actionName.includes("config") || actionName.includes("update") || actionName.includes("email") || actionName.includes("stop")) {
      risk = "medium";
    } else {
      risk = "low";
    }
  }

  return {
    action: actionName,
    available: !isBlocked,
    reason: isBlocked ? disabledUpstream[actionName] : null,
    risk,
    category: meta.domain,
    summary: meta.title,
    request_schema: sampleSchemas[actionName] || {
      type: "object",
      properties: {},
      required: [],
    },
  };
});

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

