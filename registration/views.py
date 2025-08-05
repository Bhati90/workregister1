
# registration/views.py
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views import View
from django.shortcuts import render, redirect # Import render and redirect
from django.contrib.gis.geos import Point
from decimal import Decimal, InvalidOperation
import json
import logging
from dateutil.parser import isoparse # Make sure you have python-dateutil installed (pip install python-dateutil)

# Assuming these forms and models exist and are correctly defined
from .forms import (
    BaseInformationForm, IndividualLaborForm, MukkadamForm,
    TransportForm, OthersForm, DataSharingAgreementForm
)
from .models import IndividualLabor, Mukkadam, Transport, Others

logger = logging.getLogger('registration')

class MultiStepRegistrationView(View):
    """
    This view only handles GET requests for the PWA's multi-step form pages.
    The form submissions are handled by a separate API endpoint.
    """
    template_name = 'registration/multi_step_form.html'

    def get_form_class(self, category):
        form_mapping = {
            'individual_labor': IndividualLaborForm,
            'mukkadam': MukkadamForm,
            'transport': TransportForm,
            'others': OthersForm,
        }
        return form_mapping.get(category)

    def get(self, request):
        step = request.GET.get('step', '1')
        # Retrieve current_category from the query parameter which the JS will send
        current_category = request.GET.get('current_category_from_db')
        context = {
            'step': int(step),
            'form': None,
            'step_title': '',
            'progress_percent': 0,
            'category': current_category # Pass this to the template
        }

        if step == '1':
            context['form'] = BaseInformationForm()
            context['step_title'] = 'Basic Information'
            context['progress_percent'] = 33
        elif step == '2':
            if not current_category:
                messages.error(request, 'Please complete basic information first.')
                return redirect('registration:registration') # Use namespaced URL
            form_class = self.get_form_class(current_category)
            if not form_class:
                messages.error(request, 'Invalid category selected.')
                return redirect('registration:registration') # Use namespaced URL
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
            if not current_category:
                messages.error(request, 'Please complete basic information first.')
                return redirect('registration:registration') # Use namespaced URL
            context['form'] = DataSharingAgreementForm()
            context['step_title'] = 'Data Sharing Agreement'
            context['progress_percent'] = 100
        else:
            return redirect('registration:registration') # Use namespaced URL

        return render(request, self.template_name, context)

