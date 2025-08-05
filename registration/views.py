# registration/views.py

import base64
import uuid
import json
import logging
from decimal import Decimal, InvalidOperation
from dateutil.parser import isoparse

from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.files.base import ContentFile
from django.contrib.gis.geos import Point
from django.core.files.storage import default_storage
from django.contrib import messages

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
        current_category = request.GET.get('current_category_from_db')
        context = {
            'step': int(step),
            'form': None,
            'step_title': '',
            'progress_percent': 0,
            'category': current_category
        }

        if step == '1':
            context['form'] = BaseInformationForm()
            context['step_title'] = 'Basic Information'
            context['progress_percent'] = 33
        elif step == '2':
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
            if not current_category:
                messages.error(request, 'Please complete basic information first.')
                return redirect('registration:registration')
            context['form'] = DataSharingAgreementForm()
            context['step_title'] = 'Data Sharing Agreement'
            context['progress_percent'] = 100
        else:
            return redirect('registration:registration')

        return render(request, self.template_name, context)

@csrf_exempt
@require_POST
def check_mobile_number_api(request):
    """
    API endpoint to check if a mobile number already exists in the database.
    """
    # This function is preserved exactly as you had it.
    try:
        data = json.loads(request.body)
        mobile_number = data.get('mobile_number', '').strip()
        if not mobile_number:
            return JsonResponse({'exists': False, 'message': 'No mobile number provided'})
        
        exists = mobile_number_exists(mobile_number)
        return JsonResponse({
            'exists': exists,
            'message': 'Mobile number already registered' if exists else 'Mobile number available'
        })
    except Exception as e:
        logger.error(f"Error checking mobile number: {e}")
        return JsonResponse({'exists': False, 'message': 'Server error'}, status=500)


@csrf_exempt
@require_POST
def submit_registration_api(request):
    """
    Handles both ONLINE (file upload) and OFFLINE (base64 string) submissions
    and saves the image to Cloudinary. This is the fully corrected version.
    """
    logger.info("API received a submission.")
    try:
        data = request.POST
        
        # --- Get Image Data (handles both online and offline paths) ---
        photo_file = request.FILES.get('photo')
        photo_base64 = data.get('photo_base64')

        # --- Create Model Instance ---
        category = data.get('category')
        common_data = {
            'full_name': data.get('full_name'),
            'mobile_number': data.get('mobile_number'),
            'taluka': data.get('taluka'),
            'village': data.get('village'),
            'data_sharing_agreement': data.get('data_sharing_agreement') == 'true'
        }
        
        instance = None
        if category == 'individual_labor':
            skills_str = data.get('skills', '[]')
            skills = json.loads(skills_str)
            comm_prefs_str = data.get('communication_preferences', '[]')
            communication_preferences = json.loads(comm_prefs_str)
            instance = IndividualLabor(
                **common_data,
                gender=data.get('gender'),
                age=int(data.get('age', 0)),
                primary_source_income=data.get('primary_source_income'),
                employment_type=data.get('employment_type'),
                willing_to_migrate=data.get('willing_to_migrate') == 'true',
                expected_wage=Decimal(data.get('expected_wage', 0)),
                availability=data.get('availability'),
                skill_pruning='pruning' in skills,
                skill_harvesting='harvesting' in skills,
                skill_dipping='dipping' in skills,
                skill_thinning='thinning' in skills,
                comm_mobile_app='mobile_app' in communication_preferences,
                comm_whatsapp='whatsapp' in communication_preferences,
                comm_calling='calling' in communication_preferences,
                comm_sms='sms' in communication_preferences,
            )
        elif category == 'mukkadam':
             instance = Mukkadam(
                **common_data,
                providing_labour_count=int(data.get('providing_labour_count', 0)),
                total_workers_peak=int(data.get('total_workers_peak', 0)),
                expected_charges=Decimal(data.get('expected_charges', 0)),
                labour_supply_availability=data.get('labour_supply_availability'),
                arrange_transport=data.get('arrange_transport'),
                supply_areas=data.get('supply_areas'),
            )
        elif category == 'transport':
            instance = Transport(
                **common_data,
                vehicle_type=data.get('vehicle_type'),
                people_capacity=int(data.get('people_capacity', 0)),
                expected_fair=Decimal(data.get('expected_fair', 0)),
                availability=data.get('availability'),
                service_areas=data.get('service_areas')
            )
        elif category == 'others':
             instance = Others(
                **common_data,
                business_name=data.get('business_name'),
                help_description=data.get('help_description'),
            )
        else:
            return JsonResponse({'status': 'error', 'message': f'Invalid category: {category}'}, status=400)

        # --- Handle Location ---
        location_str = data.get('location')
        if location_str:
            try:
                location_data = json.loads(location_str)
                if location_data and 'latitude' in location_data and 'longitude' in location_data:
                    instance.location = Point(float(location_data['longitude']), float(location_data['latitude']))
                    instance.location_accuracy = float(location_data.get('accuracy', 0))
                    if 'timestamp' in location_data:
                        instance.location_timestamp = isoparse(location_data['timestamp'])
            except Exception as e:
                logger.warning(f"Could not parse location data '{location_str}'. Error: {e}")

        # --- Save the main model data (without photo yet) ---
        instance.save()

        # --- FINAL DEBUGGING CHECK ---
        print("\n--- RUNTIME STORAGE CHECK ---")
        print(f"The default_storage object being used is: {default_storage}")
        print(f"The class of the storage object is: {default_storage.__class__}")
        print("---------------------------\n")

        # --- Save Photo to Cloudinary (Handles both paths) ---
        if photo_file:
            instance.photo.save(photo_file.name, photo_file, save=True)
            logger.info(f"Photo for {common_data['full_name']} saved to Cloudinary from direct upload.")
        elif photo_base64:
            try:
                header, img_str = photo_base64.split(';base64,')
                ext = header.split('/')[-1]
                file_name = f"{uuid.uuid4().hex}.{ext}"
                decoded_file = base64.b64decode(img_str)
                content_file = ContentFile(decoded_file, name=file_name)
                instance.photo.save(file_name, content_file, save=True)
                logger.info(f"Photo for {common_data['full_name']} saved to Cloudinary from offline sync.")
            except Exception as e:
                logger.error(f"Failed to save photo from Base64. Error: {e}", exc_info=True)

        return JsonResponse({'status': 'success', 'message': 'Registration saved.'}, status=200)

    except Exception as e:
        logger.error(f"Critical error in submit_registration_api: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'An unexpected server error occurred.'}, status=500)


def success_view(request):
    return render(request, 'registration/success.html')


def home_view(request):
    return render(request, 'registration/home.html')


@csrf_exempt
def location_status_api(request):
    # This function is preserved exactly as you had it.
    if request.method == 'POST':
        return JsonResponse({'status': 'success', 'message': 'Location received successfully'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


def mobile_number_exists(mobile_number):
    """Checks if a mobile number exists in ANY of the registration models."""
    # This function is preserved exactly as you had it.
    if not mobile_number:
        return False
    cleaned_number = str(mobile_number).strip().replace('+91', '')
    if not cleaned_number.isdigit():
        return False
    if IndividualLabor.objects.filter(mobile_number__endswith=cleaned_number).exists():
        return True
    if Mukkadam.objects.filter(mobile_number__endswith=cleaned_number).exists():
        return True
    if Transport.objects.filter(mobile_number__endswith=cleaned_number).exists():
        return True
    if Others.objects.filter(mobile_number__endswith=cleaned_number).exists():
        return True
    return False