"""Тесты служебных команд: проверяем разбор аргументов (без БД)."""
from app.cli import build_parser


def test_grant_admin_parses_telegram_id() -> None:
    args = build_parser().parse_args(["grant-admin", "123456789"])

    assert args.command == "grant-admin"
    assert args.telegram_id == 123456789


def test_seed_demo_defaults_to_two_weeks() -> None:
    args = build_parser().parse_args(["seed-demo"])

    assert args.command == "seed-demo"
    assert args.days == 14


def test_seed_demo_accepts_custom_days() -> None:
    args = build_parser().parse_args(["seed-demo", "--days", "30"])

    assert args.days == 30


def test_show_state_command_parses() -> None:
    args = build_parser().parse_args(["show-state"])

    assert args.command == "show-state"
