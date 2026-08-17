from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("learning", "0005_alter_readingtext_source"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailysession",
            name="active_seconds",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="dailysession",
            name="last_heartbeat_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
