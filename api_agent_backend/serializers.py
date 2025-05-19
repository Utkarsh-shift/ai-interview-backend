from rest_framework import serializers
from .models import StudentJobData
from .models import JobDetails


class StudentDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentJobData
        fields = '__all__'


class JobDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobDetails
        fields = '__all__'        