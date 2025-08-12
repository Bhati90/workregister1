# from django import forms
# from django.contrib.gis.geos import Point
# from django.utils import timezone
# from .models import IndividualLabor, Mukkadam, Transport, Others
# import json
# import base64
# from django.core.files.base import ContentFile
# import uuid
# from django.core.validators import RegexValidator

# # Define a common phone regex validator at the top level
# phone_regex = RegexValidator(
#     # Matches:
#     # 1. 10 digits (e.g., 9876543210)
#     # 2. +91 followed by 10 digits (e.g., +919876543210)
#     # 3. 0 followed by 10 digits (e.g., 09876543210)
#     regex=r'^(?:\+91|0)?[6-9]\d{9}$', # For Indian mobile numbers typically starting with 6,7,8,9
#     message="Enter a valid 10-digit Indian phone number (e.g., 9876543210, +919876543210, or 09876543210)."
# )

# class BaseInformationForm(forms.Form):
#     full_name = forms.CharField(
#         max_length=200,
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': 'Enter your full name',
#             'required': True
#         })
#     )

#     mobile_number = forms.CharField(
#         validators=[phone_regex], # <--- Using the regex validator
#         max_length=17, # Increased length
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': 'e.g., +919876543210 or 9876543210',
#             'required': True
#         }),
#         help_text="This will be your username for logging in." # <--- Added help text
#     )

#     password = forms.CharField(
#         widget=forms.PasswordInput(attrs={
#             'class': 'form-control',
#             'placeholder': 'Enter password',
#             'required': True
#         }),
#         label="Password"
#     )
#     password_confirm = forms.CharField(
#         widget=forms.PasswordInput(attrs={
#             'class': 'form-control',
#             'placeholder': 'Confirm password',
#             'required': True
#         }),
#         label="Confirm Password"
#     )

#     taluka = forms.CharField(
#         max_length=100,
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': 'Enter taluka',
#             'required': True
#         })
#     )

#     village = forms.CharField(
#         max_length=100,
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': 'Enter village',
#             'required': True
#         })
#     )


#     # Hidden fields for location data
#     latitude = forms.FloatField(
#         widget=forms.HiddenInput(),
#         required=False
#     )

#     longitude = forms.FloatField(
#         widget=forms.HiddenInput(),
#         required=False
#     )

#     location_accuracy = forms.FloatField(
#         widget=forms.HiddenInput(),
#         required=False
#     )

#     # Hidden field for captured photo data
#     captured_photo = forms.CharField(
#         widget=forms.HiddenInput(),
#         required=False
#     )

#     # Traditional photo upload as fallback
#     photo = forms.ImageField(
#         required=False,
#         widget=forms.FileInput(attrs={
#             'class': 'form-control',
#             'accept': 'image/*',
#             'style': 'display: none;'  # Hidden by default, shown if camera fails
#         })
#     )

#     CATEGORY_CHOICES = [
#         ('', 'Select Category'),
#         ('individual_labor', 'Individual Labor'),
#         ('transport', 'Transport'),
#         ('mukkadam', 'Mukkadam'),
#         ('others', 'Others'),
#     ]

#     category = forms.ChoiceField(
#         choices=CATEGORY_CHOICES,
#         widget=forms.Select(attrs={
#             'class': 'form-control',
#             'required': True
#         })
#     )

#     def clean(self):
#         """Custom validation for location and photo"""
#         cleaned_data = super().clean()
#         password = cleaned_data.get("password")
#         password_confirm = cleaned_data.get("password_confirm")

#         latitude = cleaned_data.get('latitude')
#         longitude = cleaned_data.get('longitude')
#         captured_photo = cleaned_data.get('captured_photo')
#         photo = cleaned_data.get('photo')


#         if password and password_confirm and password != password_confirm:
#             self.add_error('password_confirm', "Passwords do not match.")

#         if password and len(password) < 8:
#             self.add_error('password', "Password must be at least 8 characters long.")
        
