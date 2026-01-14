import hashlib
import json
import secrets
from datetime import datetime
from pathlib import Path

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.decorators import log_action
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.core.settings import settings

DATA_DIR = Path(settings.get("data_dir", "data"))
USERS_FILE = Path(settings.get("users_file", DATA_DIR / "users.json"))
PORTFOLIOS_FILE = Path(settings.get("portfolios_file", DATA_DIR / "portfolios.json"))
RATES_FILE = Path(settings.get("rates_file", DATA_DIR / "rates.json"))
RATES_TTL_SECONDS = settings.get("rates_ttl_seconds", 300)
DEFAULT_BASE_CURRENCY = settings.get("default_base_currency", "USD")

_current_user = None


def get_rate_from_cache(currency_code, base_currency="USD"):
    """Получает курс валюты из кеша"""
    try:
        from valutatrade_hub.parser_service.storage import load_rates_cache
        cache = load_rates_cache()
        pairs = cache.get("pairs", {})
        
        if currency_code == base_currency:
            return 1.0
        
        pair_key = f"{currency_code}_{base_currency}"
        if pair_key in pairs:
            return pairs[pair_key]["rate"]
        
        if base_currency == "USD":
            return None
        
        usd_pair = f"{currency_code}_USD"
        base_usd_pair = f"{base_currency}_USD"
        
        if usd_pair in pairs and base_usd_pair in pairs:
            currency_rate = pairs[usd_pair]["rate"]
            base_rate = pairs[base_usd_pair]["rate"]
            return currency_rate / base_rate
        
        return None
    except (ValueError, ImportError):
        return None


def load_json_file(file_path):
    """Загружает данные из JSON файла (безопасная операция)"""
    try:
        if not file_path.exists():
            return []
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        raise ValueError(f"Ошибка при чтении файла {file_path}: {e}")


def save_json_file(file_path, data):
    """Сохраняет данные в JSON файл (безопасная операция)"""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except (IOError, OSError) as e:
        raise ValueError(f"Ошибка при записи файла {file_path}: {e}")


def get_next_user_id():
    """Получает следующий доступный user_id"""
    users = load_json_file(USERS_FILE)
    if not users:
        return 1
    max_id = max(user.get("user_id") for user in users)
    return max_id + 1


def is_username_taken(username):
    """Проверяет, занято ли имя пользователя"""
    users = load_json_file(USERS_FILE)
    return any(user.get("username") == username for user in users)


@log_action("REGISTER")
def register_user(username, password):
    """Регистрирует нового пользователя"""
    if not username or not username.strip():
        raise ValueError("Имя пользователя не может быть пустым")

    if len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")

    if is_username_taken(username):
        raise ValueError(f"Имя пользователя '{username}' уже занято")

    user_id = get_next_user_id()

    salt = secrets.token_hex(16)
    hashed_password = hashlib.sha256((password + salt).encode()).hexdigest()

    registration_date = datetime.now()
    user = User(
        user_id=user_id,
        username=username.strip(),
        hashed_password=hashed_password,
        salt=salt,
        registration_date=registration_date,
    )

    try:
        users = load_json_file(USERS_FILE)
        users.append(user.to_dict())
        save_json_file(USERS_FILE, users)
    except ValueError as e:
        raise ValueError(f"Ошибка при сохранении пользователя: {e}")

    try:
        portfolios = load_json_file(PORTFOLIOS_FILE)
        portfolio_data = {
            "user_id": user_id,
            "wallets": {},
        }
        portfolios.append(portfolio_data)
        save_json_file(PORTFOLIOS_FILE, portfolios)
    except ValueError as e:
        raise ValueError(f"Ошибка при создании портфеля: {e}")

    return user_id


@log_action("LOGIN")
def login_user(username, password):
    """Вход пользователя в систему"""
    global _current_user
    if not username or not username.strip():
        raise ValueError("Имя пользователя не может быть пустым")

    users = load_json_file(USERS_FILE)
    user_data = next((u for u in users if u.get("username") == username.strip()), None)

    if user_data is None:
        raise ValueError(f"Пользователь '{username}' не найден")

    user = User.from_dict(user_data)

    if not user.verify_password(password):
        raise ValueError("Неверный пароль")

    _current_user = user
    return user


