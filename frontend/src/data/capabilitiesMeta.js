/**
 * Реестр структурированных метаданных для возможностей BitrixVM.
 * Полная локализация на русский язык, группировка по доменам и подгруппам.
 */

export const DOMAINS = {
  sites: {
    id: "sites",
    label: "Сайты и проекты",
    shortLabel: "Сайты",
    description: "Создание, удаление сайтов, настройка HTTPS, Cron, почты, композита и Nginx",
    order: 1,
    subgroups: [
      { id: "create_delete", label: "Создание и удаление", description: "Управление сайтами и ядрами Bitrix" },
      { id: "ssl", label: "HTTPS и сертификаты", description: "Включение и отключение защищённого протокола" },
      { id: "cron", label: "Cron и фоновые процессы", description: "Управление выполнением агентов и cron-заданий" },
      { id: "email_backup", label: "Почта и резервные копии", description: "Настройка SMTP и расписания резервного копирования" },
      { id: "performance", label: "Производительность и Nginx", description: "Композитный сайт, кэширование и тюнинг веб-сервера" },
      { id: "ntlm", label: "Active Directory / NTLM", description: "Корпоративная доменная авторизация" },
    ],
  },
  pool: {
    id: "pool",
    label: "Пул и хосты",
    shortLabel: "Пул",
    description: "Управление кластером Bitrix, добавление хостов, обновление пакетов и пароли",
    order: 2,
    subgroups: [
      { id: "pool_mgmt", label: "Пул серверов", description: "Создание, удаление и общее управление пулом" },
      { id: "host_mgmt", label: "Хосты в пуле", description: "Добавление, удаление, переименование и пароли" },
      { id: "maintenance", label: "Обновление и обслуживание", description: "Обновление пакетов Bitrix/ОС, перезагрузка хостов" },
    ],
  },
  runtime: {
    id: "runtime",
    label: "Платформа и PHP",
    shortLabel: "Платформа",
    description: "Переключение версий PHP, обновление MySQL/PostgreSQL, расширения и сертификаты",
    order: 3,
    subgroups: [
      { id: "php_versions", label: "Версии PHP (8.1 – 8.5)", description: "Обновление и откат интерпретатора PHP" },
      { id: "db_versions", label: "Обновление СУБД", description: "Переход на актуальные версии MySQL и PostgreSQL" },
      { id: "web_cluster", label: "Расширения и веб-кластер", description: "Управление модулями PHP и узлами кластера" },
      { id: "certificates", label: "SSL/TLS сертификаты", description: "Let's Encrypt и собственные сертификаты" },
    ],
  },
  mysql: {
    id: "mysql",
    label: "Базы данных MySQL",
    shortLabel: "MySQL",
    description: "Управление службой, пароль root, my.cnf и настройка репликации",
    order: 4,
    subgroups: [
      { id: "service_config", label: "Служба и конфигурация", description: "Запуск, останов, пароли и my.cnf" },
      { id: "replication", label: "Репликация MySQL", description: "Создание, удаление реплик и переключение мастера" },
    ],
  },
  cache: {
    id: "cache",
    label: "Кэширование",
    shortLabel: "Кэш",
    description: "Управление экземплярами Memcached в пуле",
    order: 5,
    subgroups: [
      { id: "memcached", label: "Memcached", description: "Создание, обновление и удаление экземпляров кэша" },
    ],
  },
  services: {
    id: "services",
    label: "Сервисы и интеграции",
    shortLabel: "Сервисы",
    description: "Push-сервер Node.js, трансформер документов, Sphinx и мониторинг",
    order: 6,
    subgroups: [
      { id: "push", label: "Push-сервер (Bitrix RTC)", description: "Сервер мгновенных сообщений и очередей" },
      { id: "transformer", label: "Трансформер документов", description: "Сервис конвертации и предпросмотра файлов" },
      { id: "sphinx", label: "Поиск Sphinx", description: "Индексы и полнотекстовый поиск Bitrix" },
      { id: "monitoring", label: "Мониторинг пула", description: "Nagios / Munin агент и сбор метрик" },
    ],
  },
  system: {
    id: "system",
    label: "Система и ОС",
    shortLabel: "Система",
    description: "Сетевые параметры, hostname, системные пакеты, перезагрузка и фоновые задачи",
    order: 7,
    subgroups: [
      { id: "network", label: "Сеть и имя хоста", description: "DHCP, статический IP и hostname" },
      { id: "power_update", label: "Питание и обновление ОС", description: "Обновление дистрибутива EL9, reboot, halt" },
      { id: "tasks", label: "Фоновые задачи", description: "Остановка процессов Bitrix и очистка истории" },
    ],
  },
};