#         # Validate location (optional but recommended)
#         if latitude is None or longitude is None:
#             # Location is not required but add a warning
#             self.add_error(None, "Location access was not granted. This may affect service quality.")

#         # Validate photo (at least one method should be used)
#         # if not captured_photo and not photo:
#         #     # Photo is not strictly required but recommended
#         #     self.add_error(None, "No photo was captured or uploaded. This may affect verification process.")

#         return cleaned_data

#     def process_captured_photo(self):
#         """Convert base64 photo data to file"""
#         captured_photo = self.cleaned_data.get('captured_photo')
#         if captured_photo:
#             try:
#                 # Remove data URL prefix (data:image/jpeg;base64,)
#                 format_part, image_data = captured_photo.split(';base64,')
#                 image_format = format_part.split('/')[-1]  # jpeg, png, etc.

#                 # Decode base64
#                 image_binary = base64.b64decode(image_data)

#                 # Create a file
#                 filename = f"captured_{uuid.uuid4().hex}.{image_format}"
#                 image_file = ContentFile(image_binary, name=filename)

#                 return image_file
#             except Exception as e:
#                 # If processing fails, return None
#                 return None
#         return None

#     def get_location_point(self):
#         """Create a PostGIS Point from coordinates"""
#         latitude = self.cleaned_data.get('latitude')
#         longitude = self.cleaned_data.get('longitude')

#         if latitude is not None and longitude is not None:
#             # PostGIS Point format: Point(longitude, latitude)
#             return Point(longitude, latitude, srid=4326)
#         return None

# class IndividualLaborForm(forms.ModelForm):
#     # Skills as checkboxes
#     skills = forms.MultipleChoiceField(
#         choices=[
#             ('pruning', 'Pruning'),
#             ('harvesting', 'Harvesting'),
#             ('dipping', 'Dipping'),
#             ('thinning', 'Thinning'),
#             ('none', 'None'),
#         ],
#         widget=forms.CheckboxSelectMultiple(attrs={
#             'class': 'form-check-input'
#         }),
#         required=False
#     )

#     skill_other = forms.CharField(
#         max_length=200,
#         required=False,
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': 'Specify other skills'
#         })
#     )

#     # Communication preferences as checkboxes
#     communication_preferences = forms.MultipleChoiceField(
#         choices=[
#             ('mobile_app', 'Mobile App'),
#             ('whatsapp', 'WhatsApp'),
#             ('calling', 'Calling'),
#             ('sms', 'SMS'),
#         ],
#         widget=forms.CheckboxSelectMultiple(attrs={
#             'class': 'form-check-input'
#         }),
#         required=False
#     )

#     comm_other = forms.CharField(
#         max_length=200,
#         required=False,
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': 'Specify other communication method'
#         })
#     )

#     class Meta:
#         model = IndividualLabor
#         fields = [
#             'gender', 'age', 'primary_source_income', 'employment_type',
#             'willing_to_migrate', 'expected_wage', 'availability', 'want_training',
#             # 'adult_men_seeking_employment', 'adult_women_seeking_employment',
#             'can_refer_others', 'referral_name', 'referral_contact'
#         ]
#         widgets = {
#             'gender': forms.Select(attrs={'class': 'form-control'}),
#             'age': forms.NumberInput(attrs={'class': 'form-control', 'min': '18', 'max': '65'}),
#             'primary_source_income': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Agriculture, Labor work'}),
#             'employment_type': forms.Select(attrs={'class': 'form-control'}),
#             'willing_to_migrate': forms.Select(attrs={'class': 'form-control'}),
#             'expected_wage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Amount in ₹'}),
#             'availability': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'When are you available to work?'}),
#             'want_training': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
#             # 'adult_men_seeking_employment': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
#             # 'adult_women_seeking_employment': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
#             'can_refer_others': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
#             'referral_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Name of person you can refer'}),
#             'referral_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact number'})
#         }

