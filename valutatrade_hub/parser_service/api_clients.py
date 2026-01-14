from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import config


class BaseApiClient(ABC):
    """Абстрактный базовый класс для клиентов API"""
    
    @abstractmethod
    def fetch_rates(self):
        """Получает курсы валют из API"""
        pass


class CoinGeckoClient(BaseApiClient):
    """Клиент для работы с CoinGecko API"""
    
    def fetch_rates(self):
        """Получает курсы криптовалют из CoinGecko API"""
        crypto_ids = [config.CRYPTO_ID_MAP.get(code) for code in config.CRYPTO_CURRENCIES]  # noqa: E501
        
        params = {
            "ids": ",".join(crypto_ids),
            "vs_currencies": config.BASE_CURRENCY.lower()
        }
        
        url = config.COINGECKO_URL
        
        try:
            response = requests.get(
                url,
                params=params,
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            
            result = {}
            for code in config.CRYPTO_CURRENCIES:
                crypto_id = config.CRYPTO_ID_MAP.get(code)
                
                if crypto_id and crypto_id in data:
                    rate = data[crypto_id].get(config.BASE_CURRENCY.lower())
                    if rate:
                        pair_key = f"{code}_{config.BASE_CURRENCY}"
                        result[pair_key] = float(rate)
            
            return result
            
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"Ошибка при запросе к CoinGecko: {e}")
        except (ValueError, KeyError, TypeError) as e:
            raise ApiRequestError(f"Ошибка при парсинге ответа CoinGecko: {e}")


class ExchangeRateApiClient(BaseApiClient):
    """Клиент для работы с ExchangeRate-API"""
    
    def fetch_rates(self):
        """ Получает курсы фиатных валют из ExchangeRate-API"""
        if not config.EXCHANGERATE_API_KEY:
            raise ApiRequestError("EXCHANGERATE_API_KEY не установлен. Установите переменную окружения.")  # noqa: E501
        
        url = f"{config.EXCHANGERATE_API_URL}/{config.EXCHANGERATE_API_KEY}/latest/{config.BASE_CURRENCY}"  # noqa: E501
        try:
            response = requests.get(
                url,
                timeout=config.REQUEST_TIMEOUT,
            )
            
            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    if "error-type" in error_data:
                        error_msg = error_data["error-type"]
                except (ValueError, KeyError):
                    pass
                raise ApiRequestError(f"Ошибка ExchangeRate-API: {error_msg}")
            
            response.raise_for_status()
            data = response.json()
            if data.get("result") != "success":
                error_type = data.get("error-type", "unknown")
                raise ApiRequestError(f"ExchangeRate-API вернул ошибку: {error_type}")
            
            rates = data.get("conversion_rates", {})
            result = {}
            
            for code in config.FIAT_CURRENCIES:
                if code in rates:
                    rate = rates[code]
                    pair_key = f"{code}_{config.BASE_CURRENCY}"
                    result[pair_key] = float(rate)
            
            return result
            
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"Ошибка при запросе к ExchangeRate-API: {e}")
        except (ValueError, KeyError, TypeError) as e:
            raise ApiRequestError(f"Ошибка при парсинге ответа ExchangeRate-API: {e}")
