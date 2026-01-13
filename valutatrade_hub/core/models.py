import hashlib
import secrets


class User:
    """Класс пользователя системы"""

    def __init__(
        self,
        user_id,
        username,
        hashed_password,
        salt,
        registration_date,
    ):
        """Инициализация пользователя"""
        self._user_id = user_id
        self.username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self):
        """Возвращает идентификатор пользователя"""
        return self._user_id

    @property
    def username(self):
        """Возвращает имя пользователя"""
        return self._username

    @property
    def hashed_password(self):
        """Возвращает хешированный пароль"""
        return self._hashed_password

    @property
    def salt(self):
        """Возвращает соль пользователя"""
        return self._salt

    @property
    def registration_date(self):
        """Возвращает дату регистрации"""
        return self._registration_date

    @username.setter
    def username(self, value):
        """Устанавливает имя пользователя с валидацией"""
        if not value or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value.strip()

    def get_user_info(self):
        """Возвращает информацию о пользователе (без пароля)"""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def change_password(self, new_password):
        """Изменяет пароль пользователя с хешированием нового пароля"""
        if len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        new_salt = secrets.token_hex(16)

        password_hash = hashlib.sha256(new_password + new_salt).hexdigest()

        self._hashed_password = password_hash
        self._salt = new_salt

    def verify_password(self, password):
        """Проверяет введённый пароль на совпадение"""
        password_hash = hashlib.sha256(password + self._salt).hexdigest()
        return password_hash == self._hashed_password


class Wallet:
    """Класс кошелька пользователя для одной конкретной валюты"""

    def __init__(self, currency_code, balance=0.0):
        """Инициализация кошелька"""
        self.currency_code = currency_code
        self.balance = balance

    @property
    def balance(self):
        """Возвращает текущий баланс"""
        return self._balance

    @balance.setter
    def balance(self, value):
        """Устанавливает баланс с валидацией"""
        if not isinstance(value, (int, float)):
            raise TypeError("Баланс должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(value)

    def deposit(self, amount):
        """Пополнение баланса"""
        if not isinstance(amount, (int, float)):
            raise TypeError("Сумма должна быть числом")
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительным числом")
        self._balance += float(amount)

    def withdraw(self, amount):
        """Снятие средств (если баланс позволяет)"""
        if not isinstance(amount, (int, float)):
            raise TypeError("Сумма должна быть числом")
        if amount <= 0:
            raise ValueError("Сумма снятия должна быть положительным числом")
        if amount > self._balance:
            raise ValueError("Недостаточно средств на балансе")
        self._balance -= float(amount)

    def get_balance_info(self):
        """Вывод информации о текущем балансе"""
        return {
            "currency_code": self.currency_code,
            "balance": self._balance,
        }


class Portfolio:
    """Класс управления всеми кошельками одного пользователя"""

    exchange_rates = {
        "USD": 1.0,
        "EUR": 1.1,
        "BTC": 50000.0,
        "ETH": 3000.0,
        "RUB": 0.011,
    }

    def __init__(self, user_id, user=None, wallets=None):
        """Инициализация портфеля"""
        self._user_id = user_id
        self._user = user
        self._wallets = wallets if wallets is not None else {}

    @property
    def user(self):
        """Возвращает объект пользователя (без возможности перезаписи)"""
        return self._user

    @property
    def wallets(self):
        """Возвращает копию словаря кошельков"""
        return self._wallets.copy()

    def add_currency(self, currency_code):
        """Добавляет новый кошелёк в портфель (если его ещё нет)"""
        if currency_code in self._wallets:
            raise ValueError(f"Валюта {currency_code} уже существует в портфеле")
        self._wallets[currency_code] = Wallet(currency_code, 0.0)

    def get_wallet(self, currency_code):
        """Возвращает объект Wallet по коду валюты"""
        if currency_code not in self._wallets:
            raise ValueError(f"Валюта {currency_code} не найдена в портфеле")
        return self._wallets[currency_code]

    def get_total_value(self, base_currency="USD"):
        """Возвращает общую стоимость всех валют пользователя в указанной базовой валюте"""
        if base_currency not in self.exchange_rates:
            raise ValueError(f"Курс для валюты {base_currency} не найден")

        base_rate = self.exchange_rates[base_currency]
        total_value = 0.0

        for currency_code, wallet in self._wallets.items():
            if currency_code not in self.exchange_rates:
                continue
            currency_rate = self.exchange_rates[currency_code]
            value_in_base = wallet.balance * (currency_rate / base_rate)
            total_value += value_in_base

        return total_value
