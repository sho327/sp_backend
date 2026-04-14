import factory
from django.utils import timezone
from datetime import timedelta
from apps.common.models import T_SpotifyUserToken

class SpotifyUserTokenFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = T_SpotifyUserToken

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    access_token = factory.Faker("sha256")
    refresh_token = factory.Faker("sha256")
    # デフォルトは有効期限内
    expired_at = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=1))
    refreshing = False
    refreshing_until = None
    deleted_at = None
