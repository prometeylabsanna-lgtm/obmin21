from src.core.deploy_seed import empty_needs_seed
from src.network.models import default_map_embed_url


def fill_empty_map_embeds(apps, schema_editor):
    Branch = apps.get_model('network', 'Branch')
    for branch in Branch.objects.all().iterator():
        if not empty_needs_seed(branch.map_embed_url, schema_editor):
            continue
        filled = default_map_embed_url(branch.address)
        if not filled:
            continue
        branch.map_embed_url = filled
        branch.save(update_fields=['map_embed_url'])
