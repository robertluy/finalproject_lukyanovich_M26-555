import hashlib
import math
import secrets
from datetime import datetime, timezone

from valutatrade_hub.core.exceptions import InsufficientFundsError
from valutatrade_hub.core.utils import (
    get_exchange_rate,
    normalize_currency_code,
)

MIN_PASSWORD_LENGTH = 4


class User:
    """Пользователь платформы с хешированным паролем."""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ):
        self._user_id = user_id
        self.username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        """Вернуть идентификатор пользователя."""
        return self._user_id

    @property
    def username(self) -> str:
        """Вернуть имя пользователя."""
        return self._username

    @username.setter
    def username(self, value: str):
        """Проверить и установить имя пользователя."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value.strip()

    @property
    def hashed_password(self) -> str:
        """Вернуть хеш для сохранения в хранилище."""
        return self._hashed_password

    @property
    def salt(self) -> str:
        """Вернуть соль для сохранения в хранилище."""
        return self._salt

    @property
    def registration_date(self) -> datetime:
        """Вернуть дату регистрации."""
        return self._registration_date

    @classmethod
    def create(cls, user_id: int, username: str, password: str) -> "User":
        """Создать нового пользователя с солью и хешем пароля."""
        user = cls(
            user_id=user_id,
            username=username,
            hashed_password="",
            salt=secrets.token_hex(16),
            registration_date=datetime.now(timezone.utc),
        )
        user.change_password(password)
        return user

    def _hash_password(self, password: str) -> str:
        """Вычислить SHA-256 пароля с солью пользователя."""
        return hashlib.sha256((password + self._salt).encode("utf-8")).hexdigest()

    def change_password(self, new_password: str):
        """Установить новый пароль после проверки длины."""
        if not isinstance(new_password, str) or len(new_password) < MIN_PASSWORD_LENGTH:
            raise ValueError("Пароль должен быть не короче 4 символов")
        self._hashed_password = self._hash_password(new_password)

    def verify_password(self, password: str) -> bool:
        """Проверить введённый пароль."""
        if not isinstance(password, str):
            return False
        return secrets.compare_digest(
            self._hash_password(password), self._hashed_password
        )

    def get_user_info(self) -> dict:
        """Вернуть информацию о пользователе без хеша и соли."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "registration_date": self.registration_date.isoformat(),
        }

    def to_dict(self) -> dict:
        """Подготовить запись пользователя для JSON-хранилища."""
        return {
            **self.get_user_info(),
            "hashed_password": self.hashed_password,
            "salt": self.salt,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Восстановить пользователя из JSON-записи."""
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            hashed_password=data["hashed_password"],
            salt=data["salt"],
            registration_date=datetime.fromisoformat(data["registration_date"]),
        )


class Wallet:
    """Кошелёк пользователя для одной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0):
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")
        self.currency_code = currency_code.strip().upper()
        self.balance = balance

    @staticmethod
    def _validate_number(value: float) -> float:
        """Проверить, что значение является конечным числом."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Сумма должна быть числом")
        if not math.isfinite(value):
            raise ValueError("Сумма должна быть конечным числом")
        return float(value)

    @staticmethod
    def _validate_amount(amount: float) -> float:
        """Проверить положительную сумму операции."""
        amount = Wallet._validate_number(amount)
        if amount <= 0:
            raise ValueError("Сумма должна быть положительным числом")
        return amount

    @property
    def balance(self) -> float:
        """Вернуть текущий баланс."""
        return self._balance

    @balance.setter
    def balance(self, value: float):
        """Установить неотрицательный баланс."""
        value = self._validate_number(value)
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = value

    def deposit(self, amount: float):
        """Пополнить кошелёк на указанную сумму."""
        amount = self._validate_amount(amount)
        self.balance += amount

    def withdraw(self, amount: float):
        """Списать сумму, если средств достаточно."""
        amount = self._validate_amount(amount)
        if amount > self.balance:
            raise InsufficientFundsError(
                available=self.balance,
                required=amount,
                code=self.currency_code,
            )
        self.balance -= amount

    def get_balance_info(self) -> str:
        """Вернуть информацию о балансе кошелька."""
        return f"{self.currency_code}: {self.balance:.4f}"

    def to_dict(self) -> dict:
        """Подготовить кошелёк для JSON-хранилища."""
        return {
            "currency_code": self.currency_code,
            "balance": self.balance,
        }


class Portfolio:
    """Все валютные кошельки одного пользователя."""

    def __init__(self, user: User, wallets: dict[str, Wallet] | None = None):
        self._user = user
        self._user_id = user.user_id
        self._wallets = wallets.copy() if wallets is not None else {}

    @property
    def user(self) -> User:
        """Вернуть владельца портфеля."""
        return self._user

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Вернуть копию словаря кошельков."""
        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> Wallet:
        """Создать кошелёк при отсутствии и вернуть его."""
        code = normalize_currency_code(currency_code)
        get_exchange_rate(code)
        if code not in self._wallets:
            self._wallets[code] = Wallet(code)
        return self._wallets[code]

    def get_wallet(self, currency_code: str) -> Wallet:
        """Получить кошелёк по коду валюты."""
        code = normalize_currency_code(currency_code)
        if code not in self._wallets:
            raise ValueError(f"У вас нет кошелька '{code}'")
        return self._wallets[code]

    def get_total_value(self, base_currency: str = "USD") -> float:
        """Рассчитать стоимость портфеля в выбранной валюте."""
        base_rate = get_exchange_rate(base_currency)
        return sum(
            (
                wallet.balance * get_exchange_rate(code) / base_rate
                for code, wallet in self._wallets.items()
            ),
            0.0,
        )

    def to_dict(self) -> dict:
        """Подготовить портфель для JSON-хранилища."""
        return {
            "user_id": self._user_id,
            "wallets": {
                code: wallet.to_dict()
                for code, wallet in self._wallets.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict, user: User) -> "Portfolio":
        """Восстановить портфель сохранённого пользователя."""
        if data["user_id"] != user.user_id:
            raise ValueError("Портфель принадлежит другому пользователю")
        portfolio = cls(user)
        for code, wallet_data in data["wallets"].items():
            wallet = portfolio.add_currency(code)
            wallet.balance = wallet_data["balance"]
        return portfolio