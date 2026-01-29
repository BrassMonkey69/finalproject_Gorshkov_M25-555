from datetime import datetime
from typing import Optional, Dict, Any
from .models import User, Portfolio, Wallet
import hashlib


def register_user(
    users_data: list,
    username: str,
    password: str,
    salt: str,
    registration_date: datetime
) -> User:
    """Создаёт пользователя (вызывается из CLI)."""
    user_id = max((u["user_id"] for u in users_data), default=0) + 1
    hashed_password = hashlib.sha256((password + salt).encode()).hexdigest()
    
    user = User(
        user_id=user_id,
        username=username,
        hashed_password=hashed_password,
        salt=salt,
        registration_date=registration_date
    )
    return user



def login_user(users_data: list, username: str, password: str) -> Optional[User]:
    """Проверяет логин/пароль и возвращает объект User или None."""
    for user_data in users_data:
        if user_data["username"] == username:
            user = User.from_dict(user_data)
            if user.verify_password(password):
                return user
    return None



def show_portfolio(portfolios_data: list, user_id: int) -> Optional[Portfolio]:
    """Возвращает портфель пользователя по user_id."""
    for portfolio_data in portfolios_data:
        if portfolio_data["user_id"] == user_id:
            return Portfolio.from_dict(portfolio_data)
    return None



def get_rate(rates_data: dict, currency: str) -> Optional[float]:
    """
    Возвращает курс валюты к USD (например, 1 BTC = X USD).
    Если валюта не найдена — возвращает None.
    """
    key = f"{currency}_USD"
    if key in rates_data:
        return rates_data[key]["rate"]
    return None



def buy_currency(
    portfolios_data: list,
    rates_data: dict,
    user_id: int,
    currency: str,
    amount: float
) -> bool:
    """
    Покупает валюту: списывает USD с кошелька, добавляет купленную валюту.
    Возвращает True при успехе, False при ошибке.
    """
    portfolio = show_portfolio(portfolios_data, user_id)
    if not portfolio:
        return False

    # Получаем курс
    rate_key = f"{currency}_USD"
    if rate_key not in rates_data:
        return False
    rate = rates_data[rate_key]["rate"]


    # Рассчитываем стоимость в USD
    usd_cost = amount * rate

    # Проверяем USD-кошелёк
    usd_wallet = portfolio.get_wallet("USD")
    if not usd_wallet or usd_wallet.balance < usd_cost:
        return False  # Недостаточно средств


    # Списываем USD
    usd_wallet.withdraw(usd_cost)


    # Добавляем купленную валюту (если кошелька нет — создаём)
    if currency not in portfolio._wallets:
        portfolio.add_currency(currency)
    target_wallet = portfolio.get_wallet(currency)
    target_wallet.deposit(amount)


    # Обновляем данные в хранилище
    for i, p_data in enumerate(portfolios_data):
        if p_data["user_id"] == user_id:
            portfolios_data[i] = portfolio.to_dict()
            break

    return True



def sell_currency(
    portfolios_data: list,
    rates_data: dict,
    user_id: int,
    currency: str,
    amount: float
) -> bool:
    """
    Продаёт валюту: списывает валюту с кошелька, начисляет USD.
    Возвращает True при успехе, False при ошибке.
    """
    portfolio = show_portfolio(portfolios_data, user_id)
    if not portfolio:
        return False

    # Получаем кошелёк продаваемой валюты
    wallet = portfolio.get_wallet(currency)
    if not wallet or wallet.balance < amount:
        return False  # Нет кошелька или недостаточно средств

    # Получаем курс
    rate_key = f"{currency}_USD"
    if rate_key not in rates_data:
        return False
    rate = rates_data[rate_key]["rate"]

    # Рассчитываем выручку в USD
    usd_revenue = amount * rate

    # Списываем продаваемую валюту
    wallet.withdraw(amount)

    # Начисляем USD (если кошелька нет — создаём)
    usd_wallet = portfolio.get_wallet("USD")
    if usd_wallet:
        usd_wallet.deposit(usd_revenue)
    else:
        portfolio.add_currency("USD")
        usd_wallet = portfolio.get_wallet("USD")
        usd_wallet.deposit(usd_revenue)

    # Обновляем данные в хранилище
    for i, p_data in enumerate(portfolios_data):
        if p_data["user_id"] == user_id:
            portfolios_data[i] = portfolio.to_dict()
            break

    return True