export const ACTIONS_META = {
  // --- Сайты (sites) ---
  "site.create_kernel": {
    title: "Создать сайт с ядром Bitrix",
    description: "Создание нового полнофункционального сайта с выделенным ядром 1С-Битрикс",
    domain: "sites",
    subgroup: "create_delete",
  },
  "site.create_external_kernel": {
    title: "Создать сайт с внешним ядром",
    description: "Создание сайта, использующего разделяемое внешнее ядро 1С-Битрикс",
    domain: "sites",
    subgroup: "create_delete",
  },
  "site.create_link": {
    title: "Создать сайт-ссылку (multi-site)",
    description: "Создание зависимого сайта, работающего на ядре существующего проекта",
    domain: "sites",
    subgroup: "create_delete",
  },
  "site.delete": {
    title: "Удалить сайт",
    description: "Полное удаление сайта, виртуального хоста Nginx/Apache и конфигураций",
    domain: "sites",
    subgroup: "create_delete",
  },
  "site.https_enable": {
    title: "Включить HTTPS для сайта",
    description: "Активация SSL/TLS и перенаправление HTTP-запросов на защищённое соединение",
    domain: "sites",
    subgroup: "ssl",
    pairWith: "site.https_disable",
    pairType: "enable",
  },
  "site.https_disable": {
    title: "Отключить HTTPS для сайта",
    description: "Деактивация SSL/TLS конфигурации виртуального хоста",
    domain: "sites",
    subgroup: "ssl",
    pairWith: "site.https_enable",
    pairType: "disable",
  },
  "site.cron_enable": {
    title: "Включить Bitrix Cron",
    description: "Перевод выполнения периодических агентов и очередей сайта на системный Cron",
    domain: "sites",
    subgroup: "cron",
    pairWith: "site.cron_disable",
    pairType: "enable",
  },
  "site.cron_disable": {
    title: "Отключить Bitrix Cron",
    description: "Возврат к выполнению агентов через веб-хиты браузера",
    domain: "sites",
    subgroup: "cron",
    pairWith: "site.cron_enable",
    pairType: "disable",
  },
  "site.cronservice_enable": {
    title: "Включить перезапуск службы Cron",
    description: "Активация регулярного перезапуска службы cron для предотвращения утечек",
    domain: "sites",
    subgroup: "cron",
    pairWith: "site.cronservice_disable",
    pairType: "enable",
  },
  "site.cronservice_disable": {
    title: "Отключить перезапуск службы Cron",
    description: "Деактивация автоматического перезапуска службы cron",
    domain: "sites",
    subgroup: "cron",
    pairWith: "site.cronservice_enable",
    pairType: "disable",
  },
  "site.email": {
    title: "Настроить отправку почты (SMTP)",
    description: "Конфигурация параметров SMTP-сервера и учётной записи для отправки писем",
    domain: "sites",
    subgroup: "email_backup",
  },
  "site.backup_enable": {
    title: "Включить расписание резервного копирования",
    description: "Автоматическое регулярное создание бэкапов сайта и базы данных",
    domain: "sites",
    subgroup: "email_backup",
    pairWith: "site.backup_disable",
    pairType: "enable",
  },
  "site.backup_disable": {
    title: "Отключить резервное копирование",
    description: "Остановка автоматического создания бэкапов сайта по расписанию",
    domain: "sites",
    subgroup: "email_backup",
    pairWith: "site.backup_enable",
    pairType: "disable",
  },
  "site.composite_enable": {
    title: "Включить композитный сайт",
    description: "Активация режима композитного кэширования для ускорения отдачи страниц",
    domain: "sites",
    subgroup: "performance",
    pairWith: "site.composite_disable",
    pairType: "enable",
  },
  "site.composite_disable": {
    title: "Отключить композитный сайт",
    description: "Выключение композитного ускорения страниц в Nginx",
    domain: "sites",
    subgroup: "performance",
    pairWith: "site.composite_enable",
    pairType: "disable",
  },
  "site.nginx_custom_settings_enable": {
    title: "Включить пользовательские настройки Nginx",
    description: "Подключение файла custom_settings.conf для тонких настроек веб-сервера",
    domain: "sites",
    subgroup: "performance",
    pairWith: "site.nginx_custom_settings_disable",
    pairType: "enable",
  },
  "site.nginx_custom_settings_disable": {
    title: "Отключить пользовательские настройки Nginx",
    description: "Возврат к стандартной конфигурации Nginx без кастомных директив",
    domain: "sites",
    subgroup: "performance",
    pairWith: "site.nginx_custom_settings_enable",
    pairType: "disable",
  },
  "site.temporary_files_enable": {
    title: "Включить временные файлы в RAM",
    description: "Размещение временных файлов в tmpfs (оперативной памяти) для максимальной скорости",
    domain: "sites",
    subgroup: "performance",
    pairWith: "site.temporary_files_disable",
    pairType: "enable",
  },
  "site.temporary_files_disable": {
    title: "Отключить временные файлы в RAM",
    description: "Хранение временных файлов на стандартном дисковом накопителе",
    domain: "sites",
    subgroup: "performance",
    pairWith: "site.temporary_files_enable",
    pairType: "disable",
  },
  "site.proxy_ignore_client_abort_enable": {
    title: "Включить proxy_ignore_client_abort",
    description: "Продолжать выполнение PHP-скрипта в бэкенде при досрочном разрыве соединения клиентом",
    domain: "sites",
    subgroup: "performance",
    pairWith: "site.proxy_ignore_client_abort_disable",
    pairType: "enable",
  },
  "site.proxy_ignore_client_abort_disable": {
    title: "Отключить proxy_ignore_client_abort",
    description: "Прерывать выполнение запроса при отключении пользователя",
    domain: "sites",
    subgroup: "performance",
    pairWith: "site.proxy_ignore_client_abort_enable",
    pairType: "disable",
  },
  "site.ntlm_create": {
    title: "Ввод в домен AD и настройка NTLM",
    description: "Интеграция сервера в корпоративный каталог Active Directory и настройка сквозной авторизации",
    domain: "sites",
    subgroup: "ntlm",
  },
  "site.ntlm_update": {
    title: "Обновить параметры NTLM",
    description: "Актуализация параметров подключения и учётных данных Active Directory",
    domain: "sites",
    subgroup: "ntlm",
  },
  "site.ntlm_delete": {
    title: "Удалить NTLM и выйти из AD",
    description: "Отключение доменной авторизации NTLM и вывод сервера из Active Directory",
    domain: "sites",
    subgroup: "ntlm",
  },

  // --- Пул и хосты (pool, hosts) ---
  "pool.create": {
    title: "Создать пул серверов Bitrix",
    description: "Инициализация управляющего пула BitrixVM на текущем сервере",
    domain: "pool",
    subgroup: "pool_mgmt",
    pairWith: "pool.delete",
  },
  "pool.delete": {
    title: "Удалить пул серверов Bitrix",
    description: "Удаление конфигурации пула и возврат к изолированному серверу",
    domain: "pool",
    subgroup: "pool_mgmt",
    pairWith: "pool.create",
  },
  "host.timezone": {
    title: "Установить часовой пояс пула",
    description: "Синхронизация системного часового пояса на всех серверах пула",
    domain: "pool",
    subgroup: "pool_mgmt",
  },
  "host.add": {
    title: "Добавить хост в пул",
    description: "Подключение нового удалённого сервера по SSH и ввод в инфраструктурный пул",
    domain: "pool",
    subgroup: "host_mgmt",
  },
  "host.delete": {
    title: "Удалить хост из пула",
    description: "Корректное удаление хоста и очистка его ролей из пула Bitrix",
    domain: "pool",
    subgroup: "host_mgmt",
  },
  "host.forget": {
    title: "Забыть недоступный хост",
    description: "Принудительное исключение сбойного или недоступного хоста из реестра",
    domain: "pool",
    subgroup: "host_mgmt",
  },
  "host.rename": {
    title: "Переименовать хост в пуле",
    description: "Изменение внутреннего сетевого имени хоста в конфигурациях пула",
    domain: "pool",
    subgroup: "host_mgmt",
  },
  "host.change_bitrix_password": {
    title: "Сменить пароль пользователя bitrix",
    description: "Обновление системного пароля пользователя bitrix на выбранном хосте",
    domain: "pool",
    subgroup: "host_mgmt",
  },
  "host.update_bitrix": {
    title: "Обновить пакеты Bitrix",
    description: "Обновление специализированных пакетов окружения BitrixEnv на хосте",
    domain: "pool",
    subgroup: "maintenance",
  },
  "host.upgrade_all": {
    title: "Обновить все системные пакеты ОС",
    description: "Полное обновление пакетов операционной системы через dnf/yum",
    domain: "pool",
    subgroup: "maintenance",
  },
  "host.reboot": {
    title: "Перезагрузить хост пула",
    description: "Плановая перезагрузка операционной системы выбранного сервера в пуле",
    domain: "pool",
    subgroup: "maintenance",
  },
  "host.repository": {
    title: "Переключить канал репозитория",
    description: "Переключение между стабильным (stable) и тестовым (beta) каналом BitrixEnv",
    domain: "pool",
    subgroup: "maintenance",
  },

  // --- Платформа и PHP (runtime, web) ---
  "runtime.php_upgrade_82": {
    title: "Обновить PHP до 8.2",
    description: "Перевод веб-окружения на версию PHP 8.2 с адаптацией php.ini",
    domain: "runtime",
    subgroup: "php_versions",
    pairWith: "runtime.php_rollback_81",
    pairType: "upgrade",
  },
  "runtime.php_upgrade_83": {
    title: "Обновить PHP до 8.3",
    description: "Перевод веб-окружения на версию PHP 8.3",
    domain: "runtime",
    subgroup: "php_versions",
    pairWith: "runtime.php_rollback_82",
    pairType: "upgrade",
  },
  "runtime.php_upgrade_84": {
    title: "Обновить PHP до 8.4",
    description: "Перевод веб-окружения на версию PHP 8.4",
    domain: "runtime",
    subgroup: "php_versions",
    pairWith: "runtime.php_rollback_83",
    pairType: "upgrade",
  },
  "runtime.php_upgrade_85": {
    title: "Обновить PHP до 8.5",
    description: "Перевод веб-окружения на версию PHP 8.5",
    domain: "runtime",
    subgroup: "php_versions",
    pairWith: "runtime.php_rollback_84",
    pairType: "upgrade",
  },
  "runtime.php_rollback_81": {
    title: "Откатить PHP до 8.1",
    description: "Понижение версии интерпретатора PHP до 8.1",
    domain: "runtime",
    subgroup: "php_versions",
    pairWith: "runtime.php_upgrade_82",
    pairType: "rollback",
  },
  "runtime.php_rollback_82": {
    title: "Откатить PHP до 8.2",
    description: "Понижение версии интерпретатора PHP до 8.2",
    domain: "runtime",
    subgroup: "php_versions",
    pairWith: "runtime.php_upgrade_83",
    pairType: "rollback",
  },
  "runtime.php_rollback_83": {
    title: "Откатить PHP до 8.3",
    description: "Понижение версии интерпретатора PHP до 8.3",
    domain: "runtime",
    subgroup: "php_versions",
    pairWith: "runtime.php_upgrade_84",
    pairType: "rollback",
  },
  "runtime.php_rollback_84": {
    title: "Откатить PHP до 8.4",
    description: "Понижение версии интерпретатора PHP до 8.4",
    domain: "runtime",
    subgroup: "php_versions",
    pairWith: "runtime.php_upgrade_85",
    pairType: "rollback",
  },
  "runtime.mysql_upgrade_84": {
    title: "Обновить MySQL до версии 8.4",
    description: "Миграция СУБД MySQL / Percona Server на релизную ветку 8.4",
    domain: "runtime",
    subgroup: "db_versions",
  },
  "runtime.postgresql_upgrade_15": {
    title: "Обновить PostgreSQL до 15",
    description: "Миграция базы данных PostgreSQL на версию 15",
    domain: "runtime",
    subgroup: "db_versions",
  },
  "runtime.postgresql_upgrade_16": {
    title: "Обновить PostgreSQL до 16",
    description: "Миграция базы данных PostgreSQL на версию 16",
    domain: "runtime",
    subgroup: "db_versions",
  },
  "web.extension_enable": {
    title: "Включить расширение PHP",
    description: "Активация дополнительного модуля (opcache, imagick, xdebug и др.) в PHP",
    domain: "runtime",
    subgroup: "web_cluster",
    pairWith: "web.extension_disable",
    pairType: "enable",
  },
  "web.extension_disable": {
    title: "Отключить расширение PHP",
    description: "Деактивация модуля PHP и перезагрузка веб-окружения",
    domain: "runtime",
    subgroup: "web_cluster",
    pairWith: "web.extension_enable",
    pairType: "disable",
  },
  "web.add_node": {
    title: "Добавить хост в веб-кластер",
    description: "Назначение роли Web-узла для балансировки нагрузки сайтов",
    domain: "runtime",
    subgroup: "web_cluster",
    pairWith: "web.remove_node",
  },
  "web.remove_node": {
    title: "Исключить хост из веб-кластера",
    description: "Снятие роли Web-узла и вывод сервера из балансировки",
    domain: "runtime",
    subgroup: "web_cluster",
    pairWith: "web.add_node",
  },
  "web.certificate_letsencrypt": {
    title: "Выпустить сертификат Let's Encrypt",
    description: "Автоматический выпуск и настройка бесплатного TLS-сертификата Let's Encrypt",
    domain: "runtime",
    subgroup: "certificates",
  },
  "web.certificate_custom": {
    title: "Установить собственный SSL-сертификат",
    description: "Загрузка и установка коммерческого SSL/TLS сертификата и приватного ключа",
    domain: "runtime",
    subgroup: "certificates",
  },
  "web.certificate_reset": {
    title: "Сбросить на общий сертификат",
    description: "Возврат виртуальных хостов на базовый общий сертификат сервера",
    domain: "runtime",
    subgroup: "certificates",
  },

  // --- Базы данных MySQL (mysql) ---
  "mysql.start": {
    title: "Запустить службу MySQL",
    description: "Запуск сервиса базы данных mysqld / mariadb через systemd",
    domain: "mysql",
    subgroup: "service_config",
    pairWith: "mysql.stop",
    pairType: "start",
  },
  "mysql.stop": {
    title: "Остановить службу MySQL",
    description: "Остановка службы базы данных",
    domain: "mysql",
    subgroup: "service_config",
    pairWith: "mysql.start",
    pairType: "stop",
  },
  "mysql.update_config": {
    title: "Обновить конфигурацию my.cnf",
    description: "Применение оптимизированных настроек буферов памяти и соединений MySQL",
    domain: "mysql",
    subgroup: "service_config",
  },
  "mysql.change_password": {
    title: "Сменить пароль root MySQL",
    description: "Безопасное обновление административного пароля суперпользователя СУБД",
    domain: "mysql",
    subgroup: "service_config",
  },
  "mysql.client_config": {
    title: "Записать клиентский конфиг (~/.my.cnf)",
    description: "Сохранение учётных данных доступа в файл ~/.my.cnf для системных утилит",
    domain: "mysql",
    subgroup: "service_config",
  },
  "mysql.create_replica": {
    title: "Создать реплику MySQL",
    description: "Настройка репликации базы данных на дополнительный сервер пула",
    domain: "mysql",
    subgroup: "replication",
  },
  "mysql.promote_master": {
    title: "Назначить сервером Master",
    description: "Переключение реплики в статус основного управляющего узла Master",
    domain: "mysql",
    subgroup: "replication",
  },
  "mysql.remove_replica": {
    title: "Удалить реплику MySQL",
    description: "Остановка репликации и перевод узла в автономный режим",
    domain: "mysql",
    subgroup: "replication",
  },

  // --- Кэширование (memcached) ---
  "memcached.create": {
    title: "Создать экземпляр Memcached",
    description: "Развёртывание и запуск нового сервиса кэширования в оперативной памяти",
    domain: "cache",
    subgroup: "memcached",
    pairWith: "memcached.remove",
  },
  "memcached.update": {
    title: "Обновить конфигурации Memcached",
    description: "Перезапись параметров выделяемой оперативной памяти и сетевых портов",
    domain: "cache",
    subgroup: "memcached",
  },
  "memcached.remove": {
    title: "Удалить экземпляр Memcached",
    description: "Остановка и удаление сервиса Memcached на сервере",
    domain: "cache",
    subgroup: "memcached",
    pairWith: "memcached.create",
  },

  // --- Сервисы и интеграции (services) ---
  "push.configure": {
    title: "Настроить Push-сервер Node.js",
    description: "Конфигурация сервиса реального времени Bitrix Push and Pull на базе Node.js",
    domain: "services",
    subgroup: "push",
    pairWith: "push.remove",
    pairType: "enable",
  },
  "push.remove": {
    title: "Удалить Push-сервер Node.js",
    description: "Отключение и удаление службы Push-сервера",
    domain: "services",
    subgroup: "push",
    pairWith: "push.configure",
    pairType: "disable",
  },
  "transformer.configure": {
    title: "Настроить трансформер документов",
    description: "Подключение службы конвертации и генерации превью офисных документов",
    domain: "services",
    subgroup: "transformer",
    pairWith: "transformer.remove",
    pairType: "enable",
  },
  "transformer.remove": {
    title: "Удалить трансформер документов",
    description: "Отключение службы трансформации документов",
    domain: "services",
    subgroup: "transformer",
    pairWith: "transformer.configure",
    pairType: "disable",
  },
  "sphinx.create_instance": {
    title: "Создать экземпляр Sphinx",
    description: "Развёртывание службы поискового демона Sphinx searchd",
    domain: "services",
    subgroup: "sphinx",
  },
  "sphinx.create_index": {
    title: "Создать / перестроить индекс Sphinx",
    description: "Генерация полнотекстового поискового индекса для сайта",
    domain: "services",
    subgroup: "sphinx",
  },
  "sphinx.delete": {
    title: "Удалить экземпляр / индекс Sphinx",
    description: "Удаление службы поискового демона или выбранного индекса",
    domain: "services",
    subgroup: "sphinx",
  },
  "monitoring.enable": {
    title: "Включить мониторинг пула",
    description: "Активация агента мониторинга Nagios / Munin для сбора системных метрик",
    domain: "services",
    subgroup: "monitoring",
    pairWith: "monitoring.disable",
    pairType: "enable",
  },
  "monitoring.update": {
    title: "Обновить конфигурацию мониторинга",
    description: "Актуализация пороговых значений и параметров отправки оповещений",
    domain: "services",
    subgroup: "monitoring",
  },
  "monitoring.disable": {
    title: "Отключить мониторинг пула",
    description: "Деактивация сбора метрик и службы мониторинга",
    domain: "services",
    subgroup: "monitoring",
    pairWith: "monitoring.enable",
    pairType: "disable",
  },

  // --- Система и ОС (local, tasks) ---
  "local.network_dhcp": {
    title: "Переключить сеть на DHCP",
    description: "Смена конфигурации сетевого интерфейса на автоматическое получение IP-адреса",
    domain: "system",
    subgroup: "network",
  },
  "local.network_static": {
    title: "Настроить статический IPv4",
    description: "Установка фиксированного IP-адреса, маски подсети и основного шлюза",
    domain: "system",
    subgroup: "network",
  },
  "local.hostname": {
    title: "Изменить имя хоста (hostname)",
    description: "Установка нового системного имени сервера (hostnamectl)",
    domain: "system",
    subgroup: "network",
  },
  "local.update": {
    title: "Обновить системные пакеты EL9",
    description: "Обновление дистрибутива операционной системы и пакетов безопасности",
    domain: "system",
    subgroup: "power_update",
  },
  "local.reboot": {
    title: "Перезагрузить сервер",
    description: "Перезапуск операционной системы текущего хоста",
    domain: "system",
    subgroup: "power_update",
  },
  "local.halt": {
    title: "Выключить сервер",
    description: "Корректное завершение работы всех служб и отключение питания",
    domain: "system",
    subgroup: "power_update",
  },
  "tasks.stop": {
    title: "Остановить фоновую задачу",
    description: "Принудительное завершение зависшей или длительной операции Bitrix",
    domain: "system",
    subgroup: "tasks",
  },
  "tasks.clean": {
    title: "Очистить историю задач",
    description: "Удаление устаревших журналов и записей завершённых фоновых процессов",
    domain: "system",
    subgroup: "tasks",
  },
};

