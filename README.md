# BitrixVM Controller

Внешний HTTPS API для управления BitrixEnv 9.x на EL9. Контроллер работает без агента:
подключается к master-хосту по SSH, использует штатные `wrapper_ansible_conf` и `bx-*`,
нормализует их ответы и ведёт собственный аудит операций.

Проект содержит backend, Swagger и адаптивную веб-консоль. Реестр включает 83 типизированных действия из
активных и скрытых модулей `menu.sh`: pool/hosts/local, MySQL, memcached, tasks, sites,
Sphinx, web/PHP/certificates, monitoring, push и transformer.

## Быстрый запуск

Требуются Docker и Docker Compose.

```bash
cp .env.example .env
mkdir -p secrets
python3 -c 'import secrets; print(secrets.token_urlsafe(48))' > secrets/postgres_password
python3 -c 'import secrets; print(secrets.token_urlsafe(48))' > secrets/master_key
python3 -c 'import secrets; print(secrets.token_urlsafe(48))' > secrets/jwt_secret
chmod 600 secrets/*
docker compose up -d --build
docker compose exec api bitrixvm-admin create admin
```

Веб-консоль доступна по `https://localhost`, Swagger — по `https://localhost/docs`. Caddy использует internal CA; для браузера
нужно доверить корневой сертификат из volume Caddy либо заменить TLS-конфигурацию своим
сертификатом. PostgreSQL и FastAPI наружу не публикуются.

### Разработка фронтенда

```bash
cd frontend
npm install
npm run dev
```

Vite запускается на `http://127.0.0.1:5173` и проксирует API на локальный FastAPI порт
`8000`. Для изолированной проверки интерфейса без подключения к серверам откройте
`http://127.0.0.1:5173/?demo=1`; demo-режим не отправляет запросы к API.

## Рабочий процесс API

1. Войти через `POST /api/v1/auth/login`.
2. Получить SSH fingerprint через `POST /api/v1/servers/probes`.
3. Сверить fingerprint вне контроллера и добавить сервер через `POST /api/v1/servers`.
4. Получить `/capabilities` и `/snapshot`.
5. Для high/critical action вызвать `/actions/{action}/preview`.
6. Передать полученный token и уникальный `Idempotency-Key` в `/actions/{action}`.
7. Следить за `Operation` polling-запросами или через SSE `/events/stream`.

Произвольные shell-команды не поддерживаются. SSH credentials и payload операций
зашифрованы AES-GCM; пароли, ключи и secret-поля не возвращаются и очищаются из логов.

## Разработка

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/ruff check .
.venv/bin/mypy app
.venv/bin/pytest
```

Поддерживаемая серверная платформа v1 — BitrixEnv 9.x на AlmaLinux/Rocky/CentOS
Stream 9. Недоступные для конкретной конфигурации действия остаются в контракте и
получают `available=false` с причиной в capabilities.