# class MukkadamForm(forms.ModelForm):
#     # Skills as checkboxes
#     skills = forms.MultipleChoiceField(
#         choices=[
#             ('pruning', 'Pruning'),
#             ('harvesting', 'Harvesting'),
#             ('dipping', 'Dipping'),
#             ('thinning', 'Thinning'),
#             ('none', 'None'),
#         ],
#         widget=forms.CheckboxSelectMultiple(attrs={
#             'class': 'form-check-input'
#         }),
#         required=False
#     )

#     skill_other = forms.CharField(
#         max_length=200,
#         required=False,
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': 'Specify other skills'
#         })
#     )

#     transport_other = forms.CharField(
#         max_length=200,
#         required=False,
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': 'Specify other transport arrangement'
#         })
#     )

#     class Meta:
#         model = Mukkadam
#         fields = [
#             'providing_labour_count', 'total_workers_peak', 'expected_charges',
#             'labour_supply_availability', 'arrange_transport', 'provide_tools', 'supply_areas'
#         ]
#         widgets = {
#             'providing_labour_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Number of laborers you provide'}),
#             'total_workers_peak': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Maximum workers at peak season'}),
#             'expected_charges': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Charges in ₹'}),
#             'labour_supply_availability': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'When can you supply labor?'}),
#             'arrange_transport': forms.Select(attrs={'class': 'form-control'}),
#             'provide_tools': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
#             'supply_areas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Which areas do you supply labor to?'})
#         }

# class TransportForm(forms.ModelForm):
#     class Meta:
#         model = Transport
#         fields = [
#             'vehicle_type', 'people_capacity', 'expected_fair', 'availability', 'service_areas'
#         ]
#         widgets = {
#             'vehicle_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Bus, Tempo, Van'}),
#             'people_capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Number of people it can carry'}),
#             'expected_fair': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Transport fare in ₹'}),
#             'availability': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'When is your transport available?'}),
#             'service_areas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'What areas do you offer transport to?'})
#         }

# class OthersForm(forms.ModelForm):
#     class Meta:
#         model = Others
#         fields = [
#             'business_name', 'interested_referrals', 'help_description', 'know_mukadams_labourers'
#         ]
#         widgets = {
#             'business_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your business name'}),
#             'interested_referrals': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
#             'help_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'How can you help source labor or connect us?'}),
#             'know_mukadams_labourers': forms.CheckboxInput(attrs={'class': 'form-check-input'})
#         }

# class DataSharingAgreementForm(forms.Form):
#     agreement_text = """
#     I hereby agree to share my personal and professional information for the purpose of
#     connecting with potential employers and service providers in the agricultural sector.
#     I understand that this information will be used to match me with relevant opportunities
#     and may be shared with verified employers and contractors.

#     I consent to:
#     - Storage and processing of my personal information including location data
#     - Sharing my contact details with potential employers/clients
#     - Receiving communications regarding work opportunities
#     - Use of my information for labor market analysis and improvement of services
#     - Collection and use of my location data for job matching purposes

#     I understand that I can withdraw this consent at any time by contacting the service provider.
#     """

#     data_sharing_agreement = forms.BooleanField(
#         required=True,
#         widget=forms.CheckboxInput(attrs={
#             'class': 'form-check-input'
#         }),
#         label="I agree to the data sharing terms and conditions including location data usage"
#     )

from django import forms
from django.contrib.gis.geos import Point
from django.utils import timezone
from .models import IndividualLabor, Mukkadam, Transport, Others
import json
import base64
from django.core.files.base import ContentFile
import uuid

