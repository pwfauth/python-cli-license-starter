import json
import time

import pytest

from mytool import cli, config
from mytool.licensing import Licensing, SessionEnded
from mytool.store import FileStore

from conftest import ELSEWHERE, GOOD, TURBO, FakeClient, MemoryStore

app = cli.app


def names(client):
    return [c[0] for c in client.calls]


# ── activate ─────────────────────────────────────────────────────────────────

def test_activate_saves_the_key_and_closes_the_session(fake, runner):
    client, store = fake
    r = runner.invoke(app, ["activate", GOOD])
    assert r.exit_code == 0, r.output
    assert "License activated" in r.output
    assert "GOOD-••••-••••-3333" in r.output
    assert store.key == GOOD
    assert names(client) == ["login", "logout"]


def test_activate_asks_for_the_key_when_left_out(fake, runner):
    client, store = fake
    r = runner.invoke(app, ["activate"], input=GOOD + "\n")
    assert r.exit_code == 0, r.output
    assert store.key == GOOD


def test_activate_refuses_a_wrong_key(fake, runner):
    client, store = fake
    r = runner.invoke(app, ["activate", "NOPE-0000-0000-0000"])
    assert r.exit_code == 2
    assert "Invalid license key" in r.output
    assert store.key is None


def test_activate_moves_a_license_from_another_computer(fake, runner):
    client, store = fake
    r = runner.invoke(app, ["activate", ELSEWHERE], input="y\n")
    assert r.exit_code == 0, r.output
    assert "in use on another computer" in r.output
    assert names(client) == ["login", "reset_hardware_id", "login", "logout"]
    assert store.key == ELSEWHERE


def test_activate_keeps_the_license_where_it_is_when_the_user_says_no(fake, runner):
    client, store = fake
    r = runner.invoke(app, ["activate", ELSEWHERE], input="n\n")
    assert r.exit_code == 2
    assert "reset_hardware_id" not in names(client)
    assert store.key is None


def test_activate_yes_moves_without_asking(fake, runner):
    client, store = fake
    r = runner.invoke(app, ["activate", ELSEWHERE, "--yes"])
    assert r.exit_code == 0, r.output
    assert "reset_hardware_id" in names(client)


def test_a_key_from_the_environment_is_not_saved(fake, runner, monkeypatch):
    client, store = fake
    monkeypatch.setenv(config.ENV_LICENSE_KEY, GOOD)
    r = runner.invoke(app, ["activate", GOOD])
    assert r.exit_code == 0, r.output
    assert store.key is None
    assert "was not saved" in r.output


# ── trial ────────────────────────────────────────────────────────────────────

def test_trial_activates_the_trial_key(fake, runner):
    client, store = fake
    r = runner.invoke(app, ["trial"])
    assert r.exit_code == 0, r.output
    assert "Free trial started" in r.output
    assert store.key == GOOD


def test_a_used_trial_comes_back_with_its_key(fake, runner):
    client, store = fake
    from conftest import reply
    client.trial_reply = reply(success=False, error_code="TRIAL_USED",
                               message="You have already used your trial.", trial_key=GOOD)
    r = runner.invoke(app, ["trial"])
    assert r.exit_code == 0, r.output
    assert store.key == GOOD


def test_trial_disabled(fake, runner):
    client, store = fake
    from conftest import reply
    client.trial_reply = reply(success=False, error_code="TRIAL_DISABLED", message="Trials are not available.")
    r = runner.invoke(app, ["trial"])
    assert r.exit_code == 2
    assert "Trials are not available" in r.output


# ── status / deactivate / update ─────────────────────────────────────────────

def test_status_without_a_license_says_what_to_do(fake, runner):
    r = runner.invoke(app, ["status"])
    assert r.exit_code == 2
    assert "mytool activate" in r.output


def test_status_shows_the_card_without_a_session(fake, runner):
    client, store = fake
    store.key = TURBO
    r = runner.invoke(app, ["status"])
    assert r.exit_code == 0, r.output
    assert "Active" in r.output and "30 days" in r.output and "turbo" in r.output
    assert names(client) == ["check_key"]


