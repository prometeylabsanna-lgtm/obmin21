# SEO-аудит Обмін21 — 28.10.2026

Перевірка шаблонів, view і sitemap. Дизайн, кольори, `.env` і OG-картинка не змінювались.
Статус нижче — після head/schema/canonical/robots/llms і другого проходу: FAQPage, рубрики, розміри картинок, відділення в LocalBusiness.

## Підсумок

| Перевірка | Статус |
| --- | --- |
| Title на публічних сторінках | PASS |
| Meta description | PASS |
| Один осмислений H1 | PASS, крім статті в режимі «лише обмін» без `h1a`/`h1b` |
| Canonical `https://obmin21.com` без query | PASS |
| hreflang і x-default | PASS |
| OG image 1200×630, `og:url` = canonical | PASS |
| JSON-LD Organization / FinancialService / LocalBusiness | PASS |
| JSON-LD BreadcrumbList | PASS |
| JSON-LD Article для блогу | PASS |
| Product / Offer JSON-LD | PASS (не додавались) |
| FAQPage JSON-LD | PASS |
| Оцінка лише з видимих відгуків | PASS |
| Зображення: WebP, lazy, width/height | PASS для дірок з аудиту |
| Sitemap лише індексовані URL і `.visible()` | PASS |
| robots.txt | PASS |
| llms.txt | PASS |
| Адмінка закрита від індексації без витоку шляху | PASS |
| `?city=` і `?direct=` | PASS: це фільтр тієї самої сторінки, Disallow лишився |

## Title і description

Поля `seo_title` / `seo_description` є в CMS там, де модель їх має. View віддають `page_title` і `page_description` через `mode_meta`, тож у режимі «лише обмін» береться `*_mode`, а не базовий текст.

- Головна, курси, пара, послуги, переваги, контакти, FAQ, три юридичні сторінки, блог, стаття, відгуки, міста, місто: title і description є. PASS.
- 404 і прихована сторінка мають запасний опис готівкового обміну. PASS.
- Рубрика блогу: title, description і H1 тепер від рубрики. Див. H1.

## H1–H6

- PASS. `/faq/`: заголовок сторінки — `h1.faq-section__title`. Клас той самий, що був у `h2`. На головній, послугах і перевагах блок FAQ лишається `h2`, щоб на сторінці не з’явився другий H1.
- PASS. `/blog/kategoriya/<slug>/`: один H1 — назва рубрики, клас `blog-hero__title`. Title і description теж від рубрики.
- FAIL, не чіпалось. Стаття в режимі «лише обмін»: H1 малюється лише якщо в макеті є `h1a` або `h1b`. Інакше банер без H1.

Решта публічних шаблонів мають один H1. Модальні вікна мають власні H2.

### Рубрика блогу

У `blog.Category` немає `seo_title`, `seo_description`, `seo_title_mode`, `seo_description_mode`. Це missing-in-model, поля в адмінці не вигадувались.

Поки полів немає, сторінка бере шаблон з назвою:

- H1 і title: назва рубрики
- description: `Статті рубрики {назва}.`

Якщо поле з’явиться в моделі і буде заповнене, title/description візьмуть його. У режимі «лише обмін» читаються лише `seo_*_mode`. Порожній `*_mode` не підміняється базовим `seo_*`.

У локальній базі 6 рубрик, у всіх `show_in_filter` увімкнено. Назви не виводились.

## Canonical

Канонічна адреса — `SITE_URL` (за замовчуванням `https://obmin21.com`) і шлях без query. `og:url` дорівнює їй. Сторінка з технічним query отримує `noindex, follow`.

## hreflang

PASS. У `LANGUAGES` лише `uk`. Окремої RU-версії немає, пари hreflang і `x-default` не додавались.

## Open Graph

`og:image` — `images/og-obmin21.webp`, файл 1200×630, WebP. Файл не змінювався. Для статті `og:type` = `article`, для решти `website`.

## JSON-LD

На публічних сторінках один граф:

- `Organization`
- `FinancialService` разом із `LocalBusiness`
- `department` — по одному вузлу на активне відділення активного міста
- `BreadcrumbList`, якщо на сторінці є крихти
- `Article` на `/blog/<slug>/`
- `FAQPage` на `/` і `/faq/`

`Product` і `Offer` не додавались.

### FAQPage

Питання в JSON-LD — ті самі, що в видимому блоці поточної сторінки:

- головна: `public_faq_items(limit=8)` і фільтр шаблону `exchange_safe` у режимі «лише обмін»
- `/faq/`: той самий список без ліміту 8, включно із запасом `BASE_FAQ`, коли в режимі немає жодного видимого питання
- послуги і переваги мають свій блок FAQ у HTML, але `FAQPage` туди не ставиться

У режимі «лише обмін» питання або відповідь зі стоп-словом (`src/core/seo_words.py` і список режиму) у JSON-LD не потрапляє: поле не переписується «очищеним» текстом, вузол питання пропускається. Поза режимом видимий текст, навіть зі стоп-словом, лишається в схемі.

### LocalBusiness і відділення

Батьківський вузол лишається мережею. Адреса, гео і графік не вигадуються для нього одним офісом.

Кожне відділення — `department` типу `FinancialService` + `LocalBusiness`:

- `address.streetAddress` — `Branch.address`, якщо непорожнє
- `address.addressLocality` — `City.name`, а в режимі «лише обмін» лише `City.name_mode`
- `geo` — лише коли заповнені і `lat`, і `lng`. Одна координата без другої не доповнюється
- `openingHours` — рядок `Branch.hours`, без розбору на дні тижня
- `telephone` — `Branch.phone`, якщо непорожній
- `name` складається лише з уже відданих назви міста і адреси

