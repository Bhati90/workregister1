# from django.shortcuts import render, redirect
# from django.contrib import messages
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.utils.decorators import method_decorator
# from django.views import View
# from django.utils import timezone
# from django.contrib.gis.geos import Point
# from decimal import Decimal
# import json
# import logging
# from django.contrib.auth.models import User
# from django.db import IntegrityError


# from .forms import (
#     BaseInformationForm, IndividualLaborForm, MukkadamForm,
#     TransportForm, OthersForm, DataSharingAgreementForm
# )
# from .models import IndividualLabor, Mukkadam, Transport, Others

# # Set up logging
# logger = logging.getLogger('registration')

# class MultiStepRegistrationView(View):
#     template_name = 'registration/multi_step_form.html'

#     def serialize_for_session(self, data):
#         """Convert non-JSON serializable objects to JSON-compatible format"""
#         serialized_data = {}
#         for key, value in data.items():
#             if value is not None:
#                 # Convert Decimal objects to string for JSON serialization
#                 if isinstance(value, Decimal):
#                     serialized_data[key] = str(value)
#                 else:
#                     serialized_data[key] = value
#             else:
#                 serialized_data[key] = value
#         return serialized_data

#     def deserialize_from_session(self, data, field_mapping=None):
#         """Convert session data back to proper types"""
#         if field_mapping is None:
#             field_mapping = {}

#         deserialized_data = {}
#         for key, value in data.items():
#             if key in field_mapping and field_mapping[key] == 'decimal' and value:
#                 # Convert string back to Decimal
#                 deserialized_data[key] = Decimal(str(value))
#             else:
#                 deserialized_data[key] = value
#         return deserialized_data

#     def get_form_class(self, category):
#         """Return the appropriate form class based on category"""
#         form_mapping = {
#             'individual_labor': IndividualLaborForm,
#             'mukkadam': MukkadamForm,
#             'transport': TransportForm,
#             'others': OthersForm,
#         }
#         return form_mapping.get(category)

#     def get_model_class(self, category):
#         """Return the appropriate model class based on category"""
#         model_mapping = {
#             'individual_labor': IndividualLabor,
#             'mukkadam': Mukkadam,
#             'transport': Transport,
#             'others': Others,
#         }
#         return model_mapping.get(category)

#     def get(self, request):
#         step = request.GET.get('step', '1')

#         if step == '1':
#             # Step 1: Basic Information
#             form = BaseInformationForm()
#             context = {
#                 'form': form,
#                 'step': 1,
#                 'step_title': 'Basic Information',
#                 'progress_percent': 33
#             }

#         elif step == '2':
#             # Step 2: Category-specific form
#             category = request.session.get('category')
#             if not category:
#                 return redirect('registration:registration')

#             form_class = self.get_form_class(category)
#             if not form_class:
#                 return redirect('registration:registration')

#             form = form_class()

#             # Get category display name
#             category_names = {
#                 'individual_labor': 'Individual Labor Details',
#                 'mukkadam': 'Mukkadam Details',
#                 'transport': 'Transport Details',
#                 'others': 'Business Details'
#             }

#             context = {
#                 'form': form,
#                 'step': 2,
#                 'step_title': category_names.get(category, 'Category Details'),
#                 'category': category,
#                 'progress_percent': 66
#             }

#         elif step == '3':
#             # Step 3: Data Sharing Agreement
#             if not request.session.get('category'):
#                 return redirect('registration:registration')

#             form = DataSharingAgreementForm()
#             context = {
#                 'form': form,
#                 'step': 3,
#                 'step_title': 'Data Sharing Agreement',
#                 'progress_percent': 100
#             }
#         else:
#             return redirect('registration:registration')

#         return render(request, self.template_name, context)

#     def post(self, request):
#         step = request.POST.get('step')

#         if step == '1':
#             return self.process_step1(request)
#         elif step == '2':
#             return self.process_step2(request)
#         elif step == '3':
#             return self.process_step3(request)
#         else:
#             return redirect('registration:registration')

#     def process_step1(self, request):
#         """Process basic information form with location and camera data"""
#         form = BaseInformationForm(request.POST, request.FILES)

#         if form.is_valid():
#             # Process captured photo
#             captured_photo_file = form.process_captured_photo()

#             # Get location data
#             location_point = form.get_location_point()

#             # Store form data in session
#             basic_info = {
#                 'full_name': form.cleaned_data['full_name'],
#                 'mobile_number': form.cleaned_data['mobile_number'],
#                 'password': form.cleaned_data['password'], # <--- Password stored temporarily in session
#                 'taluka': form.cleaned_data['taluka'],
#                 'village': form.cleaned_data['village'],
#                 'category': form.cleaned_data['category'],
#             }

#             # Store location data if available
#             if location_point:
#                 basic_info.update({
#                     'location_latitude': location_point.y,
#                     'location_longitude': location_point.x,
#                     'location_accuracy': form.cleaned_data.get('location_accuracy'),
#                     'location_timestamp': timezone.now().isoformat(),
#                 })
#                 logger.info(f"Location captured for {form.cleaned_data['full_name']}: {location_point}")

#             # Handle photo (captured or uploaded)
#             photo_saved = False
#             if captured_photo_file:
#                 # Store captured photo temporarily in session
#                 # In production, you might want to save to temporary storage
#                 request.session['has_captured_photo'] = True
#                 # Store the photo data temporarily (you might want to use a different approach)
#                 request.session['captured_photo_data'] = form.cleaned_data.get('captured_photo')
#                 photo_saved = True
#                 logger.info(f"Photo captured for {form.cleaned_data['full_name']}")
#             elif 'photo' in request.FILES:
#                 # Handle traditional file upload
#                 request.session['has_uploaded_photo'] = True
#                 # Store file temporarily (in production, use proper temporary file storage)
#                 photo_saved = True
#                 logger.info(f"Photo uploaded for {form.cleaned_data['full_name']}")

