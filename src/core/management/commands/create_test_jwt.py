from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

class Command(BaseCommand):
    help = "Create test JWT token for a user"
    
    def add_arguments(self, parser):
        parser.add_argument("email", type=str)
    
    def handle(self, *args, **options):
        User = get_user_model()
        email = options["email"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR("User not found"))
            return
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== JWT Tokens ==="))
        self.stdout.write(f"Access: {str(access)}")
        self.stdout.write("")
        self.stdout.write(f"Refresh: {str(refresh)}")
        self.stdout.write("")

# -------------------------------------------------
# 実行例
# -------------------------------------------------
# python manage.py create_test_jwt test@example.com

# 無期限っぽくする
# from datetime import timedelta
# refresh = RefreshToken.for_user(user)
# refresh.set_exp(lifetime=timedelta(days=3650))
# access = refresh.access_token
# access.set_exp(lifetime=timedelta(days=3650))

# さらに便利（superuser自動）
# python manage.py create_test_jwt admin@example.com
# または
# user = User.objects.filter(is_superuser=True).first()

