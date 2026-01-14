import functools
from datetime import datetime

from valutatrade_hub.core.logging_config import get_logger
from valutatrade_hub.core.usecases import get_current_user

logger = get_logger("actions")


def log_action(action_name, verbose=False):
    """Декоратор для логирования доменных операций"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            timestamp = datetime.now().isoformat()
            user = get_current_user()
            username = user.username if user else None
            user_id = user.user_id if user else None
            
            log_data = {
                "timestamp": timestamp,
                "action": action_name,
                "username": username,
                "user_id": user_id,
            }
            
            try:
                if action_name in ("BUY", "SELL"):
                    currency = kwargs.get("currency") or (args[0] if args else None)
                    amount = kwargs.get("amount") or (args[1] if len(args) > 1 else None)  # noqa: E501
                    
                    if currency:
                        log_data["currency_code"] = currency
                    if amount is not None:
                        log_data["amount"] = amount
                    
                    if verbose and action_name in ("BUY", "SELL") and user and currency:
                        try:
                            from valutatrade_hub.core.usecases import load_portfolio
                            portfolio = load_portfolio(user.user_id)
                            if portfolio and currency in portfolio._wallets:
                                wallet = portfolio._wallets[currency]
                                log_data["wallet_balance_before"] = wallet.balance
                        except Exception:
                            pass
                
                elif action_name == "REGISTER":
                    username_arg = kwargs.get("username") or (args[0] if args else None)
                    log_data["username"] = username_arg
                
                elif action_name == "LOGIN":
                    username_arg = kwargs.get("username") or (args[0] if args else None)
                    log_data["username"] = username_arg
                
                result = func(*args, **kwargs)
                
                log_data["result"] = "OK"
                
                if action_name in ("BUY", "SELL") and verbose and user:
                    try:
                        from valutatrade_hub.core.usecases import load_portfolio
                        portfolio = load_portfolio(user.user_id)
                        if portfolio:
                            currency = kwargs.get("currency") or (args[0] if args else None)  # noqa: E501
                            if currency and currency in portfolio._wallets:
                                wallet = portfolio._wallets[currency]
                                log_data["wallet_balance_after"] = wallet.balance
                                
                            from valutatrade_hub.core.models import Portfolio
                            if currency and currency in Portfolio.exchange_rates:
                                currency_rate = Portfolio.exchange_rates[currency]
                                log_data["rate"] = currency_rate
                                log_data["base"] = "USD"
                    except Exception:
                        pass
                
                log_message = _format_log_message(log_data)
                logger.info(log_message)
                
                return result
                
            except Exception as e:
                log_data["result"] = "ERROR"
                log_data["error_type"] = type(e).__name__
                log_data["error_message"] = str(e)
                
                log_message = _format_log_message(log_data)
                logger.info(log_message)
                
                raise
        
        return wrapper
    return decorator


def _format_log_message(log_data):
    """Форматирует данные лога в строку"""
    parts = []
    
    parts.append(f"action={log_data['action']}")
    
    if log_data.get("username"):
        parts.append(f"user='{log_data['username']}'")
    elif log_data.get("user_id"):
        parts.append(f"user_id={log_data['user_id']}")
    
    if log_data.get("currency_code"):
        parts.append(f"currency='{log_data['currency_code']}'")
    
    if log_data.get("amount") is not None:
        parts.append(f"amount={log_data['amount']}")
    
    if log_data.get("rate") is not None:
        parts.append(f"rate={log_data['rate']:.2f}")
    
    if log_data.get("base"):
        parts.append(f"base='{log_data['base']}'")
    
    if log_data.get("wallet_balance_before") is not None:
        parts.append(f"balance_before={log_data['wallet_balance_before']}")
    
    if log_data.get("wallet_balance_after") is not None:
        parts.append(f"balance_after={log_data['wallet_balance_after']}")
    
    parts.append(f"result={log_data['result']}")
    
    if log_data.get("error_type"):
        parts.append(f"error_type={log_data['error_type']}")
    
    if log_data.get("error_message"):
        parts.append(f"error_message='{log_data['error_message']}'")
    
    return " ".join(parts)
