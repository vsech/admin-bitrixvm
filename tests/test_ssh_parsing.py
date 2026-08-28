from __future__ import annotations

from app.ssh import parse_output, redact


def test_recursive_redaction_of_real_bitrix_shapes() -> None:
    source = {
        "params": {
            "server": {
                "host_vars": {"host_pass": "generated-password"},
                "DBPassword": "database-password",
                "ip": "192.168.0.56",
            }
        }
    }
    result = redact(source)
    assert result["params"]["server"]["host_vars"]["host_pass"] == "********"
    assert result["params"]["server"]["DBPassword"] == "********"
    assert result["params"]["server"]["ip"] == "192.168.0.56"


def test_json_output_is_normalized() -> None:
    result = parse_output('{"params":{"status":"finished","token":"x"}}', "", 0)
    assert result["exit_status"] == 0
    assert result["data"]["params"]["status"] == "finished"
    assert result["data"]["params"]["token"] == "********"


def test_plain_task_output_extracts_remote_id() -> None:
    result = parse_output("info:process:memcached_123:456:0:0:running\n", "", 0)
    assert result["remote_task_id"] == "memcached_123"


def test_plain_error_is_redacted() -> None:
    result = parse_output("error:auth\npassword=visible", "", 1)
    assert "visible" not in result["stdout"]


def test_action_identifier_ending_in_password_is_not_redacted() -> None:
    source = {"actions": {"mysql.change_password": {"available": True}}}
    assert redact(source) == source