#             request.session['basic_info'] = basic_info
#             request.session['category'] = form.cleaned_data['category']

#             # Add success message
#             success_msg = "Basic information saved successfully."
#             if location_point:
#                 success_msg += " Location captured."
#             if photo_saved:
#                 success_msg += " Photo captured."
#             messages.success(request, success_msg)

#             return redirect('/register/registration/?step=2')
#         else:
#             context = {
#                 'form': form,
#                 'step': 1,
#                 'step_title': 'Basic Information',
#                 'progress_percent': 33
#             }
#             print("Im prbm")
#             print("Form errors:", form.errors)
#             return render(request, self.template_name, context)

#     def process_step2(self, request):
#         """Process category-specific form"""
#         category = request.session.get('category')
#         if not category:
#             return redirect('registration:registration')

#         form_class = self.get_form_class(category)
#         if not form_class:
#             return redirect('registration:registration')

#         form = form_class(request.POST)

#         if form.is_valid():
#             # Store category-specific data in session
#             category_data = {}

#             for field_name, field_value in form.cleaned_data.items():
#                 if field_value is not None:
#                     category_data[field_name] = field_value

#             # Handle special fields for IndividualLabor
#             if category == 'individual_labor':
#                 # Handle skills checkboxes
#                 skills = request.POST.getlist('skills')
#                 category_data['skills'] = skills

#                 # Handle communication preferences
#                 comm_prefs = request.POST.getlist('communication_preferences')
#                 category_data['communication_preferences'] = comm_prefs

#             # Handle special fields for Mukkadam
#             elif category == 'mukkadam':
#                 skills = request.POST.getlist('skills')
#                 category_data['skills'] = skills

#             # Serialize data for session storage (handles Decimal conversion)
#             serialized_data = self.serialize_for_session(category_data)
#             request.session['category_data'] = serialized_data

#             return redirect('/register/registration/?step=3')
#         else:
#             # Get category display name
#             category_names = {
#                 'individual_labor': 'Individual Labor Details',
#                 'mukkadam': 'Mukkadam Details',
#                 'transport': 'Transport Details',
#                 'others': 'Business Details'
#             }

#             context = {
#                 'form': form,
#                 'step': 2,
#                 'step_title': category_names.get(category, 'Category Details'),
#                 'category': category,
#                 'progress_percent': 66
#             }
#             return render(request, self.template_name, context)

#     def process_step3(self, request):
#         """Process data sharing agreement and save all data"""
#         form = DataSharingAgreementForm(request.POST)

#         if form.is_valid():
#             # Get all session data
#             basic_info = request.session.get('basic_info', {})
#             category_data = request.session.get('category_data', {})
#             category = request.session.get('category')

#             if not basic_info or not category:
#                 messages.error(request, 'Session expired. Please start over.')
#                 return redirect('registration:registration')
            
#             basic_info = self.deserialize_from_session(basic_info) # No specific field mapping needed for basic_info unless you store Point objects there
#             logger.info(f"process_step3: Deserialized basic info: {basic_info}")
#              # Extract user credentials
#             mobile_number = basic_info.get('mobile_number')
#             password = basic_info.get('password')
#             full_name = basic_info.get('full_name')
#             # Save to database based on category
#             logger.info(f"process_step3: Retrieved from session - mobile_number: '{mobile_number}', password (raw): '{password[:5]}...' (truncated), full_name: '{full_name}'") # Truncate password for logs

#             if not mobile_number or not password:
#                 logger.error("process_step3: Mobile number or password missing after deserialization from session.")
#                 messages.error(request, 'User credentials (mobile number or password) missing from session. Please restart registration.')
#                 return redirect('registration:registration')

#             user = None
#             created = False

#             try:
#                 logger.info(f"process_step3: Attempting User.objects.get_or_create for username: '{mobile_number}'")
#                 user, created = User.objects.get_or_create(username=mobile_number)
#                 logger.info(f"process_step3: User.objects.get_or_create result: user={user}, created={created}")

#                 if created:
#                     logger.info(f"process_step3: User '{mobile_number}' is NEWLY created. Setting password and saving.")
#                     user.set_password(password)
#                     user.first_name = full_name
#                     user.save()
#                     logger.info(f"process_step3: User '{mobile_number}' (ID: {user.id}) password set and saved to DB.")
#                 else:
#                     logger.warning(f"process_step3: User '{mobile_number}' ALREADY EXISTS. Skipping password set.")
#                     messages.warning(request, f"An account with mobile number {mobile_number} already exists. Please log in or use password reset.")
#                     return redirect('registration:registration')
#                 if category == 'individual_labor':
#                  self.save_individual_labor(request, basic_info, category_data, user) # <--- CALL
#                 elif category == 'mukkadam':
#                  self.save_mukkadam(request, basic_info, category_data, user)         # <--- CALL
#                 elif category == 'transport':
#                  self.save_transport(request, basic_info, category_data, None)       # <--- CALL
#                 elif category == 'others':
#                  self.save_others(request, basic_info, category_data, None)           # <--- CALL

#                 # ... (rest of your save_individual_labor, save_mukkadam calls)
#                 logger.info("process_step3: All save methods called. Clearing session.")
#                 # ... (clear session, success message, redirect)

