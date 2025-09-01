# registration/views.py

import base64
import uuid
import json
import logging
import json
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator

from decimal import Decimal
from dateutil.parser import isoparse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from datetime import  timedelta
from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.files.base import ContentFile
from django.contrib.gis.geos import Point
from django.core.files.storage import default_storage
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
# Required for complex lookups
from .models import IndividualLabor, Mukkadam, Transport, Others,JobFeedback

# ... (keep all your existing views) ...
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout # Import auth functions
from django.contrib.auth.forms import AuthenticationForm # Import the built-in login form

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.contenttypes.models import ContentType
from datetime import timedelta

from .models import (
    Job, JobLeaderResponse, JobAssignment, Notification, WorkerStatus,
    IndividualLabor, Mukkadam, Transport, Others
)

from .forms import JobForm
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils.timezone import now, timedelta
from .models import Job, Notification,RegisteredLabourer # Make sure to import your models

from .forms import (
    BaseInformationForm, IndividualLaborForm, MukkadamForm,
    TransportForm, OthersForm, DataSharingAgreementForm
)
from .models import StatusUpdate,IndividualLabor, Mukkadam, Transport, Others

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

# @csrf_exempt
# @require_POST
# def check_mobile_number_api(request):
#     """
#     API endpoint to check if a mobile number already exists in the database.
#     """
#     # This function is preserved exactly as you had it.
#     try:
#         data = json.loads(request.body)
#         mobile_number = data.get('mobile_number', '').strip()
#         if not mobile_number:
#             return JsonResponse({'exists': False, 'message': 'No mobile number provided'})
        
#         exists = mobile_number_exists(mobile_number)
#         return JsonResponse({
#             'exists': exists,
#             'message': 'Mobile number already registered' if exists else 'Mobile number available'
#         })
#     except Exception as e:
#         logger.error(f"Error checking mobile number: {e}")
#         return JsonResponse({'exists': False, 'message': 'Server error'}, status=500)
# Helper function to get JSON data safely
def get_json_data(data, key):
    """
    Safely retrieves and decodes a JSON string from request data.
    Returns an empty list if the data is not a valid JSON string.
    """
    try:
        val_str = data.get(key, '[]')
        # Handle empty string case explicitly
        if not val_str:
            return []
        return json.loads(val_str)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"JSONDecodeError or TypeError for key '{key}': {data.get(key)}. Error: {e}")
        return []



