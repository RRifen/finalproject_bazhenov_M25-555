import hashlib
import json
import secrets
from datetime import datetime
from pathlib import Path

from valutatrade_hub.core.models import Portfolio, User

BASE_DIR = Path()
DATA_DIR = BASE_DIR / "data"
USERS_FILE = DATA_DIR / "users.json"
PORTFOLIOS_FILE = DATA_DIR / "portfolios.json"
RATES_FILE = DATA_DIR / "rates.json"

_current_user = None


def load_json_file(file_path):
    """Загружает данные из JSON файла"""
    if not file_path.exists():
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_file(file_path, data):
    """Сохраняет данные в JSON файл"""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


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

    users = load_json_file(USERS_FILE)
    users.append(user.to_dict())
    save_json_file(USERS_FILE, users)

    portfolios = load_json_file(PORTFOLIOS_FILE)
    portfolio_data = {
        "user_id": user_id,
        "wallets": {},
    }
    portfolios.append(portfolio_data)
    save_json_file(PORTFOLIOS_FILE, portfolios)

    return user_id


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


def show_portfolio(base_currency="USD"):
    """Отображает портфель текущего пользователя"""
    user = get_current_user()
    if user is None:
        raise ValueError("Сначала выполните login")
    
    portfolio = load_portfolio(user.user_id)
    if portfolio is None:
        raise ValueError("Портфель не найден")
    
    if base_currency not in Portfolio.exchange_rates:
        raise ValueError(f"Неизвестная базовая валюта '{base_currency}'")
    
    if not portfolio.wallets:
        return f"Портфель пользователя '{user.username}' (база: {base_currency}):\nПортфель пуст"  # noqa: E501
    
    base_rate = Portfolio.exchange_rates[base_currency]
    lines = [f"Портфель пользователя '{user.username}' (база: {base_currency}):"]
    
    total_value = 0.0
    for currency_code, wallet in sorted(portfolio.wallets.items()):
        balance = wallet.balance
        if currency_code in Portfolio.exchange_rates:
            currency_rate = Portfolio.exchange_rates[currency_code]
            value_in_base = balance * (currency_rate / base_rate)
            total_value += value_in_base
            if currency_code in ["BTC", "ETH"]:
                balance_str = f"{balance:.4f}"
            else:
                balance_str = f"{balance:.2f}"
            lines.append(f"- {currency_code}: {balance_str}  → "
                         f"{value_in_base:.2f} {base_currency}")
        else:
            balance_str = f"{balance:.2f}"
            lines.append(f"- {currency_code}: {balance_str}  → (курс не найден)")
    
    lines.append("-" * 40)
    lines.append(f"ИТОГО: {total_value:,.2f} {base_currency}")
    
    return "\n".join(lines)


def save_portfolio(portfolio):
    """Сохраняет портфель в JSON"""
    portfolios = load_json_file(PORTFOLIOS_FILE)
    portfolio_dict = portfolio.to_dict()
    
    for i, p in enumerate(portfolios):
        if p.get("user_id") == portfolio._user_id:
            portfolios[i] = portfolio_dict
            save_json_file(PORTFOLIOS_FILE, portfolios)
            return
    
    portfolios.append(portfolio_dict)
    save_json_file(PORTFOLIOS_FILE, portfolios)


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
    
    if currency not in Portfolio.exchange_rates:
        raise ValueError(f"Не удалось получить курс для {currency}→USD")
    
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
    
    currency_rate = Portfolio.exchange_rates[currency]
    base_rate = Portfolio.exchange_rates["USD"]
    cost_in_usd = amount * (currency_rate / base_rate)
    
    if currency in ["BTC", "ETH"]:
        amount_str = f"{amount:.4f}"
        old_balance_str = f"{old_balance:.4f}"
        new_balance_str = f"{new_balance:.4f}"
    else:
        amount_str = f"{amount:.2f}"
        old_balance_str = f"{old_balance:.2f}"
        new_balance_str = f"{new_balance:.2f}"
    
    result = [
        f"Покупка выполнена: {amount_str} {currency} "
        f"по курсу {currency_rate:.2f} USD/{currency}",
        "Изменения в портфеле:",
        f"- {currency}: было {old_balance_str} → стало {new_balance_str}",
        f"Оценочная стоимость покупки: {cost_in_usd:,.2f} USD"
    ]
    
    return "\n".join(result)


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
    
    if currency not in Portfolio.exchange_rates:
        raise ValueError(f"Не удалось получить курс для {currency}→USD")
    
    portfolio = load_portfolio(user.user_id)
    if portfolio is None:
        raise ValueError("Портфель не найден")
    
    if currency not in portfolio._wallets:
        raise ValueError(f"У вас нет кошелька '{currency}'. Добавьте валюту: "
                         "она создаётся автоматически при первой покупке.")
    
    wallet = portfolio.get_wallet(currency)
    old_balance = wallet.balance
    
    if amount > old_balance:
        if currency in ["BTC", "ETH"]:
            available_str = f"{old_balance:.4f}"
            required_str = f"{amount:.4f}"
        else:
            available_str = f"{old_balance:.2f}"
            required_str = f"{amount:.2f}"
        raise ValueError(f"Недостаточно средств: доступно {available_str} {currency}, "
                         f"требуется {required_str} {currency}")
    
    wallet.withdraw(amount)
    new_balance = wallet.balance
    
    save_portfolio(portfolio)
    
    currency_rate = Portfolio.exchange_rates[currency]
    base_rate = Portfolio.exchange_rates["USD"]
    revenue_in_usd = amount * (currency_rate / base_rate)
    
    if currency in ["BTC", "ETH"]:
        amount_str = f"{amount:.4f}"
        old_balance_str = f"{old_balance:.4f}"
        new_balance_str = f"{new_balance:.4f}"
    else:
        amount_str = f"{amount:.2f}"
        old_balance_str = f"{old_balance:.2f}"
        new_balance_str = f"{new_balance:.2f}"
    
    result = [
        f"Продажа выполнена: {amount_str} {currency} по курсу {currency_rate:.2f} "
        f"USD/{currency}",
        "Изменения в портфеле:",
        f"- {currency}: было {old_balance_str} → стало {new_balance_str}",
        f"Оценочная выручка: {revenue_in_usd:,.2f} USD"
    ]
    
    return "\n".join(result)