class BaseInformationForm(forms.Form):
    full_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your full name',
            'required': True
        })
    )

    mobile_number = forms.CharField(
        max_length=13,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '1234567890',
            'required': True
        })
    )


    taluka = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter taluka',
            'required': True
        })
    )

    village = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter village',
            'required': True
        })
    )


    # Hidden fields for location data
    latitude = forms.FloatField(
        widget=forms.HiddenInput(),
        required=False
    )

    longitude = forms.FloatField(
        widget=forms.HiddenInput(),
        required=False
    )

    location_accuracy = forms.FloatField(
        widget=forms.HiddenInput(),
        required=False
    )

    # Hidden field for captured photo data
    captured_photo = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )

    # Traditional photo upload as fallback
    photo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
            'style': 'display: none;'  # Hidden by default, shown if camera fails
        })
    )

    CATEGORY_CHOICES = [
        ('', 'Select Category'),
        ('individual_labor', 'Individual Labor'),
        ('transport', 'Transport'),
        ('mukkadam', 'Mukkadam'),
        ('others', 'Others'),
    ]

    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True
        })
    )

    def clean(self):
        """Custom validation for location and photo"""
        cleaned_data = super().clean()

        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        captured_photo = cleaned_data.get('captured_photo')
        photo = cleaned_data.get('photo')

        # Validate location (optional but recommended)
        if latitude is None or longitude is None:
            # Location is not required but add a warning
            self.add_error(None, "Location access was not granted. This may affect service quality.")

        # Validate photo (at least one method should be used)
        # if not captured_photo and not photo:
        #     # Photo is not strictly required but recommended
        #     self.add_error(None, "No photo was captured or uploaded. This may affect verification process.")

        return cleaned_data

    def process_captured_photo(self):
        """Convert base64 photo data to file"""
        captured_photo = self.cleaned_data.get('captured_photo')
        if captured_photo:
            try:
                # Remove data URL prefix (data:image/jpeg;base64,)
                format_part, image_data = captured_photo.split(';base64,')
                image_format = format_part.split('/')[-1]  # jpeg, png, etc.

                # Decode base64
                image_binary = base64.b64decode(image_data)

                # Create a file
                filename = f"captured_{uuid.uuid4().hex}.{image_format}"
                image_file = ContentFile(image_binary, name=filename)

                return image_file
            except Exception as e:
                # If processing fails, return None
                return None
        return None

    def get_location_point(self):
        """Create a PostGIS Point from coordinates"""
        latitude = self.cleaned_data.get('latitude')
        longitude = self.cleaned_data.get('longitude')

        if latitude is not None and longitude is not None:
            # PostGIS Point format: Point(longitude, latitude)
            return Point(longitude, latitude, srid=4326)
        return None

class IndividualLaborForm(forms.ModelForm):
    # Skills as checkboxes
    skills = forms.MultipleChoiceField(
        choices=[
            ('pruning', 'Pruning'),
            ('harvesting', 'Harvesting'),
            ('dipping', 'Dipping'),
            ('thinning', 'Thinning'),
            ('none', 'None'),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        required=False
    )

    skill_other = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Specify other skills'
        })
    )

    # Communication preferences as checkboxes
    communication_preferences = forms.MultipleChoiceField(
        choices=[
            ('mobile_app', 'Mobile App'),
            ('whatsapp', 'WhatsApp'),
            ('calling', 'Calling'),
            ('sms', 'SMS'),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        required=False
    )

    comm_other = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Specify other communication method'
        })
    )

    class Meta:
        model = IndividualLabor
        fields = [
            'gender', 'age', 'primary_source_income', 'employment_type',
            'willing_to_migrate', 'expected_wage', 'availability', 'want_training',
            'adult_men_seeking_employment', 'adult_women_seeking_employment',
            'can_refer_others', 'referral_name', 'referral_contact'
        ]
        widgets = {
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'min': '18', 'max': '65'}),
            'primary_source_income': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Agriculture, Labor work'}),
            'employment_type': forms.Select(attrs={'class': 'form-control'}),
            'willing_to_migrate': forms.Select(attrs={'class': 'form-control'}),
            'expected_wage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Amount in ₹'}),
            'availability': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'When are you available to work?'}),
            'want_training': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'adult_men_seeking_employment': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'adult_women_seeking_employment': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'can_refer_others': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'referral_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Name of person you can refer'}),
            'referral_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact number'})
        }