@csrf_exempt
# @method_decorator(require_POST, name='dispatch')
@require_POST
def submit_registration_api(request):
    """
    API endpoint that receives and saves the entire form submission
    from the PWA client in a single POST request.
    This replaces the session-based multi-step POST logic.
    """
    logger.info("submit_registration_api received a request.")
    try:
        def safe_int(value):
            try:
                # Convert to int, return None if empty string or cannot convert
                return int(value) if value else None
            except (ValueError, TypeError):
                return None

        def safe_decimal(value):
            try:
                # Convert to Decimal, return None if empty string or cannot convert
                return Decimal(value) if value else None
            except (ValueError, TypeError, InvalidOperation):
                return None

        # Basic Info (Step 1)
        full_name = request.POST.get('full_name')
        mobile_number = request.POST.get('mobile_number')
        category = request.POST.get('category')
        taluka = request.POST.get('taluka')
        village = request.POST.get('village')
        photo_file = request.FILES.get('photo') # Photo is a file, not text/base64

        location_str = request.POST.get('location')
        location_data = {}
        if location_str:
            try:
                location_data = json.loads(location_str)
            except json.JSONDecodeError:
                logger.warning(f"Failed to decode location JSON: {location_str}")
                location_data = {} # Reset to empty if invalid JSON

        logger.info(f"Received PWA submission for {full_name}, category: {category}")

        instance = None
        # Category-specific fields (Step 2)
        # Individual Labor fields
        gender = request.POST.get('gender')
        age = safe_int(request.POST.get('age'))
        primary_source_income = request.POST.get('primary_source_income')
        employment_type = request.POST.get('employment_type')
        # Skills and communication preferences are JSON strings from frontend
        skills_str = request.POST.get('skills')
        skills = json.loads(skills_str) if skills_str else []
        willing_to_migrate = request.POST.get('willing_to_migrate') == 'true' # Convert 'true'/'false' string to boolean
        expected_wage = safe_decimal(request.POST.get('expected_wage'))
        availability = request.POST.get('availability')
        adult_men_seeking_employment = safe_int(request.POST.get('adult_men_seeking_employment')) or 0
        adult_women_seeking_employment = safe_int(request.POST.get('adult_women_seeking_employment')) or 0
        comm_prefs_str = request.POST.get('communication_preferences')
        communication_preferences = json.loads(comm_prefs_str) if comm_prefs_str else []

        # Mukkadam fields
        providing_labour_count = safe_int(request.POST.get('providing_labour_count'))
        total_workers_peak = safe_int(request.POST.get('total_workers_peak'))
        expected_charges = safe_decimal(request.POST.get('expected_charges'))
        labour_supply_availability = request.POST.get('labour_supply_availability')
        arrange_transport = request.POST.get('arrange_transport')
        arrange_transport_other = request.POST.get('arrange_transport_other')
        supply_areas = request.POST.get('supply_areas')

        # Transport fields
        vehicle_type = request.POST.get('vehicle_type')
        people_capacity = safe_int(request.POST.get('people_capacity'))
        expected_fair = safe_decimal(request.POST.get('expected_fair'))
        service_areas = request.POST.get('service_areas')

        # Others fields
        business_name = request.POST.get('business_name')
        help_description = request.POST.get('help_description')

        # Agreement (Step 3)
        data_sharing_agreement = request.POST.get('data_sharing_agreement') == 'true' # Convert 'true'/'false' string to boolean

        if category == 'individual_labor':
            instance = IndividualLabor(
                full_name=full_name, mobile_number=mobile_number, taluka=taluka, village=village,
                gender=gender, age=age, primary_source_income=primary_source_income,
                employment_type=employment_type, willing_to_migrate=willing_to_migrate,
                expected_wage=expected_wage, availability=availability,
                adult_men_seeking_employment=adult_men_seeking_employment,
                adult_women_seeking_employment=adult_women_seeking_employment,
                data_sharing_agreement=data_sharing_agreement,
            )
            # Set boolean fields for skills and communication preferences
            instance.skill_pruning = 'pruning' in skills
            instance.skill_harvesting = 'harvesting' in skills
            instance.skill_dipping = 'dipping' in skills
            instance.skill_thinning = 'thinning' in skills
            instance.skill_none = 'none' in skills # Assuming 'none' is a valid skill checkbox

            instance.comm_mobile_app = 'mobile_app' in communication_preferences
            instance.comm_whatsapp = 'whatsapp' in communication_preferences
            instance.comm_calling = 'calling' in communication_preferences
            instance.comm_sms = 'sms' in communication_preferences

        elif category == 'mukkadam':
            instance = Mukkadam(
                full_name=full_name, mobile_number=mobile_number, taluka=taluka, village=village,
                providing_labour_count=providing_labour_count, total_workers_peak=total_workers_peak,
                expected_charges=expected_charges, labour_supply_availability=labour_supply_availability,
                arrange_transport=arrange_transport,
                arrange_transport_other=arrange_transport_other if arrange_transport == 'other' else None,
                supply_areas=supply_areas, data_sharing_agreement=data_sharing_agreement,
            )
            instance.skill_pruning = 'pruning' in skills
            instance.skill_harvesting = 'harvesting' in skills
            instance.skill_dipping = 'dipping' in skills
            instance.skill_thinning = 'thinning' in skills
            instance.skill_none = 'none' in skills

        elif category == 'transport':
            instance = Transport(
                full_name=full_name, mobile_number=mobile_number, taluka=taluka, village=village,
                vehicle_type=vehicle_type, people_capacity=people_capacity,
                expected_fair=expected_fair, availability=availability,
                service_areas=service_areas, data_sharing_agreement=data_sharing_agreement,
            )
        elif category == 'others':
            instance = Others(
                full_name=full_name, mobile_number=mobile_number, taluka=taluka, village=village,
                business_name=business_name, help_description=help_description,
                data_sharing_agreement=data_sharing_agreement,
            )
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid category provided.'}, status=400)

        # Handle Location (common for all categories)
        if location_data.get('latitude') and location_data.get('longitude'):
            try:
                instance.location = Point(
                    float(location_data.get('longitude')),
                    float(location_data.get('latitude')),
                    srid=4326 # Standard SRID for WGS 84 (latitude, longitude)
                )
                instance.location_accuracy = float(location_data.get('accuracy')) if location_data.get('accuracy') else None
                if location_data.get('timestamp'):
                    instance.location_timestamp = isoparse(location_data['timestamp']) # Parses ISO formatted date string
            except (ValueError, TypeError, KeyError) as loc_err:
                logger.error(f"Error processing location data: {loc_err} with data {location_data}", exc_info=True)
                # Decide if you want to fail here or just save without location
                # For now, it will proceed without location if there's an error
                instance.location = None
                instance.location_accuracy = None
                instance.location_timestamp = None

        instance.save() # Save the main instance first

        if photo_file:
            # photo_file is a Django InMemoryUploadedFile or TemporaryUploadedFile
            # It already contains the name, size, content_type
            instance.photo.save(photo_file.name, photo_file, save=True)
            logger.info(f"Photo saved for {full_name}.")

        logger.info(f"Registration for {full_name} saved successfully to database (PK: {instance.pk}).")
        return JsonResponse({'status': 'success', 'message': 'Registration processed and saved.'}, status=200)

    except json.JSONDecodeError as e:
        logger.error(f"JSON Decode Error in submit_registration_api: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': f'Invalid JSON data for fields like skills/comm_prefs/location: {e}'}, status=400)
    except Exception as e:
        logger.error(f"Unhandled error in submit_registration_api: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}, status=500)

def success_view(request):
    return render(request, 'registration/success.html')

def home_view(request):
    return render(request, 'registration/home.html')

@csrf_exempt
def location_status_api(request):
    # This API endpoint is not directly used by the multi_step_form_client for final submission
    # but was present in your code. Keep it if you have other uses.
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            accuracy = data.get('accuracy')
            if latitude and longitude:
                return JsonResponse({'status': 'success', 'message': 'Location received successfully'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid location data'}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)