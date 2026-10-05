from typing import Final


class BotState:
    IDLE: Final = 'idle'

    EX_CITY: Final = 'ex_city'
    EX_PAIR: Final = 'ex_pair'
    EX_DIRECTION: Final = 'ex_direction'
    EX_AMOUNT: Final = 'ex_amount'
    EX_BRANCH: Final = 'ex_branch'
    EX_NAME: Final = 'ex_name'
    EX_PHONE: Final = 'ex_phone'
    EX_CONSENT: Final = 'ex_consent'
    EX_CONFIRM: Final = 'ex_confirm'

    FB_NAME: Final = 'fb_name'
    FB_PHONE: Final = 'fb_phone'
    FB_TEXT: Final = 'fb_text'
    FB_CONSENT: Final = 'fb_consent'

    CITY_PICK: Final = 'city_pick'


EXCHANGE_STATES = frozenset({
    BotState.EX_CITY,
    BotState.EX_PAIR,
    BotState.EX_DIRECTION,
    BotState.EX_AMOUNT,
    BotState.EX_BRANCH,
    BotState.EX_NAME,
    BotState.EX_PHONE,
    BotState.EX_CONSENT,
    BotState.EX_CONFIRM,
})

FEEDBACK_STATES = frozenset({
    BotState.FB_NAME,
    BotState.FB_PHONE,
    BotState.FB_TEXT,
    BotState.FB_CONSENT,
})
