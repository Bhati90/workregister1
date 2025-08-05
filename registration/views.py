# registration/views.py

import base64
import uuid
import json
import logging
from decimal import Decimal, InvalidOperation
from dateutil.parser import isoparse
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.core.files.base import ContentFile
from django.contrib.gis.geos import Point
from django.core.files.storage import default_storage
from django.contrib import messages
import io
from PIL import Image
import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError

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
# def submit_registration_api(request):
#     """
#     Handles both ONLINE (file upload) and OFFLINE (base64 string) submissions
#     and saves the image to Cloudinary. This is the fully corrected version.
#     """
#     logger.info("API received a submission.")
#     try:
#         data = request.POST
        
#         # --- Get Image Data (handles both online and offline paths) ---
#         photo_file = request.FILES.get('photo')
#         photo_base64 = data.get('photo_base64')

#         # --- Create Model Instance ---
#         category = data.get('category')
#         common_data = {
#             'full_name': data.get('full_name'),
#             'mobile_number': data.get('mobile_number'),
#             'taluka': data.get('taluka'),
#             'village': data.get('village'),
#             'data_sharing_agreement': data.get('data_sharing_agreement') == 'true'
#         }
        
#         instance = None
#         if category == 'individual_labor':
#             skills_str = data.get('skills', '[]')
#             skills = json.loads(skills_str)
#             comm_prefs_str = data.get('communication_preferences', '[]')
#             communication_preferences = json.loads(comm_prefs_str)
#             instance = IndividualLabor(
#                 **common_data,
#                 gender=data.get('gender'),
#                 age=int(data.get('age', 0)),
#                 primary_source_income=data.get('primary_source_income'),
#                 employment_type=data.get('employment_type'),
#                 willing_to_migrate=data.get('willing_to_migrate') == 'true',
#                 expected_wage=Decimal(data.get('expected_wage', 0)),
#                 availability=data.get('availability'),
#                 skill_pruning='pruning' in skills,
#                 skill_harvesting='harvesting' in skills,
#                 skill_dipping='dipping' in skills,
#                 skill_thinning='thinning' in skills,
#                 comm_mobile_app='mobile_app' in communication_preferences,
#                 comm_whatsapp='whatsapp' in communication_preferences,
#                 comm_calling='calling' in communication_preferences,
#                 comm_sms='sms' in communication_preferences,
#             )
#         elif category == 'mukkadam':
#              instance = Mukkadam(
#                 **common_data,
#                 providing_labour_count=int(data.get('providing_labour_count', 0)),
#                 total_workers_peak=int(data.get('total_workers_peak', 0)),
#                 expected_charges=Decimal(data.get('expected_charges', 0)),
#                 labour_supply_availability=data.get('labour_supply_availability'),
#                 arrange_transport=data.get('arrange_transport'),
#                 supply_areas=data.get('supply_areas'),
#             )
#         elif category == 'transport':
#             instance = Transport(
#                 **common_data,
#                 vehicle_type=data.get('vehicle_type'),
#                 people_capacity=int(data.get('people_capacity', 0)),
#                 expected_fair=Decimal(data.get('expected_fair', 0)),
#                 availability=data.get('availability'),
#                 service_areas=data.get('service_areas')
#             )
#         elif category == 'others':
#              instance = Others(
#                 **common_data,
#                 business_name=data.get('business_name'),
#                 help_description=data.get('help_description'),
#             )
#         else:
#             return JsonResponse({'status': 'error', 'message': f'Invalid category: {category}'}, status=400)

#         # --- Handle Location ---
#         location_str = data.get('location')
#         if location_str:
#             try:
#                 location_data = json.loads(location_str)
#                 if location_data and 'latitude' in location_data and 'longitude' in location_data:
#                     instance.location = Point(float(location_data['longitude']), float(location_data['latitude']))
#                     instance.location_accuracy = float(location_data.get('accuracy', 0))
#                     if 'timestamp' in location_data:
#                         instance.location_timestamp = isoparse(location_data['timestamp'])
#             except Exception as e:
#                 logger.warning(f"Could not parse location data '{location_str}'. Error: {e}")

#         # --- Save the main model data (without photo yet) ---
#         instance.save()

