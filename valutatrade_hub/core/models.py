import hashlib
import json
from datetime import datetime
from typing import Optional
from core.exceptions import InsufficientFundsError


class User:
    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime
    ):
        # Приватные атрибуты
        self._user_id = user_id
        self._username = self._validate_username(username)
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    # Геттеры
    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    # Сеттер для username с проверкой
    @username.setter
    def username(self, value: str):
        self._username = self._validate_username(value)

    # Вспомогательные методы
    def _validate_username(self, username: str) -> str:
        if not username or not username.strip():
            raise ValueError("Имя пользователя не может быть пустым.")
        return username.strip()

    def _hash_password(self, password: str) -> str:
        """Создаёт хеш пароля с использованием соли."""
        if len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов.")
        # Объединяем пароль и соль, кодируем в байты
        pwd_salt = (password + self._salt).encode('utf-8')
        # Хешируем SHA-256
        return hashlib.sha256(pwd_salt).hexdigest()

    # Основные методы
    def get_user_info(self) -> dict:
        """Возвращает информацию о пользователе без пароля."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat()
        }

    def change_password(self, new_password: str):
        """Изменяет пароль пользователя, хешируя новый пароль."""
        # Проверяем длину нового пароля
        if len(new_password) < 4:
            raise ValueError("Новый пароль должен быть не короче 4 символов.")
        # Обновляем хеш пароля
        self._hashed_password = self._hash_password(new_password)

    def verify_password(self, password: str) -> bool:
        """Проверяет, совпадает ли введённый пароль с хешем."""
        try:
            return self._hash_password(password) == self._hashed_password
        except ValueError:
            return False  # Если пароль слишком короткий, сразу False

    # Методы для работы с JSON
    def to_dict(self) -> dict:
        """Преобразует объект в словарь для сохранения в JSON."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> User:
        """Создаёт объект User из словаря (например, из JSON)."""
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            hashed_password=data["hashed_password"],
            salt=data["salt"],
            registration_date=datetime.fromisoformat(data["registration_date"])
        )

class Wallet:
    def __init__(self, currency_code: str, balance: float = 0.0):
        self._currency_code = currency_code
        self._balance = self._validate_balance(balance)

    @property
    def currency_code(self) -> str:
        return self._currency_code

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float):
        self._balance = self._validate_balance(value)

    def _validate_balance(self, amount: float) -> float:
        if not isinstance(amount, (int, float)):
            raise TypeError("Баланс должен быть числом (int или float).")
        if amount < 0:
            raise ValueError("Баланс не может быть отрицательным.")
        return float(amount)

    def deposit(self, amount: float):
        """Пополнение баланса."""
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительным числом.")
        self.balance += amount

    def withdraw(self, amount: float) -> bool:
        """Снятие средств. Возвращает True, если операция успешна."""
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Сумма снятия должна быть положительным числом.")
        if amount > self.balance:
            raise InsufficientFundsError(
                available=self.balance,
                required=amount,
                code=self.currency_code
            )
        self.balance -= amount
        return True

    def get_balance_info(self) -> dict:
        """Возвращает информацию о балансе."""
        return {
            "currency_code": self._currency_code,
            "balance": self.balance
        }

    def to_dict(self) -> dict:
        """Преобразует кошелёк в словарь для JSON."""
        return {
            "currency_code": self._currency_code,
            "balance": self.balance
        }

    @classmethod
    def from_dict(cls, currency_code: str, data: dict) -> Wallet:
        """Создаёт кошелёк из словаря."""
        return cls(
            currency_code=currency_code,
            balance=data["balance"]
        )

class Portfolio:
    def __init__(self, user_id: int, wallets: Optional[dict] = None):
        self._user_id = user_id
        self._wallets = wallets if wallets is not None else {}

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def wallets(self) -> dict:
        """Возвращает копию словаря кошельков."""
        return self._wallets.copy()

    def add_currency(self, currency_code: str):
        """Добавляет новый кошелёк в портфель, если его ещё нет."""
        if currency_code in self._wallets:
            raise ValueError(f"Валюта {currency_code} уже есть в портфеле.")
        self._wallets[currency_code] = Wallet(currency_code)

    def get_wallet(self, currency_code: str) -> Optional[Wallet]:
        """Возвращает кошелёк по коду валюты или None, если не найден."""
        return self._wallets.get(currency_code)

    def get_total_value(self, base_currency: str = 'USD') -> float:
        """
        Возвращает общую стоимость всех валют в базовой валюте.
        Для упрощения используем фиксированные курсы.
        """
        # Фиксированные курсы (в реальных системах берутся из API)
        exchange_rates = {
            'USD': 1.0,
            'EUR': 1.1,
            'BTC': 40000.0,
            'RUB': 0.013,
            # Добавьте другие валюты по необходимости
        }

        if base_currency not in exchange_rates:
            raise ValueError(f"Курс для валюты {base_currency} не найден.")

        total = 0.0
        for wallet in self._wallets.values():
            currency = wallet.currency_code
            if currency not in exchange_rates:
                continue  # Пропускаем валюты без курса
            # Конвертируем баланс в базовую валюту
            rate = exchange_rates[currency] / exchange_rates[base_currency]
            total += wallet.balance * rate

        return total

    def to_dict(self) -> dict:
        """Преобразует портфель в словарь для JSON."""
        return {
            "user_id": self._user_id,
            "wallets": {code: wallet.to_dict() for code, wallet in self._wallets.items()}
        }

    @classmethod
    def from_dict(cls, data: dict) -> Portfolio:
        """Создаёт портфель из словаря."""
        wallets = {
            code: Wallet.from_dict(code, wallet_data)
            for code, wallet_data in data["wallets"].items()
        }
        return cls(user_id=data["user_id"], wallets=wallets)