def load_rates_cache():
    """Загружает кеш курсов из JSON"""
    if not RATES_FILE.exists():
        return {}
    with open(RATES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_rates_cache(rates_data):
    """Сохраняет кеш курсов в JSON"""
    with open(RATES_FILE, "w", encoding="utf-8") as f:
        json.dump(rates_data, f, indent=2)


def get_rate_from_api(from_currency, to_currency):
    """Получает курс валюты из API (заглушка, использует Portfolio.exchange_rates)"""
    if (from_currency not in Portfolio.exchange_rates or 
        to_currency not in Portfolio.exchange_rates):
        return None
    
    from_rate = Portfolio.exchange_rates[from_currency]
    to_rate = Portfolio.exchange_rates[to_currency]
    
    rate = to_rate / from_rate
    return rate


def is_rate_fresh(timestamp_str, max_age_minutes=5):
    """Проверяет, свежий ли курс (моложе max_age_minutes минут)"""
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
        age = datetime.now() - timestamp
        return age.total_seconds() < max_age_minutes * 60
    except (ValueError, TypeError):
        return False


def get_rate(from_currency, to_currency):
    """Получает курс одной валюты к другой"""
    if not from_currency or not from_currency.strip():
        raise ValueError("Код исходной валюты не может быть пустым")
    
    if not to_currency or not to_currency.strip():
        raise ValueError("Код целевой валюты не может быть пустым")
    
    from_currency = from_currency.strip()

    if from_currency != from_currency.upper():
        raise ValueError("Код валюты должен состоять из прописных букв")

    to_currency = to_currency.strip()

    if to_currency != to_currency.upper():
        raise ValueError("Код валюты должен состоять из прописных букв")
    
    if from_currency == to_currency:
        return f"Курс {from_currency}→{to_currency}: 1.0 (одинаковые валюты)"
    
    cache_key = f"{from_currency}_{to_currency}"
    rates_cache = load_rates_cache()
    
    cached_rate = rates_cache.get(cache_key)
    
    if cached_rate and is_rate_fresh(cached_rate.get("timestamp")):
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
    
    rate = get_rate_from_api(from_currency, to_currency)
    
    if rate is None:
        raise ValueError(f"Курс {from_currency}→{to_currency} недоступен. "
                         "Повторите попытку позже.")
    
    timestamp = datetime.now()
    timestamp_str = timestamp.isoformat()
    timestamp_formatted = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    
    rates_cache[cache_key] = {
        "rate": rate,
        "timestamp": timestamp_str
    }
    save_rates_cache(rates_cache)
    
    reverse_rate = 1.0 / rate
    
    result = [
        f"Курс {from_currency}→{to_currency}: {rate:.8f} "
        f"(обновлено: {timestamp_formatted})",
        f"Обратный курс {to_currency}→{from_currency}: {reverse_rate:.2f}"
    ]
    return "\n".join(result)
