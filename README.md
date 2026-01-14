# ValutaTrade Hub

Платформа для отслеживания и симуляции торговли валютами (криптовалюты и фиатные валюты).

## Описание проекта

ValutaTrade Hub — это консольное приложение для управления виртуальным портфелем валют. Система позволяет:
- Регистрировать пользователей и управлять сессиями
- Покупать и продавать валюты
- Отслеживать портфель в различных базовых валютах
- Получать актуальные курсы валют из внешних API (CoinGecko, ExchangeRate-API)
- Ведет историю всех операций с логированием

## Структура проекта

```
finalproject_bazhenov_M25-555/
├── main.py                          # Точка входа в приложение
├── pyproject.toml                   # Конфигурация Poetry и проекта
├── poetry.lock                      # Зафиксированные версии зависимостей
├── Makefile                         # Команды для сборки и запуска
├── .env                             # Переменные окружения (создать вручную)
├── .gitignore                       # Игнорируемые файлы Git
│
├── data/                            # Данные приложения
│   ├── users.json                   # База данных пользователей
│   ├── portfolios.json              # Портфели пользователей
│   ├── rates.json                   # Кэш текущих курсов валют
│   └── exchange_rates.json          # История всех курсов
│
├── logs/                            # Логи приложения
│   └── actions.log                  # Лог всех операций (ротация до 5 файлов)
│
└── valutatrade_hub/                 # Основной пакет приложения
    ├── __init__.py
    │
    ├── cli/                         # Консольный интерфейс
    │   ├── __init__.py
    │   └── interface.py             # CLI команды и парсер аргументов
    │
    ├── core/                        # Ядро приложения
    │   ├── __init__.py
    │   ├── models.py                # Модели данных (User, Wallet, Portfolio)
    │   ├── currencies.py            # Иерархия валют (Currency, FiatCurrency, CryptoCurrency)
    │   ├── exceptions.py            # Кастомные исключения
    │   ├── usecases.py              # Бизнес-логика (регистрация, покупка, продажа, портфель)
    │   ├── settings.py              # Singleton для загрузки конфигурации
    │   ├── decorators.py            # Декоратор @log_action для логирования операций
    │   ├── logging_config.py        # Настройка системы логирования
    │   └── utils.py                 # Вспомогательные утилиты
    │
    └── parser_service/              # Сервис парсинга курсов валют
        ├── __init__.py
        ├── config.py                # Конфигурация Parser Service
        ├── api_clients.py           # Клиенты для внешних API (CoinGecko, ExchangeRate-API)
        ├── storage.py               # Операции с файлами (rates.json, exchange_rates.json)
        └── updater.py               # Координатор обновления курсов (RatesUpdater)
```

## Описание файлов

### Основные файлы

- **`main.py`** — точка входа в приложение, запускает интерактивный CLI
- **`pyproject.toml`** — конфигурация проекта, зависимости и настройки
- **`Makefile`** — команды для установки, сборки и запуска проекта

### Модуль `core/`

- **`models.py`** — классы данных:
  - `User` — пользователь системы с хешированием паролей
  - `Wallet` — кошелек для одной валюты
  - `Portfolio` — портфель пользователя (коллекция кошельков)

- **`currencies.py`** — иерархия валют:
  - `Currency` — абстрактный базовый класс
  - `FiatCurrency` — фиатные валюты (EUR, USD, RUB и т.д.)
  - `CryptoCurrency` — криптовалюты (BTC, ETH, SOL)
  - `get_currency()` — фабрика для получения валюты по коду

- **`exceptions.py`** — кастомные исключения:
  - `CurrencyNotFoundError` — валюта не найдена
  - `InsufficientFundsError` — недостаточно средств
  - `ApiRequestError` — ошибка запроса к внешнему API

- **`usecases.py`** — бизнес-логика:
  - `register_user()` — регистрация нового пользователя
  - `login_user()` — вход в систему
  - `buy_currency()` — покупка валюты
  - `sell_currency()` — продажа валюты
  - `show_portfolio()` — отображение портфеля
  - `get_rate()` — получение курса валюты
  - `get_rate_from_cache()` — получение курса из кэша

- **`settings.py`** — `SettingsLoader` (Singleton) для загрузки конфигурации из `pyproject.toml`

- **`decorators.py`** — декоратор `@log_action` для логирования операций (BUY, SELL, REGISTER, LOGIN)

- **`logging_config.py`** — настройка логирования с ротацией файлов

### Модуль `parser_service/`

- **`config.py`** — конфигурация Parser Service:
  - API ключи (из переменных окружения)
  - Эндпоинты API
  - Списки отслеживаемых валют
  - Пути к файлам данных

- **`api_clients.py`** — клиенты для внешних API:
  - `BaseApiClient` — абстрактный базовый класс
  - `CoinGeckoClient` — клиент для CoinGecko API (криптовалюты)
  - `ExchangeRateApiClient` — клиент для ExchangeRate-API (фиатные валюты)