def get_current_user():
    """Возвращает текущего залогиненного пользователя"""
    return _current_user


def load_portfolio(user_id):
    """Загружает портфель пользователя из JSON"""
    portfolios = load_json_file(PORTFOLIOS_FILE)
    portfolio_data = next((p for p in portfolios if p.get("user_id") == user_id), None)
    
    if portfolio_data is None:
        return None
    
    user = get_current_user()
    return Portfolio.from_dict(portfolio_data, user=user)


def show_portfolio(base_currency=None):
    """Отображает портфель текущего пользователя"""
    if base_currency is None:
        base_currency = DEFAULT_BASE_CURRENCY
    """Отображает портфель текущего пользователя"""
    user = get_current_user()
    if user is None:
        raise ValueError("Сначала выполните login")
    
    portfolio = load_portfolio(user.user_id)
    if portfolio is None:
        raise ValueError("Портфель не найден")
    
    if not portfolio.wallets:
        return f"Портфель пользователя '{user.username}' (база: {base_currency}):\nПортфель пуст"  # noqa: E501
    
    lines = [f"Портфель пользователя '{user.username}' (база: {base_currency}):"]
    
    total_value = 0.0
    for currency_code, wallet in sorted(portfolio.wallets.items()):
        balance = wallet.balance
        currency_rate_usd = get_rate_from_cache(currency_code, "USD")
        if currency_rate_usd is not None:
            if base_currency == "USD":
                value_in_base = balance * currency_rate_usd
            else:
                base_rate_usd = get_rate_from_cache(base_currency, "USD")
                if base_rate_usd is not None:
                    currency_rate_base = currency_rate_usd / base_rate_usd
                    value_in_base = balance * currency_rate_base
                else:
                    value_in_base = None
            if value_in_base is not None:
                total_value += value_in_base
                if currency_code in ["BTC", "ETH"]:
                    balance_str = f"{balance:.4f}"
                else:
                    balance_str = f"{balance:.2f}"
                lines.append(f"- {currency_code}: {balance_str}  → "
                             f"{value_in_base:.2f} {base_currency}")
            else:
                if currency_code in ["BTC", "ETH"]:
                    balance_str = f"{balance:.4f}"
                else:
                    balance_str = f"{balance:.2f}"
                lines.append(f"- {currency_code}: {balance_str}  → (курс не найден)")
        else:
            if currency_code in ["BTC", "ETH"]:
                balance_str = f"{balance:.4f}"
            else:
                balance_str = f"{balance:.2f}"
            lines.append(f"- {currency_code}: {balance_str}  → (курс не найден)")
    
    lines.append("-" * 40)
    lines.append(f"ИТОГО: {total_value:,.2f} {base_currency}")
    
    return "\n".join(lines)


def save_portfolio(portfolio):
    """Сохраняет портфель в JSON (безопасная операция)"""
    try:
        portfolios = load_json_file(PORTFOLIOS_FILE)
        portfolio_dict = portfolio.to_dict()
        
        for i, p in enumerate(portfolios):
            if p.get("user_id") == portfolio._user_id:
                portfolios[i] = portfolio_dict
                save_json_file(PORTFOLIOS_FILE, portfolios)
                return
        
        portfolios.append(portfolio_dict)
        save_json_file(PORTFOLIOS_FILE, portfolios)
    except ValueError as e:
        raise ValueError(f"Ошибка при сохранении портфеля: {e}")


