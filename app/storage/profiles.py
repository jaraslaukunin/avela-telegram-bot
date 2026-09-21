from dataclasses import dataclass


@dataclass
class UserProfile:
    telegram_id: int
    full_name: str
    username: str | None = None
    phone: str | None = None


profiles: dict[int, UserProfile] = {}