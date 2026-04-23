import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.artist.models import T_Artist

print("Total artists:", T_Artist.objects.count())
for a in T_Artist.objects.all():
    print(a.id, "Spotify:", a.spotify_id, "Deezer:", a.deezer_id, "User:", a.user_id)