@log_action("BUY", verbose=True)
def buy_currency(currency, amount):
    """Покупает валюту"""
    user = get_current_user()
    if user is None:
        raise ValueError("Сначала выполните login")
    
    if not currency or not currency.strip():
        raise ValueError("Код валюты не может быть пустым")
    
    currency = currency.strip()

    if currency != currency.upper():
        raise ValueError("Код валюты должен состоять из прописных букв")
    
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        raise ValueError("'amount' должен быть положительным числом")
    
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    
    try:
        get_currency(currency)
    except CurrencyNotFoundError:
        raise
    
    portfolio = load_portfolio(user.user_id)
    if portfolio is None:
        raise ValueError("Портфель не найден")
    
    if currency not in portfolio._wallets:
        portfolio.add_currency(currency)
    
    wallet = portfolio.get_wallet(currency)
    old_balance = wallet.balance
    
    wallet.deposit(amount)
    new_balance = wallet.balance
    
    save_portfolio(portfolio)
    
    currency_rate = get_rate_from_cache(currency, "USD")
    if currency_rate is not None:
        cost_in_usd = amount * currency_rate
    else:
        cost_in_usd = None
    
    if currency in ["BTC", "ETH"]:
        amount_str = f"{amount:.4f}"
        old_balance_str = f"{old_balance:.4f}"
        new_balance_str = f"{new_balance:.4f}"
    else:
        amount_str = f"{amount:.2f}"
        old_balance_str = f"{old_balance:.2f}"
        new_balance_str = f"{new_balance:.2f}"
    
    result = [f"Покупка выполнена: {amount_str} {currency}"]
    
    if currency_rate:
        result.append(f"по курсу {currency_rate:.2f} USD/{currency}")
    
    result.extend([
        "Изменения в портфеле:",
        f"- {currency}: было {old_balance_str} → стало {new_balance_str}"
    ])
    
    if cost_in_usd is not None:
        result.append(f"Оценочная стоимость покупки: {cost_in_usd:,.2f} USD")
    
    return "\n".join(result)


@log_action("SELL", verbose=True)
def sell_currency(currency, amount):
    """Продаёт валюту"""
    user = get_current_user()
    if user is None:
        raise ValueError("Сначала выполните login")
    
    if not currency or not currency.strip():
        raise ValueError("Код валюты не может быть пустым")
    
    currency = currency.strip()

    if currency != currency.upper():
        raise ValueError("Код валюты должен состоять из прописных букв")
    
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        raise ValueError("'amount' должен быть положительным числом")
    
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    
    try:
        get_currency(currency)
    except CurrencyNotFoundError:
        raise
    
    portfolio = load_portfolio(user.user_id)
    if portfolio is None:
        raise ValueError("Портфель не найден")
    
    if currency not in portfolio._wallets:
        raise ValueError(f"У вас нет кошелька '{currency}'. Добавьте валюту: "
                         "она создаётся автоматически при первой покупке.")
    
    wallet = portfolio.get_wallet(currency)
    old_balance = wallet.balance
    
    try:
        wallet.withdraw(amount)
    except InsufficientFundsError:
        raise
    new_balance = wallet.balance
    
    save_portfolio(portfolio)
    
    currency_rate = get_rate_from_cache(currency, "USD")
    if currency_rate is not None:
        revenue_in_usd = amount * currency_rate
    else:
        revenue_in_usd = None
    
    if currency in ["BTC", "ETH"]:
        amount_str = f"{amount:.4f}"
        old_balance_str = f"{old_balance:.4f}"
        new_balance_str = f"{new_balance:.4f}"
    else:
        amount_str = f"{amount:.2f}"
        old_balance_str = f"{old_balance:.2f}"
        new_balance_str = f"{new_balance:.2f}"
    
    result = [f"Продажа выполнена: {amount_str} {currency}"]
    
    if currency_rate:
        result.append(f"по курсу {currency_rate:.2f} USD/{currency}")
    
    result.extend([
        "Изменения в портфеле:",
        f"- {currency}: было {old_balance_str} → стало {new_balance_str}"
    ])
    
    if revenue_in_usd is not None:
        result.append(f"Оценочная выручка: {revenue_in_usd:,.2f} USD")
    
    return "\n".join(result)


