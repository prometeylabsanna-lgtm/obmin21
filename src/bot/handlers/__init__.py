from src.bot.handlers import branches, common, contact, exchange, rates


def register_handlers(bot) -> None:
    common.register(bot)
    rates.register(bot)
    branches.register(bot)
    contact.register(bot)
    exchange.register(bot)

    @bot.message_handler(func=lambda _m: True, content_types=['text'])
    def fallback(message) -> None:
        from src.bot.handlers.common import send_menu
        from src.bot import texts

        send_menu(bot, message.chat.id, texts.UNKNOWN)