#         # --- FINAL DEBUGGING CHECK ---
#         print("\n--- RUNTIME STORAGE CHECK ---")
#         print(f"The default_storage object being used is: {default_storage}")
#         print(f"The class of the storage object is: {default_storage.__class__}")
#         print("---------------------------\n")

#         # --- Save Photo to Cloudinary (Handles both paths) ---
#         if photo_file:
#             instance.photo.save(photo_file.name, photo_file, save=True)
#             logger.info(f"Photo for {common_data['full_name']} saved to Cloudinary from direct upload.")
#         elif photo_base64:
#             try:
#                 header, img_str = photo_base64.split(';base64,')
#                 ext = header.split('/')[-1]
#                 file_name = f"{uuid.uuid4().hex}.{ext}"
#                 decoded_file = base64.b64decode(img_str)
#                 content_file = ContentFile(decoded_file, name=file_name)
#                 instance.photo.save(file_name, content_file, save=True)
#                 logger.info(f"Photo for {common_data['full_name']} saved to Cloudinary from offline sync.")
#             except Exception as e:
#                 logger.error(f"Failed to save photo from Base64. Error: {e}", exc_info=True)

#         return JsonResponse({'status': 'success', 'message': 'Registration saved.'}, status=200)

#     except Exception as e:
#         logger.error(f"Critical error in submit_registration_api: {e}", exc_info=True)
#         return JsonResponse({'status': 'error', 'message': 'An unexpected server error occurred.'}, status=500)
@csrf_exempt
@require_http_methods(["POST"])
def submit_registration_api(request):
    """
    Enhanced API endpoint to handle both online and offline registration submissions.
    Now supports Cloudinary upload for offline-synced images.
    """
    try:
        logger.info("Registration API called")
        
        # Check for duplicate mobile number first
        mobile_number = request.POST.get('mobile_number', '').strip()
        if mobile_number:
            # Clean mobile number for comparison
            clean_mobile = ''.join(filter(str.isdigit, mobile_number))
            if len(clean_mobile) >= 10:
                clean_mobile = clean_mobile[-10:]  # Take last 10 digits
                
                # Check for existing registration
                existing_registration = LaborRegistration.objects.filter(
                    mobile_number__icontains=clean_mobile
                ).first()
                
                if existing_registration:
                    logger.warning(f"Duplicate mobile number attempt: {mobile_number}")
                    return JsonResponse({
                        'success': False,
                        'error_type': 'duplicate_mobile',
                        'message': f'Mobile number {mobile_number} is already registered.',
                        'existing_id': existing_registration.id
                    }, status=400)
        
        # Create new registration instance
        registration = LaborRegistration()
        
        # Handle image upload - Priority system for offline sync compatibility
        photo_file = None
        cloudinary_url = None
        
        # Method 1: Direct file upload (online submissions)
        if 'photo' in request.FILES:
            photo_file = request.FILES['photo']
            logger.info(f"Direct photo file received: {photo_file.name}, size: {photo_file.size}")
        
        # Method 2: Base64 image from offline sync
        elif 'photo_base64' in request.POST:
            try:
                base64_data = request.POST['photo_base64']
                logger.info("Base64 photo data received from offline sync")
                
                # Extract base64 data
                if ',' in base64_data:
                    header, base64_string = base64_data.split(',', 1)
                else:
                    base64_string = base64_data
                
                # Decode base64 to bytes
                image_data = base64.b64decode(base64_string)
                
                # Create file-like object
                image_io = io.BytesIO(image_data)
                
                # Determine file extension from header or default to jpeg
                if 'data:image/png' in base64_data:
                    file_extension = 'png'
                    content_type = 'image/png'
                elif 'data:image/jpeg' in base64_data or 'data:image/jpg' in base64_data:
                    file_extension = 'jpeg'
                    content_type = 'image/jpeg'
                else:
                    file_extension = 'jpeg'  # Default
                    content_type = 'image/jpeg'
                
                # Create ContentFile for Django
                filename = f"offline_sync_{mobile_number}_{int(time.time())}.{file_extension}"
                photo_file = ContentFile(image_data, name=filename)
                
                logger.info(f"Base64 converted to file: {filename}, size: {len(image_data)}")
                
            except Exception as e:
                logger.error(f"Error processing base64 image: {str(e)}")
                # Continue without image rather than failing the entire registration
        
        # Upload to Cloudinary if we have a photo
        if photo_file:
            try:
                # Upload to Cloudinary
                upload_result = cloudinary.uploader.upload(
                    photo_file,
                    folder="labor_registrations",
                    public_id=f"registration_{mobile_number}_{int(time.time())}",
                    overwrite=True,
                    resource_type="image",
                    format="jpg",  # Convert all to JPG for consistency
                    quality="auto:good",  # Optimize quality
                    fetch_format="auto"
                )
                
                cloudinary_url = upload_result.get('secure_url')
                logger.info(f"Image uploaded to Cloudinary: {cloudinary_url}")
                
                # Store the Cloudinary URL in the photo field
                registration.photo = cloudinary_url
                
            except CloudinaryError as e:
                logger.error(f"Cloudinary upload failed: {str(e)}")
                # For offline sync, we don't want to fail the entire registration
                # Continue without storing the image URL
            except Exception as e:
                logger.error(f"Unexpected error during image upload: {str(e)}")
        
        # Fill basic information
        registration.full_name = request.POST.get('full_name', '').strip()
        registration.mobile_number = mobile_number
        registration.category = request.POST.get('category', '').strip()
        registration.taluka = request.POST.get('taluka', '').strip()
        registration.village = request.POST.get('village', '').strip()
        
        # Handle location data
        location_data = request.POST.get('location')
        if location_data:
            try:
                if isinstance(location_data, str):
                    location_json = json.loads(location_data)
                else:
                    location_json = location_data
                
                registration.latitude = float(location_json.get('latitude', 0))
                registration.longitude = float(location_json.get('longitude', 0))
                registration.location_accuracy = float(location_json.get('accuracy', 0))
                
                logger.info(f"Location saved: {registration.latitude}, {registration.longitude}")
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                logger.warning(f"Invalid location data: {str(e)}")
        
        # Handle category-specific fields based on category
        category = registration.category
        
        if category == 'individual_labor':
            # Individual Labor fields
            registration.gender = request.POST.get('gender', '').strip()
            
            age_str = request.POST.get('age', '').strip()
            if age_str and age_str.isdigit():
                registration.age = int(age_str)
            
            registration.primary_source_income = request.POST.get('primary_source_income', '').strip()
            registration.employment_type = request.POST.get('employment_type', '').strip()
            
            # Handle skills (JSON array)
            skills_data = request.POST.get('skills')
            if skills_data:
                try:
                    if isinstance(skills_data, str):
                        registration.skills = json.loads(skills_data)
                    else:
                        registration.skills = skills_data
                except json.JSONDecodeError:
                    registration.skills = []
            
            # Boolean field
            willing_to_migrate = request.POST.get('willing_to_migrate', '').strip().lower()
            registration.willing_to_migrate = willing_to_migrate in ['true', '1', 'yes']
            
            registration.expected_wage = request.POST.get('expected_wage', '').strip()
            registration.availability = request.POST.get('availability', '').strip()
            
            # Handle integer fields
            for field_name in ['adult_men_seeking_employment', 'adult_women_seeking_employment']:
                field_value = request.POST.get(field_name, '').strip()
                if field_value and field_value.isdigit():
                    setattr(registration, field_name, int(field_value))
            
            # Handle communication preferences (JSON array)
            comm_prefs = request.POST.get('communication_preferences')
            if comm_prefs:
                try:
                    if isinstance(comm_prefs, str):
                        registration.communication_preferences = json.loads(comm_prefs)
                    else:
                        registration.communication_preferences = comm_prefs
                except json.JSONDecodeError:
                    registration.communication_preferences = []
        
        elif category == 'mukkadam':
            # Mukkadam fields
            for field_name in ['providing_labour_count', 'total_workers_peak']:
                field_value = request.POST.get(field_name, '').strip()
                if field_value and field_value.isdigit():
                    setattr(registration, field_name, int(field_value))
            
            registration.expected_charges = request.POST.get('expected_charges', '').strip()
            registration.labour_supply_availability = request.POST.get('labour_supply_availability', '').strip()
            registration.arrange_transport = request.POST.get('arrange_transport', '').strip()
            registration.arrange_transport_other = request.POST.get('arrange_transport_other', '').strip()
            
            # Handle supply areas and skills (JSON arrays)
            for json_field in ['supply_areas', 'skills']:
                field_data = request.POST.get(json_field)
                if field_data:
                    try:
                        if isinstance(field_data, str):
                            setattr(registration, json_field, json.loads(field_data))
                        else:
                            setattr(registration, json_field, field_data)
                    except json.JSONDecodeError:
                        setattr(registration, json_field, [])
        
        elif category == 'transport':
            # Transport fields
            registration.vehicle_type = request.POST.get('vehicle_type', '').strip()
            
            people_capacity = request.POST.get('people_capacity', '').strip()
            if people_capacity and people_capacity.isdigit():
                registration.people_capacity = int(people_capacity)
            
            registration.expected_fair = request.POST.get('expected_fair', '').strip()
            registration.availability = request.POST.get('availability', '').strip()
            
            # Handle service areas (can be JSON array or string)
            service_areas = request.POST.get('service_areas')
            if service_areas:
                try:
                    if isinstance(service_areas, str) and service_areas.startswith('['):
                        registration.service_areas = json.loads(service_areas)
                    else:
                        registration.service_areas = service_areas
                except json.JSONDecodeError:
                    registration.service_areas = service_areas
        
        elif category == 'others':
            # Others category fields
            registration.business_name = request.POST.get('business_name', '').strip()
            registration.help_description = request.POST.get('help_description', '').strip()
        
        # Handle data sharing agreement
        data_sharing = request.POST.get('data_sharing_agreement', '').strip().lower()
        registration.data_sharing_agreement = data_sharing in ['true', '1', 'yes', 'on']
        
        # Save the registration
        registration.save()
        
        logger.info(f"Registration saved successfully with ID: {registration.id}")
        
        response_data = {
            'success': True,
            'message': 'Registration submitted successfully!',
            'registration_id': registration.id,
            'mobile_number': registration.mobile_number
        }
        
        # Include Cloudinary URL in response if available
        if cloudinary_url:
            response_data['photo_url'] = cloudinary_url
        
        return JsonResponse(response_data, status=201)
        
    except Exception as e:
        logger.error(f"Registration submission failed: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while processing your registration.',
            'details': str(e)
        }, status=500)