#             except IntegrityError as e:
#                 logger.error(f"process_step3: CAUGHT IntegrityError: {e}", exc_info=True)
#                 # ... (existing IntegrityError handling)
#             except Exception as e:
#                 logger.error(f"process_step3: CAUGHT General Exception: {e}", exc_info=True)
#                 # ... (existing general Exception handling)
#         else:
#             logger.warning(f"process_step3: DataSharingAgreementForm is INVALID (final check). Errors: {form.errors.as_json()}")
#             context = {
#                 'form': form,
#                 'step': 3,
#                 'step_title': 'Data Sharing Agreement',
#                 'progress_percent': 100
#             }
#             return render(request, self.template_name, context)
#             # try:
#             #     if category == 'individual_labor':
#             #         self.save_individual_labor(request, basic_info, category_data)
#             #     elif category == 'mukkadam':
#             #         self.save_mukkadam(request, basic_info, category_data)
#             #     elif category == 'transport':
#             #         self.save_transport(request, basic_info, category_data)
#             #     elif category == 'others':
#             #         self.save_others(request, basic_info, category_data)

#             #     # Clear session data
#             #     session_keys = [
#             #         'basic_info', 'category_data', 'category',
#             #         'has_captured_photo', 'has_uploaded_photo', 'captured_photo_data'
#             #     ]
#             #     for key in session_keys:
#             #         request.session.pop(key, None)

#             #     messages.success(request, 'Registration completed successfully!')
#             #     logger.info(f"Registration completed for {basic_info.get('full_name', 'Unknown')}")
#             #     return redirect('registration:registration')

#             # except Exception as e:
#             #     logger.error(f"Error saving registration: {str(e)}")
#             #     messages.error(request, f'Error saving registration: {str(e)}')
#             #     return redirect('registration:registration')
#             # else:
#             #      context = {
#             #     'form': form,
#             #     'step': 3,
#             #     'step_title': 'Data Sharing Agreement',
#             #     'progress_percent': 100
#             # }
#             # return render(request, self.template_name, context)

           
#     def save_with_location_and_photo(self, instance, request, basic_info):
#         """Helper method to save location and photo data"""
#         # Set location if available
#         if 'location_latitude' in basic_info and 'location_longitude' in basic_info:
#             instance.location = Point(
#                 basic_info['location_longitude'],
#                 basic_info['location_latitude'],
#                 srid=4326
#             )
#             instance.location_accuracy = basic_info.get('location_accuracy')
#             if basic_info.get('location_timestamp'):
#                 from dateutil import parser
#                 instance.location_timestamp = parser.isoparse(basic_info['location_timestamp'])

#         # Handle photo
#         if request.session.get('has_captured_photo'):
#             # Process captured photo
#             captured_photo_data = request.session.get('captured_photo_data')
#             if captured_photo_data:
#                 form = BaseInformationForm()
#                 form.cleaned_data = {'captured_photo': captured_photo_data}
#                 photo_file = form.process_captured_photo()
#                 if photo_file:
#                     instance.photo.save(photo_file.name, photo_file, save=False)
#         elif request.session.get('has_uploaded_photo') and 'photo' in request.FILES:
#             instance.photo = request.FILES['photo']

#         return instance

#     def save_individual_labor(self, request, basic_info, category_data):
#         """Save Individual Labor registration"""
#         individual = IndividualLabor()

#         # Set basic info
#         for key, value in basic_info.items():
#             if key not in ['location_latitude', 'location_longitude', 'location_accuracy', 'location_timestamp'] and key != 'category':
#                 setattr(individual, key, value)

#         # Set location and photo
#         individual = self.save_with_location_and_photo(individual, request, basic_info)

#         # Define field mapping for decimal conversion
#         field_mapping = {
#             'expected_wage': 'decimal'
#         }

#         # Deserialize category data (convert strings back to proper types)
#         deserialized_data = self.deserialize_from_session(category_data, field_mapping)

#         # Set category-specific data
#         for key, value in deserialized_data.items():
#             if key == 'skills':
#                 # Handle skills checkboxes
#                 individual.skill_pruning = 'pruning' in value
#                 individual.skill_harvesting = 'harvesting' in value
#                 individual.skill_dipping = 'dipping' in value
#                 individual.skill_thinning = 'thinning' in value
#                 individual.skill_none = 'none' in value
#             elif key == 'communication_preferences':
#                 # Handle communication preferences
#                 individual.comm_mobile_app = 'mobile_app' in value
#                 individual.comm_whatsapp = 'whatsapp' in value
#                 individual.comm_calling = 'calling' in value
#                 individual.comm_sms = 'sms' in value
#             else:
#                 setattr(individual, key, value)

#         individual.data_sharing_agreement = True
#         individual.save()
#         logger.info(f"Individual Labor saved: {individual.full_name}")

#     def save_mukkadam(self, request, basic_info, category_data):
#         """Save Mukkadam registration"""
#         mukkadam = Mukkadam()

#         # Set basic info
#         for key, value in basic_info.items():
#             if key not in ['location_latitude', 'location_longitude', 'location_accuracy', 'location_timestamp'] and key != 'category':
#                 setattr(mukkadam, key, value)

#         # Set location and photo
#         mukkadam = self.save_with_location_and_photo(mukkadam, request, basic_info)

#         # Define field mapping for decimal conversion
#         field_mapping = {
#             'expected_charges': 'decimal'
#         }

