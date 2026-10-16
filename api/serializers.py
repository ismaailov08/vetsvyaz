from rest_framework import serializers

from consultations.models import Consultation, Prescription
from farms.models import Animal, Vaccination
from twin.models import Reading, Sensor


class VaccinationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vaccination
        fields = ["id", "vaccine", "done_on", "next_on"]


class AnimalSerializer(serializers.ModelSerializer):
    species_display = serializers.CharField(source="get_species_display", read_only=True)
    vaccinations = VaccinationSerializer(many=True, read_only=True)

    class Meta:
        model = Animal
        fields = ["id", "tag", "name", "species", "species_display", "breed", "sex", "born",
                  "weight_kg", "status", "vaccinations"]


class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prescription
        fields = ["drug", "dose", "days", "withdrawal_days"]


class ConsultationSerializer(serializers.ModelSerializer):
    prescriptions = PrescriptionSerializer(many=True, read_only=True)

    class Meta:
        model = Consultation
        fields = ["id", "animal", "vet", "kind", "scheduled_at", "complaint", "status", "diagnosis",
                  "conclusion", "prescriptions"]
        read_only_fields = ["status", "diagnosis", "conclusion"]


class ReadingSerializer(serializers.ModelSerializer):
    serial = serializers.SlugRelatedField(source="sensor", slug_field="serial", queryset=Sensor.objects.all())

    class Meta:
        model = Reading
        fields = ["id", "serial", "taken_at", "temperature", "heart_rate", "activity", "rumination"]
