# SEO-аудит Обмін21 — 28.10.2026

Перевірка шаблонів, view і sitemap. Дизайн, CSS і `.env` не змінювались.
Статус нижче — після мінімальних правок у head, schema, canonical, robots і llms.

## Підсумок

| Перевірка | Статус |
| --- | --- |
| Title на публічних сторінках | PASS |
| Meta description | PASS |
| Один осмислений H1 | FAIL |
| Canonical `https://obmin21.com` без query | PASS |
| hreflang і x-default | PASS |
| OG image 1200×630, `og:url` = canonical | PASS |
| JSON-LD Organization / FinancialService / LocalBusiness | PASS |
| JSON-LD BreadcrumbList | PASS |
| JSON-LD Article для блогу | PASS |
| Product / Offer JSON-LD | PASS |
| FAQPage JSON-LD | PASS |
| Оцінка лише з видимих відгуків | PASS |
| Зображення: WebP, lazy, width/height | FAIL |
| Sitemap лише індексовані URL і `.visible()` | FAIL |
| robots.txt | PASS |
| llms.txt | PASS |
| Адмінка закрита від індексації без витоку шляху | PASS |

## Title і description

Поля `seo_title` / `seo_description` є в CMS. View віддають `page_title` і `page_description` через `mode_meta`, тож у режимі «лише обмін» береться `*_mode`, а не базовий текст.

- Головна, курси, пара, послуги, переваги, контакти, FAQ, три юридичні сторінки, блог, стаття, відгуки, міста, місто: title і description є. PASS.
- 404 і прихована сторінка раніше не мали description. Тепер у head стоїть запасний опис готівкового обміну. PASS.
- Рубрика блогу: поза режимом title — назва рубрики, у режимі «лише обмін» title знов від сторінки блогу. Description завжди від сторінки блогу, не від рубрики. Див. H1.

## H1–H6

Ієрархія H2/H3 на головній, послугах, перевагах і статті витримана. Окремі сторінки без єдиного H1:

- FAIL. `/faq/`: заголовок сторінки — це H2 у `partials/shared_faq_section.html`. Окремого H1 немає.
- FAIL. `/blog/kategoriya/<slug>/`: H1 і лід — від сторінки блогу, не від рубрики. Разом із спільним description рубрики не відрізняються одна від одної.
- FAIL. Стаття в режимі «лише обмін»: H1 малюється лише якщо в макеті є `h1a` або `h1b`. Інакше банер без H1.

Решта публічних шаблонів мають один H1 (контакти, відгуки, місто — якщо заповнена назва). Модальні вікна мають власні H2 і не замінюють H1 сторінки.

Ці заголовки не змінювались: правка вийшла б за межі head.

## Canonical

Було FAIL: `request.build_absolute_uri` тягнув схему, хост запиту і query (`board`, `sort`, `utm`, `limit`).

Стало PASS. Канонічна адреса з `SITE_URL` (за замовчуванням `https://obmin21.com`) і шлях без query. `og:url` дорівнює їй. Сторінка з технічним query отримує `noindex, follow`, чиста адреса лишається індексованою.

## hreflang

PASS. У `LANGUAGES` лише `uk`, каталогу `locale/ru` немає. Окремої RU-версії немає, тому пари hreflang і `x-default` не додавались. Якщо з’явиться російська мова, `x-default` має вести на uk.

## Open Graph

Було FAIL: тегів OG не було.

Стало PASS. `og:image` — `images/og-obmin21.webp`, файл 1200×630, WebP. У meta стоять width, height і type. `og:url` збігається з canonical. Для статті `og:type` = `article`, для решти `website`. `theme.css` і статичні CSS/JS у robots не закриті.

## JSON-LD

Було FAIL: на статті був неповний `Article` без видавця, картинки і канонічної сторінки. Organization, LocalBusiness і BreadcrumbList не було.

Стало PASS. На публічних сторінках один граф:

