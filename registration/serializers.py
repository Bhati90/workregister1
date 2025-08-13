# File: yourapp/serializers.py (NEW FILE)

from rest_framework import serializers
from .models import IndividualLabor, Mukkadam, Transport, Others
import json

class BaseRegistrationSerializer(serializers.ModelSerializer):
    """
    A base class to automatically handle fields that the JS client might stringify,
    like arrays (skills) or objects (location).
    """
    def to_internal_value(self, data):
        # Create a mutable copy to modify
        mutable_data = data.copy()
        
        # List of fields that might be sent as JSON strings
        json_fields = ['skills', 'communication_preferences', 'supply_areas', 'location']
        
        for field_name in json_fields:
            if field_name in mutable_data and isinstance(mutable_data[field_name], str):
                try:
                    # Attempt to parse the string back into a Python object
                    mutable_data[field_name] = json.loads(mutable_data[field_name])
                except (json.JSONDecodeError, TypeError):
                    # If parsing fails, let the default validation handle the error
                    pass
        
        return super().to_internal_value(mutable_data)

class IndividualLaborSerializer(BaseRegistrationSerializer):
    class Meta:
        model = IndividualLabor
        fields = '__all__' # Using '__all__' for simplicity. List fields explicitly for production.

class MukkadamSerializer(BaseRegistrationSerializer):
    class Meta:
        model = Mukkadam
        fields = '__all__'

class TransportSerializer(BaseRegistrationSerializer):
    class Meta:
        model = Transport
        fields = '__all__'

class OthersSerializer(BaseRegistrationSerializer):
    class Meta:
        model = Others
        fields = '__all__'