#         # Deserialize category data (convert strings back to proper types)
#         deserialized_data = self.deserialize_from_session(category_data, field_mapping)

#         # Set category-specific data
#         for key, value in deserialized_data.items():
#             if key == 'skills':
#                 # Handle skills checkboxes
#                 mukkadam.skill_pruning = 'pruning' in value
#                 mukkadam.skill_harvesting = 'harvesting' in value
#                 mukkadam.skill_dipping = 'dipping' in value
#                 mukkadam.skill_thinning = 'thinning' in value
#                 mukkadam.skill_none = 'none' in value
#             else:
#                 setattr(mukkadam, key, value)

#         mukkadam.data_sharing_agreement = True
#         mukkadam.save()
#         logger.info(f"Mukkadam saved: {mukkadam.full_name}")

#     def save_transport(self, request, basic_info, category_data):
#         """Save Transport registration"""
#         transport = Transport()

#         # Set basic info
#         for key, value in basic_info.items():
#             if key not in ['location_latitude', 'location_longitude', 'location_accuracy', 'location_timestamp'] and key != 'category':
#                 setattr(transport, key, value)

#         # Set location and photo
#         transport = self.save_with_location_and_photo(transport, request, basic_info)

#         # Define field mapping for decimal conversion
#         field_mapping = {
#             'expected_fair': 'decimal'
#         }

#         # Deserialize category data (convert strings back to proper types)
#         deserialized_data = self.deserialize_from_session(category_data, field_mapping)

#         # Set category-specific data
#         for key, value in deserialized_data.items():
#             setattr(transport, key, value)

#         transport.data_sharing_agreement = True
#         transport.save()
#         logger.info(f"Transport saved: {transport.full_name}")

#     def save_others(self, request, basic_info, category_data):
#         """Save Others registration"""
#         others = Others()

#         # Set basic info
#         for key, value in basic_info.items():
#             if key not in ['location_latitude', 'location_longitude', 'location_accuracy', 'location_timestamp'] and key != 'category':
#                 setattr(others, key, value)

#         # Set location and photo
#         others = self.save_with_location_and_photo(others, request, basic_info)

#         # No decimal fields in Others model, so no field mapping needed
#         # Set category-specific data
#         for key, value in category_data.items():
#             setattr(others, key, value)

#         others.data_sharing_agreement = True
#         others.save()
#         logger.info(f"Others saved: {others.full_name}")

# def success_view(request):
#     """Success page after registration completion"""
#     return render(request, 'registration/success.html')

# def home_view(request):
#     """Home page with registration link"""
#     return render(request, 'registration/home.html')

# @csrf_exempt
# def location_status_api(request):
#     """API endpoint to check location permissions (optional)"""
#     if request.method == 'POST':
#         data = json.loads(request.body)
#         latitude = data.get('latitude')
#         longitude = data.get('longitude')
#         accuracy = data.get('accuracy')

#         if latitude and longitude:
#             return JsonResponse({
#                 'status': 'success',
#                 'message': 'Location received successfully'
#             })
#         else:
#             return JsonResponse({
#                 'status': 'error',
#                 'message': 'Invalid location data'
#             })

#     return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
# # Ensure username is unique, perhaps using mobile_number



from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views import View
from django.utils import timezone
from django.contrib.gis.geos import Point
from decimal import Decimal
import json
import logging
from dateutil import parser

from .forms import (
    BaseInformationForm, IndividualLaborForm, MukkadamForm,
    TransportForm, OthersForm, DataSharingAgreementForm
)
from .models import IndividualLabor, Mukkadam, Transport, Others

# Set up logging
logger = logging.getLogger('registration')

