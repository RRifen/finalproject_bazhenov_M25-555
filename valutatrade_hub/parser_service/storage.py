import json
import tempfile
from pathlib import Path

from valutatrade_hub.parser_service.config import config


def generate_rate_id(from_currency, to_currency, timestamp):
    """Генерирует уникальный идентификатор для записи курса"""
    return f"{from_currency}_{to_currency}_{timestamp}Z"


def save_to_history(rate_data):
    """Сохраняет запись курса в exchange_rates.json (исторические данные)"""
    history_file = Path(config.HISTORY_FILE_PATH)
    history_file.parent.mkdir(parents=True, exist_ok=True)
    
    rate_id = generate_rate_id(
        rate_data["from_currency"],
        rate_data["to_currency"],
        rate_data["timestamp"]
    )
    
    record = {
        "id": rate_id,
        "from_currency": rate_data["from_currency"],
        "to_currency": rate_data["to_currency"],
        "rate": rate_data["rate"],
        "timestamp": rate_data["timestamp"],
        "source": rate_data["source"],
        "meta": rate_data.get("meta", {})
    }
    
    try:
        if history_file.exists():
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        else:
            history = []
        
        history.append(record)
        
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8", dir=history_file.parent) as tmp:  # noqa: E501
            json.dump(history, tmp, indent=2, ensure_ascii=False)
            tmp_path = tmp.name
        
        Path(tmp_path).replace(history_file)
        
    except (json.JSONDecodeError, IOError, OSError) as e:
        raise ValueError(f"Ошибка при сохранении в историю: {e}")


def update_rates_cache(rates_data):
    """Обновляет rates.json (текущий кэш курсов)"""
    rates_file = Path(config.RATES_FILE_PATH)
    rates_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8", dir=rates_file.parent) as tmp:  # noqa: E501
            json.dump(rates_data, tmp, indent=2, ensure_ascii=False)
            tmp_path = tmp.name
        
        Path(tmp_path).replace(rates_file)
        
    except (IOError, OSError) as e:
        raise ValueError(f"Ошибка при обновлении кэша курсов: {e}")


def load_rates_cache():
    """ Загружает rates.json (текущий кэш курсов)"""
    rates_file = Path(config.RATES_FILE_PATH)
    
    try:
        if not rates_file.exists():
            return {"pairs": {}, "last_refresh": None}
        
        with open(rates_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        raise ValueError(f"Ошибка при чтении кэша курсов: {e}")
