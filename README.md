# ValutaTrade Hub

Учебное консольное приложение для торговли валютами. Позволяет
зарегистрироваться, покупать и продавать валюту, просматривать портфель
и получать курсы из внешних API.

Поддерживаемые валюты: USD, EUR, GBP, RUB, BTC, ETH, SOL.

## Модель торговли

Используется упрощённая модель торговли:

- При регистрации создаётся пустой портфель.
- Покупка увеличивает количество выбранной валюты и создаёт кошелёк,
  если его ещё нет.
- Продажа уменьшает количество валюты при достаточном остатке.
- Доллары при покупке не списываются, а при продаже не начисляются.
- Стоимость покупки и выручка в USD показываются как оценочные значения.

Баланс кошелька не может быть отрицательным. Сумма операции должна быть
положительным конечным числом.

## Установка на Windows

Необходимы Git, Python с командой `py` и доступ в интернет.
Проект использует Python 3.12.

В PowerShell:

```powershell
git clone https://github.com/robertluy/finalproject_lukyanovich_M26-555.git
cd finalproject_lukyanovich_M26-555

py -m pip install uv
py -m uv sync --frozen
```

## Настройка API

Источники курсов:

- [CoinGecko](https://www.coingecko.com/) - BTC, ETH и SOL.
  Используется публичный API без ключа.
- [ExchangeRate-API](https://www.exchangerate-api.com/) - EUR, GBP и RUB.
  Требуется API-ключ из личного кабинета сервиса.

Перед запуском приложения введи ключ в PowerShell:

```powershell
$exchangeKey = Read-Host "API-ключ ExchangeRate-API" -AsSecureString
$env:EXCHANGERATE_API_KEY = ([System.Net.NetworkCredential]::new("", $exchangeKey).Password).Trim()
Remove-Variable exchangeKey
```

Вводится только ключ, без URL и кавычек. Ввод скрыт.
Ключ хранится в переменной окружения текущего терминала.
После закрытия терминала его потребуется ввести снова.

## Запуск

```powershell
py -m uv run valutatrade
```

Команды ниже вводятся внутри приложения, после приглашения `>`.

Регистрация и вход:

```text
register --username student --password 1234
login --username student --password 1234
```

Имя пользователя должно быть уникальным, пароль - не короче четырёх
символов. Пароли сохраняются в виде SHA-256-хешей с индивидуальной солью.

Обновление курсов и торговля:

```text
update-rates
buy --currency EUR --amount 100
buy --currency BTC --amount 0.005
sell --currency EUR --amount 20
show-portfolio
show-portfolio --base EUR
get-rate --from EUR --to USD
get-rate --from BTC --to EUR
```

Просмотр курсов:

```text
show-rates
show-rates --currency RUB
show-rates --top 2
show-rates --base EUR
```

Параметр `--top` выбирает самые дорогие криптовалюты по цене одной единицы
в указанной базовой валюте.

Обновление отдельного источника:

```text
update-rates --source coingecko
update-rates --source exchangerate
```

Справка и выход:

```text
help
help buy
help update-rates
exit
```

## Кеш и история курсов

Данные сохраняются в каталоге `data/`:

- `users.json` - пользователи, хеши паролей и соли.
- `portfolios.json` - кошельки и остатки пользователей.
- `rates.json` - последние курсы, источники и время обновления каждой пары.
- `exchange_rates.json` - история полученных курсов.

В `rates.json` курсы находятся в словаре `pairs`.
Для каждой пары сохраняются `rate`, `updated_at` и `source`.
Поле `last_refresh` содержит время последнего обновления кеша.

Базовая валюта загрузки - USD. Доступны прямые и обратные курсы,
пересчёт других пар через USD.

Срок действия курса - 60 секунд. Он проверяется отдельно для каждой
необходимой пары. Если курс устарел, программа предлагает выполнить
`update-rates`. Сделка по устаревшему курсу не выполняется.

Время в кеше обозначает момент получения данных приложением.
Частота изменения самих котировок зависит от источника.

Свежая запись заменяет старую в кеше. История дополняется без дубликатов
по идентификатору пары и времени. Каждый JSON-файл записывается через
временный файл с последующей заменой.

При недоступности одного API результаты второго сохраняются.
Если недоступны оба источника, существующие данные остаются на месте.

## Периодическое обновление

Планировщик запускается отдельно из PowerShell:

```powershell
py -m uv run python -m valutatrade_hub.parser_service.scheduler
```

Интервал по умолчанию - 60 секунд после завершения предыдущего обновления.
Первое обновление выполняется сразу. Остановка - Ctrl+C.

Интервал и источник можно указать явно:

```powershell
py -m uv run python -m valutatrade_hub.parser_service.scheduler --interval 120 --source exchangerate
```

## Настройки и логи

Основные настройки находятся в секции `[tool.valutatrade]`
файла `pyproject.toml`:

- `rates_ttl_seconds` - срок действия курса.
- `rates_update_interval_seconds` - интервал планировщика.
- `default_base_currency` - базовая валюта отображения.
- `data_dir` и `logs_dir` - каталоги данных и логов.

Адреса API, списки валют, таймаут запросов и пути файлов парсера
определены в `parser_service/config.py`.

В `logs/actions.log` записываются покупки и продажи, включая ошибки.
В `logs/parser.log` записываются этапы обновления курсов.
Для логов настроена ротация.

## Структура проекта

- `valutatrade_hub/core/` - модели, валюты, исключения и бизнес-логика.
- `valutatrade_hub/infra/` - настройки и работа с JSON-файлами.
- `valutatrade_hub/parser_service/` - API-клиенты, обновление, хранение
  курсов и планировщик.
- `valutatrade_hub/cli/` - обработка команд и форматирование вывода.
- `valutatrade_hub/decorators.py` - декоратор логирования операций.
- `valutatrade_hub/logging_config.py` - настройка логов.
- `data/` - данные пользователей, портфелей и курсов.

## Проверка и сборка

Проверка стиля:

```powershell
py -m uv run ruff check .
```

Сборка пакета:

```powershell
py -m uv build
```

Собранные пакеты находятся в каталоге `dist/`.

## Демонстрация

[![asciicast](https://asciinema.org/a/EwhF5n7GePSQUSee.svg)](https://asciinema.org/a/EwhF5n7GePSQUSee)

Запись показывает регистрацию, вход, покупку и продажу валют,
просмотр портфеля и курсов, обновление данных и обработку ошибок.