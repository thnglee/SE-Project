# Generated by Django 5.0.4 on 2024-04-23 03:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myApp', '0005_artist_album_playlist_song'),
    ]

    operations = [
        migrations.AlterField(
            model_name='album',
            name='like_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='song',
            name='albums',
            field=models.ManyToManyField(null=True, related_name='songs', to='myApp.album'),
        ),
        migrations.AlterField(
            model_name='song',
            name='like_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='song',
            name='playlists',
            field=models.ManyToManyField(null=True, related_name='songs', to='myApp.playlist'),
        ),
    ]
