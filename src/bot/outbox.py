from dataclasses import dataclass, field

from telebot.types import InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove


@dataclass
class Outgoing:
    html: str
    buttons: list[dict] = field(default_factory=list)
    request_contact: bool = False


class CollectorBot:
    """Той самий інтерфейс, що TeleBot.send_message, без мережі Telegram."""

    def __init__(self):
        self.items: list[Outgoing] = []

    def send_message(self, chat_id, text, reply_markup=None, **_kwargs) -> None:
        buttons: list[dict] = []
        request_contact = False
        if isinstance(reply_markup, InlineKeyboardMarkup):
            for row in reply_markup.keyboard:
                for btn in row:
                    if getattr(btn, 'callback_data', None):
                        buttons.append({'label': btn.text, 'data': btn.callback_data})
        elif isinstance(reply_markup, ReplyKeyboardMarkup):
            for row in reply_markup.keyboard:
                for btn in row:
                    if getattr(btn, 'request_contact', False):
                        request_contact = True
        elif isinstance(reply_markup, ReplyKeyboardRemove):
            pass
        self.items.append(Outgoing(html=str(text), buttons=buttons, request_contact=request_contact))

    def answer_callback_query(self, *args, **kwargs) -> None:
        return None
