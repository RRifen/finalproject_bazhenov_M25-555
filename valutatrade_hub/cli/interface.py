import argparse
import shlex
import sys

from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.usecases import (
    buy_currency,
    get_rate,
    login_user,
    register_user,
    sell_currency,
    show_portfolio,
)
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.storage import load_rates_cache
from valutatrade_hub.parser_service.updater import RatesUpdater


def register_command(args):
    """Обработчик команды register"""
    try:
        user_id = register_user(args.username, args.password)
        print(f"Пользователь '{args.username}' зарегистрирован (id={user_id}). "
              f"Войдите: login --username {args.username} --password ****")
    except ValueError as e:
        print(str(e))


def login_command(args):
    """Обработчик команды login"""
    try:
        user = login_user(args.username, args.password)
        print(f"Вы вошли как '{user.username}'")
    except ValueError as e:
        print(str(e))


def show_portfolio_command(args):
    """Обработчик команды show-portfolio"""
    try:
        base = args.base if args.base else "USD"
        result = show_portfolio(base_currency=base)
        print(result)
    except ValueError as e:
        print(str(e))
    except CurrencyNotFoundError as e:
        print(str(e))


def buy_command(args):
    """Обработчик команды buy"""
    try:
        result = buy_currency(args.currency, args.amount)
        print(result)
    except ValueError as e:
        print(str(e))
    except CurrencyNotFoundError as e:
        print(str(e))


def sell_command(args):
    """Обработчик команды sell"""
    try:
        result = sell_currency(args.currency, args.amount)
        print(result)
    except InsufficientFundsError as e:
        print(str(e))
    except ValueError as e:
        print(str(e))
    except CurrencyNotFoundError as e:
        print(str(e))


def get_rate_command(args):
    """Обработчик команды get-rate"""
    try:
        result = get_rate(args.from_currency, args.to_currency)
        print(result)
    except CurrencyNotFoundError as e:
        print(str(e))
        print("Используйте команду 'get-rate' для справки или проверьте список поддерживаемых валют")  # noqa: E501
    except ApiRequestError as e:
        print(str(e))
        print("Повторите попытку позже или проверьте подключение к сети")
    except ValueError as e:
        print(str(e))


def update_rates_command(args):
    """Обработчик команды update-rates"""
    print("INFO: Starting rates update...")
    
    api_clients = []
    
    if args.source:
        source_lower = args.source.lower()
        if source_lower == "coingecko":
            api_clients.append(CoinGeckoClient())
        elif source_lower == "exchangerate":
            api_clients.append(ExchangeRateApiClient())
        else:
            print(f"ERROR: Unknown source '{args.source}'. Use 'coingecko' or 'exchangerate'")  # noqa: E501
            return
    else:
        api_clients.append(CoinGeckoClient())
        api_clients.append(ExchangeRateApiClient())
    
    updater = RatesUpdater(api_clients)
    
    try:
        result = updater.run_update()
        
        has_errors = bool(result["results"]["failed"])
        
        for success in result["results"]["success"]:
            client_name = success["client"]
            pairs_count = success["pairs_count"]
            if "CoinGecko" in client_name:
                print(f"INFO: Fetching from CoinGecko... OK ({pairs_count} rates)")
            elif "ExchangeRate" in client_name:
                print(f"INFO: Fetching from ExchangeRate-API... OK ({pairs_count} rates)")  # noqa: E501
        
        for failure in result["results"]["failed"]:
            client_name = failure["client"]
            error_msg = failure["error"]
            if "CoinGecko" in client_name:
                print(f"ERROR: Failed to fetch from CoinGecko: {error_msg}")
            elif "ExchangeRate" in client_name:
                print(f"ERROR: Failed to fetch from ExchangeRate-API: {error_msg}")
        
        if result["results"]["total_pairs"] > 0:
            print(f"INFO: Writing {result['results']['total_pairs']} rates to data/rates.json...")  # noqa: E501
        
        if has_errors:
            print("Update completed with errors. Check logs/parser.log for details.")
        else:
            print(f"Update successful. Total rates updated: {result['results']['total_pairs']}. "  # noqa: E501
                  f"Last refresh: {result['last_refresh']}")
            
    except ApiRequestError as e:
        print(f"ERROR: {e}")
    except ValueError as e:
        print(f"ERROR: Failed to save rates: {e}")
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")


