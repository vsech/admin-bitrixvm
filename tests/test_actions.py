from __future__ import annotations

import pytest

from app.actions import ACTIONS, ActionValidationError


def test_catalog_covers_all_menu_scenarios() -> None:
    assert len(ACTIONS) == 83
    assert {
        "pool.create",
        "host.reboot",
        "mysql.create_replica",
        "site.ntlm_create",
        "web.certificate_custom",
        "monitoring.disable",
        "transformer.remove",
    }.issubset(ACTIONS)


def test_every_action_has_machine_readable_contract() -> None:
    for name, spec in ACTIONS.items():
        schema = spec.request_schema()
        assert spec.name == name
        assert spec.category
        assert spec.summary
        assert schema["additionalProperties"] is False
        assert set(schema["required"]).issubset(schema["properties"])


def test_unknown_and_injected_parameters_are_rejected() -> None:
    spec = ACTIONS["host.reboot"]
    with pytest.raises(ActionValidationError, match="unknown parameters"):
        spec.normalize({"host": "bxcv.ru", "command": "rm -rf /"})
    with pytest.raises(ActionValidationError, match="invalid format"):
        spec.normalize({"host": "bxcv.ru; shutdown -h now"})


def test_secrets_are_redacted_but_preserved_for_encrypted_execution() -> None:
    spec = ACTIONS["mysql.change_password"]
    normalized = spec.normalize({"host": "db1.example", "password": "super-secret"})
    assert normalized["password"] == "super-secret"
    assert spec.redact(normalized)["password"] == "********"


def test_kernel_site_uses_supported_bx_sites_options_and_password_file() -> None:
    spec = ACTIONS["site.create_kernel"]
    values = spec.normalize(
        {
            "root": "/home/bitrix/test_site",
            "site": "test_s",
            "db_name": "test_p",
            "db_type": "pgsql",
            "db_user": "test_u",
            "db_password": "super-secret",
        }
    )
    command = spec.builder(values, {"db_password": "/tmp/bitrixvm-secret"})[0]

    assert command.argv == (
        "/opt/webdir/bin/bx-sites",
        "-a",
        "create",
        "--site",
        "test_s",
        "--type",
        "kernel",
        "--charset",
        "utf-8",
        "--root",
        "/home/bitrix/test_site",
        "--dbtype",
        "pgsql",
        "--database",
        "test_p",
        "--user",
        "test_u",
        "--password_file",
        "/tmp/bitrixvm-secret",
    )
    assert "super-secret" not in command.argv


def test_kernel_site_rejects_server_address_as_database_name() -> None:
    spec = ACTIONS["site.create_kernel"]

    with pytest.raises(ActionValidationError, match="db_name has invalid format"):
        spec.normalize(
            {
                "root": "/home/bitrix/test_site",
                "site": "test_site",
                "db_name": "192.168.0.56",
                "db_type": "pgsql",
                "db_user": "test_u",
                "db_password": "super-secret",
            }
        )


def test_external_kernel_uses_its_real_type_and_database_contract() -> None:
    spec = ACTIONS["site.create_external_kernel"]
    values = spec.normalize(
        {
            "root": "/home/bitrix/ext_kernel",
            "site": "shared_kernel",
            "db_name": "shared_db",
            "db_type": "pgsql",
            "db_user": "shared_user",
            "db_password": "super-secret",
        }
    )
    command = spec.builder(values, {"db_password": "/tmp/bitrixvm-secret"})[0]

    assert ("--type", "ext_kernel") == command.argv[5:7]
    assert ("--database", "shared_db") == command.argv[13:15]
    assert ("--password_file", "/tmp/bitrixvm-secret") == command.argv[-2:]
    assert "--kernel_root" not in command.argv


def test_link_site_sets_link_type_explicitly() -> None:
    spec = ACTIONS["site.create_link"]
    values = spec.normalize(
        {
            "site": "linked.example.com",
            "kernel_root": "/home/bitrix/ext_www/kernel.example.com",
        }
    )
    command = spec.builder(values, {})[0]

    assert ("--type", "link") == command.argv[5:7]


