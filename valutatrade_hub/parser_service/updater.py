from datetime import datetime

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.logging_config import get_logger
from valutatrade_hub.parser_service.storage import save_to_history, update_rates_cache

logger = get_logger("parser_service")


class RatesUpdater:
    """Класс для координации процесса обновления курсов валют"""
    
    def __init__(self, api_clients):
        """Инициализация RatesUpdater"""
        self.api_clients = api_clients
    
    def run_update(self):
        """Выполняет обновление курсов валют от всех клиентов"""
        logger.info("Запуск обновления курсов валют")
        
        timestamp = datetime.utcnow().isoformat() + "Z"
        results = {
            "success": [],
            "failed": [],
            "total_pairs": 0
        }
        
        rates_with_source = {}
        
        for client in self.api_clients:
            client_name = client.__class__.__name__
            logger.info(f"Запрос курсов от {client_name}")
            
            source = "Unknown"
            if "CoinGecko" in client_name:
                source = "CoinGecko"
            elif "ExchangeRate" in client_name:
                source = "ExchangeRate-API"
            
            try:
                rates = client.fetch_rates()
                
                if rates:
                    for pair_key, rate in rates.items():
                        rates_with_source[pair_key] = {
                            "rate": rate,
                            "source": source
                        }
                    
                    results["success"].append({
                        "client": client_name,
                        "pairs_count": len(rates)
                    })
                    logger.info(f"{client_name}: успешно получено {len(rates)} курсов")
                else:
                    logger.warning(f"{client_name}: не получено ни одного курса")
                    
            except ApiRequestError as e:
                results["failed"].append({
                    "client": client_name,
                    "error": str(e)
                })
                logger.error(f"{client_name}: ошибка - {e}")
            except Exception as e:
                results["failed"].append({
                    "client": client_name,
                    "error": f"Неожиданная ошибка: {e}"
                })
                logger.error(f"{client_name}: неожиданная ошибка - {e}")
        
        if not rates_with_source:
            logger.warning("Не получено ни одного курса от всех клиентов")
            return {
                "pairs": {},
                "last_refresh": timestamp,
                "results": results
            }
        
        logger.info(f"Всего получено {len(rates_with_source)} уникальных пар валют")
        
        pairs_data = {}
        for pair_key, rate_info in rates_with_source.items():
            parts = pair_key.split("_")
            if len(parts) >= 2:
                from_currency = parts[0]
                to_currency = "_".join(parts[1:])
                rate = rate_info["rate"]
                source = rate_info["source"]
                
                pairs_data[pair_key] = {
                    "rate": rate,
                    "updated_at": timestamp,
                    "source": source
                }
                
                rate_data = {
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "rate": rate,
                    "timestamp": timestamp,
                    "source": source,
                    "meta": {}
                }
                
                try:
                    save_to_history(rate_data)
                except ValueError as e:
                    logger.warning(f"Не удалось сохранить в историю {pair_key}: {e}")
        
        rates_data = {
            "pairs": pairs_data,
            "last_refresh": timestamp
        }
        
        try:
            update_rates_cache(rates_data)
            results["total_pairs"] = len(pairs_data)
            logger.info(f"Кэш курсов обновлен: {len(pairs_data)} пар")
        except ValueError as e:
            logger.error(f"Ошибка при обновлении кэша: {e}")
            raise
        
        logger.info("Обновление курсов завершено успешно")
        
        return {
            "pairs": pairs_data,
            "last_refresh": timestamp,
            "results": results
        }
