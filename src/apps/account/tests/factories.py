import factory
from apps.account.models import M_User, T_Profile, T_UserToken
from django.utils import timezone

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = M_User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    is_active = True
    is_staff = False
    is_superuser = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        password = extracted or "password123"
        self.set_password(password)
        if create:
            self.save()

class UserTokenFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = T_UserToken

    user = factory.SubFactory(UserFactory)
    token_type = T_UserToken.TokenTypes.ACTIVATION
    token_hash = factory.Faker("sha256")
    expired_at = factory.LazyFunction(lambda: timezone.now() + timezone.timedelta(hours=24))