class MultiStepRegistrationView(View):
    template_name = 'registration/multi_step_form.html'

    # def serialize_for_session(self, data):
    #     """Convert non-JSON serializable objects to JSON-compatible format"""
    #     serialized_data = {}
    #     for key, value in data.items():
    #         if value is not None:
    #             # Convert Decimal objects to string for JSON serialization
    #             if isinstance(value, Decimal):
    #                 serialized_data[key] = str(value)
    #             else:
    #                 serialized_data[key] = value
    #         else:
    #             serialized_data[key] = value
    #     return serialized_data

    # def deserialize_from_session(self, data, field_mapping=None):
    #     """Convert session data back to proper types"""
    #     if field_mapping is None:
    #         field_mapping = {}

    #     deserialized_data = {}
    #     for key, value in data.items():
    #         if key in field_mapping and field_mapping[key] == 'decimal' and value:
    #             # Convert string back to Decimal
    #             deserialized_data[key] = Decimal(str(value))
    #         else:
    #             deserialized_data[key] = value
    #     return deserialized_data

    def get_form_class(self, category):
        """Return the appropriate form class based on category"""
        form_mapping = {
            'individual_labor': IndividualLaborForm,
            'mukkadam': MukkadamForm,
            'transport': TransportForm,
            'others': OthersForm,
        }
        return form_mapping.get(category)

    def get_model_class(self, category):
        """Return the appropriate model class based on category"""
        model_mapping = {
            'individual_labor': IndividualLabor,
            'mukkadam': Mukkadam,
            'transport': Transport,
            'others': Others,
        }
        return model_mapping.get(category)

    # def get(self, request):
        step = request.GET.get('step', '1')

        if step == '1':
            # Step 1: Basic Information
            form = BaseInformationForm()
            context = {
                'form': form,
                'step': 1,
                'step_title': 'Basic Information',
                'progress_percent': 33
            }

        elif step == '2':
            # Step 2: Category-specific form
            category = request.session.get('category')
            if not category:
                return redirect('registration:registration')

            form_class = self.get_form_class(category)
            if not form_class:
                return redirect('registration:registration')

            form = form_class()

            # Get category display name
            category_names = {
                'individual_labor': 'Individual Labor Details',
                'mukkadam': 'Mukkadam Details',
                'transport': 'Transport Details',
                'others': 'Business Details'
            }

            context = {
                'form': form,
                'step': 2,
                'step_title': category_names.get(category, 'Category Details'),
                'category': category,
                'progress_percent': 66
            }

        elif step == '3':
            # Step 3: Data Sharing Agreement
            if not request.session.get('category'):
                return redirect('registration:registration')

            form = DataSharingAgreementForm()
            context = {
                'form': form,
                'step': 3,
                'step_title': 'Data Sharing Agreement',
                'progress_percent': 100
            }
        else:
            return redirect('registration:registration')

        return render(request, self.template_name, context)
     # --- MODIFY THIS METHOD ---
    def get(self, request):
        step = request.GET.get('step', '1')
        # Client-side JS will pass the category via a GET parameter 'current_category_from_db'
        current_category = request.GET.get('current_category_from_db')

        context = {
            'step': int(step), # Ensure step is integer
            'form': None,
            'step_title': '',
            'progress_percent': 0,
            'category': current_category # Pass this to context for dynamic rendering in template
        }

        if step == '1':
            context['form'] = BaseInformationForm()
            context['step_title'] = 'Basic Information'
            context['progress_percent'] = 33

        elif step == '2':
            # If category is missing (e.g., direct access without step 1 having been filled offline)
            if not current_category:
                messages.error(request, 'Please complete basic information first.')
                return redirect('registration:registration')

            form_class = self.get_form_class(current_category)
            if not form_class:
                messages.error(request, 'Invalid category selected.')
                return redirect('registration:registration')

            context['form'] = form_class()
            category_names = {
                'individual_labor': 'Individual Labor Details',
                'mukkadam': 'Mukkadam Details',
                'transport': 'Transport Details',
                'others': 'Business Details'
            }
            context['step_title'] = category_names.get(current_category, 'Category Details')
            context['progress_percent'] = 66

        elif step == '3':
            # Ensure we have a category from step 1
            if not current_category:
                messages.error(request, 'Please complete basic information first.')
                return redirect('registration:registration')

            context['form'] = DataSharingAgreementForm()
            context['step_title'] = 'Data Sharing Agreement'
            context['progress_percent'] = 100
        else:
            return redirect('registration:registration')

        return render(request, self.template_name, context)

    # def post(self, request):
        step = request.POST.get('step')

        if step == '1':
            return self.process_step1(request)
        elif step == '2':
            return self.process_step2(request)
        elif step == '3':
            return self.process_step3(request)
        else:
            return redirect('registration:registration')

    # def process_step1(self, request):
        """Process basic information form with location and camera data"""
        form = BaseInformationForm(request.POST, request.FILES)

        if form.is_valid():
            # Process captured photo
            captured_photo_file = form.process_captured_photo()

            # Get location data
            location_point = form.get_location_point()

            # Store form data in session
            basic_info = {
                'full_name': form.cleaned_data['full_name'],
                'mobile_number': form.cleaned_data['mobile_number'],
                # 'whatsapp_number': form.cleaned_data['whatsapp_number'],
                'taluka': form.cleaned_data['taluka'],
                'village': form.cleaned_data['village'],
                # 'home_address': form.cleaned_data['home_address'],
                'category': form.cleaned_data['category'],
            }

            # Store location data if available
            if location_point:
                basic_info.update({
                    'location_latitude': location_point.y,
                    'location_longitude': location_point.x,
                    'location_accuracy': form.cleaned_data.get('location_accuracy'),
                    'location_timestamp': timezone.now().isoformat(),
                })
                logger.info(f"Location captured for {form.cleaned_data['full_name']}: {location_point}")

            # Handle photo (captured or uploaded)
            photo_saved = False
            if captured_photo_file:
                # Store captured photo temporarily in session
                # In production, you might want to save to temporary storage
                request.session['has_captured_photo'] = True
                # Store the photo data temporarily (you might want to use a different approach)
                request.session['captured_photo_data'] = form.cleaned_data.get('captured_photo')
                photo_saved = True
                logger.info(f"Photo captured for {form.cleaned_data['full_name']}")
            elif 'photo' in request.FILES:
                # Handle traditional file upload
                request.session['has_uploaded_photo'] = True
                # Store file temporarily (in production, use proper temporary file storage)
                photo_saved = True
                logger.info(f"Photo uploaded for {form.cleaned_data['full_name']}")

            request.session['basic_info'] = basic_info
            request.session['category'] = form.cleaned_data['category']

            # Add success message
            success_msg = "Basic information saved successfully."
            if location_point:
                success_msg += " Location captured."
            if photo_saved:
                success_msg += " Photo captured."
            messages.success(request, success_msg)

            return redirect('/register/registration/?step=2')
        else:
            context = {
                'form': form,
                'step': 1,
                'step_title': 'Basic Information',
                'progress_percent': 33
            }
            print("Im prbm")
            return render(request, self.template_name, context)

    # def process_step2(self, request):
        """Process category-specific form"""
        category = request.session.get('category')
        if not category:
            return redirect('registration:registration')

        form_class = self.get_form_class(category)
        if not form_class:
            return redirect('registration:registration')

        form = form_class(request.POST)

        if form.is_valid():
            # Store category-specific data in session
            category_data = {}

            for field_name, field_value in form.cleaned_data.items():
                if field_value is not None:
                    category_data[field_name] = field_value

            # Handle special fields for IndividualLabor
            if category == 'individual_labor':
                # Handle skills checkboxes
                skills = request.POST.getlist('skills')
                category_data['skills'] = skills

                # Handle communication preferences
                comm_prefs = request.POST.getlist('communication_preferences')
                category_data['communication_preferences'] = comm_prefs

            # Handle special fields for Mukkadam
            elif category == 'mukkadam':
                skills = request.POST.getlist('skills')
                category_data['skills'] = skills

            # Serialize data for session storage (handles Decimal conversion)
            serialized_data = self.serialize_for_session(category_data)
            request.session['category_data'] = serialized_data

            return redirect('/register/registration/?step=3')
        else:
            # Get category display name
            category_names = {
                'individual_labor': 'Individual Labor Details',
                'mukkadam': 'Mukkadam Details',
                'transport': 'Transport Details',
                'others': 'Business Details'
            }

            context = {
                'form': form,
                'step': 2,
                'step_title': category_names.get(category, 'Category Details'),
                'category': category,
                'progress_percent': 66
            }
            return render(request, self.template_name, context)

    # def process_step3(self, request):
        """Process data sharing agreement and save all data"""
        form = DataSharingAgreementForm(request.POST)

        if form.is_valid():
            # Get all session data
            basic_info = request.session.get('basic_info', {})
            category_data = request.session.get('category_data', {})
            category = request.session.get('category')

            if not basic_info or not category:
                messages.error(request, 'Session expired. Please start over.')
                return redirect('registration:registration')

            # Save to database based on category
            try:
                if category == 'individual_labor':
                    self.save_individual_labor(request, basic_info, category_data)
                elif category == 'mukkadam':
                    self.save_mukkadam(request, basic_info, category_data)
                elif category == 'transport':
                    self.save_transport(request, basic_info, category_data)
                elif category == 'others':
                    self.save_others(request, basic_info, category_data)

                # Clear session data
                session_keys = [
                    'basic_info', 'category_data', 'category',
                    'has_captured_photo', 'has_uploaded_photo', 'captured_photo_data'
                ]
                for key in session_keys:
                    request.session.pop(key, None)

                messages.success(request, 'Registration completed successfully!')
                logger.info(f"Registration completed for {basic_info.get('full_name', 'Unknown')}")
                return redirect('registration:registration')

            except Exception as e:
                logger.error(f"Error saving registration: {str(e)}")
                messages.error(request, f'Error saving registration: {str(e)}')
                return redirect('registration:registration')
        else:
            context = {
                'form': form,
                'step': 3,
                'step_title': 'Data Sharing Agreement',
                'progress_percent': 100
            }
            return render(request, self.template_name, context)

    # def save_with_location_and_photo(self, instance, request, basic_info):
        """Helper method to save location and photo data"""
        # Set location if available
        if 'location_latitude' in basic_info and 'location_longitude' in basic_info:
            instance.location = Point(
                basic_info['location_longitude'],
                basic_info['location_latitude'],
                srid=4326
            )
            instance.location_accuracy = basic_info.get('location_accuracy')
            if basic_info.get('location_timestamp'):
                from dateutil import parser
                instance.location_timestamp = parser.isoparse(basic_info['location_timestamp'])

        # Handle photo
        if request.session.get('has_captured_photo'):
            # Process captured photo
            captured_photo_data = request.session.get('captured_photo_data')
            if captured_photo_data:
                form = BaseInformationForm()
                form.cleaned_data = {'captured_photo': captured_photo_data}
                photo_file = form.process_captured_photo()
                if photo_file:
                    instance.photo.save(photo_file.name, photo_file, save=False)
        elif request.session.get('has_uploaded_photo') and 'photo' in request.FILES:
            instance.photo = request.FILES['photo']

        return instance

    # def save_individual_labor(self, request, basic_info, category_data):
        """Save Individual Labor registration"""
        individual = IndividualLabor()

        # Set basic info
        for key, value in basic_info.items():
            if key not in ['location_latitude', 'location_longitude', 'location_accuracy', 'location_timestamp'] and key != 'category':
                setattr(individual, key, value)

        # Set location and photo
        individual = self.save_with_location_and_photo(individual, request, basic_info)

        # Define field mapping for decimal conversion
        field_mapping = {
            'expected_wage': 'decimal'
        }

        # Deserialize category data (convert strings back to proper types)
        deserialized_data = self.deserialize_from_session(category_data, field_mapping)

        # Set category-specific data
        for key, value in deserialized_data.items():
            if key == 'skills':
                # Handle skills checkboxes
                individual.skill_pruning = 'pruning' in value
                individual.skill_harvesting = 'harvesting' in value
                individual.skill_dipping = 'dipping' in value
                individual.skill_thinning = 'thinning' in value
                individual.skill_none = 'none' in value
            elif key == 'communication_preferences':
                # Handle communication preferences
                individual.comm_mobile_app = 'mobile_app' in value
                individual.comm_whatsapp = 'whatsapp' in value
                individual.comm_calling = 'calling' in value
                individual.comm_sms = 'sms' in value
            else:
                setattr(individual, key, value)

        individual.data_sharing_agreement = True
        individual.save()
        logger.info(f"Individual Labor saved: {individual.full_name}")

    # def save_mukkadam(self, request, basic_info, category_data):
        """Save Mukkadam registration"""
        mukkadam = Mukkadam()

        # Set basic info
        for key, value in basic_info.items():
            if key not in ['location_latitude', 'location_longitude', 'location_accuracy', 'location_timestamp'] and key != 'category':
                setattr(mukkadam, key, value)

        # Set location and photo
        mukkadam = self.save_with_location_and_photo(mukkadam, request, basic_info)

        # Define field mapping for decimal conversion
        field_mapping = {
            'expected_charges': 'decimal'
        }

        # Deserialize category data (convert strings back to proper types)
        deserialized_data = self.deserialize_from_session(category_data, field_mapping)

        # Set category-specific data
        for key, value in deserialized_data.items():
            if key == 'skills':
                # Handle skills checkboxes
                mukkadam.skill_pruning = 'pruning' in value
                mukkadam.skill_harvesting = 'harvesting' in value
                mukkadam.skill_dipping = 'dipping' in value
                mukkadam.skill_thinning = 'thinning' in value
                mukkadam.skill_none = 'none' in value
            else:
                setattr(mukkadam, key, value)

        mukkadam.data_sharing_agreement = True
        mukkadam.save()
        logger.info(f"Mukkadam saved: {mukkadam.full_name}")

    # def save_transport(self, request, basic_info, category_data):
        """Save Transport registration"""
        transport = Transport()

        # Set basic info
        for key, value in basic_info.items():
            if key not in ['location_latitude', 'location_longitude', 'location_accuracy', 'location_timestamp'] and key != 'category':
                setattr(transport, key, value)

        # Set location and photo
        transport = self.save_with_location_and_photo(transport, request, basic_info)

        # Define field mapping for decimal conversion
        field_mapping = {
            'expected_fair': 'decimal'
        }

        # Deserialize category data (convert strings back to proper types)
        deserialized_data = self.deserialize_from_session(category_data, field_mapping)

        # Set category-specific data
        for key, value in deserialized_data.items():
            setattr(transport, key, value)

        transport.data_sharing_agreement = True
        transport.save()
        logger.info(f"Transport saved: {transport.full_name}")

    # def save_others(self, request, basic_info, category_data):
        """Save Others registration"""
        others = Others()

        # Set basic info
        for key, value in basic_info.items():
            if key not in ['location_latitude', 'location_longitude', 'location_accuracy', 'location_timestamp'] and key != 'category':
                setattr(others, key, value)

        # Set location and photo
        others = self.save_with_location_and_photo(others, request, basic_info)

        # No decimal fields in Others model, so no field mapping needed
        # Set category-specific data
        for key, value in category_data.items():
            setattr(others, key, value)

        others.data_sharing_agreement = True
        others.save()
        logger.info(f"Others saved: {others.full_name}")
    def post(self, request):
        messages.error(request, 'Invalid form submission. Please use the intended PWA flow.')
        return redirect('registration:registration')

