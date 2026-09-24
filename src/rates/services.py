from decimal import Decimal, InvalidOperation


def parse_amount(raw):
    if raw is None:
        raise InvalidOperation
    text = str(raw).strip().replace(' ', '').replace(',', '.')
    if not text:
        raise InvalidOperation
    return Decimal(text)


def calc_receive(amount_give, rate, direction):
    """
    direction buy: клієнт купує валюту за UAH → віддає UAH, отримує валюту (ділення на sell)
    direction sell: клієнт продає валюту → віддає валюту, отримує UAH (множення на buy)
    """
    amount = Decimal(amount_give)
    rate = Decimal(rate)
    if direction == 'sell':
        return (amount * rate).quantize(Decimal('0.01'))
    if rate == 0:
        return Decimal('0.00')
    return (amount / rate).quantize(Decimal('0.01'))
