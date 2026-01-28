from abc import ABC, abstractmethod
from typing import Dict


class CurrencyNotFoundError(Exception):
    """Исключение для случая, когда валюта по коду не найдена."""
    pass


class Currency(ABC):
    """
    Абстрактный базовый класс для всех валют.
    """

    def __init__(self, name: str, code: str):
        # Валидация имени
        if not name or not isinstance(name, str):
            raise ValueError("Name must be a non-empty string.")
        
        self.name = name

        # Валидация кода
        if (not code or
                not isinstance(code, str) or
                len(code) < 2 or len(code) > 5 or
                ' ' in code or not code.isupper()):
            raise ValueError(
                "Code must be 2–5 uppercase letters without spaces (e.g., 'USD', 'BTC')."
            )
        self.code = code

    @abstractmethod
    def get_display_info(self) -> str:
        """Возвращает строковое представление для UI/логов."""
        pass



class FiatCurrency(Currency):
    """Фиатная валюта (государственная)."""

    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)
        if not issuing_country or not isinstance(issuing_country, str):
            raise ValueError("Issuing country must be a non-empty string.")
        self.issuing_country = issuing_country


    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"




class CryptoCurrency(Currency):
    """Криптовалюта."""

    def __init__(self, name: str, code: str, algorithm: str, market_cap: float):
        super().__init__(name, code)
        if not algorithm or not isinstance(algorithm, str):
            raise ValueError("Algorithm must be a non-empty string.")
        self.algorithm = algorithm

        if market_cap < 0:
            raise ValueError("Market cap must be non-negative.")
        self.market_cap = market_cap

    def get_display_info(self) -> str:
        # Форматируем капитализацию в экспоненциальной записи (например, 1.12e12)
        mcap_str = f"{self.market_cap:.2e}" if self.market_cap >= 1e6 else f"{self.market_cap}"
        return (f"[CRYPTO] {self.code} — {self.name} "
                f"(Algo: {self.algorithm}, MCAP: {mcap_str})")




# Реестр валют (глобальный словарь)
_CURRENCY_REGISTRY: Dict[str, Currency] = {}



def register_currency(currency: Currency):
    """Добавляет валюту в реестр."""
    _CURRENCY_REGISTRY[currency.code] = currency


def get_currency(code: str) -> Currency:
    """
    Возвращает валюту по коду.
    Если код неизвестен — бросает CurrencyNotFoundError.
    """
    code = code.upper()  # Нормализуем регистр
    if code not in _CURRENCY_REGISTRY:
        raise CurrencyNotFoundError(f"Currency with code '{code}' not found.")
    return _CURRENCY_REGISTRY[code]




# Пример заполнения реестра (можно вынести в отдельный модуль/конфиг)
if __name__ == "__main__":
    # Регистрируем примеры валют
    register_currency(FiatCurrency("US Dollar", "USD", "United States"))
    register_currency(FiatCurrency("Euro", "EUR", "Eurozone"))
    register_currency(CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12))
    register_currency(CryptoCurrency("Ethereum", "ETH", "Ethash", 3.72e11))


    # Тестируем get_display_info()
    print(get_currency("USD").get_display_info())
    print(get_currency("BTC").get_display_info())

    # Тест на ошибку
    try:
        get_currency("XYZ")
    except CurrencyNotFoundError as e:
        print(e)