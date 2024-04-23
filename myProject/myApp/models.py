from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User


# Create your models here.
class UserProfile(models.Model):
    SEX = {
        "M": "Male",
        "F": "Female",
        "N": "None",
    }

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image_uri = models.CharField(max_length=255, default="default.png")
    age = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(150)], null=True, blank=True)
    sex = models.CharField(max_length=1, choices=SEX, default="None")

    def __str__(self):
        return self.user.username

    def get_absolute_url(self):
        return reverse('user-detail', args=[str(self.id)])

    def get_image_uri(self):
        return "/media/image/user/" + self.image_uri


class Artist(models.Model):
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    Artist_name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.Artist_name

    def get_absolute_url(self):
        return reverse('artist-detail', args=[str(self.id)])


class Song(models.Model):
    GENRE = {
        "POP": "Pop",
        "ROCK": "Rock",
        "COUNTRY": "Country",
        "RAP": "Rap",
        "JAZZ": "Jazz",
        "BLUES": "Blues",
        "RNB": "R&B",
        "HIPHOP": "Hip Hop",
        "EDM": "Electronic Dance Music",
        "CLASSICAL": "Classical",
        "REGGAE": "Reggae",
        "HEAVY_METAL": "Heavy Metal",
        "FOLK": "Folk",
        "SOUL": "Soul",
        "PUNK": "Punk",
        "ALTERNATIVE": "Alternative",
        "INDIE": "Indie",
        "OTHER": "Other",
    }

    name = models.CharField(max_length=100)
    image_uri = models.CharField(max_length=255, default="default.png")
    uri = models.CharField(max_length=255, unique=True)
    like_count = models.IntegerField(default=0)
    genres = models.CharField(max_length=255, choices=GENRE, default="Other")
    artists = models.ManyToManyField('Artist', related_name='songs')
    albums = models.ManyToManyField('Album', related_name='songs', blank=True)
    playlists = models.ManyToManyField('Playlist', related_name='songs', blank=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('song-detail', args=[str(self.id)])

    def get_image_uri(self):
        return "/media/image/song/" + self.image_uri

    def get_uri(self):
        return "/media/audio/" + self.uri


class Album(models.Model):
    name = models.CharField(max_length=255)
    image_uri = models.CharField(max_length=255, default="default.png")
    like_count = models.IntegerField(default=0)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('album-detail', args=[str(self.id)])

    def get_image_uri(self):
        return "/media/image/album/" + self.image_uri


class Playlist(models.Model):
    name = models.CharField(max_length=255)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('playlist-detail', args=[str(self.id)])

    def get_all_songs(self):
        return self.songs.all()
