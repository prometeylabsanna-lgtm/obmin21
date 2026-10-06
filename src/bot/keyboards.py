from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

CB_MENU = 'mn:home'
CB_RATES = 'mn:rates'
CB_EX = 'mn:ex'
CB_FB = 'mn:fb'
CB_BR = 'mn:br'
CB_CANCEL = 'mn:cancel'
CB_CONSENT_YES = 'ok:1'
CB_CONSENT_NO = 'ok:0'
CB_CONFIRM = 'cf:1'


def remove_reply() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def main_menu() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton('Курси', callback_data=CB_RATES),
        InlineKeyboardButton('Заявка', callback_data=CB_EX),
        InlineKeyboardButton('Відділення', callback_data=CB_BR),
        InlineKeyboardButton('Звернення', callback_data=CB_FB),
    )
    return markup


def cancel_row() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton('Скасувати', callback_data=CB_CANCEL)]


def cities_keyboard(cities, purpose: str) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton(city.name, callback_data=f'c:{purpose}:{city.pk}')
        for city in cities
    ]
    markup.add(*buttons)
    markup.add(*cancel_row())
    return markup


def pairs_keyboard(pairs) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton(pair.code, callback_data=f'p:{pair.pk}')
        for pair in pairs
    ]
    markup.add(*buttons)
    markup.add(*cancel_row())
    return markup


def direction_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton('Продати', callback_data='d:sell'),
        InlineKeyboardButton('Купити', callback_data='d:buy'),
    )
    markup.add(*cancel_row())
    return markup


def branches_keyboard(branches) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=1)
    for branch in branches:
        label = branch.address[:60]
        markup.add(InlineKeyboardButton(label, callback_data=f'br:{branch.pk}'))
    markup.add(*cancel_row())
    return markup


def consent_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton('Погоджуюсь', callback_data=CB_CONSENT_YES),
        InlineKeyboardButton('Ні', callback_data=CB_CONSENT_NO),
    )
    markup.add(*cancel_row())
    return markup


def confirm_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton('Підтвердити', callback_data=CB_CONFIRM),
        InlineKeyboardButton('Скасувати', callback_data=CB_CANCEL),
    )
    return markup


def phone_keyboard() -> ReplyKeyboardMarkup:
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton('Надіслати номер', request_contact=True))
    return markup