def success_view(request):
    """Success page after registration completion"""
    return render(request, 'registration/success.html')

def home_view(request):
    """Home page with registration link"""
    return render(request, 'registration/home.html')

@csrf_exempt # WARNING: For production, implement proper token-based API authentication instead of csrf_exempt
@method_decorator(require_POST, name='dispatch') # Ensure it only accepts POST requests
def submit_registration_api(request):
    try:
        # --- Parse Data from FormData (all fields come from request.POST or request.FILES) ---
        # Text fields, JSON-stringified fields (like location, skills), and files.

        # Basic Information (Step 1 fields)
        full_name = request.POST.get('full_name')
        mobile_number = request.POST.get('mobile_number')
        category = request.POST.get('category')
        taluka = request.POST.get('taluka')
        village = request.POST.get('village')

        # Location data is sent as a JSON string from JS
        location_str = request.POST.get('location')
        location_data = json.loads(location_str) if location_str else None

        # Photo file (sent as a Blob from JS, received as an uploaded file by Django)
        photo_file = request.FILES.get('photo')

        # Category-specific data (Step 2 fields)
        # These are conditionally present based on the category and need parsing if they were arrays/objects
        gender = request.POST.get('gender')
        age = request.POST.get('age')
        primary_source_income = request.POST.get('primary_source_income')
        employment_type = request.POST.get('employment_type')
        skills_str = request.POST.get('skills') # Expecting JSON string for array
        skills = json.loads(skills_str) if skills_str else []

        willing_to_migrate = request.POST.get('willing_to_migrate')
        expected_wage = request.POST.get('expected_wage') # Convert to Decimal later
        availability = request.POST.get('availability')
        adult_men_seeking_employment = request.POST.get('adult_men_seeking_employment')
        adult_women_seeking_employment = request.POST.get('adult_women_seeking_employment')
        comm_prefs_str = request.POST.get('communication_preferences') # Expecting JSON string for array
        communication_preferences = json.loads(comm_prefs_str) if comm_prefs_str else []

        # Mukkadam specific fields
        providing_labour_count = request.POST.get('providing_labour_count')
        total_workers_peak = request.POST.get('total_workers_peak')
        expected_charges = request.POST.get('expected_charges')
        labour_supply_availability = request.POST.get('labour_supply_availability')
        arrange_transport = request.POST.get('arrange_transport')
        arrange_transport_other = request.POST.get('arrange_transport_other')
        supply_areas = request.POST.get('supply_areas')

        # Transport specific fields
        vehicle_type = request.POST.get('vehicle_type')
        people_capacity = request.POST.get('people_capacity')
        expected_fair = request.POST.get('expected_fair')
        service_areas = request.POST.get('service_areas')

        # Others specific fields
        business_name = request.POST.get('business_name')
        help_description = request.POST.get('help_description')

        # Data Sharing Agreement (Step 3 field)
        data_sharing_agreement_str = request.POST.get('data_sharing_agreement')
        # Convert string 'true'/'false' from JS to Python boolean
        data_sharing_agreement = data_sharing_agreement_str == 'true'

        logger.info(f"Received PWA submission for {full_name}, category: {category}")

        # --- Create and Save Model Instance based on Category ---
        instance = None
        if category == 'individual_labor':
            instance = IndividualLabor(
                full_name=full_name,
                mobile_number=mobile_number,
                taluka=taluka,
                village=village,
                gender=gender,
                age=int(age) if age else None,
                primary_source_income=primary_source_income,
                employment_type=employment_type,
                willing_to_migrate=willing_to_migrate == 'true', # Convert bool string
                expected_wage=Decimal(expected_wage) if expected_wage else None,
                availability=availability,
                adult_men_seeking_employment=int(adult_men_seeking_employment) if adult_men_seeking_employment else 0,
                adult_women_seeking_employment=int(adult_women_seeking_employment) if adult_women_seeking_employment else 0,
                data_sharing_agreement=data_sharing_agreement,
            )
            # Handle skills (assuming boolean fields in your model)
            instance.skill_pruning = 'pruning' in skills
            instance.skill_harvesting = 'harvesting' in skills
            instance.skill_dipping = 'dipping' in skills
            instance.skill_thinning = 'thinning' in skills
            instance.skill_none = 'none' in skills

            # Handle communication preferences (assuming boolean fields)
            instance.comm_mobile_app = 'mobile_app' in communication_preferences
            instance.comm_whatsapp = 'whatsapp' in communication_preferences
            instance.comm_calling = 'calling' in communication_preferences
            instance.comm_sms = 'sms' in communication_preferences

        elif category == 'mukkadam':
            instance = Mukkadam(
                full_name=full_name,
                mobile_number=mobile_number,
                taluka=taluka,
                village=village,
                providing_labour_count=int(providing_labour_count) if providing_labour_count else None,
                total_workers_peak=int(total_workers_peak) if total_workers_peak else None,
                expected_charges=Decimal(expected_charges) if expected_charges else None,
                labour_supply_availability=labour_supply_availability,
                arrange_transport=arrange_transport,
                arrange_transport_other=arrange_transport_other if arrange_transport == 'other' else None,
                supply_areas=supply_areas,
                data_sharing_agreement=data_sharing_agreement,
            )
            # Handle skills for Mukkadam (assuming boolean fields)
            instance.skill_pruning = 'pruning' in skills
            instance.skill_harvesting = 'harvesting' in skills
            instance.skill_dipping = 'dipping' in skills
            instance.skill_thinning = 'thinning' in skills
            instance.skill_none = 'none' in skills

        elif category == 'transport':
            instance = Transport(
                full_name=full_name,
                mobile_number=mobile_number,
                taluka=taluka,
                village=village,
                vehicle_type=vehicle_type,
                people_capacity=int(people_capacity) if people_capacity else None,
                expected_fair=Decimal(expected_fair) if expected_fair else None,
                availability=availability,
                service_areas=service_areas,
                data_sharing_agreement=data_sharing_agreement,
            )
        elif category == 'others':
            instance = Others(
                full_name=full_name,
                mobile_number=mobile_number,
                taluka=taluka,
                village=village,
                business_name=business_name,
                help_description=help_description,
                data_sharing_agreement=data_sharing_agreement,
            )
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid category provided.'}, status=400)

        # --- Set Location and Photo for all instances ---
        if location_data:
            instance.location = Point(
                float(location_data.get('longitude')),
                float(location_data.get('latitude')),
                srid=4326
            )
            instance.location_accuracy = float(location_data.get('accuracy')) if location_data.get('accuracy') else None
            if location_data.get('timestamp'):
                instance.location_timestamp = parser.isoparse(location_data['timestamp'])
            logger.info(f"Location received for {full_name}: {instance.location}")

        # Save instance first if photo is a FileField (to get primary key if needed by FileField)
        instance.save()
        # def success_view(request):
        #     return render(request, 'registration/success.html')


        # Save photo if available (requires instance to be saved first for FileField)
        if photo_file:
            instance.photo.save(photo_file.name, photo_file, save=True)

        logger.info(f"Registration for {full_name} saved successfully to database (PK: {instance.pk}).")
        return JsonResponse({'status': 'success', 'message': 'Registration processed and saved.'}, status=200)

    except json.JSONDecodeError as e:
        logger.error(f"JSON Decode Error in submit_registration_api: {e}")
        return JsonResponse({'status': 'error', 'message': f'Invalid JSON data: {e}'}, status=400)
    except Exception as e:
        logger.error(f"Error in submit_registration_api: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# Success page view
def success_view(request):
    return render(request, 'registration/success.html')

# Home page view (if you have one)
def home_view(request):
    return render(request, 'registration/home.html')

# Example: location_status_api (if you still need it, otherwise remove)
@csrf_exempt
def location_status_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        accuracy = data.get('accuracy')

        if latitude and longitude:
            return JsonResponse({
                'status': 'success',
                'message': 'Location received successfully'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid location data'
            })
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
    """API endpoint to check location permissions (optional)"""
    if request.method == 'POST':
        data = json.loads(request.body)
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        accuracy = data.get('accuracy')

        if latitude and longitude:
            return JsonResponse({
                'status': 'success',
                'message': 'Location received successfully'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid location data'
            })

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})