class InsufficientFundsError(Exception):
    """Недостаточно средств для списания."""

    def __init__(self, available: float, required: float, code: str):
        super().__init__(
            f"Недостаточно средств: доступно {available:g} {code}, "
            f"требуется {required:g} {code}"
        )