def load_rates_cache():
    """Загружает кеш курсов из JSON (безопасная операция)"""
    try:
        if not RATES_FILE.exists():
            return {}
        with open(RATES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        raise ValueError(f"Ошибка при чтении кеша курсов: {e}")


def save_rates_cache(rates_data):
    """Сохраняет кеш курсов в JSON (безопасная операция)"""
    try:
        RATES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(RATES_FILE, "w", encoding="utf-8") as f:
            json.dump(rates_data, f, indent=2)
    except (IOError, OSError) as e:
        raise ValueError(f"Ошибка при сохранении кеша курсов: {e}")


def get_rate_from_api(from_currency, to_currency):
    """Получает курс валюты из API (использует кеш rates.json)"""
    try:
        get_currency(from_currency)
        get_currency(to_currency)
    except CurrencyNotFoundError as e:
        raise ApiRequestError(f"Валюта '{e.code}' не поддерживается")
    
    from_rate = get_rate_from_cache(from_currency, "USD")
    to_rate = get_rate_from_cache(to_currency, "USD")
    
    if from_rate is None or to_rate is None:
        raise ApiRequestError(f"Курс {from_currency}→{to_currency} недоступен в кеше")
    
    if to_currency == "USD":
        return from_rate
    elif from_currency == "USD":
        return 1.0 / to_rate
    else:
        return to_rate / from_rate


def is_rate_fresh(timestamp_str, max_age_seconds=None):
    """Проверяет, свежий ли курс (моложе max_age_seconds секунд)"""
    if max_age_seconds is None:
        max_age_seconds = RATES_TTL_SECONDS
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
        age = datetime.now() - timestamp
        return age.total_seconds() < max_age_seconds
    except (ValueError, TypeError):
        return False


def get_rate(from_currency, to_currency):
    """Получает курс одной валюты к другой"""
    if not from_currency or not from_currency.strip():
        raise ValueError("Код исходной валюты не может быть пустым")
    
    if not to_currency or not to_currency.strip():
        raise ValueError("Код целевой валюты не может быть пустым")
    
    from_currency = from_currency.strip()
    to_currency = to_currency.strip()

    if from_currency != from_currency.upper():
        raise ValueError("Код исходной валюты должен состоять из прописных букв")
    
    if to_currency != to_currency.upper():
        raise ValueError("Код целевой валюты должен состоять из прописных букв")
    
    try:
        get_currency(from_currency)
        get_currency(to_currency)
    except CurrencyNotFoundError:
        raise
    
    if from_currency == to_currency:
        return f"Курс {from_currency}→{to_currency}: 1.0 (одинаковые валюты)"
    
    cache_key = f"{from_currency}_{to_currency}"
    
    try:
        rates_cache = load_rates_cache()
    except ValueError:
        rates_cache = {}
    
    cached_rate = rates_cache.get(cache_key)
    
    if cached_rate and is_rate_fresh(cached_rate.get("timestamp"), RATES_TTL_SECONDS):
        rate = cached_rate.get("rate")
        timestamp_str = cached_rate.get("timestamp")
        timestamp = datetime.fromisoformat(timestamp_str)
        timestamp_formatted = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        reverse_rate = 1.0 / rate
        
        result = [
            f"Курс {from_currency}→{to_currency}: {rate:.8f} "
            f"(обновлено: {timestamp_formatted})",
            f"Обратный курс {to_currency}→{from_currency}: {reverse_rate:.2f}"
        ]
        return "\n".join(result)
    
    try:
        rate = get_rate_from_api(from_currency, to_currency)
    except ApiRequestError:
        raise
    
    timestamp = datetime.now()
    timestamp_str = timestamp.isoformat()
    timestamp_formatted = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        rates_cache[cache_key] = {
            "rate": rate,
            "timestamp": timestamp_str
        }
        save_rates_cache(rates_cache)
    except ValueError:
        pass
    
    reverse_rate = 1.0 / rate
    
    result = [
        f"Курс {from_currency}→{to_currency}: {rate:.8f} "
        f"(обновлено: {timestamp_formatted})",
        f"Обратный курс {to_currency}→{from_currency}: {reverse_rate:.2f}"
    ]
    return "\n".join(result)
