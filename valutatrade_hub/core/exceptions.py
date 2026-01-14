class CurrencyNotFoundError(Exception):
    """Исключение, возникающее при попытке получить неизвестную валюту"""
    
    def __init__(self, code):
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class InsufficientFundsError(Exception):
    """Исключение, возникающее при недостатке средств"""
    
    def __init__(self, available, required, code):
        self.available = available
        self.required = required
        self.code = code
        super().__init__(f"Недостаточно средств: доступно {available} {code}, требуется {required} {code}")  # noqa: E501


class ApiRequestError(Exception):
    """Исключение, возникающее при сбое внешнего API"""
    
    def __init__(self, reason):
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")
