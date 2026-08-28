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