# from .whats_app import send_whatsapp_template
from .models import WhatsAppLog
from .whats_app import send_whatsapp_template
@csrf_exempt
@require_POST
def submit_registration_api(request):
    """
    Handles both ONLINE and OFFLINE submissions and saves the image to Cloudinary.
    This version includes robust error handling for JSON fields and duplicate mobile numbers.
    """
    logger.info("API received a submission.")
    try:
        
        data = request.POST
        category = data.get('category')
        # Check for duplicate mobile number here for immediate feedback
        mobile_number = data.get('mobile_number')
        # if mobile_number and IndividualLabor.objects.filter(mobile_number=mobile_number).exists():
        #     return JsonResponse({'status': 'error', 'error_type': 'duplicate_mobile', 'message': 'This mobile number is already registered.'}, status=409)

        common_data = {
            'full_name': data.get('full_name'),
            'mobile_number': mobile_number,
            'taluka': data.get('taluka'),
            'village': data.get('village'),
            'data_sharing_agreement': data.get('data_sharing_agreement') == 'true'
        }
        
        instance = None
        if category == 'individual_labor':
            skills = get_json_data(data, 'skills')
            communication_preferences = get_json_data(data, 'communication_preferences')
            
            instance = IndividualLabor(
                **common_data,
                gender=data.get('gender'),
                age=int(data.get('age', 0)),
                primary_source_income=data.get('primary_source_income'),
                employment_type=data.get('employment_type'),
                willing_to_migrate=data.get('willing_to_migrate') == 'true',
                expected_wage=Decimal(data.get('expected_wage', 0)),
                availability=data.get('availability'),
            )
            instance.skill_pruning = 'pruning' in skills
            instance.skill_harvesting = 'harvesting' in skills
            instance.skill_dipping = 'dipping' in skills
            instance.skill_thinning = 'thinning' in skills
            instance.comm_mobile_app = 'mobile_app' in communication_preferences
            instance.comm_whatsapp = 'whatsapp' in communication_preferences
            instance.comm_calling = 'calling' in communication_preferences
            instance.comm_sms = 'sms' in communication_preferences

        elif category == 'mukkadam':
            skills = get_json_data(data, 'skills')
            # ▼▼▼ MODIFIED HERE ▼▼▼
            # REMOVED: supply_areas = get_json_data(data, 'supply_areas')
            # 'supply_areas' is a simple TextField, not a JSON array. We get it directly.
            # --- SAFER NUMBER HANDLING ---
            labour_count_str = data.get('providing_labour_count')
            peak_workers_str = data.get('total_workers_peak')
            charges_str = data.get('expected_charges')

            instance = Mukkadam(
                **common_data,
                providing_labour_count=int(labour_count_str) if labour_count_str else 0,
                total_workers_peak=int(peak_workers_str) if peak_workers_str else 0,
                expected_charges=Decimal(charges_str) if charges_str else Decimal('0.00'),
                labour_supply_availability=data.get('labour_supply_availability'),
                arrange_transport=data.get('arrange_transport'),
                transport_other=data.get('arrange_transport_other'),
                # ADDED: Pass the 'supply_areas' string directly to the model.
                supply_areas=data.get('supply_areas', '') 
            )
            # ▲▲▲ MODIFICATION END ▲▲▲
            instance.save()
            logger.info(f"Main instance for '{instance.full_name}' saved successfully.")

        # ▼▼▼ ADD THIS NEW BLOCK HERE ▼▼▼
        # After the main instance is saved, we can now save its related laborers.
            if category == 'mukkadam':
                labourers_data = get_json_data(data, 'labourers')
                if labourers_data and isinstance(labourers_data, list):
                    for labourer_info in labourers_data:
                    # Create a RegisteredLabourer object for each item in the list
                        RegisteredLabourer.objects.create(
                            mukkadam=instance, # Link it to the Mukkadam we just saved
                            name=labourer_info.get('name'),
                            mobile_number=labourer_info.get('mobile_number', '')
                        )
                    logger.info(f"Saved {len(labourers_data)} registered labourers for Mukkadam {instance.full_name}.")
        # ▲▲▲ END OF NEW BLOCK ▲▲▲
                instance.skill_pruning = 'pruning' in skills
                instance.skill_harvesting = 'harvesting' in skills
                instance.skill_dipping = 'dipping' in skills
                instance.skill_thinning = 'thinning' in skills

        elif category == 'transport':
            service_areas = get_json_data(data, 'service_areas')
            
            instance = Transport(
                **common_data,
                vehicle_type=data.get('vehicle_type'),
                people_capacity=int(data.get('people_capacity', 0)),
                expected_fair=Decimal(data.get('expected_fair', 0)),
                availability=data.get('availability'),
            )
            instance.service_areas_local = 'local' in service_areas
            instance.service_areas_taluka = 'taluka' in service_areas
            instance.service_areas_district = 'district' in service_areas

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

        # --- Handle and Save Photo (Unified Logic) ---
        photo_file = request.FILES.get('photo')
        if photo_file:
            instance.photo.save(photo_file.name, photo_file, save=False)
            logger.info(f"Photo for {common_data['full_name']} attached to instance from file upload.")
        else:
            photo_base64 = data.get('photo_base64')
            if photo_base64:
                try:
                    header, img_str = photo_base64.split(';base64,')
                    ext = header.split('/')[-1]
                    file_name = f"{uuid.uuid4().hex}.{ext}"
                    decoded_file = base64.b64decode(img_str)
                    content_file = ContentFile(decoded_file, name=file_name)
                    instance.photo.save(file_name, content_file, save=False)
                    logger.info(f"Photo for {common_data['full_name']} attached to instance from Base64 string.")
                except Exception as e:
                    logger.error(f"Failed to save photo from Base64. Error: {e}", exc_info=True)

        instance.save()
        logger.info("Instance and photo saved successfully.")
        try:
            recipient_name = instance.full_name
            recipient_number = str(instance.mobile_number)

            if recipient_number:
                if recipient_number.startswith('+'):
                    recipient_number = recipient_number[1:]

                template_config = {
                    'individual_labor': {'name': 'farmer_labour_intro', 'image_url': 'https://images.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png'},
                    'mukkadam': {'name': 'labour_message_1', 'image_url': 'https://images.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png'},
                    'transport': {'name': 'labour_message_1', 'image_url': 'https://images.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png'},
                    'others': {'name': 'labour_message_1', 'image_url': 'https://images.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png'},
                }
                config = template_config.get(category)
                
                if config:
                    components = [
                        {"type": "header", "parameters": [{"type": "image", "image": {"link": config['image_url']}}]},
                        {"type": "body", "parameters": [{"type": "text", "text": recipient_name}]}
                    ]
                    success, details = send_whatsapp_template(
                        to_number=recipient_number,
                        template_name=config['name'],
                        components=components
                    )
                    WhatsAppLog.objects.create(
                        recipient_number=recipient_number,
                        template_name=config['name'],
                        status='sent' if success else 'failed',
                        details=str(details)
                    )
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message for {instance.full_name}. Error: {e}")
        # --- WHATSAPP INTEGRATION END ---

        return JsonResponse({'status': 'success', 'message': 'Registration saved.'}, status=200)

    except Exception as e:
        logger.error(f"Critical error in submit_registration_api: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'An unexpected server error occurred.'}, status=500)


from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import ChatContact, Message
# from .whats_app import send_whatsapp_text_message # We will create this next
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from django.db.models import Q

from .models import ChatContact, Message

logger = logging.getLogger(__name__)

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import F, Q
import json
import logging

from .models import ChatContact, Message, WhatsAppLog
from .whats_app import download_media_from_meta, upload_media_to_meta, send_whatsapp_message, save_outgoing_message
import datetime
logger = logging.getLogger(__name__)

# registration/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import F, Q
import json
import logging
import datetime

from .models import ChatContact, Message, WhatsAppLog


logger = logging.getLogger(__name__)



from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import os, requests, logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ... your other views ...

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import os, requests, logging, json
from dotenv import load_dotenv
from .whats_app import upload_media_to_meta, send_whatsapp_message, save_outgoing_message
from .models import ChatContact

load_dotenv()
logger = logging.getLogger(__name__)

# ... your other views ...



@csrf_exempt
def whatsapp_webhook_view(request):
    """Handles all incoming WhatsApp events."""
    if request.method == 'POST':
        data = json.loads(request.body)
        logger.info(f"Webhook received: {json.dumps(data, indent=2)}")
        try:
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    if 'messages' in value:
                        for msg in value.get('messages', []):
                            contact, _ = ChatContact.objects.get_or_create(wa_id=msg['from'])
                            contact.last_contact_at = timezone.now()
                            contact.save()

                            message_type = msg.get('type')

                            if message_type == 'reaction':
                                reaction_data = msg['reaction']
                                target_wamid = reaction_data['message_id']
                                emoji = reaction_data.get('emoji') # Use .get() to handle reaction removals

                                try:
                                    message_to_update = Message.objects.get(wamid=target_wamid)
                                    if emoji:
                                        message_to_update.status = f"Reacted with {emoji}"
                                    else:
                                        message_to_update.status = 'read' # Reaction was removed
                                    message_to_update.save()
                                except Message.DoesNotExist:
                                    logger.warning(f"Received reaction for a message not found in DB: {target_wamid}")
                                
                                continue 
                            defaults = {
                                'contact': contact, 'direction': 'inbound', 'message_type': message_type,
                                'timestamp': datetime.datetime.fromtimestamp(int(msg['timestamp']), tz=datetime.timezone.utc),
                                'raw_data': msg
                            }
                            if 'context' in msg and msg['context'].get('id'):
                                try:
                                    defaults['replied_to'] = Message.objects.get(wamid=msg['context']['id'])
                                except Message.DoesNotExist: pass
                            
                            if message_type == 'text':
                                defaults['text_content'] = msg['text']['body']
                            elif message_type in ['image', 'video', 'audio', 'document','sticker']:
                                media_info = msg[message_type]
                                defaults['media_id'] = media_info.get('id')
                                defaults['caption'] = media_info.get('caption', '')
                                message_instance, _ = Message.objects.update_or_create(wamid=msg['id'], defaults=defaults)
                                file_name, file_content = download_media_from_meta(media_info['id'])
                                if file_name and file_content:
                                    message_instance.media_file.save(file_name, file_content, save=True)
                                continue

                            elif message_type == 'contacts':
                                contact_data = msg['contacts'][0]
                                
                                # Use the structured name and phone number from the payload
                                defaults['contact_name'] = contact_data['name']['formatted_name']
                                if contact_data.get('phones') and contact_data['phones'][0]:
                                    defaults['contact_phone'] = contact_data['phones'][0].get('phone')

                                # You can optionally still save the raw vCard to the text field
                                if 'vcard' in contact_data:
                                    defaults['text_content'] = contact_data['vcard']

                            elif message_type == 'location':
                                location_data = msg['location']
                                defaults['latitude'] = location_data['latitude']
                                defaults['longitude'] = location_data['longitude']
                                # Save the location name/address to the main text field
                                defaults['text_content'] = location_data.get('name', '') or location_data.get('address', '')
                            
                            elif message_type == 'reaction':
                                emoji = msg['reaction']['emoji']
                                Message.objects.filter(wamid=msg['reaction']['message_id']).update(status=f"Reacted with {emoji}")
                                continue
                            
                            Message.objects.update_or_create(wamid=msg['id'], defaults=defaults)
                            
                            if message_type in ['image', 'video', 'audio', 'document', 'sticker']:
                                media_info = msg[message_type]
                                media_id = media_info.get('id')
                                if media_id:
                                    file_name, file_content = download_media_from_meta(media_id)
                                    if file_name and file_content:
                                        message_instance.media_file.save(file_name, file_content, save=True)
                    elif 'statuses' in value:
                        for status_data in value.get('statuses', []):
                            Message.objects.filter(wamid=status_data['id']).update(status=status_data['status'])
        except Exception as e:
            logger.error(f"Error in webhook: {e}", exc_info=True)
        return JsonResponse({"status": "success"}, status=200)

@login_required
def template_sender_view(request):
    """
    Fetches templates from the Meta API and renders the sender tool page.
    """
    templates_data = []
    error = None
    contacts = ChatContact.objects.all()
    try:
        META_ACCESS_TOKEN="EAAhMBt21QaMBPCyLtJj6gwjDy6Gai4fZApb3MXuZBZCCm0iSEd8ZCZCJdkRt4cOtvhyeFLZCNUwitFaLZA3ZCwv7enN6FBFgDMAOKl7LMx0J2kCjy6Qd6AqnbnhB2bo2tgsdGmn9ZCN5MD6yCgE3shuP62t1spfSB6ZALy1QkNLvIaeWZBcvPH00HHpyW6US4kil2ENZADL4ZCvDLVWV9seSbZCxXYzVCezIenCjhSYtoKTIlJ"
        
        WABA_ID="1477047197063313"
        url = f"https://graph.facebook.com/v19.0/{WABA_ID}/message_templates?fields=name,components,status"
        headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        # Filter for only approved templates
        all_templates = response.json().get('data', [])
        templates_data = [t for t in all_templates if t.get('status') == 'APPROVED']
    except Exception as e:
        logger.error(f"Failed to fetch templates: {e}")
        error = "Could not load templates from Meta API. Please check your credentials."

    
    return render(request, 'registration/chat/template_sender.html', {
        "templates": templates_data,
        "contacts": contacts,
        "error": error,
    })

@csrf_exempt
@login_required
def send_template_api_view(request):
    """
    API endpoint to send a composed template message to one or many recipients.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

    try:
        recipients = request.POST.getlist('recipients[]')  # list of wa_ids
        template_name = request.POST.get('template_name')
        params = request.POST.getlist('params[]')
        media_file = request.FILES.get('header_image')

        results = []

        for wa_id in recipients:
            try:
                contact = ChatContact.objects.get(wa_id=wa_id)

                # Personalize params: replace $name with actual contact name
                personalized_params = []
                for p in params:
                    if "$name" in p:
                        personalized_params.append(p.replace("$name", contact.name or ""))
                    else:
                        personalized_params.append(p)

                payload = {
                    "messaging_product": "whatsapp",
                    "to": wa_id,
                    "type": "template",
                    "template": {
                        "name": template_name,
                        "language": {"code": "en"}
                    }
                }

                components = []
                # Handle header image
                if media_file:
                    media_id = upload_media_to_meta(media_file)
                    if not media_id:
                        results.append({
                            "wa_id": wa_id,
                            "status": "error",
                            "error": "Failed to upload media"
                        })
                        continue
                    components.append({
                        "type": "header",
                        "parameters": [{"type": "image", "image": {"id": media_id}}]
                    })

                # Handle body parameters
                if personalized_params:
                    parameters_list = [{"type": "text", "text": p} for p in personalized_params]
                    components.append({"type": "body", "parameters": parameters_list})

                if components:
                    payload['template']['components'] = components

                success, response_data = send_whatsapp_message(payload)

                if success:
                    # Save outgoing message
                    save_outgoing_message(
                        contact=contact,
                        wamid=response_data['messages'][0]['id'],
                        message_type='template',
                        text_content=f"Sent template: {template_name}",
                        raw_data=response_data
                    )
                    results.append({"wa_id": wa_id, "status": "success", "response": response_data})
                else:
                    results.append({"wa_id": wa_id, "status": "error", "response": response_data})

            except ChatContact.DoesNotExist:
                results.append({"wa_id": wa_id, "status": "error", "error": "Contact not found"})
            except Exception as e:
                logger.error(f"Error sending to {wa_id}: {e}", exc_info=True)
                results.append({"wa_id": wa_id, "status": "error", "error": str(e)})

        return JsonResponse({"results": results})

    except Exception as e:
        logger.error(f"Error in send_template_api_view: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def chat_contact_list_view(request):
    contacts = ChatContact.objects.all().order_by(F('last_contact_at').desc(nulls_last=True))
    return render(request, 'registration/chat/chat_list.html', {'contacts': contacts})

@login_required
def chat_detail_view(request, wa_id):
    wa_id = wa_id.strip()
    contact = get_object_or_404(ChatContact, wa_id=wa_id)
    conversation_messages = list(contact.messages.select_related('replied_to').order_by('timestamp'))
    from types import SimpleNamespace
    try:
        search_number = wa_id[2:] if wa_id.startswith('91') else wa_id
        initial_template_log = WhatsAppLog.objects.filter(recipient_number=search_number, status='sent').order_by('timestamp').first()
        if initial_template_log:
            initial_message = SimpleNamespace(
                direction='outbound', text_content=f"Sent template: {initial_template_log.template_name}",
                timestamp=initial_template_log.timestamp, status='sent', message_type='template',
                media_file=None, caption=None, replied_to=None
            )
            conversation_messages.append(initial_message)
            conversation_messages.sort(key=lambda msg: msg.timestamp)
    except Exception as e:
        logger.error(f"Could not query WhatsAppLog: {e}")
    return render(request, 'registration/chat/chat_detail.html', {'contact': contact, 'messages': conversation_messages})

@csrf_exempt
@login_required
def send_reply_api_view(request):
    to_number = request.POST.get('to_number')
    message_text = request.POST.get('message_text', '').strip()
    media_file = request.FILES.get('media_file')
    replied_to_wamid = request.POST.get('replied_to_wamid')

    if not message_text and not media_file:
        return JsonResponse({'status': 'error', 'message': 'Cannot send an empty message.'}, status=400)

    payload = {"messaging_product": "whatsapp", "to": to_number}
    if replied_to_wamid:
        payload['context'] = {'message_id': replied_to_wamid}
    
    message_api_type = 'text'

    if media_file:
        media_id = upload_media_to_meta(media_file)
        if not media_id:
            return JsonResponse({'status': 'error', 'message': 'Failed to upload media'}, status=500)
        
        
        content_type = media_file.content_type
        if content_type.startswith('image/'):
            message_api_type = 'image'
        elif content_type.startswith('video/'):
            message_api_type = 'video'
        elif content_type.startswith('audio/'):
            message_api_type = 'audio'
        else:
            # Default to 'document' for PDFs, DOCX, etc.
            message_api_type = 'document'
        
        payload['type'] = message_api_type
        payload[message_api_type] = {'id': media_id}

        # --- FIX: Only add caption if message_text is not empty ---
        if message_text:
            payload[message_api_type]['caption'] = message_text
        if message_api_type == 'document':
            payload[message_api_type]['filename'] = media_file.name
    else:
        payload.update({"type": "text", "text": {"body": message_text}})

    success, response_data = send_whatsapp_message(payload)
    if success:
        save_outgoing_message(
            contact=get_object_or_404(ChatContact, wa_id=to_number),
            wamid=response_data['messages'][0]['id'],
            message_type=message_api_type,
            text_content=message_text if not media_file else "",
            caption=message_text if media_file else "",
            raw_data=response_data,
            replied_to_wamid=replied_to_wamid,
            media_file=media_file
        )
        return JsonResponse({'status': 'success', 'data': response_data})
    else:
        return JsonResponse({'status': 'error', 'data': response_data}, status=500)


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
 
    return render(request, 'dashboard/login.html', {'form': form})
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                # --- START OF CHANGE ---
                # Check if the authenticated user is a mukadam.
                # Adjust the condition `user.is_mukadam` to match your model's field name.
                # getattr() is used for a safe check in case the attribute doesn't exist.
                if getattr(user, 'is_mukadam', False):
                    login(request, user)
                    # After successful login, redirect them to the dashboard
                    return redirect('registration:leader_dashboard')
                else:
                    # User is valid, but not a mukadam. Show an error.
                    messages.error(request, "Access Denied: You do not have permission to log in here.")
                # --- END OF CHANGE ---
            else:
                # This handles cases where username/password is incorrect.
                messages.error(request, "Invalid username or password.")
        else:
            # Form itself is invalid (e.g., empty fields)
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

def logout_view(request):
    logout(request)
    # After logout, redirect them back to the login page


@login_required
def job_requests_view(request):
    """Main job requests view with corrected context data."""
    today = now().date()
    four_days_ago = today - timedelta(days=4) # Changed from 2 to 4 as in your template text

    # Get jobs for the tabs
    latest_jobs = Job.objects.filter(
        status='pending',
        created_at__date__gte=four_days_ago
    ).order_by('-created_at')

    pending_jobs = Job.objects.filter(
        status='pending',
        created_at__date__lt=four_days_ago
    ).order_by('-created_at')

    # ongoing_jobs = Job.objects.filter(
    #     status__in=['waiting_for_response', 'ongoing']
    # ).order_by('-created_at')

    completed_jobs = Job.objects.filter(
        status='completed'
    ).order_by('-completion_date')

    # KEY CHANGE: Create a combined list of jobs that need allocation for the modals
    allocatable_jobs = list(latest_jobs) + list(pending_jobs)

    # Get all team leaders
    # Note: Assumes leaders are not superusers to filter out main admins.
    # team_leaders = User.objects.filter(is_superuser=False & is_mukadam = False).distinct()
    # Excludes any user who is a member of the group named 'Mukadam'
    team_leaders = User.objects.exclude(groups__name='Mukadams')
    ongoing_jobs = Job.objects.filter(
    status__in=['waiting_for_response', 'leader_responded', 'ongoing']
).order_by('-updated_at')

    context = {
        'latest_jobs': latest_jobs,
        'pending_jobs': pending_jobs,
        'ongoing_jobs': ongoing_jobs,
        'completed_jobs': completed_jobs,
        'allocatable_jobs': allocatable_jobs, # Pass this new list to the template
        'team_leaders': team_leaders,
        'today_date': today.isoformat(),
    }
    return render(request, 'registration/job/job_requests.html', context)

@login_required
def job_create_view(request):
    """View to create a new job."""
    if request.method == 'POST':
        # If the form is submitted, process the data
        form = JobForm(request.POST)
        if form.is_valid():
            form.save() # The new job is created and saved
            # Redirect to the main job list page after successful creation
            return redirect('registration:job_requests') 
    else:
        # If it's a GET request, show an empty form
        form = JobForm()
    
    context = {
        'form': form
    }
    return render(request, 'registration/job/job_form.html', context)


@login_required
def job_detail_view(request, job_id):
    """Shows the full details of a single job."""
    job = get_object_or_404(Job, id=job_id)
    assignments = JobAssignment.objects.filter(job=job).select_related('content_type')


    # If the job is ongoing or completed, find the team that was assigned
   
    context = {
        'job': job,
        'assignments': assignments,
    }
    return render(request, 'registration/job/job_detail.html', context)


# You'll also need the view to handle the form submission
@login_required
def allocate_job_to_leaders(request, job_id):
    if request.method == 'POST':
        job = Job.objects.get(id=job_id)
        leader_ids = request.POST.getlist('leaders') # 'leaders' is the name of our select input

        leaders = User.objects.filter(id__in=leader_ids)

        for leader in leaders:
            JobLeaderAllocation.objects.get_or_create(job=job, leader=leader)

            job.sent_to_leaders.add(leader)
            Notification.objects.create(
                user=leader,
                message=f"You have been requested for a new job: '{job.title}'.",
                job=job
            )

        # Update job status and save
        job.status = 'waiting_for_response'
        job.save()

        # You can add a Django message here for user feedback
        # messages.success(request, f"Request sent to {len(leaders)} leaders for job '{job.title}'.")
        return redirect('registration:job_requests')

    # Redirect if accessed via GET
    return redirect('registration:job_requests')


@login_required
def mark_notification_read_and_redirect_view(request, notification_id):
    """Marks a notification as read and redirects the leader to the relevant page."""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save()
    
    # Redirect to the page to find laborers for the job linked to the notification
    # 1. First, check if this is a Bid Notification
    bid_content_type = ContentType.objects.get_for_model(JobBid)
    if notification.content_type == bid_content_type:
        # If it's a bid notification, go to the leader's bid page
        return redirect('registration:leader_bids')

    # 2. If not a bid, check if it's an old job allocation notification
    elif notification.job:
        # This is your old logic, which we keep for backwards compatibility
        # NOTE: You might want to change where this goes, e.g., to the job detail page
        return redirect('registration:find_laborers_for_job', job_id=notification.job.id)

    return redirect('registration:leader_dashboard')

# @login_required
# def leader_new_requests_view(request):
#     """Displays new job requests sent to the leader."""
#     all_notifications = Notification.objects.filter(user=request.user)
#     unread_count = all_notifications.filter(is_read=False).count()
    
#     assigned_jobs = Job.objects.filter(
#         sent_to_leaders=request.user, 
#         status='waiting_for_response'
#     ).order_by('-created_at')

#     context = {
#         'assigned_jobs': assigned_jobs,
#         'notifications': all_notifications.order_by('-created_at')[:5],
#         'unread_count': unread_count,
#     }
#     return render(request, 'registration/leader/leader_new_requests.html', context)

# @login_required
# def leader_confirmations_view(request):
#     """Displays jobs approved by admin, awaiting leader's final confirmation."""
#     all_notifications = Notification.objects.filter(user=request.user)
#     unread_count = all_notifications.filter(is_read=False).count()

#     jobs_awaiting_confirmation = Job.objects.filter(
#         finalized_leader=request.user, 
#         status='awaiting_leader_confirmation'
#     ).order_by('-updated_at')

#     context = {
#         'jobs_awaiting_confirmation': jobs_awaiting_confirmation,
#         'notifications': all_notifications.order_by('-created_at')[:5],
#         'unread_count': unread_count,
#     }
#     return render(request, 'registration/leader/leader_confirmations.html', context)


# @login_required
# def leader_ongoing_jobs_view(request):
#     """Displays jobs that the leader has confirmed and are in progress."""
#     all_notifications = Notification.objects.filter(user=request.user)
#     unread_count = all_notifications.filter(is_read=False).count()

#     ongoing_jobs = Job.objects.filter(
#         finalized_leader=request.user, 
#         status='ongoing'
#     ).order_by('-updated_at')

#     context = {
#         'ongoing_jobs': ongoing_jobs,
#         'notifications': all_notifications.order_by('-created_at')[:5],
#         'unread_count': unread_count,
#     }
#     return render(request, 'registration/leader/leader_ongoing_jobs.html', context)


# registration/views.py

@login_required
def leader_new_requests_view(request):
    """Displays new job requests and marks related notifications as read."""
    
    # Mark notifications for new jobs as read UPON visiting this page
    Notification.objects.filter(
        user=request.user,
        is_read=False,
        job__status='waiting_for_response'
    ).update(is_read=True)

    # Get all notifications for the navbar dropdown
    all_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_count = all_notifications.filter(is_read=False).count()
    
    assigned_jobs = Job.objects.filter(sent_to_leaders=request.user, status='waiting_for_response').order_by('-created_at')

    context = {
        'assigned_jobs': assigned_jobs,
        'notifications': all_notifications[:5], # Show 5 most recent in dropdown
        'unread_count': unread_count,
    }
    return render(request, 'registration/leader/leader_new_requests.html', context)


@login_required
def leader_confirmations_view(request):
    """Displays jobs awaiting confirmation and marks related notifications as read."""

    # Mark notifications for jobs needing confirmation as read UPON visiting this page
    Notification.objects.filter(
        user=request.user,
        is_read=False,
        job__status='awaiting_leader_confirmation'
    ).update(is_read=True)

    all_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_count = all_notifications.filter(is_read=False).count()

    jobs_awaiting_confirmation = Job.objects.filter(
        finalized_leader=request.user, 
        status='awaiting_leader_confirmation'
    ).order_by('-updated_at')

    context = {
        'jobs_awaiting_confirmation': jobs_awaiting_confirmation,
        'notifications': all_notifications[:5],
        'unread_count': unread_count,
    }
    return render(request, 'registration/leader/leader_confirmations.html', context)


@login_required
def leader_ongoing_jobs_view(request):
    """Displays jobs that are in progress."""
    all_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_count = all_notifications.filter(is_read=False).count()

    ongoing_jobs = Job.objects.filter(finalized_leader=request.user, status='ongoing').order_by('-updated_at')

    context = {
        'ongoing_jobs': ongoing_jobs,
        'notifications': all_notifications[:5],
        'unread_count': unread_count,
    }
    return render(request, 'registration/leader/leader_ongoing_jobs.html', context)

@login_required
def find_laborers_view(request, job_id):
    """
    Page for a leader to find and filter available workers for a specific job.
    """
    job = get_object_or_404(Job, id=job_id)

    # Find all workers who are already booked
    booked_status = WorkerStatus.objects.filter(availability_status='booked')
    
    # Create a dictionary to easily check if a worker is booked
    booked_workers = {}
    for status in booked_status:
        # Key: "model_name-pk", e.g., "individuallabor-5"
        key = f"{status.content_type.model}-{status.object_id}"
        booked_workers[key] = True

    # Query all potential workers and then filter out the booked ones in Python
    # This is often more efficient than complex multi-table EXCLUDE queries
    all_individuals = [w for w in IndividualLabor.objects.all() if f"individuallabor-{w.pk}" not in booked_workers]
    all_mukkadams = [w for w in Mukkadam.objects.all() if f"mukkadam-{w.pk}" not in booked_workers]
    all_transports = [w for w in Transport.objects.all() if f"transport-{w.pk}" not in booked_workers]

    context = {
        'job': job,
        'available_individuals': all_individuals,
        'available_mukkadams': all_mukkadams,
        'available_transports': all_transports,
    }
    return render(request, 'registration/labours/find_laborers.html', context)

from django.contrib.contenttypes.models import ContentType

@login_required
def assign_team_to_job_view(request, job_id):
    """STEP 1: Leader proposes a team by updating WorkerStatus to 'proposed'."""
    job = get_object_or_404(Job, id=job_id)
    if request.method == 'POST':
        worker_ids = request.POST.getlist('workers')
        response_message = request.POST.get('response_message', '')
        quoted_price = request.POST.get('quoted_price')

        for worker_id_str in worker_ids:
            model_name, pk = worker_id_str.split('-')
            content_type = ContentType.objects.get(model=model_name)
            WorkerStatus.objects.update_or_create(
                content_type=content_type, object_id=pk,
                defaults={
                    'availability_status': 'proposed',
                    'current_job': job,
                    'proposed_by': request.user
                }
            )
        
        job.finalized_leader = request.user
        job.status = 'leader_responded'
        job.leader_response_message = response_message
        if quoted_price:
            job.leader_quoted_price = Decimal(quoted_price)
        job.save()

        # Notify admin
        admin_user = User.objects.filter(is_superuser=True).first()
        if admin_user:
            Notification.objects.create(
                user=admin_user,
                message=f"Leader {request.user.username} has proposed a team for '{job.title}'.",
                job=job
            )
        
        messages.success(request, "Your team proposal has been sent.")
        return redirect('registration:leader_dashboard')
    return redirect('registration:find_laborers_for_job', job_id=job.id)


@login_required
def request_help_view(request, assignment_id):
    assignment = get_object_or_404(JobAssignment, id=assignment_id)
    if request.method == 'POST':
        # Prevent duplicate pending requests
        if HelpRequest.objects.filter(assignment=assignment, status='pending').exists():
            messages.error(request, 'There is already a pending request for this worker.')
        else:
            request_type = request.POST.get('request_type')
            details = request.POST.get('details', '')
            HelpRequest.objects.create(
                assignment=assignment,
                request_type=request_type,
                details=details
            )
            messages.success(request, 'Your requirement request has been sent to the admin.')
            
    return redirect('registration:leader_manage_team', job_id=assignment.job.id)

@login_required
# @user_passes_test(lambda u: u.is_superuser) # Optional: ensure only admins can access
def resolve_help_request_view(request, request_id):
    help_request = get_object_or_404(HelpRequest, id=request_id)
    job_id = help_request.assignment.job.id
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            help_request.status = 'approved'
            messages.success(request, 'The request has been approved.')
        elif action == 'reject':
            help_request.status = 'rejected'
            messages.warning(request, 'The request has been rejected.')
        
        help_request.resolved_at = timezone.now()
        help_request.save()

    return redirect('registration:live_job_status', job_id=job_id)

@login_required
def view_leader_response_view(request, job_id):
    """A simple view for the ADMIN to see the leader's response."""
    job = get_object_or_404(Job, id=job_id)
    # Add logic here for the admin to approve the team, which would change the status to 'ongoing'
    # For now, just display the details.
    # NEW LOGIC: Find workers by their 'proposed' status for this job
    proposed_worker_statuses = WorkerStatus.objects.filter(
        current_job=job,
        availability_status='proposed'
    )
    # Manually fetch the actual worker objects for display
    proposed_workers = [status.worker for status in proposed_worker_statuses]

    context = {
        'job': job,
        'assignments': proposed_workers, # Pass the worker objects to the template
    }
    return render(request, 'registration/job/admin_view_response.html', context)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Job, JobAssignment,HelpRequest, StatusUpdate, User,JobLeaderAllocation

@login_required
def leader_manage_team_view(request, job_id):
    """
    Displays the team management page for a specific job, including the
    current status and the next possible status action for each worker.
    """
    job = get_object_or_404(Job, id=job_id, finalized_leader=request.user)
    assignments = JobAssignment.objects.filter(job=job)

    # Define the sequence of statuses
    status_sequence = [choice[0] for choice in StatusUpdate.STATUS_CHOICES]
    
    assignments_with_status = []
    for assignment in assignments:
        latest_update = assignment.status_updates.order_by('-timestamp').first()
        current_status = latest_update.status if latest_update else None

        next_status = None
        if current_status:
            # Find the next status in the sequence, if not the last one
            try:
                current_index = status_sequence.index(current_status)
                if current_index < len(status_sequence) - 1:
                    next_status = status_sequence[current_index + 1]
            except ValueError:
                # This handles cases where status might be invalid, though unlikely
                pass
        else:
            # If there's no status yet, the first one is the next logical step
            next_status = status_sequence[0]

        help_request = HelpRequest.objects.filter(assignment=assignment).order_by('-created_at').first()
        
        assignments_with_status.append({
            'assignment': assignment,
            'latest_update': latest_update,
            'next_status': next_status,
            'help_request': help_request # Add this to the context item
        })

    context = {
        'job': job,
        'assignments_with_status': assignments_with_status,
        'all_statuses': StatusUpdate.STATUS_CHOICES,
    }
    return render(request, 'registration/leader/leader_manage_team.html', context)
@login_required
def update_worker_status_view(request, assignment_id):
    """
    Handles the POST request from the leader's "Manage Team" page.
    Its only job is to create a new status update and redirect back.
    """
    # Use a generic redirect in case something goes wrong early
    fallback_redirect = redirect('registration:leader_dashboard')

    if request.method == 'POST':
        print(f"Received POST for assignment_id: {assignment_id}") # DEBUG
        try:
            # This is the most likely point of failure.
            assignment = get_object_or_404(JobAssignment, id=assignment_id, job__finalized_leader=request.user)
            fallback_redirect = redirect('registration:leader_manage_team', job_id=assignment.job.id)
        except JobAssignment.DoesNotExist:
             messages.error(request, "Assignment not found or you do not have permission to update it.")
             return fallback_redirect

        new_status = request.POST.get('status')
        print(f"Attempting to set new status: {new_status}") # DEBUG

        # Check if the status is valid
        valid_statuses = [choice[0] for choice in StatusUpdate.STATUS_CHOICES]
        if new_status in valid_statuses:
            StatusUpdate.objects.create(
                assignment=assignment,
                status=new_status,
                updated_by=request.user
            )
            messages.success(request, f"Status for '{assignment.worker.full_name}' successfully updated to '{dict(StatusUpdate.STATUS_CHOICES)[new_status]}'.")
            print("Status update successful!") # DEBUG
        else:
            messages.error(request, "Invalid status provided.")
            print(f"Invalid status '{new_status}' received.") # DEBUG

        return fallback_redirect

    # Redirect if accessed via GET
    return fallback_redirect


from django.db.models import Exists, OuterRef
# registration/views.py

@login_required
def live_job_status_view(request, job_id):
    # ... (code at the top of the view is the same)
    job = get_object_or_404(Job, id=job_id)

    # UPDATED QUERY FOR STATUS UPDATES
    status_updates = StatusUpdate.objects.filter(
        assignment__job=job
    ).select_related('assignment').prefetch_related(
        'assignment__content_object'  # CHANGED from assigned_object
    ).order_by('-timestamp')

    all_help_requests = HelpRequest.objects.filter(
        assignment__job=job
    ).select_related(
        'assignment'
    ).prefetch_related(
        'assignment__content_object'
    ).order_by('-created_at') 

    pending_help_requests = [req for req in all_help_requests if req.status == 'pending']
    resolved_help_requests = [req for req in all_help_requests if req.status != 'pending']
    # --- END MODIFIED SECTION ---


    # ... (The rest of your view for checking completion is the same)
    total_assignments = JobAssignment.objects.filter(job=job).count()
    incomplete_assignments_exist = JobAssignment.objects.filter(
        job=job
    ).exclude(
        status_updates__status='payment_processed'
    ).exists()
    all_complete = (total_assignments > 0) and not incomplete_assignments_exist
    
    context = {
        'job': job,
        'status_updates': status_updates,
        'pending_help_requests': pending_help_requests,  # Pass the pending list
        'resolved_help_requests': resolved_help_requests, # Pass the resolved list
        'show_complete_button': all_complete,
    }
    return render(request, 'registration/job/live_job_status.html', context)

@login_required
def approve_team_view(request, job_id):
    """Admin action to approve a leader's proposed team and start the job."""
    if request.method == 'POST':
        job = get_object_or_404(Job, id=job_id)
        job.status = 'awaiting_leader_confirmation'
        job.save()
        if job.finalized_leader:
            Notification.objects.create(
                user=job.finalized_leader,
                message=f"Admin has approved your team for '{job.title}'. Please confirm to start.",
                job=job
            )
        messages.success(request, "Approval sent to leader for final confirmation.")
    return redirect('registration:job_requests')
# --- 2. ADD these two NEW views for the leader's actions ---

@login_required
def leader_confirm_start_view(request, job_id):
    """STEP 2: Leader gives FINAL confirmation. JobAssignments and the first 'assigned' status are created."""
    job = get_object_or_404(Job, id=job_id, finalized_leader=request.user)
    if request.method == 'POST':
        proposed_statuses = WorkerStatus.objects.filter(
            current_job=job,
            availability_status='proposed',
            proposed_by=request.user
        )
        for status in proposed_statuses:
            assignment, created = JobAssignment.objects.get_or_create(
                job=job, content_type=status.content_type, object_id=status.object_id,
                defaults={'assigned_by': request.user}
            )
            if created:
                StatusUpdate.objects.create(
                    assignment=assignment,
                    status='assigned',
                    updated_by=request.user
                )
            status.availability_status = 'booked'
            status.save()

        job.status = 'ongoing'
        job.save()
        messages.success(request, f"You have confirmed the job '{job.title}'.")
    return redirect('registration:leader_dashboard')

@login_required
def leader_cancel_job_view(request, job_id):
    """Leader action to cancel the job after admin approval."""
    job = get_object_or_404(Job, id=job_id, finalized_leader=request.user)
    if request.method == 'POST':
        # This logic is similar to the admin's reject view
        # 1. Free up workers
        assignments = JobAssignment.objects.filter(job=job)
        for assignment in assignments:
            WorkerStatus.objects.update_or_create(
                content_type=assignment.content_type,
                object_id=assignment.object_id,
                defaults={'availability_status': 'available', 'current_job': None}
            )
        # 2. Delete assignments
        assignments.delete()
        # 3. Reset job fields
        job.status = 'pending'
        job.finalized_leader = None
        job.leader_response_message = None
        job.leader_quoted_price = None
        job.save()
        messages.error(request, f"You have canceled the job '{job.title}'. It is now pending again.")
        # Notify admin of cancellation
        admin_user = User.objects.filter(is_superuser=True).first()
        if admin_user:
             Notification.objects.create(user=admin_user, message=f"Leader CANCELED the job after approval: '{job.title}'", job=job)
    return redirect('registration:leader_dashboard')

@login_required
def reject_team_view(request, job_id):
    """Admin action to reject a leader's proposed team and reopen the job."""
    if not request.user.is_superuser:
        return redirect('registration:leader_dashboard')

    if request.method == 'POST':
        job = get_object_or_404(Job, id=job_id)
        rejected_leader = job.finalized_leader

        # 1. Free up all the workers that were part of the proposed team
        assignments = JobAssignment.objects.filter(job=job)
        for assignment in assignments:
            WorkerStatus.objects.update_or_create(
                content_type=assignment.content_type,
                object_id=assignment.object_id,
                defaults={'availability_status': 'available', 'current_job': None}
            )
        
        # 2. Delete the now-rejected assignments
        assignments.delete()

        # 3. Reset the job's fields and revert its status to 'pending'
        job.status = 'pending'
        job.finalized_leader = None
        job.leader_response_message = None
        job.leader_quoted_price = None
        job.save()

        # 4. Notify the rejected leader
        if rejected_leader:
            Notification.objects.create(
                user=rejected_leader,
                message=f"Your proposed team for '{job.title}' was not approved. The job has been reopened.",
                job=job
            )

        messages.warning(request, f"Team rejected for '{job.title}'. The job is now pending reallocation.")
        return redirect('registration:job_requests')

    return redirect('registration:job_requests')
@login_required
def job_response_view(request, job_id):
    """View to manage responses from team leaders"""
    job = get_object_or_404(Job, id=job_id)
    responses = JobLeaderResponse.objects.filter(job=job).select_related('leader')
    
    context = {
        'job': job,
        'responses': responses,
    }
    return render(request, 'registration/job_response_screen.html', context)

# API Views
@login_required
def respond_to_job_api(request, job_id):
    """API endpoint for leaders to respond to job requests"""
    if request.method == 'POST':
        job = get_object_or_404(Job, id=job_id)
        response_type = request.POST.get('response')  # 'accepted' or 'rejected'
        quoted_price = request.POST.get('quoted_price')
        rejection_reason = request.POST.get('rejection_reason', '')
        available_workers = request.POST.get('available_workers_count')
        
        # Update or create response
        job_response, created = JobLeaderResponse.objects.update_or_create(
            job=job,
            leader=request.user,
            defaults={
                'response': response_type,
                'quoted_price': quoted_price if response_type == 'accepted' else None,
                'rejection_reason': rejection_reason if response_type == 'rejected' else '',
                'available_workers_count': available_workers if response_type == 'accepted' else None,
                'response_date': timezone.now()
            }
        )
        
        # Create notification for admin
        admin_users = User.objects.filter(is_superuser=True)
        for admin in admin_users:
            Notification.objects.create(
                user=admin,
                title=f'Job Response: {job.title}',
                message=f'{request.user.get_full_name()} has {response_type} the job "{job.title}".',
                job=job
            )
        
        return JsonResponse({'status': 'success', 'message': 'Response recorded successfully.'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


# registration/views.py


# registration/views.py

from datetime import timedelta
from decimal import Decimal
from geopy.geocoders import GoogleV3
from geopy.distance import geodesic
from .models import Job, LaboursAdvancedProfiles # Ensure models are imported

@login_required
def advanced_labor_search_view(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # --- Geocoding setup remains the same ---
    API_KEY = "AIzaSyC0gN6MTJX6Nn1I0Ia41XeTMbThF3Nu_dY"
    geolocator = GoogleV3(api_key=API_KEY)
    try:
        job_geocode = geolocator.geocode(job.location)
        if not job_geocode:
            messages.error(request, f"Could not find coordinates for job location: {job.location}")
            return redirect('registration:find_laborers_for_job', job_id=job.id)
        job_coords = (job_geocode.latitude, job_geocode.longitude)
    except Exception as e:
        messages.error(request, f"Location service error: {e}")
        return redirect('registration:find_laborers_for_job', job_id=job.id)

    # --- NEW LOGIC FOR DATE RANGE OVERLAP ---

    # 1. Define the job's required date range
    job_start_date = job.required_by_date
    job_end_date = job_start_date + timedelta(days=job.duration_days - 1)

    # 2. Find all profiles whose availability range OVERLAPS with the job's range.
    # The logic is: their availability starts before the job ends, AND their availability ends after the job starts.
    overlapping_profiles = LaboursAdvancedProfiles.objects.filter(
        available_from__isnull=False, # Ensure dates are not empty
        available_to__isnull=False,
        available_from__lte=job_end_date,
        available_to__gte=job_start_date
    )
    
    ranked_laborers = []
    for profile in overlapping_profiles:
        # --- Transport cost logic remains the same ---
        transport_cost = Decimal(0)
        if profile.requires_transport:
            try:
                labourer_location_str = f"{profile.labour.village}, {profile.labour.taluka}"
                labourer_geocode = geolocator.geocode(labourer_location_str)
                if labourer_geocode:
                    labourer_coords = (labourer_geocode.latitude, labourer_geocode.longitude)
                    distance_km = geodesic(job_coords, labourer_coords).kilometers
                    transport_cost = Decimal(distance_km * 5)
                else: continue
            except Exception: continue

        # --- NEW: Calculate the actual number of overlapping days for profit calculation ---
        overlap_start = max(job_start_date, profile.available_from)
        overlap_end = min(job_end_date, profile.available_to)
        overlapping_days = (overlap_end - overlap_start).days + 1
        
        if overlapping_days <= 0:
            continue # Should not happen with the query above, but a good safeguard

        # Calculate profit based on the ACTUAL number of days they can work
        job_revenue_for_overlap = job.rate_per_day * overlapping_days
        labourer_cost_for_overlap = (profile.advanced_rate_per_day * overlapping_days) + transport_cost
        profit = job_revenue_for_overlap - labourer_cost_for_overlap
        
        # We now include everyone with an overlap, for negotiation purposes
        ranked_laborers.append({
            'labourer': profile.labour,
            'profit': profit,
            'transport_cost': transport_cost,
            'profile': profile,
            'overlapping_days': overlapping_days,
            'overlap_start_date': overlap_start,
            'overlap_end_date': overlap_end,
        })

    # Sort the final list by profit, highest first
    ranked_laborers.sort(key=lambda x: x['profit'], reverse=True)
    
    context = {
        'job': job,
        'ranked_laborers': ranked_laborers,
    }
    return render(request, 'registration/labours/advanced_search_results.html', context)


# registration/views.py
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .models import Job, Mukkadam, JobBid
from .forms import JobBidForm
from .decorators import mukadam_required

# --- Mukadam Login/Logout ---
def mukadam_login_view(request):
    if request.user.is_authenticated:
        if request.user.groups.filter(name='Mukadams').exists():
            return redirect('registration:mukadam_dashboard')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.groups.filter(name='Mukadams').exists():
                login(request, user)
                return redirect('registration:mukadam_dashboard')
            else:
                messages.error(request, 'This portal is for Mukadams only.')
        else:
            messages.error(request, 'Invalid username or password.')
    
    form = AuthenticationForm()
    return render(request, 'registration/mukadam/login.html', {'form': form})

def mukadam_logout_view(request):
    logout(request)
    return redirect('registration:mukadam_login')


# --- Mukadam Portal Views ---
# registration/views.py
from django.db.models import Q # Make sure Q is imported
# registration/views.py



# registration/views.py
from django.db.models import Q # Make sure Q is imported

@mukadam_required
def mukadam_dashboard_view(request):
    mukadam_profile = get_object_or_404(Mukkadam, user=request.user)
    
    # NEW QUERY:
    # Get all jobs that are NOT ongoing or completed, AND the deadline has not passed.
    open_jobs = Job.objects.filter(
        ~Q(status='ongoing') &
        ~Q(status='completed'),
        bidding_deadline__gte=timezone.now()
    ).order_by('required_by_date')

    my_bids = JobBid.objects.filter(mukadam=mukadam_profile).select_related('job')
    my_bid_job_ids = [bid.job.id for bid in my_bids]

    context = {
        'open_jobs': open_jobs,
        'my_bids': my_bids,
        'my_bid_job_ids': my_bid_job_ids,
        'mukadam_profile': mukadam_profile,
    }
    return render(request, 'registration/mukadam/dashboard.html', context)


@mukadam_required
def mukadam_profile_view(request):
    profile = get_object_or_404(Mukkadam, user=request.user)
    context = {'profile': profile}
    return render(request, 'registration/mukadam/profile.html', context)


# In mukadam_views.py (or views.py)

@mukadam_required
def mukadam_bid_view(request, job_id):
    job = get_object_or_404(Job, id=job_id, bidding_deadline__gte=timezone.now())
    mukadam_profile = get_object_or_404(Mukkadam, user=request.user)
    
    # ▼▼▼ 1. ADD THIS LINE ▼▼▼
    # Get the count of this Mukkadam's registered laborers for the template.
    mukkadam_labourer_count = mukadam_profile.registered_labourers.count()
    
    existing_bid = JobBid.objects.filter(job=job, mukadam=mukadam_profile).first()

    if request.method == 'POST':
        # ▼▼▼ 2. PASS MUKKADAM HERE ▼▼▼
        # Pass the mukkadam's profile into the form so it can filter the dropdown.
        form = JobBidForm(request.POST, instance=existing_bid, mukkadam=mukadam_profile)
        if form.is_valid():
            bid = form.save(commit=False)
            bid.job = job
            bid.mukadam = mukadam_profile
            bid.save()
            form.save_m2m() # Saves the many-to-many relationship for labourers
            
            messages.success(request, f"Your bid for '{job.title}' has been updated successfully!")
            return redirect('registration:mukadam_dashboard')
    else:
        # ▼▼▼ 2. PASS MUKKADAM HERE AS WELL ▼▼▼
        form = JobBidForm(instance=existing_bid, mukkadam=mukadam_profile)

    context = {
        'form': form,
        'job': job,
        # ▼▼▼ 3. ADD THE COUNT TO THE CONTEXT ▼▼▼
        'mukkadam_labourer_count': mukkadam_labourer_count,
    }
    return render(request, 'registration/mukadam/bid_form.html', context)
# registration/views.py
from django.db.models import Prefetch # Make sure to import Prefetch

# ... (keep all your other views) ...

# registration/views.py
from django.db.models import Q, Prefetch # Make sure Q and Prefetch are imported

# ... (keep all your other views) ...

# registration/views.py
from django.db.models import Count # Make sure to import Count

# --- UPDATE THIS VIEW ---
# registration/views.py
from django.db.models import Count, Q # Make sure Q is imported
from django.utils import timezone
from .models import Job, JobBid # and other models

# ... (other views) ...

# --- REPLACE your old live_bids_dashboard_view with this ---
@login_required
def live_bids_dashboard_view(request):
    """
    This is the SUMMARY view. It shows jobs and the number of bids.
    This version uses the CORRECT query.
    """
    # This query now matches your mukadam_dashboard_view logic
    biddable_jobs_query = Job.objects.filter(
        ~Q(status='ongoing') &
        ~Q(status='completed'),
        bidding_deadline__gte=timezone.now()
    )

    # Use annotate() to efficiently count the number of bids for each job
    jobs_with_bid_counts = biddable_jobs_query.annotate(
        bid_count=Count('bids')
    ).order_by('-created_at')

    context = {
        'jobs': jobs_with_bid_counts
    }
    return render(request, 'registration/bids/live_bids_dashboard.html', context)

# ... (rest of your views.py) ...

# --- ADD THIS NEW VIEW for the detail page ---
@login_required
def bid_detail_view(request, job_id):
    """
    Displays the full list of bids for a SINGLE job and shows allocated leaders.
    """
    job = get_object_or_404(Job, id=job_id)
    
    # Get all bids for this job, lowest price first
    bids = JobBid.objects.filter(job=job).order_by('bid_price').select_related('mukadam')
    
    # Get all leaders allocated to this job from our new model
    allocations = JobLeaderAllocation.objects.filter(job=job).select_related('leader')
    
    context = {
        'job': job,
        'bids': bids,
        'allocations': allocations,
    }
    return render(request, 'registration/bids/bid_detail.html', context)



# # --- ADD THIS NEW VIEW for the notification action ---
# @require_POST # Ensures this can only be called by a form submission
# @login_required
# def notify_leader_of_bid_view(request, bid_id):
#     bid = get_object_or_404(JobBid, id=bid_id)
#     job = bid.job
    
#     # Find all leaders allocated to this job
#     allocations = JobLeaderAllocation.objects.filter(job=job)
    
#     if not allocations:
#         messages.error(request, f"Cannot send notification: No leader is allocated to the job '{job.title}'.")
#         return redirect('registration:bid_detail', job_id=job.id)

#     # Create a detailed notification for each allocated leader
#     for allocation in allocations:
#         leader = allocation.leader
#         Notification.objects.create(
#             user=leader,
#             message=(
#                 f"A promising bid was placed for '{job.title}'. "
#                 f"Mukadam: {bid.mukadam.full_name}, "
#                 f"he has this much worker: {bid.workers_provided}"
#             ),
#             job=job
#         )
    
#     messages.success(request, f"Notification about {bid.mukadam.full_name}'s bid sent to {allocations.count()} leader(s).")
#     return redirect('registration:bid_detail', job_id=job.id)

# registration/views.py

@require_POST
@login_required
def notify_leader_of_bid_view(request, bid_id):
    bid = get_object_or_404(JobBid, id=bid_id)
    job = bid.job
    allocations = JobLeaderAllocation.objects.filter(job=job)
    
    bid_content_type = ContentType.objects.get_for_model(JobBid)
    

    message_lines = [
        f"A promising bid was placed for '{job.title}'.",
        f"Mukadam: {bid.mukadam.full_name}",
        f"Bid Price: {bid.bid_price}",
        f"Workers Provided: {bid.workers_provided}",
    ]

    if not allocations:
        messages.error(request, f"Cannot send: No leader is allocated to '{job.title}'.")
        return redirect('registration:bid_detail', job_id=job.id)

    if bid.notes_on_skills:
        message_lines.append(f"Skills Mentioned: {bid.notes_on_skills}")

    # Add the list of registered labourers if they were selected
    registered_labourers = bid.registered_labourers.all()
    if registered_labourers:
        labourer_names = ", ".join([labourer.full_name  for labourer in registered_labourers])
        labourer_number = ", ".join([labourer.mobile_number  for labourer in registered_labourers])
       
        message_lines.append(f"Registered Labourers in Bid: {labourer_names}")
        
    # Join all the lines into a single message
    detailed_message = "\n".join(message_lines)

    # Create a notification for each allocated leader
    for allocation in allocations:
        leader = allocation.leader
        Notification.objects.create(
            user=leader,
            title=f"New Bid from {bid.mukadam.full_name}", # A more specific title
            message=detailed_message,
            job=job,

            content_type=bid_content_type,
            object_id=bid.pk
            
        )
    
    # This success message is already in your code and will work as you requested
    messages.success(request, f"Notification about {bid.mukadam.full_name}'s bid sent to {allocations.count()} leader(s).")
    return redirect('registration:bid_detail', job_id=job.id)
# registration/views.py

# registration/views.py

@login_required
def leader_bids_view(request):
    bid_content_type = ContentType.objects.get_for_model(JobBid)
    
    # Find all notifications for this leader that are linked to a JobBid
    bid_notifications = Notification.objects.filter(
        user=request.user,
        content_type=bid_content_type
    )

    # --- START OF DEBUG CODE ---
    print("\n--- Leader Bids Page Debug ---")
    print(f"Logged in as leader: {request.user.username}")
    print(f"Looking for notifications with ContentType ID: {bid_content_type.id} (JobBid)")
    print(f"Found {bid_notifications.count()} bid-related notifications for this user.")
    for notif in bid_notifications:
        print(f"  -> Notification ID: {notif.id}, Message: {notif.message}")
    print("----------------------------\n")
    # --- END OF DEBUG CODE ---
    
    # Mark these notifications as read when the leader visits the page
    bid_notifications.filter(is_read=False).update(is_read=True)

    context = {
        'bid_notifications': bid_notifications,
    }
    return render(request, 'registration/leader/leader_bids.html', context)



# registration/views.py
from django.db.models import Count, Sum, Avg

# --- MUKADAM PROFILE VIEW ---
@login_required # Should be admin only
def mukadam_performance_profile_view(request, mukadam_id):
    mukadam = get_object_or_404(Mukkadam, id=mukadam_id)
    
    all_bids = JobBid.objects.filter(mukadam=mukadam).order_by('-timestamp')
    won_bids = all_bids.filter(status='won')
    
    # Calculate stats
    stats = {
        'total_bids': all_bids.count(),
        'bids_won': won_bids.count(),
        'total_earnings': won_bids.aggregate(total=Sum('bid_price'))['total'] or 0,
        'total_workers_provided': won_bids.aggregate(total=Sum('workers_provided'))['total'] or 0,
    }
    
    # Get feedback
    feedback_ct = ContentType.objects.get_for_model(Mukkadam)
    feedback = JobFeedback.objects.filter(content_type=feedback_ct, object_id=mukadam.id)
    stats['average_rating'] = feedback.aggregate(avg=Avg('rating'))['avg'] or 'N/A'

    context = {
        'mukadam': mukadam,
        'stats': stats,
        'all_bids': all_bids,
        'feedback_list': feedback,
    }
    return render(request, 'registration/profiles/mukadam_profile.html', context)


# --- LABOURER PROFILE VIEW ---
@login_required
def labourer_profile_view(request, labourer_id):
    labourer = get_object_or_404(IndividualLabor, id=labourer_id)
    
    # Get work history
    labourer_ct = ContentType.objects.get_for_model(IndividualLabor)
    work_history = JobAssignment.objects.filter(content_type=labourer_ct, object_id=labourer.id).select_related('job')
    
    # Get feedback
    feedback = JobFeedback.objects.filter(content_type=labourer_ct, object_id=labourer.id)
    average_rating = feedback.aggregate(avg=Avg('rating'))['avg'] or 'N/A'

    context = {
        'labourer': labourer,
        'work_history': work_history,
        'job_count': work_history.count(),
        'average_rating': average_rating,
    }
    return render(request, 'registration/profiles/labourer_profile.html', context)


# --- LEADER PROFILE VIEW ---
@login_required
def leader_profile_view(request, user_id):
    leader = get_object_or_404(User, id=user_id)
    
    # Get jobs managed by this leader
    jobs_managed = Job.objects.filter(finalized_leader=leader).order_by('-created_at')
    
    # Calculate stats
    stats = {
        'total_jobs': jobs_managed.count(),
        'completed_jobs': jobs_managed.filter(status='completed').count(),
        'ongoing_jobs': jobs_managed.filter(status='ongoing').count(),
    }
    
    context = {
        'leader': leader,
        'jobs_managed': jobs_managed,
        'stats': stats,
    }
    return render(request, 'registration/profiles/leader_profile.html', context)


# registration/views.py
from django.contrib.auth.models import Group

# ... (keep all your other views) ...

@login_required # Make sure only logged-in admins can see this
def profile_selector_view(request):
    """
    Provides the data for the page where an admin can select
    a role and a person to view their profile.
    """
    labourers = IndividualLabor.objects.all().order_by('full_name')
    mukadams = Mukkadam.objects.all().order_by('full_name')
    
    # Assuming your Leaders are users in a "Leaders" group
    try:
        leader_group = Group.objects.get(name='Leaders')
        leaders = leader_group.user_set.all().order_by('username')
    except Group.DoesNotExist:
        leaders = User.objects.none() # Return an empty list if group doesn't exist

    context = {
        'labourers': labourers,
        'mukadams': mukadams,
        'leaders': leaders,
    }
    return render(request, 'registration/profiles/profile_selector.html', context)

# @login_required
# def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'status': 'success'})