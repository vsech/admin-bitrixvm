from __future__ import annotations

import ipaddress
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

Risk = Literal["low", "medium", "high", "critical"]
BIN = "/opt/webdir/bin"


class ActionValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ParamSpec:
    kind: Literal["string", "integer", "boolean", "enum", "secret"] = "string"
    required: bool = True
    default: Any = None
    enum: tuple[str, ...] = ()
    pattern: str | None = None
    minimum: int | None = None
    maximum: int | None = None
    description: str = ""

    def validate(self, name: str, value: Any) -> Any:
        if self.kind in {"string", "secret", "enum"}:
            if not isinstance(value, str):
                raise ActionValidationError(f"{name} must be a string")
            if not value and self.required:
                raise ActionValidationError(f"{name} must not be empty")
            if len(value) > 4096:
                raise ActionValidationError(f"{name} is too long")
            if self.kind == "enum" and value not in self.enum:
                raise ActionValidationError(f"{name} must be one of: {', '.join(self.enum)}")
            if self.pattern and not re.fullmatch(self.pattern, value):
                raise ActionValidationError(f"{name} has invalid format")
            return value
        if self.kind == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise ActionValidationError(f"{name} must be an integer")
            if self.minimum is not None and value < self.minimum:
                raise ActionValidationError(f"{name} must be >= {self.minimum}")
            if self.maximum is not None and value > self.maximum:
                raise ActionValidationError(f"{name} must be <= {self.maximum}")
            return value
        if self.kind == "boolean":
            if not isinstance(value, bool):
                raise ActionValidationError(f"{name} must be a boolean")
            return value
        raise ActionValidationError(f"unknown parameter type for {name}")

    def json_schema(self) -> dict[str, Any]:
        result: dict[str, Any] = {"description": self.description}
        if self.kind in {"string", "secret", "enum"}:
            result["type"] = "string"
        elif self.kind == "integer":
            result["type"] = "integer"
        else:
            result["type"] = "boolean"
        if self.kind == "secret":
            result["writeOnly"] = True
            result["format"] = "password"
        if self.enum:
            result["enum"] = list(self.enum)
        if self.pattern:
            result["pattern"] = self.pattern
        if self.minimum is not None:
            result["minimum"] = self.minimum
        if self.maximum is not None:
            result["maximum"] = self.maximum
        if not self.required:
            result["default"] = self.default
        return result


@dataclass(frozen=True)
class RemoteCommand:
    argv: tuple[str, ...]
    expect_disconnect: bool = False
    task_result: bool = True
    secret_files: dict[str, str] = field(default_factory=dict)


CommandBuilder = Callable[[dict[str, Any], dict[str, str]], tuple[RemoteCommand, ...]]


@dataclass(frozen=True)
class ActionSpec:
    name: str
    category: str
    risk: Risk
    summary: str
    builder: CommandBuilder
    params: dict[str, ParamSpec] = field(default_factory=dict)
    required_commands: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    menu_sources: tuple[str, ...] = ()
    disabled_reason: str | None = None

    @property
    def confirmation_required(self) -> bool:
        return self.risk in {"high", "critical"}

    def normalize(self, supplied: dict[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(supplied) - set(self.params))
        if unknown:
            raise ActionValidationError(f"unknown parameters: {', '.join(unknown)}")
        result: dict[str, Any] = {}
        for name, spec in self.params.items():
            if name not in supplied:
                if spec.required:
                    raise ActionValidationError(f"missing parameter: {name}")
                result[name] = spec.default
            else:
                result[name] = spec.validate(name, supplied[name])
        return result

    def request_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {name: spec.json_schema() for name, spec in self.params.items()},
            "required": [name for name, spec in self.params.items() if spec.required],
        }

    def redact(self, normalized: dict[str, Any]) -> dict[str, Any]:
        return {
            key: "********" if self.params[key].kind == "secret" else value
            for key, value in normalized.items()
        }


HOST = ParamSpec(pattern=r"[A-Za-z0-9_.-]{1,253}", description="Bitrix pool hostname")
SITE = ParamSpec(pattern=r"[A-Za-z0-9_.-]{1,253}", description="Bitrix site name")
PATH = ParamSpec(pattern=r"/[A-Za-z0-9_./-]{1,1023}", description="Absolute remote path")
INTERFACE = ParamSpec(pattern=r"[A-Za-z0-9_.:/-]{1,64}")
BOOL = ParamSpec(kind="boolean")
SECRET = ParamSpec(kind="secret")


