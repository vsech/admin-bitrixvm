from __future__ import annotations

from app.worker import find_status, remote_status_succeeded


def test_find_status_in_remote_task_shape() -> None:
    payload = {
        "exit_status": 0,
        "data": {"params": {"memcached_123": {"errors": 0, "status": "finished"}}},
    }
    assert find_status(payload) == "finished"


def test_reboot_interrupt_is_the_only_successful_interrupt() -> None:
    assert remote_status_succeeded("host.reboot", "interrupt")
    assert not remote_status_succeeded("tasks.stop", "interrupt")