Порожнє значення або стоп-слово в режимі «лише обмін» прибирає це поле. Неактивне відділення і відділення неактивного міста не потрапляють у граф. `addressCountry`, `postalCode`, `addressRegion`, `dayOfWeek`, `opens`, `closes` у моделі немає, тож у JSON-LD їх немає.

`aggregateRating` є лише з `Review.objects.visible()` і опублікованих відгуків. Тексти відгуків у JSON-LD не копіюються.

У режимі «лише обмін» список валют `UAH, USD, EUR, PLN` у схему не потрапляє.

## Поля адмінки для адреси, гео і графіка

Підрахунок з `../Obmin21/db.sqlite3`, відкритої лише на читання (`file:...?mode=ro`). Значення не виводились. Записів не змінювалось.

Рядки: `network_city` — 16 (активних 11, неактивних 5), `network_branch` — 16 (усі активні). У схему потрапляють 11 відділень, бо місто в них активне.

| Модель | Поле | Стан |
| --- | --- | --- |
| Branch | address | є в моделі; заповнено 16, порожньо 0 |
| Branch | hours (`openingHours`) | є в моделі; заповнено 16, порожньо 0 |
| Branch | lat | є в моделі; заповнено 0, порожньо 16 |
| Branch | lng | є в моделі; заповнено 0, порожньо 16 |
| Branch | phone | є в моделі; заповнено 16, порожньо 0 |
| City | name | є в моделі; заповнено 16, порожньо 0 |
| City | name_mode | є в моделі; заповнено 16, порожньо 0 |
| City | address, lat, lng, hours | missing-in-model |
| City, Branch | postalCode, addressRegion, addressCountry | missing-in-model |
| City, Branch | dayOfWeek, opens, closes | missing-in-model |
| Category | seo_title, seo_description, seo_title_mode, seo_description_mode | missing-in-model |

Через порожні `lat`/`lng` у поточних даних жоден `department` не отримує `geo`, доки координати не внесуть в адмінці. Адреса і графік у цих 11 відділень заповнені, тож `streetAddress` і `openingHours` віддаються.

## Зображення

Статичні картинки через `static_img` віддають WebP і мають width/height. Логотип і герой без `loading=lazy` — вони на першому екрані.

Додано width/height з реального файлу або `ImageField.width` / `height`, без зміни CSS:

- картинка в тілі статті (`Post.figure`) і картинка макета (`images/articles/...jpg`, інакше `Post.image_size`)
- фото героя послуг (`ServicesPage.hero_image`)
- монети на «Перевагах» у режимі «лише обмін» (`why_coins_mode`)

Якщо розмір прочитати не вдалось, атрибути не ставляться. Обкладинка з файлу може лишитись не WebP, якщо так збережено в медіа.

## Sitemap

У видачу входять статичні публічні сторінки, опубліковані пости `get_published_posts().visible()`, активні пари `CurrencyPair.objects.visible()`, рубрики від цих постів, активні послуги лише якщо є публічний шлях, активні міста. Чернетки, `/partials/`, `/htmx/`, `/telegram/`, `/tinymce/`, `/admin/` і query в sitemap немає. Протокол `https`.

Рубрика повторює правила сторінки: `show_in_filter`, видимий опублікований пост, і в режимі «лише обмін» приховування за стоп-словом у назві або slug (`category_is_public`). Пост такої рубрики в sitemap лишається, якщо сам пост видимий.

## `?city=` і `?direct=`

Це не окремі посадкові сторінки. `Disallow` лишився. Canonical і без цих параметрів уже був шляхом без query (`src/core/seo.py`, `canonical_url`).

`?city=` змінює лише набір курсів у JSON калькулятора, не HTML-документ:

- `src/core/views.py:169-175` — `_quotes_city` читає `request.GET['city']` і підставляє місто в `quotes_json`
- `src/core/views.py:178-182` — відповідь лишається `/partials/quotes.json`
- `src/core/static/js/booking-modal.js:243-245` — модалка дописує `board=retail&city=` до цього ж JSON
- `src/network/middleware.py:14-20` — місто сторінки береться з сесії або cookie, не з query

`?direct=` лише перемикає крок тієї самої модалки заявки:

- `src/leads/views.py:211` — `booking_direct`, коли метод не POST і `direct=1`
- `templates/partials/modal_request.html:7` і `:69` — ховається перший або другий крок тієї самої форми

Обидва URL уже під `/partials/` або `/htmx/`, які закриті в robots. На публічній сторінці (`/?city=`, `/kursy/?direct=1`, `/kontakty/?city=`) документ той самий, canonical без параметрів: `src/core/seo.py:38-39` (`Disallow`) і `src/core/seo.py:94-98` (`canonical_url`).

## robots.txt і адмінка

- Завжди `Disallow: /admin/`, `/partials/`, `/tinymce/`, `/htmx/`, `/telegram/`, `/*/obraty/`
- Технічні query: `sort`, `utm`, `fbclid`, `gclid`, `yclid`, `gbraid`, `wbraid`, `board`, `limit`, `home`, `hide_full`, `city`, `direct`, `ref`, `_openstat`
- `Sitemap: https://obmin21.com/sitemap.xml`
- `/theme.css` і `/static/` не закриті
- Значення `settings.ADMIN_URL`, якщо воно не `admin/`, у файл не потрапляє
- Префікс справжньої адмінки віддає `X-Robots-Tag: noindex, nofollow`

## llms.txt

`/llms.txt` описує Обмін21, основні розділи і правила для ШІ. У режимі «лише обмін» блок про криптовалюту, золото, перекази і SWIFT не віддається; текст проходить `strip_stop_words` / `contains_stop_word`. Шлях панелі керування не друкується.
