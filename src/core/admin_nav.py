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
            'title': 'Сторінки сайту',
            'separator': True,
            'collapsible': False,
            'items': [
                _item('Головна', 'home', 'admin:content_homepage_changelist'),
                _item('Курси валют', 'currency_exchange', 'admin:content_ratespage_changelist'),
                _item('Контакти', 'call', 'admin:content_contactspage_changelist'),
                _item('Послуги', 'handyman', 'admin:content_servicespage_changelist'),
                _item('Переваги', 'star', 'admin:content_advantagespage_changelist'),
                _item('Блог', 'article', 'admin:content_blogpage_changelist'),
                _item('Відгуки', 'rate_review', 'admin:content_reviewspage_changelist'),
                _item('Міста', 'location_city', 'admin:content_citiespage_changelist'),
                _item('Часті питання', 'help', 'admin:content_faqpage_changelist'),
                _item(
                    'Політика конфіденційності',
                    'policy',
                    'admin:content_privacypage_changelist',
                ),
                _item('Публічна оферта', 'gavel', 'admin:content_offerpage_changelist'),
                _item('Файли cookie', 'cookie', 'admin:content_cookiepage_changelist'),
            ],
        },
        {
            'title': 'Списки на сторінках',
            'separator': True,
            'collapsible': True,
            'items': [
                _item('Картки послуг', 'list', 'admin:content_service_changelist'),
                _item('Пункти переваг', 'checklist', 'admin:content_advantageitem_changelist'),
                _item('Питання і відповіді', 'quiz', 'admin:content_faqitem_changelist'),
                _item('Статті блогу', 'newspaper', 'admin:blog_post_changelist'),
                _item('Категорії блогу', 'category', 'admin:blog_category_changelist'),
            ],
        },
        {
            'title': 'Заявки та відгуки',
            'separator': True,
            'collapsible': True,
            'items': [
                _item('Заявки на обмін', 'assignment', 'admin:leads_exchangerequest_changelist'),
                _item('Повідомлення з форми', 'mail', 'admin:leads_contactmessage_changelist'),
                _item('Відгуки клієнтів', 'reviews', 'admin:reviews_review_changelist'),
            ],
        },
        {
            'title': 'Мережа і курси',
            'separator': True,
            'collapsible': True,
            'items': [
                _item('Міста мережі', 'map', 'admin:network_city_changelist'),
                _item('Відділення', 'store', 'admin:network_branch_changelist'),
                _item('Валютні пари', 'payments', 'admin:rates_currencypair_changelist'),
                _item('Таблиця курсів', 'table_chart', 'admin:rates_quote_changelist'),
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