- **`storage.py`** — операции с файлами:
  - `save_to_history()` — сохранение в `exchange_rates.json` (история)
  - `update_rates_cache()` — обновление `rates.json` (кэш)
  - `load_rates_cache()` — загрузка кэша курсов

- **`updater.py`** — класс `RatesUpdater`:
  - Координирует обновление курсов от всех клиентов
  - Объединяет данные и сохраняет в кэш и историю
  - Обеспечивает отказоустойчивость

### Модуль `cli/`

- **`interface.py`** — консольный интерфейс:
  - Парсер аргументов командной строки
  - Обработчики команд
  - Интерактивный режим работы

## Установка и настройка

### Установка зависимостей

```bash
# Установка зависимостей проекта
poetry install

# Или через Makefile
make install
```

### Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```bash
# .env
EXCHANGERATE_API_KEY=your_api_key_here
```

### Конфигурация

Основные настройки находятся в `pyproject.toml` в секции `[tool.valutatrade]`:

```toml
[tool.valutatrade]
data_dir = "data"
users_file = "users.json"
portfolios_file = "portfolios.json"
rates_file = "rates.json"
rates_ttl_seconds = 300          # TTL кэша курсов (5 минут)
default_base_currency = "USD"
log_path = "logs/actions.log"
```

## Запуск проекта

### Интерактивный режим

```bash
make project
```

### Доступные команды CLI

#### Регистрация и авторизация

```bash
# Регистрация нового пользователя
> register --username alice --password 1234

# Вход в систему
> login --username alice --password 1234
```

#### Управление портфелем

```bash
# Показать портфель (в USD по умолчанию)
> show-portfolio

# Показать портфель в другой валюте
> show-portfolio --base EUR

# Купить валюту
> buy --currency BTC --amount 0.05

# Продать валюту
> sell --currency BTC --amount 0.02
```

#### Работа с курсами

```bash
# Получить курс одной валюты к другой
> get-rate --from USD --to BTC

# Обновить курсы из внешних API
> update-rates

# Обновить курсы только из CoinGecko
> update-rates --source coingecko

# Обновить курсы только из ExchangeRate-API
> update-rates --source exchangerate

# Показать курсы из кэша
> show-rates

# Показать курс конкретной валюты
> show-rates --currency BTC

# Показать топ-3 самых дорогих криптовалют
> show-rates --top 3

# Показать все курсы относительно EUR
> show-rates --base EUR
```

#### Справка

```bash
# Показать справку по всем командам
> help

# Выход из приложения
> exit
# или
> quit
# или
> q
```

## Структура данных

### `data/users.json`

Список пользователей с хешированными паролями:

```json
[
  {
    "user_id": 1,
    "username": "alice",
    "hashed_password": "...",
    "salt": "...",
    "registration_date": "2025-01-01T00:00:00"
  }
]
```

### `data/portfolios.json`

Портфели пользователей:

```json
[
  {
    "user_id": 1,
    "wallets": {
      "USD": {"balance": 1000.0},
      "BTC": {"balance": 0.05}
    }
  }
]
```

### `data/rates.json`

Кэш текущих курсов валют:

```json
{
  "pairs": {
    "BTC_USD": {
      "rate": 59337.21,
      "updated_at": "2025-10-10T12:00:00Z",
      "source": "CoinGecko"
    },
    "EUR_USD": {
      "rate": 1.0786,
      "updated_at": "2025-10-10T12:00:00Z",
      "source": "ExchangeRate-API"
    }
  },
  "last_refresh": "2025-10-10T12:00:01Z"
}
```

### `data/exchange_rates.json`

История всех курсов (массив записей):

```json
[
  {
    "id": "BTC_USD_2025-10-10T12:00:00Z",
    "from_currency": "BTC",
    "to_currency": "USD",
    "rate": 59337.21,
    "timestamp": "2025-10-10T12:00:00Z",
    "source": "CoinGecko",
    "meta": {}
  }
]
```

## Логирование

Все операции логируются в `logs/actions.log` с ротацией файлов (максимум 10MB на файл, до 5 резервных копий).

Формат лога:
```
INFO 2025-10-10T12:05:22 action=BUY user='alice' currency='BTC' amount=0.05 rate=59300.00 base='USD' result=OK
```

## Разработка

### Линтинг

```bash
# Проверка кода
make lint

# Или напрямую
poetry run ruff check .
```

### Сборка пакета

```bash
# Сборка wheel и source distribution
make build

# Установка собранного пакета
make package-install
```

- **Decorator** — `@log_action` для аспектно-ориентированного логирования

## Зависимости

- `requests` — HTTP запросы к внешним API
- `prettytable` — форматирование таблиц (если используется)
- `python-dotenv` — загрузка переменных окружения из `.env`

## Asciinema
<a href="https://asciinema.org/a/9d5mtiq93J9g6dXa" target="_blank"><img src="https://asciinema.org/a/9d5mtiq93J9g6dXa.svg" /></a>
