class InsufficientFundsError(Exception):
    """Недостаточно средств для списания."""

    def __init__(self, available: float, required: float, code: str):
        super().__init__(
            f"Недостаточно средств: доступно {available:g} {code}, "
            f"требуется {required:g} {code}"
        )

class CurrencyNotFoundError(ValueError):
    """Валюта отсутствует в реестре поддерживаемых валют."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(Exception):
    """Не удалось получить данные из внешнего API."""

    def __init__(self, reason: str):
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")