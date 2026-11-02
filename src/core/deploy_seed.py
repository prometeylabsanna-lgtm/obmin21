"""Правила deploy/migrate наповнення: порожні поля лише в RunPython, не при повторному deploy."""


class SeedFillContext:
    """Передати замість schema_editor у seed_demo для первинного наповнення."""


SEED_FILL_CONTEXT = SeedFillContext()


def migration_context(schema_editor):
    return schema_editor is not None


def empty_needs_seed(value, schema_editor):
    if not migration_context(schema_editor):
        return False
    return not str(value or '').strip()


def json_needs_seed(value, schema_editor):
    if not migration_context(schema_editor):
        return False
    if value in (None, '', [], ()):
        return True
    return isinstance(value, dict) and not value


def run_deploy_fill_pipeline(apps, schema_editor):
    """Усі fill-функції, які міграції викликають повторно на deploy (schema_editor=None)."""
    from src.content.advantages_mode_copy import fill_advantages_page_mode
    from src.content.home_copy import fill_calc_lock
    from src.content.legal_copy import apply_legal_replacements
    from src.content.page_meta_mode import fill_page_meta_mode
    from src.content.promo_slides import fill_promo_slides
    from src.content.public_copy_fill import clear_unseen_public_copy
    from src.content.reader_mode_copy import fill_reader_mode_fields
    from src.content.stage3_fill import (
        fill_article_layouts,
        fill_articles_lead,
        fill_cmp_and_home_lead_mode,
        fill_content_copy,
        fill_home_seo_mode,
        fill_services_page_mode,
    )
    from src.content.visit_steps import fill_home_fallback, fill_visit_steps
    from src.network.city_mode_copy import fill_city_banner_seo_mode, fill_city_name_mode
    from src.network.map_embed_fill import fill_empty_map_embeds
    from src.rates.pair_mode_copy import fill_fiat_pair_mode

    for fn in (
        fill_city_banner_seo_mode,
        fill_city_name_mode,
        fill_fiat_pair_mode,
        fill_content_copy,
        fill_article_layouts,
        fill_services_page_mode,
        fill_home_seo_mode,
        fill_articles_lead,
        fill_cmp_and_home_lead_mode,
        fill_advantages_page_mode,
        fill_page_meta_mode,
        fill_reader_mode_fields,
        fill_promo_slides,
        fill_visit_steps,
        fill_home_fallback,
        fill_calc_lock,
        clear_unseen_public_copy,
        fill_empty_map_embeds,
        apply_legal_replacements,
    ):
        fn(apps, schema_editor)
