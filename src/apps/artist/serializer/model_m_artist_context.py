from rest_framework import serializers
from apps.artist.models import M_ArtistContext

class Model_M_ArtistContextSerializer(serializers.ModelSerializer):
    class Meta:
        model = M_ArtistContext
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
