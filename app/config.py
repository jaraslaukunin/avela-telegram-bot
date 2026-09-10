from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str


def get_settings() -> Settings:
    bot_token = getenv("BOT_TOKEN")

    if not bot_token:
        raise RuntimeError(
            "Переменная окружения BOT_TOKEN не задана. "
            "Добавь её в файл .env в корне проекта."
        )

    return Settings(bot_token=bot_token)