from html import escape


def sanitize_bot_html(value):
    text = str(value or '').replace('\r\n', '\n').replace('\r', '\n')
    escaped = escape(text, quote=False)
    escaped = escaped.replace('\n', '<br>')
    allowed = (
        ('&lt;b&gt;', '<b>'),
        ('&lt;/b&gt;', '</b>'),
        ('&lt;i&gt;', '<i>'),
        ('&lt;/i&gt;', '</i>'),
        ('&lt;br&gt;', '<br>'),
        ('&lt;br/&gt;', '<br>'),
        ('&lt;br /&gt;', '<br>'),
        ('&lt;B&gt;', '<b>'),
        ('&lt;/B&gt;', '</b>'),
        ('&lt;I&gt;', '<i>'),
        ('&lt;/I&gt;', '</i>'),
        ('&lt;BR&gt;', '<br>'),
        ('&lt;BR/&gt;', '<br>'),
        ('&lt;BR /&gt;', '<br>'),
    )
    for src, dst in allowed:
        escaped = escaped.replace(src, dst)
    return escaped
