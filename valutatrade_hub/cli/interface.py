import argparse
import json
import sys
import hashlib
import time
from typing import Optional
from datetime import datetime, timedelta
from core.models import User, Portfolio
from core.usecases import (
    register_user,
    login_user,
    show_portfolio,
    buy_currency,
    sell_currency,
    get_rate
)
from core.exceptions import (
    InsufficientFundsError,
    CurrencyNotFoundError,
    ApiRequestError
)
from core.currencies import get_currency

def handle_cli_exception(exc: Exception, command: str):
    """
    Централизованная обработка исключений для CLI.
    Выводит пользовательские сообщения и завершает выполнение.
    """
    if isinstance(exc, InsufficientFundsError):
        print(str(exc))  # Сообщение как есть
    elif isinstance(exc, CurrencyNotFoundError):
        print(str(exc))
        print("Используйте `get-rate --help` для списка поддерживаемых валют.")
        # Или: показать список из реестра (если доступен)
        # print("Поддерживаемые валюты: USD, EUR, BTC, ETH")
    elif isinstance(exc, ApiRequestError):
        print(str(exc))
        print("Попробуйте повторить запрос позже или проверьте подключение к сети.")
    else:
        # Неожиданные исключения
        print(f"Непредвиденная ошибка в команде '{command}': {exc}")
    
    sys.exit(1)
    
def load_json(filepath: str) -> dict:
    """Загружает JSON‑файл. Если файла нет — возвращает пустой словарь."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}



def save_json(filepath: str, data: dict):
    """Сохраняет данные в JSON‑файл."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)



def generate_salt() -> str:
    """Генерирует случайную соль (для примера — фиксированная строка)."""
    return "x5T9!"  # В реальной системе используйте secrets.token_hex(16)

def is_rate_fresh(updated_at_str: str, max_age_minutes: int = 5) -> bool:
    """Проверяет, что курс обновлён не более X минут назад."""
    try:
        updated_at = datetime.fromisoformat(updated_at_str)
        now = datetime.now()
        return now - updated_at <= timedelta(minutes=max_age_minutes)
    except ValueError:
        return False

def fetch_rate_from_parser(from_curr: str, to_curr: str) -> Optional[dict]:
    """
    Заглушка для Parser Service. В реальной реализации:
    - делает HTTP-запрос к API (CoinGecko, Binance и т. п.);
    - возвращает {"rate": float, "updated_at": iso_str} или None.
    """
    # Пример заглушки (заменить на реальный API-запрос)
    mock_rates = {
        "USD_BTC": 0.00001685,
        "BTC_USD": 59337.21,
        "USD_ETH": 0.000268,
        "ETH_USD": 3731.34,
    }
    key = f"{from_curr}_{to_curr}"
    if key in mock_rates:
        return {
            "rate": mock_rates[key],
            "updated_at": datetime.now().isoformat()
        }
    return None

def get_exchange_rate(
    rates_data: dict,
    from_curr: str,
    to_curr: str
) -> Optional[dict]:
    """
    Возвращает курс from_curr → to_curr.
    Если курс устарел или отсутствует — пытается обновить через Parser Service.
    """
    key = f"{from_curr}_{to_curr}"

    # Проверяем кэш
    if key in rates_data:
        rate_entry = rates_data[key]
        if is_rate_fresh(rate_entry["updated_at"]):
            return rate_entry

    # Пытаемся обновить курс
    new_rate = fetch_rate_from_parser(from_curr, to_curr)
    if new_rate:
        # Обновляем кэш
        rates_data[key] = new_rate
        save_json("data/rates.json", rates_data)
        return new_rate

    return None  # Курс недоступен

current_user: User = None