def test_host_password_change_supplies_all_native_mandatory_values() -> None:
    spec = ACTIONS["host.change_bitrix_password"]
    values = spec.normalize({"host": "vm1.example.com", "password": "super-secret"})
    command = spec.builder(values, {"password": "/tmp/unused-secret"})[0]

    assert command.argv == (
        "/opt/webdir/bin/wrapper_ansible_conf",
        "-a",
        "bx_passwd",
        "--host",
        "vm1.example.com",
        "--user",
        "bitrix",
        "--new",
        "super-secret",
    )
    assert spec.redact(values)["password"] == "********"


def test_timezone_can_update_php_configuration_like_native_menu() -> None:
    spec = ACTIONS["host.timezone"]
    values = spec.normalize({"timezone": "Asia/Yekaterinburg"})
    command = spec.builder(values, {})[0]

    assert command.argv[-1] == "--php"


def test_site_email_uses_password_file_instead_of_plain_argv() -> None:
    spec = ACTIONS["site.email"]
    values = spec.normalize(
        {
            "site": "example.com",
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "sender": "admin@example.com",
            "smtp_user": "admin",
            "smtp_password": "super-secret",
        }
    )
    command = spec.builder(values, {"smtp_password": "/tmp/smtp-secret"})[0]

    assert ("--password_file", "/tmp/smtp-secret") == command.argv[-2:]
    assert "super-secret" not in command.argv


@pytest.mark.parametrize("action", ("site.ntlm_create", "site.ntlm_update"))
def test_ntlm_actions_supply_mandatory_database(action: str) -> None:
    spec = ACTIONS[action]
    if action == "site.ntlm_update":
        supplied = {"database": "sitemanager"}
        secret_files = {}
    else:
        supplied = {
            "domain": "EXAMPLE",
            "fqdn": "example.com",
            "domain_controller": "dc.example.com",
            "login": "Administrator",
            "password": "super-secret",
            "host": "vm1.example.com",
            "database": "sitemanager",
        }
        secret_files = {"password": "/tmp/ntlm-secret"}
    command = spec.builder(spec.normalize(supplied), secret_files)[0]

    assert ("--database", "sitemanager") == command.argv[-2:]


@pytest.mark.parametrize("action", ("site.backup_enable", "site.backup_disable"))
def test_site_backup_uses_supported_database_option(action: str) -> None:
    spec = ACTIONS[action]
    supplied = {"database": "test_p"}
    if action == "site.backup_enable":
        supplied.update(minute=10, hour=23, day="*", month="*", weekday="6")
    command = spec.builder(spec.normalize(supplied), {})[0]

    assert "--database" in command.argv
    assert "--dbname" not in command.argv


def test_high_risk_requires_confirmation() -> None:
    assert ACTIONS["site.delete"].confirmation_required
    assert ACTIONS["local.network_static"].confirmation_required
    assert not ACTIONS["memcached.update"].confirmation_required


def test_known_upstream_disabled_actions_are_explicit() -> None:
    disabled = {name for name, spec in ACTIONS.items() if spec.disabled_reason}
    assert disabled == {
        "host.repository",
        "mysql.create_replica",
        "mysql.promote_master",
        "mysql.remove_replica",
        "web.add_node",
        "web.remove_node",
        "monitoring.enable",
        "monitoring.update",
        "monitoring.disable",
    }


def test_static_network_validates_real_ip_values() -> None:
    spec = ACTIONS["local.network_static"]
    values = spec.normalize(
        {
            "connection": "System_eth0",
            "address": "192.168.0.56",
            "prefix": 24,
            "gateway": "192.168.0.1",
            "dns": "1.1.1.1,8.8.8.8",
        }
    )
    commands = spec.builder(values, {})
    assert commands[0].argv[0] == "/usr/bin/nmcli"
    assert commands[-1].expect_disconnect
