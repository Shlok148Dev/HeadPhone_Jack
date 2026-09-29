from django.db import migrations

FLAGS = [
    ("apple_music_enabled", False, "Apple Music adapter (needs Apple Developer Program)."),
    ("amazon_music_enabled", False, "Amazon Music adapter (BR-11: hidden while off)."),
    ("google_dataportability_enabled", False, "YouTube via Google Data Portability API."),
    ("spotify_direct_enabled", True, "Direct Spotify route for allowlisted testers."),
    ("concerts_enabled", False, "Concerts (EP-10); needs a Ticketmaster key."),
]


def seed(apps, schema_editor):
    FeatureFlag = apps.get_model("core_api", "FeatureFlag")
    for name, enabled, note in FLAGS:
        FeatureFlag.objects.get_or_create(name=name, defaults={"enabled": enabled, "note": note})


def unseed(apps, schema_editor):
    FeatureFlag = apps.get_model("core_api", "FeatureFlag")
    FeatureFlag.objects.filter(name__in=[f[0] for f in FLAGS]).delete()


class Migration(migrations.Migration):
    dependencies = [("core_api", "0001_initial")]

    operations = [migrations.RunPython(seed, unseed)]
