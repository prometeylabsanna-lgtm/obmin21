from django.urls import reverse_lazy


def _item(title, icon, url_name):
    return {
        'title': title,
        'icon': icon,
        'link': reverse_lazy(url_name),
    }


def build_unfold_navigation():
    return [
        {
            'title': 'Оформлення сайту',
            'separator': False,
            'collapsible': False,
            'items': [
                _item('Шапка сайту', 'web_asset', 'admin:core_headersettings_changelist'),
                _item('Підвал сайту', 'view_agenda', 'admin:core_footersettings_changelist'),
                _item('Загальні налаштування', 'settings', 'admin:core_sitesettings_changelist'),
            ],
        },
        {
            'title': 'Головна',
            'separator': True,
            'collapsible': True,
            'items': [
                _item('Банер', 'photo', 'admin:network_bannercity_changelist'),
                _item('Розрахунок обміну', 'calculate', 'admin:content_homecalcsettings_changelist'),
                _item('Вигідний курс', 'payments', 'admin:content_homepromosettings_changelist'),
                _item(
                    'Знайдіть нас на карті',
                    'map',
                    'admin:network_mapcity_changelist',
                ),
                _item(
                    'Чому нас обирають',
                    'star',
                    'admin:content_homewhysettings_changelist',
                ),
                _item(
                    'Наші послуги',
                    'handyman',
                    'admin:content_homeservicessettings_changelist',
                ),
                _item(
                    'Відповіді на поширені запитання',
                    'help',
                    'admin:content_homefaqsettings_changelist',
                ),
                _item(
                    'Відгуки',
                    'rate_review',
                    'admin:content_homereviewssettings_changelist',
                ),
                _item(
                    'Корисні статті',
                    'article',
                    'admin:content_homearticlessettings_changelist',
                ),
            ],
        },
        {
            'title': 'Блог',
            'separator': True,
            'collapsible': True,
            'items': [
                _item('Сторінка Блог', 'article', 'admin:content_blogpage_changelist'),
                _item('Статті', 'newspaper', 'admin:blog_post_changelist'),
                _item('Категорії', 'category', 'admin:blog_category_changelist'),
            ],
        },
        {
            'title': 'Контакти',
            'separator': True,
            'collapsible': True,
            'items': [
                _item('Сторінка контактів', 'call', 'admin:content_contactspage_changelist'),
                _item('Адреси по містах', 'location_city', 'admin:network_contactcity_changelist'),
            ],
        },
        {
            'title': 'Документи',
            'separator': True,
            'collapsible': True,
            'items': [
                _item(
                    'Політика конфіденційності',
                    'policy',
                    'admin:content_privacypage_changelist',
                ),
                _item('Публічна оферта', 'gavel', 'admin:content_offerpage_changelist'),
                _item(
                    'Політика використання файлів Cookie',
                    'cookie',
                    'admin:content_cookiepage_changelist',
                ),
            ],
        },
        {
            'title': 'Інші сторінки',
            'separator': True,
            'collapsible': True,
            'items': [
                _item('Курси валют', 'currency_exchange', 'admin:content_ratespage_changelist'),
                _item('Послуги', 'handyman', 'admin:content_servicespage_changelist'),
                _item('Переваги', 'star', 'admin:content_advantagespage_changelist'),
                _item('Питання та відповіді', 'quiz', 'admin:content_faqpage_changelist'),
                _item('Відгуки (сторінка)', 'reviews', 'admin:content_reviewspage_changelist'),
                _item('Міста мережі', 'location_city', 'admin:network_city_changelist'),
            ],
        },
        {
            'title': 'Заявки',
            'separator': True,
            'collapsible': True,
            'items': [
                _item('Заявки на обмін', 'assignment', 'admin:leads_exchangerequest_changelist'),
                _item('Повідомлення з форми', 'mail', 'admin:leads_contactmessage_changelist'),
            ],
        },
        {
            'title': 'Курси',
            'separator': True,
            'collapsible': True,
            'items': [
                _item('Валютні пари', 'payments', 'admin:rates_currencypair_changelist'),
                _item('Таблиця курсів', 'table_chart', 'admin:rates_quote_changelist'),
                _item('Відділення', 'store', 'admin:network_branch_changelist'),
            ],
        },
        {
            'title': 'Доступ',
            'separator': True,
            'collapsible': True,
            'items': [
                _item('Користувачі панелі', 'group', 'admin:auth_user_changelist'),
                _item('Ролі', 'admin_panel_settings', 'admin:auth_group_changelist'),
            ],
        },
    ]