def cli(path: str, *parts: str, task: bool = True, disconnect: bool = False) -> CommandBuilder:
    def build(_: dict[str, Any], __: dict[str, str]) -> tuple[RemoteCommand, ...]:
        return (RemoteCommand((path, *parts), expect_disconnect=disconnect, task_result=task),)

    return build


def dynamic(path: str, action: str, mapping: tuple[tuple[str, str], ...] = ()) -> CommandBuilder:
    def build(values: dict[str, Any], secret_files: dict[str, str]) -> tuple[RemoteCommand, ...]:
        argv = [path, "-a", action]
        for param, flag in mapping:
            value = (
                secret_files.get(param, values.get(param))
                if flag in {"--password_file", "--password-file"}
                else values.get(param)
            )
            if value is None or value is False or value == "":
                continue
            if isinstance(value, bool):
                argv.append(flag)
            else:
                argv.extend((flag, str(value)))
        return (RemoteCommand(tuple(argv), secret_files=secret_files),)

    return build


def system_command(*parts: str, disconnect: bool = False) -> CommandBuilder:
    def build(values: dict[str, Any], _: dict[str, str]) -> tuple[RemoteCommand, ...]:
        return (
            RemoteCommand(
                tuple(part.format_map(values) for part in parts),
                expect_disconnect=disconnect,
                task_result=False,
            ),
        )

    return build


def mysql_password(action: str) -> CommandBuilder:
    return dynamic(
        f"{BIN}/bx-mysql", action, (("host", "--server"), ("password", "--password_file"))
    )


def site_email(values: dict[str, Any], secret_files: dict[str, str]) -> tuple[RemoteCommand, ...]:
    # bx-sites has no password-file option. A fixed root-only wrapper reads the temporary file.
    argv = [
        f"{BIN}/bx-sites",
        "-a",
        "email",
        "-s",
        values["site"],
        "--smtphost",
        values["smtp_host"],
        "--smtpport",
        str(values["smtp_port"]),
        "--email",
        values["sender"],
    ]
    if values.get("smtp_user"):
        argv.extend(("--smtpuser", values["smtp_user"]))
    if values.get("tls"):
        argv.append("--smtptls")
    if values.get("smtp_password"):
        argv.extend(("--password", values["smtp_password"]))
    return (RemoteCommand(tuple(argv), secret_files=secret_files),)


def local_static(values: dict[str, Any], _: dict[str, str]) -> tuple[RemoteCommand, ...]:
    ipaddress.ip_interface(f"{values['address']}/{values['prefix']}")
    ipaddress.ip_address(values["gateway"])
    connection = values["connection"]
    commands = [
        RemoteCommand(
            (
                "/usr/bin/nmcli",
                "connection",
                "modify",
                connection,
                "ipv4.method",
                "manual",
                "ipv4.addresses",
                f"{values['address']}/{values['prefix']}",
                "ipv4.gateway",
                values["gateway"],
                "ipv4.dns",
                values["dns"],
            ),
            task_result=False,
        ),
        RemoteCommand(("/usr/bin/nmcli", "connection", "up", connection), True, False),
    ]
    return tuple(commands)


def _spec(
    name: str,
    category: str,
    risk: Risk,
    summary: str,
    builder: CommandBuilder,
    params: dict[str, ParamSpec] | None = None,
    commands: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
    sources: tuple[str, ...] = (),
    disabled_reason: str | None = None,
) -> ActionSpec:
    return ActionSpec(
        name,
        category,
        risk,
        summary,
        builder,
        params or {},
        commands,
        warnings,
        sources,
        disabled_reason,
    )


def repository_channel(values: dict[str, Any], _: dict[str, str]) -> tuple[RemoteCommand, ...]:
    action = "enable_beta_version" if values["channel"] == "beta" else "disable_beta_version"
    return (RemoteCommand((W, "-a", action)),)


def web_create(values: dict[str, Any], _: dict[str, str]) -> tuple[RemoteCommand, ...]:
    action = {"complete": "create_web", "prepare": "web1", "finish": "web2"}[values["mode"]]
    return (
        RemoteCommand(
            (SITES, "-a", action, "--hostname", values["host"], "--fstype", values["fstype"])
        ),
    )


W = f"{BIN}/wrapper_ansible_conf"
SITES = f"{BIN}/bx-sites"
MYSQL = f"{BIN}/bx-mysql"
MC = f"{BIN}/bx-mc"
SPHINX = f"{BIN}/bx-sphinx"
MONITOR = f"{BIN}/bx-monitor"
PROCESS = f"{BIN}/bx-process"


