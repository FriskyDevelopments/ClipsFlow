from services import db


def test_ensure_friskydev_account_creates_pending_account(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "clipsflow.sqlite3"))

    user = db.ensure_friskydev_account(
        "telegram",
        "123",
        username="frisky_user",
        environment="friskydev",
    )

    assert user["platform"] == "telegram"
    assert user["platform_id"] == "123"
    assert user["username"] == "frisky_user"
    assert user["friskydev_environment"] == "friskydev"
    assert user["friskydev_account_status"] == "pro_pending"
    assert user["friskydev_account_id"].startswith("fdev_")
    assert user["pro_upgrade_requested_at"]


def test_ensure_friskydev_account_reuses_existing_account(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "clipsflow.sqlite3"))

    first = db.ensure_friskydev_account("telegram", "123", environment="friskydev")
    second = db.ensure_friskydev_account("telegram", "123", environment="friskydev")

    assert second["friskydev_account_id"] == first["friskydev_account_id"]


def test_ensure_friskydev_account_marks_active_when_user_is_pro(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "clipsflow.sqlite3"))

    db.set_user_pro("telegram", "123", True)
    user = db.ensure_friskydev_account("telegram", "123", environment="friskydev")

    assert user["is_pro"] == 1
    assert user["friskydev_account_status"] == "pro_active"


def test_mark_telegram_stars_payment_activates_pro_account(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "clipsflow.sqlite3"))

    pending = db.ensure_friskydev_account("telegram", "123", environment="friskydev")
    active = db.mark_telegram_stars_payment(
        "telegram",
        "123",
        stars_amount=250,
        charge_id="stars_charge_123",
        environment="friskydev",
    )

    assert active["friskydev_account_id"] == pending["friskydev_account_id"]
    assert active["is_pro"] == 1
    assert active["friskydev_account_status"] == "pro_active"
    assert active["telegram_stars_amount"] == 250
    assert active["telegram_stars_charge_id"] == "stars_charge_123"
    assert active["telegram_stars_paid_at"]


def test_free_trial_state_counts_lifetime_exports(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "clipsflow.sqlite3"))

    state = db.get_free_trial_state("telegram", "123", limit=2)
    assert state == {"used": 0, "limit": 2, "remaining": 2, "exhausted": False}

    db.record_free_export("telegram", "123")
    state = db.get_free_trial_state("telegram", "123", limit=2)
    assert state == {"used": 1, "limit": 2, "remaining": 1, "exhausted": False}

    db.record_free_export("telegram", "123")
    state = db.get_free_trial_state("telegram", "123", limit=2)
    assert state == {"used": 2, "limit": 2, "remaining": 0, "exhausted": True}