def register_command():
    parser = argparse.ArgumentParser(description="Регистрация нового пользователя")
    parser.add_argument("--username", type=str, required=True)
    parser.add_argument("--password", type=str, required=True)
    args = parser.parse_args(sys.argv[2:])
    
    try:
        user = register_user(args.username, args.password)
        print(f"Пользователь {user.username} успешно зарегистрирован (ID: {user.user_id})")
    except UserAlreadyExistsError:
        print(f"Ошибка: имя пользователя {args.username} уже занято")
    except Exception as e:
        print(f"Ошибка регистрации: {str(e)}")

def login_command():
    global current_user
    parser = argparse.ArgumentParser(description="Вход в систему")
    parser.add_argument("--username", type=str, required=True)
    parser.add_argument("--password", type=str, required=True)
    args = parser.parse_args(sys.argv[2:])
    
    try:
        current_user = login_user(args.username, args.password)
        print(f"Успешный вход как {current_user.username}")
    except AuthenticationError:
        print("Ошибка: неверный логин или пароль")
    except Exception as e:
        print(f"Ошибка входа: {str(e)}")

def show_portfolio_command():
    global current_user
    if not current_user:
        print("Ошибка: сначала выполните login")
        return
        
    parser = argparse.ArgumentParser(description="Просмотр портфеля")
    parser.add_argument("--base", type=str, default="USD")
    args = parser.parse_args(sys.argv[2:])
    
    try:
        portfolio = show_portfolio(current_user.user_id, args.base)
        print(f"Портфель пользователя {current_user.username} (база: {args.base}):")
        # Логика отображения портфеля
    except Exception as e:
        print(f"Ошибка при просмотре портфеля: {str(e)}")

def buy_command():
    global current_user
    if not current_user:
        print("Ошибка: сначала выполните login")
        return
        
    parser = argparse.ArgumentParser(description="Покупка валюты")
    parser.add_argument("--currency", type=str, required=True)
    parser.add_argument("--amount", type=float, required=True)
    args = parser.parse_args(sys.argv[2:])
    
    try:
        buy_currency(current_user.user_id, args.currency, args.amount)
        print(f"Успешно куплено {args.amount} {args.currency}")
    except InsufficientFundsError:
        print("Ошибка: недостаточно средств")
    except CurrencyNotFoundError:
        print(f"Ошибка: валюта {args.currency} не найдена")
    except Exception as e:
        print(f"Ошибка при покупке: {str(e)}")
        
def sell_command():
    global current_user
    if not current_user:
        print("Ошибка: сначала выполните login")
        return
        
    parser = argparse.ArgumentParser(description="Продажа валюты")
    parser.add_argument("--currency", type=str, required=True)
    parser.add_argument("--amount", type=float, required=True)
    args = parser.parse_args(sys.argv[2:])
    
    try:
        sell_currency(current_user.user_id, args.currency, args.amount)
    except InsufficientFundsError:
        print(f"Ошибка: недостаточно {args.currency} для продажи")
    except CurrencyNotFoundError:
        print(f"Ошибка: валюта {args.currency} не найдена")
    except Exception as e:
        print(f"Ошибка при продаже: {str(e)}")
        
def get_rate_command():
    parser = argparse.ArgumentParser(description="Получение курса валют")
    parser.add_argument("--from", type=str, required=True, help="Исходная валюта")
    parser.add_argument("--to", type=str, required=True, help="Целевая валюта")
    args = parser.parse_args(sys.argv[2:])
    
    try:
        rate = get_exchange_rate(args.from_curr, args.to)
        print(f"Курс {args.from_curr} → {args.to}: {rate}")
    except CurrencyNotFoundError:
        print(f"Ошибка: валюта {args.from_curr} или {args.to} не найдена")
    except Exception as e:
        print(f"Ошибка при получении курса: {str(e)}")

def main():
    commands = {
        "register": register_command,
        "login": login_command,
        "show-portfolio": show_portfolio_command,
        "buy": buy_command,
        "sell": sell_command,
        "get-rate": get_rate_command
    }
    
    if len(sys.argv) < 2:
        print("Укажите команду: register, login, show-portfolio, buy, sell, get-rate")
        return
    
    command_name = sys.argv[1]
    if command_name in commands:
        commands[command_name]()
    else:
        print(f"Неизвестная команда: {command_name}")
        