ACTION_SPECS = [
    _spec(
        "pool.create",
        "pool",
        "high",
        "Create the native Bitrix server pool",
        dynamic(W, "create", (("host", "--host"), ("interface", "--interface"))),
        {"host": HOST, "interface": INTERFACE},
        (W,),
    ),
    _spec(
        "pool.delete",
        "pool",
        "critical",
        "Remove the native Bitrix server pool",
        cli(W, "-a", "delete_pool"),
        commands=(W,),
        warnings=("Pool metadata and configuration will be removed.",),
    ),
    _spec(
        "host.add",
        "hosts",
        "high",
        "Add a host to the Bitrix pool",
        dynamic(W, "add", (("host", "--host"), ("ip", "--ip"))),
        {"host": HOST, "ip": ParamSpec(pattern=r"[0-9a-fA-F:.]{2,45}")},
        (W,),
    ),
    _spec(
        "host.delete",
        "hosts",
        "critical",
        "Remove a host and its Bitrix pool configuration",
        dynamic(W, "del", (("host", "--host"),)),
        {"host": HOST},
        (W,),
    ),
    _spec(
        "host.forget",
        "hosts",
        "critical",
        "Forget an unreachable host",
        dynamic(W, "forget_host", (("host", "--host"),)),
        {"host": HOST},
        (W,),
    ),
    _spec(
        "host.reboot",
        "hosts",
        "critical",
        "Reboot a pool host",
        dynamic(W, "bx_reboot", (("host", "--host"),)),
        {"host": HOST},
        (W,),
        ("SSH connectivity will be interrupted.",),
    ),
    _spec(
        "host.update_bitrix",
        "hosts",
        "high",
        "Update Bitrix packages on a pool host",
        dynamic(W, "bx_update", (("host", "--host"),)),
        {"host": HOST},
        (W,),
    ),
    _spec(
        "host.upgrade_all",
        "hosts",
        "critical",
        "Upgrade all operating system packages",
        dynamic(W, "bx_upgrade", (("host", "--host"),)),
        {"host": HOST},
        (W,),
    ),
    _spec(
        "host.change_bitrix_password",
        "hosts",
        "high",
        "Change the bitrix user password",
        dynamic(W, "bx_passwd", (("host", "--host"),)),
        {"host": HOST},
        (W,),
    ),
    _spec(
        "host.timezone",
        "hosts",
        "high",
        "Set timezone for the whole pool",
        dynamic(W, "timezone", (("timezone", "--timezone"),)),
        {"timezone": ParamSpec(pattern=r"[A-Za-z_+-]+(?:/[A-Za-z0-9_+.-]+)+")},
        (W,),
    ),
    _spec(
        "host.rename",
        "hosts",
        "critical",
        "Rename a pool host",
        dynamic(W, "change_hostname", (("host", "--host"), ("hostname", "--hostname"))),
        {"host": HOST, "hostname": HOST},
        (W,),
        ("The host identity and SSH connectivity can change.",),
    ),
    _spec(
        "host.repository",
        "hosts",
        "high",
        "Switch Bitrix package repository channel",
        repository_channel,
        {"channel": ParamSpec(kind="enum", enum=("stable", "beta"))},
        (W,),
        disabled_reason="Repository switching is disabled in BitrixEnv 9.0.10",
    ),
    *[
        _spec(
            f"runtime.php_{direction}",
            "runtime",
            "critical",
            f"{direction.title()} PHP runtime",
            dynamic(W, action, (("host", "--host"),)),
            {"host": HOST},
            (W,),
        )
        for direction, action in (
            ("upgrade_82", "bx_php_upgrade_php82"),
            ("upgrade_83", "bx_php_upgrade_php83"),
            ("upgrade_84", "bx_php_upgrade_php84"),
            ("upgrade_85", "bx_php_upgrade_php85"),
            ("rollback_81", "bx_php_rollback_php81"),
            ("rollback_82", "bx_php_rollback_php82"),
            ("rollback_83", "bx_php_rollback_php83"),
            ("rollback_84", "bx_php_rollback_php84"),
        )
    ],
    _spec(
        "runtime.mysql_upgrade_84",
        "runtime",
        "critical",
        "Upgrade MySQL to 8.4",
        dynamic(W, "bx_upgrade_mysql84", (("host", "--host"),)),
        {"host": HOST},
        (W,),
    ),
    _spec(
        "runtime.postgresql_upgrade_15",
        "runtime",
        "critical",
        "Upgrade PostgreSQL to 15",
        dynamic(W, "bx_upgrade_pgsql_15", (("host", "--host"),)),
        {"host": HOST},
        (W,),
    ),
    _spec(
        "runtime.postgresql_upgrade_16",
        "runtime",
        "critical",
        "Upgrade PostgreSQL to 16",
        dynamic(W, "bx_upgrade_pgsql_16", (("host", "--host"),)),
        {"host": HOST},
        (W,),
    ),
    _spec(
        "local.hostname",
        "local",
        "critical",
        "Change the local hostname",
        system_command("/usr/bin/hostnamectl", "set-hostname", "{hostname}"),
        {"hostname": HOST},
        ("/usr/bin/hostnamectl",),
    ),
    _spec(
        "local.network_dhcp",
        "local",
        "critical",
        "Switch a NetworkManager connection to DHCP",
        system_command(
            "/usr/bin/nmcli", "connection", "modify", "{connection}", "ipv4.method", "auto"
        ),
        {"connection": INTERFACE},
        ("/usr/bin/nmcli",),
        ("The controller can lose SSH connectivity.",),
    ),
    _spec(
        "local.network_static",
        "local",
        "critical",
        "Configure a static IPv4 address",
        local_static,
        {
            "connection": INTERFACE,
            "address": ParamSpec(pattern=r"[0-9.]{7,15}"),
            "prefix": ParamSpec(kind="integer", minimum=1, maximum=32),
            "gateway": ParamSpec(pattern=r"[0-9.]{7,15}"),
            "dns": ParamSpec(pattern=r"[0-9., ]{7,128}"),
        },
        ("/usr/bin/nmcli",),
        ("The controller can lose SSH connectivity.",),
    ),
    _spec(
        "local.reboot",
        "local",
        "critical",
        "Reboot the BitrixVM server",
        system_command("/usr/sbin/shutdown", "-r", "now", disconnect=True),
        commands=("/usr/sbin/shutdown",),
        warnings=("SSH connectivity will be interrupted.",),
    ),
    _spec(
        "local.halt",
        "local",
        "critical",
        "Power off the BitrixVM server",
        system_command("/usr/sbin/shutdown", "-h", "now", disconnect=True),
        commands=("/usr/sbin/shutdown",),
        warnings=("The server requires out-of-band power-on.",),
    ),
    _spec(
        "local.update",
        "local",
        "critical",
        "Update all EL9 packages",
        cli("/usr/bin/dnf", "-y", "update", task=False),
        commands=("/usr/bin/dnf",),
    ),
    _spec(
        "mysql.update_config",
        "mysql",
        "medium",
        "Update MySQL configuration",
        cli(MYSQL, "-a", "update"),
        commands=(MYSQL,),
    ),
    _spec(
        "mysql.change_password",
        "mysql",
        "high",
        "Change MySQL root password",
        mysql_password("change_password"),
        {"host": HOST, "password": SECRET},
        (MYSQL,),
    ),
    _spec(
        "mysql.client_config",
        "mysql",
        "high",
        "Write MySQL client configuration",
        mysql_password("client_config"),
        {"host": HOST, "password": SECRET},
        (MYSQL,),
    ),
    _spec(
        "mysql.start",
        "mysql",
        "high",
        "Start MySQL service",
        dynamic(MYSQL, "start_service", (("host", "--server"),)),
        {"host": HOST},
        (MYSQL,),
    ),
    _spec(
        "mysql.stop",
        "mysql",
        "critical",
        "Stop MySQL service",
        dynamic(MYSQL, "stop_service", (("host", "--server"),)),
        {"host": HOST},
        (MYSQL,),
    ),
    _spec(
        "mysql.create_replica",
        "mysql",
        "critical",
        "Create a MySQL replica",
        dynamic(
            MYSQL,
            "slave",
            (
                ("host", "--server"),
                ("cluster_login", "--cluster_login"),
                ("cluster_password", "--cluster_password"),
                ("replica_login", "--replica_login"),
                ("replica_password", "--replica_password"),
            ),
        ),
        {
            "host": HOST,
            "cluster_login": HOST,
            "cluster_password": SECRET,
            "replica_login": HOST,
            "replica_password": SECRET,
        },
        (MYSQL,),
        disabled_reason="MySQL replication actions are disabled in BitrixEnv 9.0.10",
    ),
    _spec(
        "mysql.promote_master",
        "mysql",
        "critical",
        "Promote a MySQL server to master",
        dynamic(MYSQL, "master", (("host", "--server"),)),
        {"host": HOST},
        (MYSQL,),
        disabled_reason="MySQL replication actions are disabled in BitrixEnv 9.0.10",
    ),
    _spec(
        "mysql.remove_replica",
        "mysql",
        "critical",
        "Remove a MySQL replica",
        dynamic(MYSQL, "remove", (("host", "--server"),)),
        {"host": HOST},
        (MYSQL,),
        disabled_reason="MySQL replication actions are disabled in BitrixEnv 9.0.10",
    ),
    _spec(
        "memcached.create",
        "memcached",
        "high",
        "Create memcached instance",
        dynamic(MC, "create", (("host", "--server"),)),
        {"host": HOST},
        (MC,),
    ),
    _spec(
        "memcached.update",
        "memcached",
        "medium",
        "Update all memcached configurations",
        cli(MC, "-a", "update"),
        commands=(MC,),
    ),
    _spec(
        "memcached.remove",
        "memcached",
        "critical",
        "Remove memcached instance",
        dynamic(MC, "remove", (("host", "--server"),)),
        {"host": HOST},
        (MC,),
    ),
    _spec(
        "tasks.stop",
        "tasks",
        "high",
        "Stop a Bitrix background task",
        dynamic(PROCESS, "stop", (("task_id", "--task"),)),
        {"task_id": ParamSpec(pattern=r"[A-Za-z0-9_-]{3,128}")},
        (PROCESS,),
    ),
    _spec(
        "tasks.clean",
        "tasks",
        "high",
        "Delete old task history",
        dynamic(PROCESS, "clean", (("days", "--days"), ("task_type", "--type"))),
        {
            "days": ParamSpec(kind="integer", minimum=0, maximum=3650),
            "task_type": ParamSpec(required=False, default="", pattern=r"[A-Za-z0-9_|()-]{0,128}"),
        },
        (PROCESS,),
    ),
    _spec(
        "site.create_kernel",
        "sites",
        "high",
        "Create a Bitrix kernel site",
        dynamic(
            SITES,
            "create",
            (
                ("site", "--site"),
                ("root", "--root"),
                ("db_type", "--dbtype"),
                ("db_name", "--dbname"),
                ("db_user", "--user"),
                ("db_password", "--password"),
            ),
        ),
        {
            "site": SITE,
            "root": PATH,
            "db_type": ParamSpec(kind="enum", enum=("mysql", "pgsql")),
            "db_name": HOST,
            "db_user": HOST,
            "db_password": SECRET,
        },
        (SITES,),
    ),
    _spec(
        "site.create_external_kernel",
        "sites",
        "high",
        "Create an external kernel",
        dynamic(SITES, "create", (("site", "--site"), ("kernel_root", "--kernel_root"))),
        {"site": SITE, "kernel_root": PATH},
        (SITES,),
    ),
    _spec(
        "site.create_link",
        "sites",
        "high",
        "Create a link site",
        dynamic(
            SITES,
            "create",
            (
                ("site", "--site"),
                ("kernel_root", "--kernel_root"),
                ("kernel_site", "--kernel_site"),
            ),
        ),
        {
            "site": SITE,
            "kernel_root": PATH,
            "kernel_site": ParamSpec(required=False, default="", pattern=r"[A-Za-z0-9_.-]{0,253}"),
        },
        (SITES,),
    ),
    _spec(
        "site.delete",
        "sites",
        "critical",
        "Delete a Bitrix site",
        dynamic(SITES, "delete", (("site", "--site"), ("root", "--root"))),
        {"site": SITE, "root": PATH},
        (SITES,),
    ),
    *[
        _spec(
            f"site.{feature}_{state}",
            "sites",
            "high",
            f"{state.title()} site {feature}",
            dynamic(SITES, feature, (("site", "--site"), (state, f"--{state}"))),
            {"site": SITE, state: ParamSpec(kind="boolean", required=False, default=True)},
            (SITES,),
        )
        for feature in ("cron", "https", "composite")
        for state in ("enable", "disable")
    ],
    _spec(
        "site.email",
        "sites",
        "high",
        "Configure site SMTP",
        site_email,
        {
            "site": SITE,
            "smtp_host": HOST,
            "smtp_port": ParamSpec(kind="integer", minimum=1, maximum=65535),
            "sender": ParamSpec(pattern=r"[^@\s]+@[^@\s]+", description="Sender email"),
            "smtp_user": ParamSpec(required=False, default="", pattern=r"[^\s]{0,255}"),
            "smtp_password": ParamSpec(kind="secret", required=False, default=""),
            "tls": ParamSpec(kind="boolean", required=False, default=True),
        },
        (SITES,),
    ),
    _spec(
        "site.backup_enable",
        "sites",
        "high",
        "Enable kernel backup schedule",
        dynamic(
            SITES,
            "backup",
            (
                ("database", "--dbname"),
                ("enable", "--enable"),
                ("minute", "--minute"),
                ("hour", "--hour"),
                ("day", "--day"),
                ("month", "--month"),
                ("weekday", "--weekday"),
            ),
        ),
        {
            "database": HOST,
            "enable": ParamSpec(kind="boolean", required=False, default=True),
            "minute": ParamSpec(kind="integer", minimum=0, maximum=59),
            "hour": ParamSpec(kind="integer", minimum=0, maximum=23),
            "day": ParamSpec(kind="string", pattern=r"\*|[1-9]|[12][0-9]|3[01]"),
            "month": ParamSpec(kind="string", pattern=r"\*|[1-9]|1[0-2]"),
            "weekday": ParamSpec(kind="string", pattern=r"\*|[1-7]"),
        },
        (SITES,),
    ),
    _spec(
        "site.backup_disable",
        "sites",
        "high",
        "Disable kernel backups",
        dynamic(SITES, "backup", (("database", "--dbname"), ("disable", "--disable"))),
        {"database": HOST, "disable": ParamSpec(kind="boolean", required=False, default=True)},
        (SITES,),
    ),
    _spec(
        "site.ntlm_create",
        "sites",
        "critical",
        "Join the host to AD and configure NTLM",
        dynamic(
            SITES,
            "ntlm_create",
            (
                ("domain", "--ntlm_domain"),
                ("fqdn", "--ntlm_fqdn"),
                ("domain_controller", "--ntlm_ads"),
                ("login", "--ntlm_login"),
                ("password", "--password_file"),
                ("host", "--ntlm_host"),
            ),
        ),
        {
            "domain": HOST,
            "fqdn": HOST,
            "domain_controller": HOST,
            "login": HOST,
            "password": SECRET,
            "host": HOST,
        },
        (SITES,),
    ),
    _spec(
        "site.ntlm_update",
        "sites",
        "high",
        "Update NTLM configuration",
        cli(SITES, "-a", "ntlm_update"),
        commands=(SITES,),
    ),
    _spec(
        "site.ntlm_delete",
        "sites",
        "critical",
        "Remove NTLM and leave AD",
        dynamic(
            SITES,
            "ntlm_delete",
            (
                ("domain", "--ntlm_domain"),
                ("fqdn", "--ntlm_fqdn"),
                ("domain_controller", "--ntlm_ads"),
                ("login", "--ntlm_login"),
                ("password", "--password_file"),
                ("host", "--ntlm_host"),
            ),
        ),
        {
            "domain": HOST,
            "fqdn": HOST,
            "domain_controller": HOST,
            "login": HOST,
            "password": SECRET,
            "host": HOST,
        },
        (SITES,),
    ),
    _spec(
        "site.cronservice_enable",
        "sites",
        "high",
        "Enable Bitrix cron service restart",
        dynamic(
            SITES, "service", (("site", "--site"), ("service", "--service"), ("enable", "--enable"))
        ),
        {
            "site": SITE,
            "service": ParamSpec(kind="enum", enum=("xmppd", "smtp")),
            "enable": ParamSpec(kind="boolean", required=False, default=True),
        },
        (SITES,),
    ),
    _spec(
        "site.cronservice_disable",
        "sites",
        "high",
        "Disable Bitrix cron service restart",
        dynamic(
            SITES,
            "service",
            (("site", "--site"), ("service", "--service"), ("disable", "--disable")),
        ),
        {
            "site": SITE,
            "service": ParamSpec(kind="enum", enum=("xmppd", "smtp")),
            "disable": ParamSpec(kind="boolean", required=False, default=True),
        },
        (SITES,),
    ),
    *[
        _spec(
            f"site.{name}_{state}",
            "sites",
            "high",
            f"{state.title()} {name}",
            dynamic(SITES, action, (("site", "--site"), (state, f"--{state}"))),
            {"site": SITE, state: ParamSpec(kind="boolean", required=False, default=True)},
            (SITES,),
        )
        for name, action in (
            ("proxy_ignore_client_abort", "proxy_ignore_client_abort"),
            ("nginx_custom_settings", "nginx_custom_site_settings"),
            ("temporary_files", "dbconn_temp_files"),
        )
        for state in ("enable", "disable")
    ],
    _spec(
        "sphinx.create_instance",
        "sphinx",
        "high",
        "Create a Sphinx instance",
        dynamic(
            SPHINX,
            "create",
            (("host", "--server"), ("database", "--dbname"), ("reindex", "--reindex")),
        ),
        {
            "host": HOST,
            "database": HOST,
            "reindex": ParamSpec(kind="boolean", required=False, default=False),
        },
        (SPHINX,),
    ),
    _spec(
        "sphinx.create_index",
        "sphinx",
        "high",
        "Create or rebuild a Sphinx index",
        dynamic(
            SPHINX,
            "create",
            (("host", "--server"), ("database", "--dbname"), ("reindex", "--reindex")),
        ),
        {
            "host": HOST,
            "database": HOST,
            "reindex": ParamSpec(kind="boolean", required=False, default=True),
        },
        (SPHINX,),
    ),
    _spec(
        "sphinx.delete",
        "sphinx",
        "critical",
        "Delete a Sphinx instance/index",
        dynamic(SPHINX, "remove", (("host", "--server"), ("database", "--dbname"))),
        {"host": HOST, "database": HOST},
        (SPHINX,),
    ),
    _spec(
        "web.add_node",
        "web",
        "high",
        "Add a host to the web cluster",
        web_create,
        {
            "host": HOST,
            "mode": ParamSpec(kind="enum", enum=("complete", "prepare", "finish")),
            "fstype": ParamSpec(kind="enum", enum=("csync2", "lsyncd")),
        },
        (SITES,),
        disabled_reason="Web-node creation is disabled in BitrixEnv 9.0.10",
    ),
    _spec(
        "web.remove_node",
        "web",
        "critical",
        "Remove a host from the web cluster",
        dynamic(SITES, "delete_web", (("host", "--hostname"),)),
        {"host": HOST},
        (SITES,),
        disabled_reason="Web-node removal is disabled in BitrixEnv 9.0.10",
    ),
    _spec(
        "web.extension_enable",
        "web",
        "high",
        "Enable a PHP extension",
        dynamic(SITES, "extension_enable", (("extension", "--extension"),)),
        {
            "extension": ParamSpec(
                kind="enum",
                enum=("ssh2", "curl", "zip", "dom", "phar", "xdebug", "imagick", "xhprof"),
            )
        },
        (SITES,),
    ),
    _spec(
        "web.extension_disable",
        "web",
        "high",
        "Disable a PHP extension",
        dynamic(SITES, "extension_disable", (("extension", "--extension"),)),
        {
            "extension": ParamSpec(
                kind="enum",
                enum=("ssh2", "curl", "zip", "dom", "phar", "xdebug", "imagick", "xhprof"),
            )
        },
        (SITES,),
    ),
    _spec(
        "web.certificate_letsencrypt",
        "web",
        "high",
        "Configure a Let's Encrypt certificate",
        dynamic(
            SITES,
            "configure_le",
            (("sites", "--site"), ("root", "--root"), ("email", "--email"), ("dns_names", "--dns")),
        ),
        {
            "sites": ParamSpec(pattern=r"[A-Za-z0-9_., -]{1,2048}"),
            "root": PATH,
            "email": ParamSpec(pattern=r"[^@\s]+@[^@\s]+"),
            "dns_names": ParamSpec(pattern=r"[A-Za-z0-9_.,* -]{1,2048}"),
        },
        (SITES,),
    ),
    _spec(
        "web.certificate_custom",
        "web",
        "high",
        "Install a custom TLS certificate",
        dynamic(
            SITES,
            "configure_cert",
            (
                ("sites", "--site"),
                ("root", "--root"),
                ("private_key", "--private_key"),
                ("certificate", "--certificate"),
                ("certificate_chain", "--certificate_chain"),
            ),
        ),
        {
            "sites": ParamSpec(pattern=r"[A-Za-z0-9_., -]{1,2048}"),
            "root": PATH,
            "private_key": PATH,
            "certificate": PATH,
            "certificate_chain": ParamSpec(
                required=False, default="", pattern=r"(?:/[A-Za-z0-9_./-]{1,1023})?"
            ),
        },
        (SITES,),
    ),
    _spec(
        "web.certificate_reset",
        "web",
        "critical",
        "Reset sites to the general certificate",
        dynamic(SITES, "reset_cert", (("sites", "--site"),)),
        {"sites": ParamSpec(pattern=r"[A-Za-z0-9_., -]{1,2048}")},
        (SITES,),
    ),
    _spec(
        "monitoring.enable",
        "monitoring",
        "high",
        "Enable pool monitoring",
        dynamic(
            MONITOR,
            "enable",
            (
                ("host", "--server"),
                ("nagios_user", "--nagios_user"),
                ("nagios_password", "--nagios_password"),
                ("munin_user", "--munin_user"),
                ("munin_password", "--munin_password"),
                ("email", "--monitor_email"),
                ("smtp_host", "--smtphost"),
                ("smtp_port", "--smtpport"),
                ("smtp_login", "--smtplogin"),
                ("smtp_password", "--smtppass"),
                ("smtp_tls", "--smtptls"),
                ("smtp_method", "--smtpmethod"),
                ("notify_nagios", "--notify_nagios"),
            ),
        ),
        {
            "host": HOST,
            "nagios_user": HOST,
            "nagios_password": SECRET,
            "munin_user": HOST,
            "munin_password": SECRET,
            "email": ParamSpec(pattern=r"[^@\s]+@[^@\s]+"),
            "smtp_host": HOST,
            "smtp_port": ParamSpec(kind="integer", minimum=1, maximum=65535),
            "smtp_login": ParamSpec(required=False, default="", pattern=r"[^\s]{0,255}"),
            "smtp_password": ParamSpec(kind="secret", required=False, default=""),
            "smtp_tls": ParamSpec(kind="boolean", required=False, default=True),
            "smtp_method": ParamSpec(
                kind="enum", required=False, default="auto", enum=("auto", "plain", "login")
            ),
            "notify_nagios": ParamSpec(kind="boolean", required=False, default=True),
        },
        (MONITOR,),
        disabled_reason="Monitoring dispatch is disabled in BitrixEnv 9.0.10",
    ),
    _spec(
        "monitoring.update",
        "monitoring",
        "medium",
        "Update monitoring configuration",
        cli(MONITOR, "-a", "update"),
        commands=(MONITOR,),
        disabled_reason="Monitoring dispatch is disabled in BitrixEnv 9.0.10",
    ),
    _spec(
        "monitoring.disable",
        "monitoring",
        "critical",
        "Disable pool monitoring",
        cli(MONITOR, "-a", "disable"),
        commands=(MONITOR,),
        disabled_reason="Monitoring dispatch is disabled in BitrixEnv 9.0.10",
    ),
    _spec(
        "push.configure",
        "push",
        "high",
        "Configure Node.js push service",
        dynamic(SITES, "push_configure_nodejs", (("host", "--hostname"),)),
        {"host": HOST},
        (SITES,),
    ),
    _spec(
        "push.remove",
        "push",
        "critical",
        "Remove Node.js push service",
        dynamic(SITES, "push_remove_nodjs", (("host", "--hostname"),)),
        {"host": HOST},
        (SITES,),
    ),
    _spec(
        "transformer.configure",
        "transformer",
        "high",
        "Configure document transformer",
        dynamic(
            SITES,
            "configure_transformer",
            (
                ("site", "--site"),
                ("root", "--root"),
                ("host", "--hostname"),
                ("domains", "--domains"),
            ),
        ),
        {
            "site": SITE,
            "root": PATH,
            "host": HOST,
            "domains": ParamSpec(pattern=r"[A-Za-z0-9_.,*-]{1,2048}"),
        },
        (SITES,),
    ),
    _spec(
        "transformer.remove",
        "transformer",
        "critical",
        "Remove document transformer",
        dynamic(
            SITES,
            "remove_transformer",
            (("site", "--site"), ("root", "--root"), ("host", "--hostname")),
        ),
        {"site": SITE, "root": PATH, "host": HOST},
        (SITES,),
    ),
]


ACTIONS: dict[str, ActionSpec] = {item.name: item for item in ACTION_SPECS}
if len(ACTIONS) != len(ACTION_SPECS):
    raise RuntimeError("duplicate action name")


def get_action(name: str) -> ActionSpec:
    try:
        return ACTIONS[name]
    except KeyError as exc:
        raise ActionValidationError(f"unknown action: {name}") from exc