class MukkadamForm(forms.ModelForm):
    # Skills as checkboxes
    skills = forms.MultipleChoiceField(
        choices=[
            ('pruning', 'Pruning'),
            ('harvesting', 'Harvesting'),
            ('dipping', 'Dipping'),
            ('thinning', 'Thinning'),
            ('none', 'None'),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        required=False
    )

    skill_other = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Specify other skills'
        })
    )

    transport_other = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Specify other transport arrangement'
        })
    )

    class Meta:
        model = Mukkadam
        fields = [
            'providing_labour_count', 'total_workers_peak', 'expected_charges',
            'labour_supply_availability', 'arrange_transport', 'provide_tools', 'supply_areas'
        ]
        widgets = {
            'providing_labour_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Number of laborers you provide'}),
            'total_workers_peak': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Maximum workers at peak season'}),
            'expected_charges': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Charges in ₹'}),
            'labour_supply_availability': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'When can you supply labor?'}),
            'arrange_transport': forms.Select(attrs={'class': 'form-control'}),
            'provide_tools': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'supply_areas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Which areas do you supply labor to?'})
        }

class TransportForm(forms.ModelForm):
    class Meta:
        model = Transport
        fields = [
            'vehicle_type', 'people_capacity', 'expected_fair', 'availability', 'service_areas'
        ]
        widgets = {
            'vehicle_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Bus, Tempo, Van'}),
            'people_capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Number of people it can carry'}),
            'expected_fair': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Transport fare in ₹'}),
            'availability': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'When is your transport available?'}),
            'service_areas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'What areas do you offer transport to?'})
        }

class OthersForm(forms.ModelForm):
    class Meta:
        model = Others
        fields = [
            'business_name', 'interested_referrals', 'help_description', 'know_mukadams_labourers'
        ]
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your business name'}),
            'interested_referrals': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'help_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'How can you help source labor or connect us?'}),
            'know_mukadams_labourers': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

class DataSharingAgreementForm(forms.Form):
    agreement_text = """
    I hereby agree to share my personal and professional information for the purpose of
    connecting with potential employers and service providers in the agricultural sector.
    I understand that this information will be used to match me with relevant opportunities
    and may be shared with verified employers and contractors.

    I consent to:
    - Storage and processing of my personal information including location data
    - Sharing my contact details with potential employers/clients
    - Receiving communications regarding work opportunities
    - Use of my information for labor market analysis and improvement of services
    - Collection and use of my location data for job matching purposes

    I understand that I can withdraw this consent at any time by contacting the service provider.
    """

    data_sharing_agreement = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label="I agree to the data sharing terms and conditions including location data usage"
    )


# registration/forms.py
from django import forms
from .models import JobBid

class LabourChoiceFieldWithNumber(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        # For each labourer, display their name and mobile number
        return f"{obj.full_name} - {obj.mobile_number}"


class JobBidForm(forms.ModelForm):
    registered_labourers = LabourChoiceFieldWithNumber(
        queryset=IndividualLabor.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False
    )
    uses_registered_labourers = forms.ChoiceField(
        choices=(('no', 'No'), ('yes', 'Yes')),
        widget=forms.RadioSelect,
        label="Are your labourers registered on our platform?"
    )

    class Meta:
        model = JobBid
        fields = [
            'bid_price', 
            'workers_provided', 
            'notes_on_skills',
            'uses_registered_labourers', # Add the new field to the list
            'registered_labourers',    
            'includes_transport', 
            'includes_accommodation', 
            'no_advance_required'
        ]
        widgets = {
            'notes_on_skills': forms.Textarea(attrs={'rows': 3}),
            'registered_labourers': forms.SelectMultiple(attrs={'class': 'form-control'}),
 
        }
        labels = {
            'bid_price': 'Your Total Bid Price (₹)',
            'workers_provided': 'Number of Workers You Can Provide',
            'notes_on_skills': 'Notes on Worker Skills',
            'includes_transport': 'I will arrange and cover transport',
            'includes_accommodation': 'I will arrange and cover accommodation',
            'no_advance_required': 'I do not require an advance payment',

        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make the dropdown not required by default, we'll handle it with JavaScript
        self.fields['registered_labourers'].required = False
