import factory
import uuid
from apps.artist.models import M_ArtistTag, M_ArtistContext, T_Artist, R_ArtistTag
from apps.account.tests.factories import UserFactory # 前回のUserFactoryを利用

class ArtistTagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = M_ArtistTag
    name = factory.Sequence(lambda n: f"Tag {n}")

class ArtistContextFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = M_ArtistContext
    name = factory.Sequence(lambda n: f"Context {n}")

class ArtistFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = T_Artist

    # Profileが必要なので、UserのProfileを紐付ける
    user = factory.LazyAttribute(lambda o: UserFactory().user_t_profile_set)
    spotify_id = factory.Sequence(lambda n: f"spotify_id_{n}")
    name = factory.Faker("name")
    genres = ["J-Pop", "Rock"]
    context = factory.SubFactory(ArtistContextFactory)

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for tag in extracted:
                R_ArtistTag.objects.create(artist=self, tag=tag, created_method="factory")