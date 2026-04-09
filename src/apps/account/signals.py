import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from apps.account.models import M_User, T_Profile

User: M_User = get_user_model()

@receiver(post_save, sender=User)
def create_profile(sender, instance: M_User, created, **kwargs):
    """
    M_User が作成されたら T_Profile を自動作成する。
    """
    if created:
        # 画面表示用IDに初期値としてUUIDの頭8文字などをセット
        default_display_id = str(uuid.uuid4())[:8]
        
        T_Profile.objects.create(
            user=instance,
            user_id_display=default_display_id,
            display_name=instance.email.split('@')[0], # 仮の名称
            affiliation=None,
            bio=None,
            icon=None,
            is_setup_completed=False,
            status_code=T_Profile.AccountStatues.ACTIVE,
            locked_until_at=None,
            created_by=instance,
            created_method="signal-create-profile",
            updated_by=instance,
            updated_method="signal-create-profile",
        )