/**
 * Получить метаданные действия по его идентификатору.
 */
export function getActionMeta(actionName) {
  if (ACTIONS_META[actionName]) {
    return ACTIONS_META[actionName];
  }

  // Запасной fallback для непредусмотренных действий
  const parts = (actionName || "").split(".");
  const domainKey = parts[0] in DOMAINS ? parts[0] : "system";
  return {
    title: actionName,
    description: "Системное действие BitrixVM",
    domain: domainKey,
    subgroup: "general",
  };
}

/**
 * Структурировать массив возможностей в иерархическое дерево:
 * Домен -> Подгруппы -> Действия.
 */
export function groupCapabilities(capabilitiesList) {
  if (!Array.isArray(capabilitiesList)) return [];

  // Создаем структуру доменов
  const domainMap = {};
  for (const domainKey of Object.keys(DOMAINS)) {
    const domainDef = DOMAINS[domainKey];
    domainMap[domainKey] = {
      ...domainDef,
      totalCount: 0,
      availableCount: 0,
      subgroupsMap: {},
    };

    for (const sg of domainDef.subgroups) {
      domainMap[domainKey].subgroupsMap[sg.id] = {
        ...sg,
        actions: [],
      };
    }
  }

  // Распределяем действия
  for (const cap of capabilitiesList) {
    const meta = getActionMeta(cap.action);
    const domainKey = meta.domain || "system";
    const subgroupKey = meta.subgroup || "general";

    let targetDomain = domainMap[domainKey];
    if (!targetDomain) {
      targetDomain = domainMap.system;
    }

    let targetSubgroup = targetDomain.subgroupsMap[subgroupKey];
    if (!targetSubgroup) {
      // Создаем динамическую подгруппу при необходимости
      targetSubgroup = {
        id: subgroupKey,
        label: "Дополнительные действия",
        description: "",
        actions: [],
      };
      targetDomain.subgroupsMap[subgroupKey] = targetSubgroup;
    }

    const enrichedAction = {
      ...cap,
      meta,
      displayTitle: meta.title || cap.summary || cap.action,
      displayDescription: meta.description || cap.summary || "",
    };

    targetSubgroup.actions.push(enrichedAction);
    targetDomain.totalCount += 1;
    if (cap.available) {
      targetDomain.availableCount += 1;
    }
  }

  // Преобразуем в упорядоченный массив
  return Object.values(domainMap)
    .sort((a, b) => a.order - b.order)
    .map((domain) => ({
      ...domain,
      subgroups: Object.values(domain.subgroupsMap).filter((sg) => sg.actions.length > 0),
    }))
    .filter((domain) => domain.totalCount > 0);
}