def test_status_json(fake, runner):
    client, store = fake
    store.key = GOOD
    r = runner.invoke(app, ["status", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data["valid"] is True and data["status"] == "active" and data["key"] == "GOOD-••••-••••-3333"


def test_status_of_a_key_the_server_does_not_know(fake, runner):
    client, store = fake
    store.key = "GONE-0000-0000-0000"
    r = runner.invoke(app, ["status"])
    assert r.exit_code == 2
    assert "Key not found" in r.output


def test_deactivate_forgets_the_key(fake, runner):
    client, store = fake
    store.key = GOOD
    r = runner.invoke(app, ["deactivate", "--yes"])
    assert r.exit_code == 0, r.output
    assert store.key is None


def test_update_shows_the_new_version(fake, runner):
    r = runner.invoke(app, ["update"])
    assert r.exit_code == 0, r.output
    assert "1.1.0" in r.output and "Faster runs" in r.output
    assert "https://pwfauth.com/api/update/download.php?v=1.1.0" in r.output


# ── run: the licensed work ───────────────────────────────────────────────────

def test_run_needs_a_license(fake, runner):
    r = runner.invoke(app, ["run"])
    assert r.exit_code == 2
    assert "no license yet" in r.output


def test_run_works_counts_and_signs_out(fake, runner):
    client, store = fake
    store.key = GOOD
    r = runner.invoke(app, ["run", "--steps", "2"])
    assert r.exit_code == 0, r.output
    assert "Version 2 is coming" in r.output          # the remote text
    assert "run mytool 1 time" in r.output
    assert client.vars["runs"] == "1"
    runner.invoke(app, ["run", "--steps", "1"])
    assert client.vars["runs"] == "2"
    assert names(client)[-1] == "logout"


def test_the_kill_switch_stops_the_work(fake, runner):
    client, store = fake
    store.key = GOOD
    client.end_after = 0.5
    started = time.monotonic()
    r = runner.invoke(app, ["run", "--steps", "400"])
    assert r.exit_code == 3, r.output
    assert "License ended" in r.output and "banned" in r.output
    assert time.monotonic() - started < 5
    assert "logout" not in names(client)              # the server already ended it


def test_no_server_is_a_clear_error(fake, runner):
    client, store = fake
    client.offline = True
    r = runner.invoke(app, ["activate", GOOD])
    assert r.exit_code == 1
    assert "Cannot reach the license server" in r.output


# ── pieces ───────────────────────────────────────────────────────────────────

def test_session_ensure_active_raises_after_the_end():
    client = FakeClient()
    client.end_after = 0.05
    lic = Licensing(client=client, store=MemoryStore(GOOD), grace_seconds=30)
    with pytest.raises(SessionEnded) as err:
        with lic.session() as s:
            for _ in range(100):
                s.ensure_active()
                time.sleep(0.05)
    assert err.value.code == "BANNED" and err.value.exit_code == 3


@pytest.mark.parametrize("value, ok", [("a" * 64, True), ("A1" * 32, True), ("", False), ("xyz", False)])
def test_app_secret_validation(monkeypatch, value, ok):
    monkeypatch.setenv(config.ENV_SECRET, value)
    if ok:
        assert config.app_secret() == value.lower()
    else:
        with pytest.raises(config.ConfigError):
            config.app_secret()


def test_missing_secret_is_a_setup_error(monkeypatch, runner):
    monkeypatch.setenv(config.ENV_SECRET, "")
    monkeypatch.setattr(cli, "licensing_factory", lambda: Licensing(store=MemoryStore()))
    r = runner.invoke(app, ["activate", GOOD])
    assert r.exit_code == 1
    assert "No app secret" in r.output


def test_file_store_round_trip(tmp_path):
    s = FileStore(tmp_path)
    assert s.get() is None
    s.set(GOOD)
    assert s.get() == GOOD
    s.clear()
    assert s.get() is None