- `Organization`
- `FinancialService` разом із `LocalBusiness` (у schema.org немає типу CurrencyExchange; для обмінного пункту це відповідний тип локального бізнесу)
- `BreadcrumbList`, якщо на сторінці є крихти
- `Article` на `/blog/<slug>/`: headline, дати, image, author, publisher

`Product` і `Offer` не додавались.

`FAQPage` не додавався. Це рішення для Анни: розмітка може дати розширений сніпет, але її не варто вмикати, поки Анна не підтвердить, що блок питань на `/faq/` і в секціях головної є основним змістом сторінки, а не допоміжним. Поки що питання лишаються звичайним HTML.

`aggregateRating` є лише якщо є опубліковані відгуки з `Review.objects.visible()`. Неопубліковані і приховані в режимі «лише обмін» у середню оцінку не входять. Якщо таких відгуків немає, оцінки в схемі немає. Тексти відгуків у JSON-LD не копіюються.

У режимі «лише обмін» рядки схеми проходять `strip_stop_words`. Список валют `UAH, USD, EUR, PLN` у цьому режимі в схему не потрапляє, щоб не повертати фразу зі старих блоків послуг.

## Зображення

FAIL. Статичні картинки через `static_img` віддають WebP і мають width/height. Логотип у шапці і герої без `loading=lazy` — це нормально, вони на першому екрані. Нижче згину lazy переважно стоїть.

Дірки, які лишились (шаблони не змінювались):

- `blog/post_detail.html`: картинка в тілі статті і картинки макета мають lazy, але без width/height
- `content/services_list.html`: фото героя з CMS без width/height
- `content/advantages.html`: монети в режимі «лише обмін» без width/height і без lazy
- width/height у карток блогу і послуг пропускаються, якщо в моделі немає розміру
- обкладинка з поля файлу може лишитись не WebP, якщо так збережено в медіа; нові завантаження в адмінці конвертуються окремо

## Sitemap

Частково PASS. У видачу входять статичні публічні сторінки, опубліковані пости `get_published_posts().visible()`, активні пари `CurrencyPair.objects.visible()`, рубрики від цих постів, активні послуги лише якщо є публічний шлях, активні міста. Чернетки, `/partials/`, `/htmx/`, `/telegram/`, `/tinymce/`, `/admin/` і query в sitemap немає. Протокол `https`.

FAIL. `CategorySitemap` не повторює правила сторінки рубрики. Рубрика може потрапити в sitemap, якщо в ній є видимий пост, навіть коли `show_in_filter` вимкнено (тоді URL дає 404) або назва містить стоп-слово (у режимі «лише обмін» сторінка прихована). Це не виправлялось: зміна sitemap поза межами head, schema, canonical, robots і llms.

## robots.txt і адмінка

Було FAIL. `Disallow: /admin/` з’являвся лише коли `ADMIN_URL` уже був `admin/`. Рядок Sitemap брав хост запиту. Службові URL і технічні query не були закриті.

Стало PASS.

- Завжди `Disallow: /admin/`, `/partials/`, `/tinymce/`, `/htmx/`, `/telegram/`, `/*/obraty/`
- Технічні query: `sort`, `utm`, `fbclid`, `gclid`, `yclid`, `gbraid`, `wbraid`, `board`, `limit`, `home`, `hide_full`, `city`, `direct`, `ref`, `_openstat`
- `Sitemap: https://obmin21.com/sitemap.xml`
- `/theme.css` і `/static/` не закриті: вони потрібні для відмальовування
- Значення `settings.ADMIN_URL`, якщо воно не `admin/`, у файл не потрапляє
- Префікс справжньої адмінки віддає заголовок `X-Robots-Tag: noindex, nofollow`

## llms.txt

Було FAIL: адреси не було.

Стало PASS. `/llms.txt` описує Обмін21, основні розділи і правила для ШІ. У режимі «лише обмін» блок про криптовалюту, золото, перекази і SWIFT не віддається; текст ще проходить `strip_stop_words` / `contains_stop_word`. Шлях панелі керування не друкується.
