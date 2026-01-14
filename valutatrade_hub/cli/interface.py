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


def buy_command(args):
    """Обработчик команды buy"""
    try:
        result = buy_currency(args.currency, args.amount)
        print(result)
    except ValueError as e:
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
