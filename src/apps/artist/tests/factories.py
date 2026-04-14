import factory
from apps.account.tests.factories import UserFactory
from apps.artist.models import M_ArtistTag, M_ArtistContext, T_Artist
from apps.common.models import T_FileResource

class ArtistTagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = M_ArtistTag
    name = factory.Sequence(lambda n: f"Tag {n}")

class ArtistContextFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = M_ArtistContext
    name = factory.Sequence(lambda n: f"Context {n}")

class FileResourceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = T_FileResource
    file_type = T_FileResource.FileType.IMAGE
    external_url = factory.Faker("url")
    file_name = factory.Sequence(lambda n: f"spotify_image_{n}")

class ArtistFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = T_Artist

    user = factory.SubFactory(UserFactory)
    spotify_id = factory.Sequence(lambda n: f"spotify_id_{n}")
    name = factory.Faker("name")
    spotify_image = factory.SubFactory(FileResourceFactory)
    context = factory.SubFactory(ArtistContextFactory)