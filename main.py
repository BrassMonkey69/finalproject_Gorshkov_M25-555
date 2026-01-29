import sys
import argparse
from valutatrade_hub.logging_config import setup_logging
from valutatrade_hub.core.currencies import initialize_currencies
from valutatrade_hub.cli.interface import (
    register_command,
    login_command,
    show_portfolio_command,
    buy_command,
    sell_command,
    get_rate_command
)


def main():
    # 1. Настройка логирования
    setup_logging()

    # 2. Инициализация реестра валют
    try:
        initialize_currencies()
    except Exception as e:
        print(f"Ошибка инициализации валют: {e}")
        sys.exit(1)

    # 3. Разбор аргументов командной строки
    if len(sys.argv) < 2:
        print("Использование:")
        print("  register --username <имя> --password <пароль>")
        print("  login --username <имя> --password <пароль>")
        print("  show-portfolio [--base <валюта>]")
        print("  buy --currency <код> --amount <количество>")
        print("  sell --currency <код> --amount <количество>")
        print("  get-rate --from <код> --to <код>")
        sys.exit(0)

    command = sys.argv[1]

    # 4. Запуск команды
    try:
        if command == "register":
            register_command()
        elif command == "login":
            login_command()
        elif command == "show-portfolio":
            show_portfolio_command()
        elif command == "buy":
            buy_command()
        elif command == "sell":
            sell_command()
        elif command == "get-rate":
            get_rate_command()
        else:
            print(f"Неизвестная команда: '{command}'. Используйте одну из: register, login, show-portfolio, buy, sell, get-rate.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nОперация прервана пользователем.")
        sys.exit(1)
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        sys.exit(1)



if __name__ == "__main__":
    main()