def show_rates_command(args):
    """Обработчик команды show-rates"""
    try:
        cache = load_rates_cache()
    except ValueError as e:
        print(f"ERROR: {e}")
        return
    
    pairs = cache.get("pairs", {})
    last_refresh = cache.get("last_refresh")
    
    if not pairs:
        print("Локальный кеш курсов пуст. Выполните 'update-rates', чтобы загрузить данные.")  # noqa: E501
        return
    
    filtered_pairs = {}
    
    if args.currency:
        currency_upper = args.currency.upper()
        for pair_key, pair_data in pairs.items():
            if pair_key.startswith(f"{currency_upper}_"):
                filtered_pairs[pair_key] = pair_data
        
        if not filtered_pairs:
            print(f"Курс для '{args.currency}' не найден в кеше.")
            return
    else:
        filtered_pairs = pairs.copy()
    
    if args.base:
        base_upper = args.base.upper()
        converted_pairs = {}
        base_rate = None
        
        for pair_key, pair_data in filtered_pairs.items():
            if pair_key.endswith(f"_{base_upper}"):
                base_rate = pair_data["rate"]
                break
        
        if base_rate is None:
            base_pair = f"{base_upper}_USD"
            if base_pair in pairs:
                base_rate = pairs[base_pair]["rate"]
            else:
                print(f"Курс для базовой валюты '{args.base}' не найден в кеше.")
                return
        
        for pair_key, pair_data in filtered_pairs.items():
            if pair_key.endswith("_USD"):
                currency = pair_key.split("_")[0]
                usd_rate = pair_data["rate"]
                converted_rate = usd_rate / base_rate
                new_pair_key = f"{currency}_{base_upper}"
                converted_pairs[new_pair_key] = {
                    "rate": converted_rate,
                    "updated_at": pair_data["updated_at"],
                    "source": pair_data["source"]
                }
        
        filtered_pairs = converted_pairs
    
    if args.top:
        sorted_pairs = sorted(
            filtered_pairs.items(),
            key=lambda x: x[1]["rate"],
            reverse=True
        )
        filtered_pairs = dict(sorted_pairs[:args.top])
    else:
        sorted_pairs = sorted(filtered_pairs.items())
        filtered_pairs = dict(sorted_pairs)
    
    print(f"Rates from cache (updated at {last_refresh}):")
    for pair_key, pair_data in filtered_pairs.items():
        rate = pair_data["rate"]
        print(f"- {pair_key}: {rate:.8f}")


def create_parser():
    """Создаёт и настраивает парсер аргументов"""
    parser = argparse.ArgumentParser(description="ValutaTrade Hub CLI", exit_on_error=False)  # noqa: E501
    subparsers = parser.add_subparsers(dest="command", help="Доступные команды")

    register_parser = subparsers.add_parser("register", help="Создать нового пользователя")  # noqa: E501
    register_parser.add_argument("--username", required=True, help="Имя пользователя")
    register_parser.add_argument("--password", required=True, help="Пароль")
    register_parser.set_defaults(func=register_command)

    login_parser = subparsers.add_parser("login", help="Войти в систему")
    login_parser.add_argument("--username", required=True, help="Имя пользователя")
    login_parser.add_argument("--password", required=True, help="Пароль")
    login_parser.set_defaults(func=login_command)

    show_portfolio_parser = subparsers.add_parser("show-portfolio", help="Показать портфель")  # noqa: E501
    show_portfolio_parser.add_argument("--base", help="Базовая валюта (по умолчанию USD)")  # noqa: E501
    show_portfolio_parser.set_defaults(func=show_portfolio_command)

    buy_parser = subparsers.add_parser("buy", help="Купить валюту")
    buy_parser.add_argument("--currency", required=True, help="Код покупаемой валюты")
    buy_parser.add_argument("--amount", required=True, type=float, help="Количество покупаемой валюты")  # noqa: E501
    buy_parser.set_defaults(func=buy_command)

    sell_parser = subparsers.add_parser("sell", help="Продать валюту")
    sell_parser.add_argument("--currency", required=True, help="Код продаваемой валюты")
    sell_parser.add_argument("--amount", required=True, type=float, help="Количество продаваемой валюты")  # noqa: E501
    sell_parser.set_defaults(func=sell_command)

    get_rate_parser = subparsers.add_parser("get-rate", help="Получить курс валюты")
    get_rate_parser.add_argument("--from", dest="from_currency", required=True, help="Исходная валюта")  # noqa: E501
    get_rate_parser.add_argument("--to", dest="to_currency", required=True, help="Целевая валюта")  # noqa: E501
    get_rate_parser.set_defaults(func=get_rate_command)

    update_rates_parser = subparsers.add_parser("update-rates", help="Обновить курсы валют из внешних API")  # noqa: E501
    update_rates_parser.add_argument("--source", help="Источник данных (coingecko или exchangerate)")  # noqa: E501
    update_rates_parser.set_defaults(func=update_rates_command)

    show_rates_parser = subparsers.add_parser("show-rates", help="Показать курсы из локального кеша")  # noqa: E501
    show_rates_parser.add_argument("--currency", help="Показать курс только для указанной валюты")  # noqa: E501
    show_rates_parser.add_argument("--top", type=int, help="Показать N самых дорогих криптовалют")  # noqa: E501
    show_rates_parser.add_argument("--base", help="Показать все курсы относительно указанной базы")  # noqa: E501
    show_rates_parser.set_defaults(func=show_rates_command)

    return parser


def parse_and_execute_command(line, parser):
    """Парсит и выполняет команду из строки"""
    if not line.strip():
        return
    
    line = line.strip()
    
    if line.lower() in ("exit", "quit", "q"):
        print("Выход из приложения")
        sys.exit(0)
    
    if line.lower() in ("help", "?"):
        parser.print_help()
        return
    
    try:
        args = parser.parse_args(shlex.split(line))
    except argparse.ArgumentError as e:
        print(str(e))
        return
    except SystemExit:
        return
    
    if args.command is None:
        parser.print_help()
    else:
        args.func(args)


def main():
    """Главная функция CLI - интерактивный режим"""
    parser = create_parser()
    
    print("ValutaTrade Hub CLI")
    print("Введите команду (help - справка, exit - выход)")
    print("-" * 50)
    
    while True:
        line = input("> ")
        parse_and_execute_command(line, parser)
