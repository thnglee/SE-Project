import os
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.files.storage import default_storage
from django.http import StreamingHttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from myApp.forms import UserInfo, SongInfo, SongInfoUpdate, UserInfoUpdate, UserProfileInfoUpdate, AlbumInfo
from myApp.models import Song, UserProfile, Artist, Album


# Create your views here.
class Login(LoginView):
    template_name = 'forms/user/authentication/login.html'
    next_page = 'home'


class Logout(LogoutView):
    next_page = 'home'


def register(request):
    if request.method == 'POST':
        form = UserInfo(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data['email']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()

            if 'image_file' in request.FILES:
                image = request.FILES['image_file']
                new_image_name = form.cleaned_data['username'] + os.path.splitext(image.name)[1]
                print(new_image_name)
                default_storage.save('image/user/' + new_image_name, image)
            else:
                new_image_name = 'default.png'
                print(new_image_name)

            user_profile = UserProfile(user=user,
                                       image_uri=new_image_name,
                                       age=form.cleaned_data['age'],
                                       sex=form.cleaned_data['sex'])
            user_profile.save()
            form.save()
            return redirect('login')
    else:
        form = UserInfo()
    return render(request, 'forms/user/authentication/register.html', {'form': form})


def update_user_info(request):
    user_profile = UserProfile.objects.get(user=request.user)
    if request.method == 'POST':
        user_form = UserInfoUpdate(request.POST, instance=request.user)
        user_profile_form = UserProfileInfoUpdate(request.POST, request.FILES, instance=user_profile)
        if user_form.is_valid() and user_profile_form.is_valid():
            user_form.save()
            profile = user_profile_form.save(commit=False)

            # Image
            if 'image_file' in request.FILES:
                # Delete the old image file
                if user_profile.image_uri:
                    default_storage.delete('image/user/' + user_profile.image_uri)

                image = request.FILES['image_file']
                new_image_name = user_profile.user.username + os.path.splitext(image.name)[1]
                default_storage.save('image/user/' + new_image_name, image)
                profile.image_uri = new_image_name

            # Artist
            if user_profile_form.cleaned_data.get('become_artist'):
                if hasattr(user_profile, 'artist'):
                    user_profile.artist.Artist_name = user_profile_form.cleaned_data.get('artist_name')
                    user_profile.artist.save()
                else:
                    Artist.objects.create(user=user_profile,
                                          Artist_name=user_profile_form.cleaned_data.get('artist_name'))
            else:
                if hasattr(user_profile, 'artist'):
                    user_profile.artist.delete()

            profile.save()

            return redirect('home')
    else:
        user_form = UserInfoUpdate(instance=request.user)
        user_profile_form = UserProfileInfoUpdate(instance=user_profile)

    return render(request, 'forms/user/update_user_info.html',
                  {'user_form': user_form, 'profile_form': user_profile_form})


@login_required(login_url='/login/')
def delete_user(request):
    User = get_user_model()
    user = get_object_or_404(User, username=request.user.username)
    user_profile = UserProfile.objects.get(user=user)

    songs = Song.objects.filter(artists__user=user_profile)

    # Delete song files and images
    for song in songs:
        if song.uri:
            default_storage.delete('audio/' + song.uri)
        if song.image_uri != 'default.png':
            default_storage.delete('image/song/' + song.image_uri)
        song.delete()

    # Delete user image
    if user_profile.image_uri != 'default.png':
        default_storage.delete('image/user/' + user_profile.image_uri)
    user.delete()

    return redirect('home')


def home(request):
    songs = Song.objects.all()  # get all songs in the database
    if request.user.is_authenticated:
        user = request.user  # get the username of the current user
        user_profile = UserProfile.objects.get(user=user)  # get the user profile object
        artist = Artist.objects.filter(user=user_profile)  # get the artist object
        return render(request,
                      'home.html',
                      {'songs': songs, 'user': user, 'user_profile': user_profile, 'artist': artist})
    else:
        return render(request, 'home.html', {'songs': songs})


@login_required(login_url='/login/')
def upload_song(request):
    user_profile = UserProfile.objects.get(user=request.user)
    if not hasattr(user_profile, 'artist'):
        return redirect('update_user_info')
    if request.method == 'POST':
        form = SongInfo(request.POST, request.FILES)
        if form.is_valid():
            song = form.save(commit=False)
            user_profile = UserProfile.objects.get(user=request.user)
            artist = Artist.objects.get(user=user_profile)
            new_name = artist.Artist_name + "_" + clean_filename(form.cleaned_data['song_name'])

            # Name
            song.name = form.cleaned_data['song_name']

            # Image
            if 'image_file' in request.FILES:
                image = request.FILES['image_file']
                new_image_name = new_name + os.path.splitext(image.name)[1]
                default_storage.save('image/song/' + new_image_name, image)
            else:
                new_image_name = 'default.png'
            song.image_uri = new_image_name

            # Audio
            song_file = request.FILES['song_file']
            new_song_filename = new_name + os.path.splitext(song_file.name)[1]
            default_storage.save('audio/' + new_song_filename, song_file)
            song.uri = new_song_filename

            # Genre
            song.genres = form.cleaned_data['genres']

            # Save the song object
            song.save()

            # Album
            song.albums.add(form.cleaned_data['album'])

            # Artist
            song.artists.add(artist)

            form.save_m2m()  # save many-to-many data
            return redirect('home')
    else:
        form = SongInfo()

    return render(request, 'forms/song/upload_song.html', {'form': form})


def stream_song(request, song_id):
    song = get_object_or_404(Song, id=song_id)
    song_path = settings.MEDIA_ROOT + song.get_uri()

    # Get the file extension
    _, file_extension = os.path.splitext(song_path)

    # Determine the content type based on the file extension
    if file_extension.lower() == '.mp3':
        content_type = 'audio/mpeg'
    elif file_extension.lower() == '.flac':
        content_type = 'audio/flac'
    else:
        content_type = 'application/octet-stream'  # Default content type

    # Read the entire file into memory
    with open(song_path, 'rb') as song_file:
        song_data = song_file.read()

    def song_generator():
        yield song_data

    response = StreamingHttpResponse(song_generator(), content_type=content_type)
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(os.path.basename(song_path))

    return response


def update_song(request, song_id):
    try:
        song = get_object_or_404(Song, id=song_id)
    except Http404:
        return redirect('home')
    user_profile = UserProfile.objects.get(user=request.user)
    if not song.artists.filter(user=user_profile).exists():
        return redirect('home')

    if request.method == 'POST':
        form = SongInfoUpdate(request.POST, request.FILES, instance=song)
        if form.is_valid():
            song = form.save(commit=False)

            artist = Artist.objects.get(user=user_profile)
            new_name = artist.Artist_name + "_" + clean_filename(form.cleaned_data['name'])

            # Name
            if 'name' in form.changed_data:
                song.name = form.cleaned_data['name']

            # Audio
            if 'song_file' in request.FILES:
                # Delete the old song file
                if song.uri:
                    default_storage.delete('audio/' + song.uri)

                song_file = request.FILES['song_file']
                new_song_filename = new_name + os.path.splitext(song_file.name)[1]
                default_storage.save('audio/' + new_song_filename, song_file)
                song.uri = new_song_filename

            # Image
            if 'image_file' in request.FILES:
                # Delete the old image file
                if song.image_uri != 'default.png':
                    default_storage.delete('image/song/' + song.image_uri)

                image = request.FILES['image_file']
                new_image_name = new_name + os.path.splitext(image.name)[1]
                default_storage.save('image/song/' + new_image_name, image)
                song.image_uri = new_image_name

            # Genre
            if 'genres' in form.changed_data:
                song.genres = form.cleaned_data['genres']

            song.save()

            # Album
            if 'albums' in form.changed_data:
                song.albums.set(form.cleaned_data['albums'])

            form.save_m2m()  #
            return redirect('home')
    else:
        form = SongInfoUpdate(instance=song)

    return render(request, 'forms/song/update_song.html', {'form': form})


@require_POST
def delete_song(request, song_id):
    song = get_object_or_404(Song, id=song_id)

    # Delete the song file and image file
    force_delete_media_file('audio/' + song.uri)
    if song.image_uri != 'default.png':
        force_delete_media_file('image/song/' + song.image_uri)

    song.delete()
    return redirect('home')


@login_required(login_url='/login/')
def artist_page(request, artist_id):
    user_profile = UserProfile.objects.get(user=request.user)
    if not hasattr(user_profile, 'artist'):
        return redirect('home')

    artist = Artist.objects.get(id=artist_id)
    songs = Song.objects.filter(artists=artist)
    albums = Album.objects.filter(artist=artist)

    return render(request, 'forms/user/artist_page.html', {'artist': artist, 'songs': songs, 'albums': albums})


@login_required(login_url='/login/')
def create_album(request):
    user_profile = UserProfile.objects.get(user=request.user)
    if not hasattr(user_profile, 'artist'):
        return redirect('update_user_info')

    if request.method == 'POST':
        form = AlbumInfo(request.POST, request.FILES)
        if form.is_valid():
            album = form.save(commit=False)
            album.artist = user_profile.artist

            # Name
            album.name = form.cleaned_data['album_name']

            # Image
            if 'image_file' in request.FILES:
                image = request.FILES['image_file']
                new_image_name = (album.artist.Artist_name + "_"
                                  + clean_filename(form.cleaned_data['album_name'])
                                  + os.path.splitext(image.name)[1])
                default_storage.save('image/album/' + new_image_name, image)
                album.image_uri = new_image_name
            else:
                album.image_uri = 'default.png'

            album.save()
            form.save_m2m()
            return redirect('home')
    else:
        form = AlbumInfo(user=request.user)

    return render(request, 'forms/album/create_album.html', {'form': form})


def clean_filename(filename):
    # Define a regex pattern for the invalid characters
    invalid_chars_pattern = r'[\\/*?:"<>|]'
    # Replace the invalid characters with an empty string
    cleaned_filename = re.sub(invalid_chars_pattern, '', filename)
    return cleaned_filename


def force_delete_media_file(file_path):
    if default_storage.exists(file_path):
        default_storage.delete(file_path)
