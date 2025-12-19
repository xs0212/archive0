from rest_framework import serializers


class SearchRequestSerializer(serializers.Serializer):
    time_start = serializers.DateTimeField()
    time_end = serializers.DateTimeField()
    departments = serializers.ListField(child=serializers.CharField(), required=False)
    participants = serializers.ListField(child=serializers.EmailField(), required=False)
    subject = serializers.CharField(required=False)
    keywords = serializers.CharField(required=False)
    fuzzy = serializers.BooleanField(required=False, default=False)
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    size = serializers.IntegerField(required=False, min_value=1, max_value=200, default=50)

    def validate(self, data):
        if data["time_end"] < data["time_start"]:
            raise serializers.ValidationError("invalid_time_range")
        return data