# Keep your existing check_mobile_number_api function unchanged
@csrf_exempt  
@require_http_methods(["POST"])
def check_mobile_number_api(request):
    """API endpoint to check if a mobile number already exists"""
    try:
        data = json.loads(request.body)
        mobile_number = data.get('mobile_number', '').strip()
        
        if not mobile_number:
            return JsonResponse({
                'exists': False,
                'message': 'No mobile number provided'
            })
        
        # Clean the mobile number (remove non-digits)
        clean_mobile = ''.join(filter(str.isdigit, mobile_number))
        
        if len(clean_mobile) < 10:
            return JsonResponse({
                'exists': False,
                'message': 'Invalid mobile number format'
            })
        
        # Take the last 10 digits for comparison
        clean_mobile = clean_mobile[-10:]
        
        # Check if this mobile number exists in the database
        exists = LaborRegistration.objects.filter(
            mobile_number__icontains=clean_mobile
        ).exists()
        
        if exists:
            existing_reg = LaborRegistration.objects.filter(
                mobile_number__icontains=clean_mobile
            ).first()
            
            return JsonResponse({
                'exists': True,
                'message': f'Mobile number {mobile_number} is already registered.',
                'registration_date': existing_reg.created_at.strftime('%Y-%m-%d') if existing_reg else None
            })
        else:
            return JsonResponse({
                'exists': False,
                'message': 'Mobile number is available'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'exists': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error checking mobile number: {str(e)}")
        return JsonResponse({
            'exists': False,
            'message': 'Error checking mobile number'
        }, status=500)
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


# def mobile_number_exists(mobile_number):
#     """Checks if a mobile number exists in ANY of the registration models."""
#     # This function is preserved exactly as you had it.
#     if not mobile_number:
#         return False
#     cleaned_number = str(mobile_number).strip().replace('+91', '')
#     if not cleaned_number.isdigit():
#         return False
#     if IndividualLabor.objects.filter(mobile_number__endswith=cleaned_number).exists():
#         return True
#     if Mukkadam.objects.filter(mobile_number__endswith=cleaned_number).exists():
#         return True
#     if Transport.objects.filter(mobile_number__endswith=cleaned_number).exists():
#         return True
#     if Others.objects.filter(mobile_number__endswith=cleaned_number).exists():
#         return True
#     return False