"""        
def main():
    parser = argparse.ArgumentParser(description="Платформа для торговли валютами")
    subparsers = parser.add_subparsers(dest="command", help="Доступные команды")

    # Команда register
    register_parser = subparsers.add_parser("register", help="Зарегистрировать нового пользователя")
    register_parser.add_argument("--username", type=str, required=True, help="Имя пользователя")
    register_parser.add_argument("--password", type=str, required=True, help="Пароль")

    # Команда login
    login_parser = subparsers.add_parser("login", help="Войти в систему")
    login_parser.add_argument("--username", type=str, required=True, help="Имя пользователя")
    login_parser.add_argument("--password", type=str, required=True, help="Пароль")

    # Команда show-portfolio
    show_parser = subparsers.add_parser("show-portfolio", help="Показать портфель пользователя")
    show_parser.add_argument("--base", type=str, help="Базовая валюта конвертации (по умолчанию USD)")

    # Команда buy
    buy_parser = subparsers.add_parser("buy", help="Купить валюту")
    buy_parser.add_argument("--currency", type=str, required=True, help="Код валюты (например, BTC)")
    buy_parser.add_argument("--amount", type=float, required=True, help="Количество покупаемой валюты")

    # Команда sell
    sell_parser = subparsers.add_parser("sell", help="Продать валюту")
    sell_parser.add_argument("--currency", type=str, required=True, help="Код валюты")
    sell_parser.add_argument("--amount", type=float, required=True, help="Количество продаваемой валюты")
    
    # Команда get-rate
    rate_parser = subparsers.add_parser("get-rate", help="Получить курс валюты")
    rate_parser.add_argument("--from-currency", type=str, required=True, help="Исходная валюта (например, USD)")
    rate_parser.add_argument("--to-currency", type=str, required=True, help="Целевая валюта (например, BTC)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Глобальные данные
    users_data = load_json("data/users.json")
    portfolios_data = load_json("data/portfolios.json")
    rates_data = load_json("data/rates.json")

    # Текущий залогиненный пользователь (хранится в памяти CLI)
    current_user = None

    try:
        if args.command == "register":
            # Проверка уникальности username
            if any(u["username"] == args.username for u in users_data):
                print(f"Имя пользователя '{args.username}' уже занято")
                sys.exit(1)

            # Валидация пароля
            if len(args.password) < 4:
                print("Пароль должен быть не короче 4 символов")
                sys.exit(1)

            # Генерация user_id (автоинкремент)
            user_id = max((u["user_id"] for u in users_data), default=0) + 1

            # Хеширование пароля
            salt = generate_salt()
            hashed_password = hashlib.sha256((args.password + salt).encode()).hexdigest()

            # Создание пользователя
            user = User(
                user_id=user_id,
                username=args.username,
                hashed_password=hashed_password,
                salt=salt,
                registration_date=datetime.now()
            )

            # Сохранение в users.json
            users_data.append(user.to_dict())
            save_json("data/users.json", users_data)

            # Создание пустого портфеля
            portfolio = Portfolio(user_id=user_id)
            portfolios_data.append(portfolio.to_dict())
            save_json("data/portfolios.json", portfolios_data)

            print(f"Пользователь '{args.username}' зарегистрирован (id={user_id}). Войдите: login --username {args.username} --password ****")

        elif args.command == "login":
            # Загружаем данные пользователей
            users_data = load_json("data/users.json")

            # Вызываем бизнес‑логику для авторизации
            user = login_user(users_data, args.username, args.password)

            if user:
                # Сохраняем текущего пользователя в контексте CLI
                current_user = user
                print(f"Вы вошли как '{user.username}'")
            else:
                # Определяем причину ошибки
                user_exists = any(
                    u["username"] == args.username for u in users_data
                )
                if not user_exists:
                    print(f"Пользователь '{args.username}' не найден")
                else:
                    print("Неверный пароль")
                sys.exit(1)

        elif args.command == "show-portfolio":
            if not current_user:
                print("Сначала выполните login")
                sys.exit(1)

            # Загружаем данные
            portfolios_data = load_json("data/portfolios.json")
            rates_data = load_json("data/rates.json")

            # Получаем базовый валютный код (по умолчанию USD)
            base_currency = (args.base or "USD").upper()

            # Проверяем, что базовая валюта существует в курсах
            if base_currency != "USD" and not any(
                key.endswith(f"_{base_currency}") for key in rates_data.keys()
            ):
                print(f"Неизвестная базовая валюта '{base_currency}'")
                sys.exit(1)

            # Получаем портфель пользователя
            portfolio = show_portfolio(portfolios_data, current_user.user_id)
            if not portfolio:
                print("Портфель не найден")
                sys.exit(0)

            # Если кошельков нет
            if not portfolio.wallets:
                print(f"Портфель пользователя '{current_user.username}' пуст")
                sys.exit(0)

            # Выводим заголовок
            print(f"Портфель пользователя '{current_user.username}' (база: {base_currency}):")

            total_in_base = 0.0

            # Для каждого кошелька
            for currency_code, wallet in portfolio.wallets.items():
                balance = wallet.balance

                # Получаем курс к базовой валюте
                if currency_code == base_currency:
                    rate = 1.0
                else:
                    # Ищем курс: например, BTC_USD или EUR_USD
                    rate_key = f"{currency_code}_{base_currency}"
                    if rate_key not in rates_data:
                        print(f"  {currency_code}: {balance:.4f} → курс не найден")
                        continue
                    rate = rates_data[rate_key]["rate"]

                # Стоимость в базовой валюте
                value_in_base = balance * rate
                total_in_base += value_in_base

                # Форматируем вывод
                if currency_code == "USD" or currency_code == base_currency:
                    print(f"  - {currency_code}: {balance:,.2f} → {value_in_base:,.2f} {base_currency}")
                else:
                    print(f"  - {currency_code}: {balance:,.4f} → {value_in_base:,.2f} {base_currency}")


            # Итого
            print("-".ljust(40, "-"))
            print(f"ИТОГО: {total_in_base:,.2f} {base_currency}")

        elif args.command in ["buy", "sell"]:
            if not current_user:
                print("Войдите в систему (login)")
                sys.exit(1)

            currency = args.currency.upper()
            amount = args.amount

            if amount <= 0:
                print("Сумма должна быть положительной")
                sys.exit(1)
            elif args.command == "buy":
                if not current_user:
                    print("Сначала выполните login")
                    sys.exit(1)

                # Валидация аргументов
                currency = args.currency.upper()
                amount = args.amount

                if amount <= 0:
                    print("'amount' должен быть положительным числом")
                    sys.exit(1)


                # Загружаем данные
                portfolios_data = load_json("data/portfolios.json")
                rates_data = load_json("data/rates.json")

                # Получаем текущий курс currency → USD
                rate_key = f"{currency}_USD"
                if rate_key not in rates_data:
                    print(f"Не удалось получить курс для {currency}→USD")
                    sys.exit(1)


                rate = rates_data[rate_key]["rate"]
                usd_cost = amount * rate

                # Выполняем покупку
                success = buy_currency(
                    portfolios_data=portfolios_data,
                    rates_data=rates_data,
                    user_id=current_user.user_id,
                    currency=currency,
                    amount=amount
                )

                if success:
                    # Сохраняем изменения
                    save_json("data/portfolios.json", portfolios_data)

                    # Получаем обновлённый портфель
                    portfolio = show_portfolio(portfolios_data, current_user.user_id)
                    wallet = portfolio.get_wallet(currency)


                    # Выводим результат
                    print(f"Покупка выполнена: {amount:,.4f} {currency} по курсу {rate:,.2f} USD/{currency}")
                    print("Изменения в портфеле:")
                    print(f"  - {currency}: было {wallet.balance - amount:,.4f} → стало {wallet.balance:,.4f}")
                    print(f"Оценочная стоимость покупки: {usd_cost:,.2f} USD")
            else:
                    print("Недостаточно средств для покупки")
                    sys.exit(1)

        elif args.command == "sell":
            if not current_user:
                print("Сначала выполните login")
                sys.exit(1)

            # Валидация аргументов
            currency = args.currency.upper()
            amount = args.amount

            if amount <= 0:
                print("'amount' должен быть положительным числом")
                sys.exit(1)

            # Загружаем данные
            portfolios_data = load_json("data/portfolios.json")
            rates_data = load_json("data/rates.json")

            # Проверяем существование кошелька
            portfolio = show_portfolio(portfolios_data, current_user.user_id)
            if not portfolio:
                print("Портфель не найден")
                sys.exit(1)

            wallet = portfolio.get_wallet(currency)
            if not wallet:
                print(f"У вас нет кошелька '{currency}'. Добавьте валюту: она создаётся автоматически при первой покупке.")
                sys.exit(1)

            # Проверяем баланс
            if wallet.balance < amount:
                print(f"Недостаточно средств: доступно {wallet.balance:.4f} {currency}, требуется {amount:.4f} {currency}")
                sys.exit(1)

            # Получаем курс
            rate_key = f"{currency}_USD"
            if rate_key not in rates_data:
                print(f"Не удалось получить курс для {currency}→USD")
                sys.exit(1)

            rate = rates_data[rate_key]["rate"]
            usd_revenue = amount * rate

            # Выполняем продажу
            success = sell_currency(
                portfolios_data=portfolios_data,
                rates_data=rates_data,
                user_id=current_user.user_id,
                currency=currency,
                amount=amount
            )

            if success:
                # Сохраняем изменения
                save_json("data/portfolios.json", portfolios_data)

                # Получаем обновлённый портфель
                portfolio = show_portfolio(portfolios_data, current_user.user_id)
                wallet = portfolio.get_wallet(currency)

                # Выводим результат
                print(f"Продажа выполнена: {amount:,.4f} {currency} по курсу {rate:,.2f} USD/{currency}")
                print("Изменения в портфеле:")
                print(f"  - {currency}: было {wallet.balance + amount:,.4f} → стало {wallet.balance:,.4f}")
                print(f"Оценочная выручка: {usd_revenue:,.2f} USD")
            else:
                print("Ошибка при продаже валюты")
                sys.exit(1)
                
        elif args.command == "get-rate":
            try:
                from_curr = args.from_currency.upper()
                to_curr = args.to_currency.upper()

                # Проверка на идентичность валют
                if from_curr == to_curr:
                    print(f"Курс {from_curr}→{to_curr}: 1.00000000 (фиксированный)")
                    sys.exit(0)


                # Проверка существования валют
                get_currency(from_curr)
                get_currency(to_curr)

                # Получение курса
                rate_info = get_exchange_rate(rates_data, from_curr, to_curr)
                if not rate_info:
                    print(f"Курс {from_curr}→{to_curr} недоступен. Попробуйте позже.")
                    sys.exit(1)
                
                print(f"Курс {from_curr}→{to_curr}: {rate_info['rate']:.8f} (обновлено: {rate_info['updated_at']})")
                
                # Проверка наличия данных после загрузки
                if not rates_data.get("rates"):
                    print("Не удалось получить курсы валют: нет данных в кэше и недоступен API.")
                    sys.exit(1)

            except (CurrencyNotFoundError, ApiRequestError) as e:
                handle_cli_exception(e, "get-rate")
    except Exception as e:
        handle_cli_exception(e, "get-rate")
"""                   

if __name__ == "__main__":
    main()
