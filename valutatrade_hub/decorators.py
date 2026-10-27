import logging
from functools import wraps


def log_action(action: str, verbose: bool = False):
    """Логировать операции buy/sell и пробрасывать их исключения."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, currency_code: str, amount: float):
            logger = logging.getLogger("valutatrade.actions")
            user = self.current_user
            record = {
                "action": action,
                "username": user.username if user is not None else None,
                "currency_code": currency_code,
                "amount": amount,
                "rate": None,
                "base": "USD",
            }

            try:
                result = func(self, currency_code, amount)
            except Exception as error:
                record.update(
                    result="ERROR",
                    error_type=type(error).__name__,
                    error_message=str(error),
                )
                logger.info("%s", record)
                raise

            record.update(
                currency_code=result["currency_code"],
                amount=result["amount"],
                rate=result["rate"],
                base=result["base"],
                result="OK",
            )
            if verbose:
                record.update(
                    balance_before=result["balance_before"],
                    balance_after=result["balance_after"],
                )
            logger.info("%s", record)
            return result

        return wrapper

    return decorator