/**
 * Фильтровать возможности по домену, строке поиска, доступности и риску.
 */
export function filterCapabilities(capabilitiesList, { search = "", domain = "all", onlyAvailable = false, risk = "all" } = {}) {
  if (!Array.isArray(capabilitiesList)) return [];

  const query = (search || "").trim().toLowerCase();

  return capabilitiesList.filter((cap) => {
    const meta = getActionMeta(cap.action);

    // Фильтр по домену
    if (domain !== "all" && meta.domain !== domain) {
      return false;
    }

    // Фильтр по доступности
    if (onlyAvailable && !cap.available) {
      return false;
    }

    // Фильтр по риску
    if (risk !== "all") {
      if (risk === "danger") {
        if (!["high", "critical"].includes(cap.risk)) return false;
      } else if (cap.risk !== risk) {
        return false;
      }
    }

    // Текстовый поиск
    if (query) {
      const matchAction = cap.action.toLowerCase().includes(query);
      const matchTitle = (meta.title || "").toLowerCase().includes(query);
      const matchDesc = (meta.description || "").toLowerCase().includes(query);
      const matchSummary = (cap.summary || "").toLowerCase().includes(query);
      if (!matchAction && !matchTitle && !matchDesc && !matchSummary) {
        return false;
      }
    }

    return true;
  });
}
