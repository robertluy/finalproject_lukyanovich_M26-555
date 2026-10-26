from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.core.utils import (
    get_exchange_rate,
    normalize_currency_code,
)
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader


class TradingService:
    """Бизнес-логика платформы и текущая пользовательская сессия."""

    def __init__(self):
        self._settings = SettingsLoader()
        self._database = DatabaseManager()
        self._current_user = None

    @property
    def current_user(self) -> User | None:
        """Вернуть текущего пользователя или None до входа."""
        return self._current_user

    def register(self, username: str, password: str) -> User:
        """Зарегистрировать пользователя и создать пустой портфель."""
        users = self._database.read("users")
        portfolios = self._database.read("portfolios")

        user_id = max(
            (item["user_id"] for item in users),
            default=0,
        ) + 1
        user = User.create(user_id, username, password)

        if any(item["username"] == user.username for item in users):
            raise ValueError(f"Имя пользователя '{user.username}' уже занято")

        portfolio = Portfolio(user)

        self._database.write("users", users + [user.to_dict()])
        try:
            self._database.write(
                "portfolios",
                portfolios + [portfolio.to_dict()],
            )
        except OSError:
            self._database.write("users", users)
            raise

        return user

    def login(self, username: str, password: str) -> User:
        """Проверить пароль и установить текущего пользователя."""
        if not isinstance(username, str) or not username.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        username = username.strip()

        users = self._database.read("users")
        user_data = next(
            (item for item in users if item["username"] == username),
            None,
        )

        if user_data is None:
            raise ValueError(f"Пользователь '{username}' не найден")

        user = User.from_dict(user_data)
        if not user.verify_password(password):
            raise ValueError("Неверный пароль")

        self._current_user = user
        return user

    def _require_login(self) -> User:
        """Проверить вход и вернуть текущего пользователя."""
        if self._current_user is None:
            raise ValueError("Сначала выполните login")
        return self._current_user

    def get_portfolio(self) -> Portfolio:
        """Загрузить портфель текущего пользователя."""
        user = self._require_login()
        portfolios = self._database.read("portfolios")
        for data in portfolios:
            if data["user_id"] == user.user_id:
                return Portfolio.from_dict(data, user)
        raise ValueError("Портфель пользователя не найден")

    def _save_portfolio(self, portfolio: Portfolio):
        """Обновить запись портфеля в хранилище."""
        portfolios = self._database.read("portfolios")
        for index, data in enumerate(portfolios):
            if data["user_id"] == portfolio.user.user_id:
                portfolios[index] = portfolio.to_dict()
                self._database.write("portfolios", portfolios)
                return
        raise ValueError("Портфель пользователя не найден")

    def show_portfolio(self, base_currency: str | None = None) -> dict:
        """Подготовить балансы и стоимость портфеля для CLI."""
        portfolio = self.get_portfolio()
        if base_currency is None:
            base_currency = self._settings.get("default_base_currency")
        base_currency = normalize_currency_code(base_currency)
        total_value = portfolio.get_total_value(base_currency)

        wallets = []
        for code, wallet in portfolio.wallets.items():
            wallets.append(
                {
                    "currency_code": code,
                    "balance": wallet.balance,
                    "value": wallet.balance * get_exchange_rate(code, base_currency),
                }
            )

        return {
            "username": portfolio.user.username,
            "base_currency": base_currency,
            "wallets": wallets,
            "total_value": total_value,
        }

    def buy(self, currency_code: str, amount: float) -> dict:
        """Купить валюту в рамках упрощённой модели."""
        return self._trade(currency_code, amount, is_buy=True)

    def sell(self, currency_code: str, amount: float) -> dict:
        """Продать валюту в рамках упрощённой модели."""
        return self._trade(currency_code, amount, is_buy=False)

    def _trade(self, currency_code: str, amount: float, is_buy: bool) -> dict:
        """Выполнить операцию с кошельком и сохранить портфель."""
        portfolio = self.get_portfolio()
        code = normalize_currency_code(currency_code)
        rate = get_exchange_rate(code)

        if is_buy:
            wallet = portfolio.add_currency(code)
        else:
            wallet = portfolio.get_wallet(code)

        balance_before = wallet.balance
        if is_buy:
            wallet.deposit(amount)
        else:
            wallet.withdraw(amount)

        self._save_portfolio(portfolio)

        return {
            "currency_code": code,
            "amount": float(amount),
            "rate": rate,
            "base": "USD",
            "estimated_usd": float(amount) * rate,
            "balance_before": balance_before,
            "balance_after": wallet.balance,
        }

    def get_rate(self, from_currency: str, to_currency: str) -> dict:
        """Получить прямой и обратный учебные курсы."""
        from_currency = normalize_currency_code(from_currency)
        to_currency = normalize_currency_code(to_currency)
        return {
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": get_exchange_rate(from_currency, to_currency),
            "reverse_rate": get_exchange_rate(to_currency, from_currency),
            "updated_at": None,
            "source": "учебные фиксированные курсы",
        }