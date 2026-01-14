import re
from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError


class Currency(ABC):

    def __init__(self, name, code):
        """Инициализация валюты"""
        if not name or not name.strip():
            raise ValueError("Имя валюты не может быть пустым")
        
        if not code or not code.strip():
            raise ValueError("Код валюты не может быть пустым")
        
        code = code.strip()
        
        if not re.match(r'^[A-Z0-9]{2,5}$', code):
            raise ValueError("Код валюты должен быть в верхнем регистре, 2-5 символов, без пробелов")  # noqa: E501
        
        self.name = name.strip()
        self.code = code

    @abstractmethod
    def get_display_info(self):
        """Возвращает строковое представление валюты для UI/логов"""
        pass


class FiatCurrency(Currency):

    def __init__(self, name, code, issuing_country):
        """Инициализация фиатной валюты"""
        super().__init__(name, code)
        if not issuing_country or not issuing_country.strip():
            raise ValueError("Страна эмиссии не может быть пустой")
        self.issuing_country = issuing_country.strip()

    def get_display_info(self):
        """Возвращает строковое представление фиатной валюты"""
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):

    def __init__(self, name, code, algorithm, market_cap):
        """Инициализация криптовалюты"""
        super().__init__(name, code)
        if not algorithm or not algorithm.strip():
            raise ValueError("Алгоритм не может быть пустым")
        if market_cap < 0:
            raise ValueError("Рыночная капитализация не может быть отрицательной")
        self.algorithm = algorithm.strip()
        self.market_cap = float(market_cap)

    def get_display_info(self) -> str:
        """Возвращает строковое представление криптовалюты"""
        return f"[CRYPTO] {self.code} — {self.name} (Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})"  # noqa: E501


_currency_registry = {}


def register_currency(currency):
    """Регистрирует валюту в реестре"""
    _currency_registry[currency.code] = currency


def get_currency(code):
    """Получает валюту по коду (фабричный метод)"""
    if not code or not code.strip():
        raise ValueError("Код валюты не может быть пустым")
    
    code = code.strip()
    
    if code not in _currency_registry:
        raise CurrencyNotFoundError(code)
    
    return _currency_registry[code]


def initialize_default_currencies():
    """Инициализирует реестр валют значениями по умолчанию"""
    register_currency(FiatCurrency("US Dollar", "USD", "United States"))
    register_currency(FiatCurrency("Euro", "EUR", "Eurozone"))
    register_currency(FiatCurrency("Russian Ruble", "RUB", "Russia"))
    register_currency(CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12))
    register_currency(CryptoCurrency("Ethereum", "ETH", "Ethash", 3.5e11))


initialize_default_currencies()
