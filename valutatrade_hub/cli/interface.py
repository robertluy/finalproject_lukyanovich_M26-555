import argparse
import shlex

from prettytable import PrettyTable

from valutatrade_hub.core.currencies import get_supported_codes
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.usecases import TradingService
from valutatrade_hub.logging_config import configure_logging


def _build_parser() -> argparse.ArgumentParser:
    """Подготовить команды и их аргументы."""
    parser = argparse.ArgumentParser(prog="valutatrade")
    commands = parser.add_subparsers(dest="command", required=True)

    for name in ("register", "login"):
        command = commands.add_parser(name)
        command.add_argument("--username", required=True)
        command.add_argument("--password", required=True)

    command = commands.add_parser("show-portfolio")
    command.add_argument("--base")

    for name in ("buy", "sell"):
        command = commands.add_parser(name)
        command.add_argument("--currency", required=True)
        command.add_argument("--amount", required=True, type=float)

    command = commands.add_parser("get-rate")
    command.add_argument("--from", dest="from_currency", required=True)
    command.add_argument("--to", dest="to_currency", required=True)
    return parser


def _print_portfolio(report: dict):
    """Вывести подготовленные данные портфеля таблицей."""
    base = report["base_currency"]
    print(f"Портфель пользователя '{report['username']}' (база: {base}):")
    if not report["wallets"]:
        print("Кошельков пока нет")
        return

    table = PrettyTable(["Валюта", "Баланс", f"Стоимость, {base}"])
    for wallet in report["wallets"]:
        table.add_row(
            [
                wallet["currency_code"],
                f"{wallet['balance']:.4f}",
                f"{wallet['value']:.2f}",
            ]
        )
    print(table)
    print(f"ИТОГО: {report['total_value']:,.2f} {base}")


def _execute_command(args: argparse.Namespace, service: TradingService):
    """Вызвать бизнес-логику выбранной команды."""
    match args.command:
        case "register":
            user = service.register(args.username, args.password)
            print(
                f"Пользователь '{user.username}' зарегистрирован "
                f"(id={user.user_id}). Теперь выполните login."
            )
        case "login":
            user = service.login(args.username, args.password)
            print(f"Вы вошли как '{user.username}'")
        case "show-portfolio":
            _print_portfolio(service.show_portfolio(args.base))
        case "buy" | "sell":
            if args.command == "buy":
                result = service.buy(args.currency, args.amount)
                action = "Покупка"
            else:
                result = service.sell(args.currency, args.amount)
                action = "Продажа"

            code = result["currency_code"]
            print(f"{action} выполнена: {result['amount']:.4f} {code}")
            print(f"Курс: {result['rate']:.8f} USD/{code}")
            print(
                f"Баланс: {result['balance_before']:.4f} "
                f"→ {result['balance_after']:.4f} {code}"
            )
            print(f"Оценочная сумма: {result['estimated_usd']:,.2f} USD")
        case "get-rate":
            result = service.get_rate(args.from_currency, args.to_currency)
            source = result["from_currency"]
            target = result["to_currency"]
            print(f"Курс {source}→{target}: {result['rate']:.8f}")
            print(f"Обратный курс {target}→{source}: {result['reverse_rate']:.8f}")
            if result["updated_at"] is not None:
                print(f"Обновлено: {result['updated_at']}")
            print(f"Источник: {result['source']}")


def main():
    """Запустить интерактивный командный интерфейс."""
    parser = _build_parser()
    try:
        configure_logging()
        service = TradingService()
    except (ValueError, OSError) as error:
        print(f"Ошибка запуска: {error}")
        return

    print("ValutaTrade Hub")
    print("Справка: help или help buy. Выход: exit.")

    while True:
        try:
            line = input("> ").strip()
            if not line:
                continue
            if line in ("exit", "quit"):
                print("До свидания!")
                break

            tokens = shlex.split(line)
            if not tokens:
                continue
            if tokens[0] == "help":
                tokens = tokens[1:] + ["--help"]

            args = parser.parse_args(tokens)
            _execute_command(args, service)
        except SystemExit:
            # argparse использует SystemExit для справки и ошибок аргументов.
            continue
        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания!")
            break
        except CurrencyNotFoundError as error:
            print(f"Ошибка: {error}")
            print("Поддерживаемые валюты: " + ", ".join(get_supported_codes()))
        except ApiRequestError as error:
            print(f"Ошибка: {error}")
            print("Повторите попытку позже или проверьте подключение к сети.")
        except (ValueError, OSError, InsufficientFundsError) as error:
            print(f"Ошибка: {error}")