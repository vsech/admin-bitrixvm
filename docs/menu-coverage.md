# Покрытие BitrixVM menu.sh

Источник инвентаризации: `bitrix-env-9.0-10.el9.x86_64`, AlmaLinux 9.8. Реестр API
содержит 83 action-контракта. Полный машинный перечень с JSON Schema возвращает
`GET /api/v1/servers/{id}/capabilities`.

| Модули menu.sh | API category | Реализованные сценарии |
|---|---|---|
| `pool_menu.sh`, `01_host*`, `01_hosts/*` | `pool`, `hosts`, `runtime` | create/delete pool, add/delete/forget host, reboot, update/upgrade, password, timezone, rename, repository, PHP/MySQL/PostgreSQL upgrade/rollback |
| `02_local*` | `local` | hostname, DHCP/static IPv4, reboot, halt, OS update |
| `03_mysql*` | `mysql` | config, password/client config, service start/stop, replica create/promote/remove |
| `04_memcached*` | `memcached` | create, update, remove |
| `05_task*` | `tasks` | stop task, clean history; status/list входят в snapshot API |
| `06_site*`, `06_site_crm*` | `sites` | kernel/link/external kernel create, delete, cron, SMTP, HTTPS, backup, NTLM, cron services, composite, proxy/nginx/temp options |
| `07_sphinx*` | `sphinx` | instance/index create, reindex, delete |
| `08_web*`, `08_web_crm*` | `web` | web nodes, PHP extensions, Let's Encrypt/custom/reset certificates |
| `09_monitor*` | `monitoring` | enable, update, disable, status |
| `10_push*`, `10_push_crm*` | `push` | configure/remove Node.js push server |
| `11_transformer*` | `transformer` | configure/remove transformer |

## Отключённые upstream-сценарии

Контракт сохраняет намеренно закомментированные функции, но capability на 9.0.10
возвращает `available=false`, чтобы контроллер не выдавал неработающий CLI за рабочий:

- переключение stable/beta repository;
- MySQL replica/master/remove;
- создание и удаление web-node;
- enable/update/disable monitoring.

Остальные скрытые пункты вызывают активные dispatch-ветки `wrapper_ansible_conf` или
`bx-*` и могут быть доступны, даже если в интерактивном меню они не отображаются.

## Правила выполнения

- Action существует в OpenAPI независимо от текущего состояния хоста.
- Capability учитывает версию BitrixEnv, наличие executable и известное состояние
  upstream dispatch.
- `high` и `critical` требуют preview token; все изменения требуют
  `Idempotency-Key` и выполняются worker-ом.
- Команды формируются только реестром; неизвестные поля и shell-метасимволы в
  идентификаторах отклоняются до SSH.

