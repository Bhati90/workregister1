from django.shortcuts import render
#import re
import json
import logging

import requests
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
import os
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import ChatContact,Message
# from registration.whats_app import send_whatsapp_message, save_outgoing_message
import re
import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from flow.models import WhatsAppFlowForm
from .models import WhatsAppForm  # <-- Add this import for WhatsAppForm
# Assuming other necessary imports like requests, settings, models are present

from django.utils import timezone



META_ACCESS_TOKEN="EAAhMBt21QaMBPCyLtJj6gwjDy6Gai4fZApb3MXuZBZCCm0iSEd8ZCZCJdkRt4cOtvhyeFLZCNUwitFaLZA3ZCwv7enN6FBFgDMAOKl7LMx0J2kCjy6Qd6AqnbnhB2bo2tgsdGmn9ZCN5MD6yCgE3shuP62t1spfSB6ZALy1QkNLvIaeWZBcvPH00HHpyW6US4kil2ENZADL4ZCvDLVWV9seSbZCxXYzVCezIenCjhSYtoKTIlJ"
WABA_ID ="1477047197063313"



API_VERSION = 'v19.0'
META_API_URL = f"https://graph.facebook.com/{API_VERSION}"

META_ACCESS_TOKEN ="EAAhMBt21QaMBPCyLtJj6gwjDy6Gai4fZApb3MXuZBZCCm0iSEd8ZCZCJdkRt4cOtvhyeFLZCNUwitFaLZA3ZCwv7enN6FBFgDMAOKl7LMx0J2kCjy6Qd6AqnbnhB2bo2tgsdGmn9ZCN5MD6yCgE3shuP62t1spfSB6ZALy1QkNLvIaeWZBcvPH00HHpyW6US4kil2ENZADL4ZCvDLVWV9seSbZCxXYzVCezIenCjhSYtoKTIlJ"
PHONE_NUMBER_ID = 705449502657013



logger = logging.getLogger(__name__)
from flow.models import WhatsAppFlowForm

logger = logging.getLogger(__name__)

# Create your views here.
def send_whatsapp_message(payload):
    url = f"{META_API_URL}/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}", "Content-Type": "application/json"}
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return True, response.json()
    except requests.exceptions.RequestException as e:
        error_details = "No response from server."
        if e.response is not None:
            try:
                error_details = e.response.json() # Try to get the detailed JSON error
            except json.JSONDecodeError:
                error_details = e.response.text # Fallback to raw text if not JSON
        
        # This new log will show the specific reason for the failure
        logger.error(f"Error from Meta API. Status: {e.response.status_code if e.response else 'N/A'}. Details: {error_details}")
        
        return False, error_details
    

def save_outgoing_message(contact, wamid, message_type, text_content="", caption="", raw_data={}, replied_to_wamid=None, media_file=None, source_node_id=None):
    
    """
    Saves an outgoing message to the database, now including the source_node_id from a flow.
    """
    defaults = {
        'contact': contact,
        'direction': 'outbound',
        'message_type': message_type,
        'text_content': text_content,
        'caption': caption,
        'timestamp': timezone.now(),
        'raw_data': raw_data,
        'status': 'sent',
        'source_node_id': source_node_id  # <-- ADDED THIS LINE
    }
    
    if replied_to_wamid:
        try:
            defaults['replied_to'] = Message.objects.get(wamid=replied_to_wamid)
        except Message.DoesNotExist:
            pass
    
    message, created = Message.objects.update_or_create(wamid=wamid, defaults=defaults)

    if media_file and not message.media_file:
        # We use the wamid to create a unique file name
        file_name = f"outbound/{contact.wa_id}/{wamid}_{media_file.name}"
        message.media_file.save(file_name, media_file, save=True)

    contact.last_contact_at = timezone.now()
    contact.save()
    """
    # Sends a WhatsApp template message using the Meta Graph API.
    # """ 

def map_component_to_flow_json(component):
    """
    Converts a single component from the builder's format to Meta's format,
    ensuring all input components have a 'name'.
    """
    comp_type = component.get('type')
    label = component.get('label')
    # The 'name' of the component will be its unique ID (e.g., "component_3")
    name = component.get('id')
    properties = component.get('properties', {})

    if comp_type in ['text-input', 'textarea', 'date-picker', 'dropdown', 'radio-group', 'checkbox-group']:
        # This block handles all components that collect user input
        
        # Map your builder type to Meta's type
        meta_type_map = {
            'text-input': 'TextInput',
            'textarea': 'TextArea',
            'date-picker': 'DatePicker',
            'dropdown': 'Dropdown',
            'radio-group': 'RadioButtonsGroup',
            'checkbox-group': 'CheckboxGroup'
        }
        
        component_json = {
            "type": meta_type_map[comp_type],
            "label": label,
            "name": name, # <-- THIS IS THE REQUIRED PROPERTY
            "required": properties.get('required', True)
        }
        
        # Add data-source for dropdowns/radios/checkboxes
        if comp_type in ['dropdown', 'radio-group', 'checkbox-group']:
            options = properties.get('options', [])
            component_json["data-source"] = [{"id": re.sub(r'\W+', '_', opt.lower()), "title": opt} for opt in options]
            
        # Add hint for text inputs
        if comp_type in ['text-input', 'textarea']:
             component_json["hint"] = properties.get('placeholder', '')
             
        return component_json
        
    # Display components do not need a 'name'
    elif comp_type == 'heading':
        return {"type": "TextHeading", "text": label}
        
    elif comp_type == 'text':
        return {"type": "TextBody", "text": properties.get('content', '')}
        
    return None


def generate_multi_screen_flow_json(screens_data):
    """
    Converts the multi-screen structure from the builder into a valid Flow JSON.
    """
    flow_screens = []
    
    # Pre-process screen data to sanitize IDs
    sanitized_screens = []
    for i, screen in enumerate(screens_data):
        original_id = screen.get('id', f'SCREEN_{i}')
        # Replace any non-alphabetic or non-underscore characters with an underscore
        sanitized_id = re.sub(r'[^a-zA-Z_]', '_', original_id.upper())
        screen['sanitized_id'] = sanitized_id
        sanitized_screens.append(screen)

    num_screens = len(sanitized_screens)
    for i, screen in enumerate(sanitized_screens):
        is_last_screen = (i == num_screens - 1)
        
        children = []
        for component in screen.get('components', []):
            mapped_component = map_component_to_flow_json(component)
            if mapped_component:
                # Handle case where component returns multiple elements (like text-input with instructions)
                if isinstance(mapped_component, list):
                    children.extend(mapped_component)
                else:
                    children.append(mapped_component)
        
        if is_last_screen:
            # For the last screen, use complete action
            footer_action = {
                "name": "complete", 
                "payload": {}
            }
            footer_label = "Submit"
        else:
            # For navigation, ensure we have the 'next' property
            next_screen_id = sanitized_screens[i + 1]['sanitized_id']
            footer_action = {
                "name": "navigate",
                "next": {
                    "type": "screen",
                    "name": next_screen_id
                },
                "payload": {}
            }
            footer_label = "Next"

        children.append({
            "type": "Footer",
            "label": footer_label,
            "on-click-action": footer_action
        })
        
        flow_screen = {
            "id": screen['sanitized_id'],
            "title": screen.get('title', f'Screen {i+1}'),
            "terminal": is_last_screen,
            "layout": {
                "type": "SingleColumnLayout",
                "children": children
            }
        }
        flow_screens.append(flow_screen)

    return {
        "version": "5.1",
        "screens": flow_screens
    }
@require_http_methods(["POST"])
def submit_form_and_template_view(request):
    """
    Handles the 2-step process for creating and submitting a multi-screen WhatsApp Flow and its trigger template to Meta.
    """
    try:
        # --- Step 1: Load and Validate Data from the Frontend ---
        data = json.loads(request.body)
        form_name = data.get('form_name')
        screens_data = data.get('screens_data')

        if not form_name or not screens_data:
            return JsonResponse({'status': 'error', 'message': 'Form name and screen data are required.'}, status=400)

        # --- Step 2: Generate the Multi-Screen Flow JSON ---
        # This function should be defined as in the previous answer
        flow_json_data = generate_multi_screen_flow_json(screens_data)
        flow_json_string = json.dumps(flow_json_data)
        
        logger.info(f"Submitting Flow '{form_name}' to Meta...")
        
        if not META_ACCESS_TOKEN or not WABA_ID or "YOUR_" in WABA_ID:
            raise ValueError("Meta API credentials (WABA_ID, META_ACCESS_TOKEN) are not configured on the server.")

        # --- Step 3: Create the Flow via Meta API (First API Call) ---
        flow_api_url = f"https://graph.facebook.com/v19.0/{WABA_ID}/flows"
        headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}", "Content-Type": "application/json"}
        
        flow_payload = {
            "name": f"{form_name}_flow",
            "flow_json": flow_json_string,
            "categories": ["LEAD_GENERATION"] # e.g., CUSTOMER_SUPPORT, MARKETING, LEAD_GENERATION
        }
        
        flow_response = requests.post(flow_api_url, headers=headers, json=flow_payload)
        flow_response_data = flow_response.json()

        if flow_response.status_code >= 400:
            logger.error(f"Meta API Error (Flow Creation): {flow_response_data}")
            return JsonResponse({
                'status': 'error', 
                'message': 'Failed to create Flow.', 
                'meta_response': flow_response_data
            }, status=flow_response.status_code)
        
        flow_id = flow_response_data.get("id")
        logger.info(f"Successfully created Flow with ID: {flow_id}")

        # --- Step 4: Publish the Flow ---
        publish_url = f"https://graph.facebook.com/v19.0/{flow_id}/publish"
        publish_response = requests.post(publish_url, headers=headers, json={})
        publish_response_data = publish_response.json()
        
        flow_published = publish_response.status_code < 400
        if flow_published:
            logger.info(f"Successfully published Flow with ID: {flow_id}")
        else:
            logger.warning(f"Meta API Warning (Flow Publishing failed): {publish_response_data}")
            logger.info("Continuing to create template with unpublished flow (might be rejected).")

        # --- Step 5: Create the Message Template to trigger the Flow (Second API Call) ---
        template_name = f"{form_name}_flow_trigger"
        template_api_url = f"https://graph.facebook.com/v19.0/{WABA_ID}/message_templates"
        
        template_payload = {
            "name": template_name,
            "language": "en_US",
            "category": data.get('template_category', 'UTILITY'),
            "components": [
                {"type": "BODY", "text": data.get('template_body', 'Tap below to start.')},
                {
                    "type": "BUTTONS",
                    "buttons": [{
                        "type": "FLOW",
                        "text": data.get('template_button_text', 'Start Form'),
                        "flow_id": flow_id,
                    }]
                }
            ]
        }
        
        logger.info(f"Submitting Template to Meta with payload:\n{json.dumps(template_payload, indent=2)}")
        template_response = requests.post(template_api_url, headers=headers, json=template_payload)
        template_response_data = template_response.json()

        if template_response.status_code >= 400:
            logger.error(f"Meta API Error (Template Creation): {template_response_data}")
            
            # Provide a more helpful response if the template fails because the flow isn't published
            if not flow_published:
                return JsonResponse({
                    'status': 'partial_success',
                    'message': 'Flow created but not published. Template creation failed as expected.',
                    'flow_response': flow_response_data,
                    'publish_response': publish_response_data,
                    'template_response': template_response_data,
                    'note': 'You can test with the flow_id, but templates require published flows.'
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Flow was published, but failed to submit the trigger template.',
                    'flow_response': flow_response_data,
                    'template_response': template_response_data
                }, status=template_response.status_code)
        template_name_generated = f"{form_name}_flow_trigger"

    # --- NEW: Save everything to your database ---
        try:
            form_instance, created = WhatsAppFlowForm.objects.update_or_create(
                name=form_name,
                defaults={
                    'meta_flow_id': flow_id,
                    'screens_data': {'screens_data': screens_data}, # Save the original builder structure
                    'template_category': data.get('template_category', 'UTILITY'),
                    'template_body': data.get('template_body'),
                    'template_button_text': data.get('template_button_text'),
                    'flow_status': 'PUBLISHED', # You can update this later after publishing
                    'template_name': template_name_generated,
                }
            )
            logger.info(f"Successfully saved/updated form '{form_name}' in the database.")
        except Exception as e:
            logger.error(f"Database Error: Failed to save form '{form_name}'. Reason: {e}")
    # --- END OF NEW CODE ---
        logger.info(f"Successfully submitted template '{template_name}' to Meta.")
        return JsonResponse({
            'status': 'success',
            'message': 'Flow and trigger template submitted to Meta successfully!',
            'flow_response': flow_response_data,
            'template_response': template_response_data,
            'flow_published': flow_published
        })

    except ValueError as ve:
        logger.error(f"Configuration error: {ve}")
        return JsonResponse({'status': 'error', 'message': str(ve)}, status=500)
    except Exception as e:
        logger.error(f"An unexpected error occurred in submit_form_and_template_view: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': f'An unexpected server error occurred: {e}'}, status=500)
@csrf_exempt  
@login_required
def send_interactive_flow_message(request):
    """Alternative: Send Flow as an interactive message (if template doesn't work)"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)
    
    try:
        recipients = request.POST.getlist('recipients[]')
        flow_id = request.POST.get('flow_id')
        flow_text = request.POST.get('flow_text', 'Please fill out this form')
        button_text = request.POST.get('button_text', 'Start Form')
        
        if not recipients or not flow_id:
            return JsonResponse({'status': 'error', 'message': 'Recipients and Flow ID are required.'}, status=400)

        results = []
        for wa_id in recipients:
            contact = get_object_or_404(ChatContact, wa_id=wa_id)
            
            # Interactive Flow message structure
            payload = {
                "messaging_product": "whatsapp",
                "to": wa_id,
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "header": {
                        "type": "text",
                        "text": "Form Request"
                    },
                    "body": {
                        "text": flow_text
                    },
                    "footer": {
                        "text": "Tap the button below to start"
                    },
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "5.1",
                            "flow_id": flow_id,
                            "flow_cta": button_text,
                            "flow_action": "navigate",
                            "flow_action_payload": {
                                "screen": "FORM_SCREEN"
                            }
                        }
                    }
                }
            }
            
            logger.info(f"Sending interactive Flow message: {json.dumps(payload, indent=2)}")
            
            success, response_data = send_whatsapp_message(payload)
            if success:
                save_outgoing_message(
                    contact=contact, 
                    wamid=response_data['messages'][0]['id'], 
                    message_type='interactive_flow', 
                    text_content=f"Sent interactive flow: {flow_id}"
                )
                results.append({"wa_id": wa_id, "status": "success"})
            else:
                logger.error(f"Failed to send interactive flow to {wa_id}: {response_data}")
                results.append({"wa_id": wa_id, "status": "error", "response": response_data})
                
        return JsonResponse({"results": results})
        
    except Exception as e:
        logger.error(f"Error in send_interactive_flow_message: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    

@csrf_exempt # Use this for simplicity, or implement proper CSRF handling in JS fetch
@require_http_methods(["GET", "POST"])
def whatsapp_form_builder_view(request):
    """
    Handles the creation and editing of WhatsApp forms.
    GET: Renders the form builder page.
    POST: Saves the form structure as JSON.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            form_name = data.get('name')
            form_structure = data.get('structure')

            if not form_name or not form_structure:
                return JsonResponse({'status': 'error', 'message': 'Form name and structure are required.'}, status=400)

            # Use update_or_create to save the form
            form_obj, created = WhatsAppForm.objects.update_or_create(
                name=form_name,
                defaults={'structure': form_structure}
            )
            
            message = f"Form '{form_name}' was created successfully." if created else f"Form '{form_name}' was updated."
            logger.info(message)
            return JsonResponse({'status': 'success', 'message': message, 'form_id': form_obj.id})

        except json.JSONDecodeError:
            logger.error("Failed to decode JSON from form builder request.")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON format.'}, status=400)
        except Exception as e:
            logger.error(f"Error saving WhatsApp form: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # For a GET request, just render the builder page.
    return render(request, 'registration/chat/whatsapp_form.html')


@csrf_exempt
@login_required
def send_flow_template_api_view(request):
    """Send WhatsApp Flow templates (forms) to recipients"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)
    
    try:
        recipients = request.POST.getlist('recipients[]')
        if not recipients:
            return JsonResponse({'status': 'error', 'message': 'No recipients selected.'}, status=400)
        
        template_name = request.POST.get('template_name')
        if not template_name:
            return JsonResponse({'status': 'error', 'message': 'Template name is required.'}, status=400)
        
        results = []
        for wa_id in recipients:
            contact = get_object_or_404(ChatContact, wa_id=wa_id)
            
            # --- THIS IS THE FIX ---
            # For Flow templates, Meta requires an explicit components structure,
            # even if there are no dynamic variables to fill.
            payload = {
                "messaging_product": "whatsapp",
                "to": wa_id,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "en_US"},
                    "components": [
                        # We must include a component object for the button.
                        # Since the template defines the button at index 0, we specify that.
                        {
                            "type": "button",
                            "sub_type": "flow",
                            "index": "0",
                            "parameters": [] # No parameters are needed as the flow_id is in the template.
                        }
                    ]
                }
            }
            
            logger.info(f"Sending Flow template payload: {json.dumps(payload, indent=2)}")
            
            success, response_data = send_whatsapp_message(payload)
            if success:
                save_outgoing_message(
                    contact=contact, 
                    wamid=response_data['messages'][0]['id'], 
                    message_type='flow_template', 
                    text_content=f"Sent flow template: {template_name}"
                )
                results.append({"wa_id": wa_id, "status": "success"})
            else:
                logger.error(f"Failed to send flow template to {wa_id}: {response_data}")
                results.append({"wa_id": wa_id, "status": "error", "response": response_data})
                
        return JsonResponse({"results": results})
        
    except Exception as e:
        logger.error(f"Error in send_flow_template_api_view: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@login_required
def get_flow_templates(request):
    """Get list of available flow templates for the frontend"""
    try:
        headers = {
            "Authorization": f"Bearer {META_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Get message templates
        # Ensure WABA_ID is defined, likely same as WHATSAPP_BUSINESS_ACCOUNT_ID
        # WABA_ID = os.environ.get("WHATSAPP_BUSINESS_ACCOUNT_ID")
        templates_url = f"https://graph.facebook.com/v19.0/{WABA_ID}/message_templates?fields=name,status,category,language,components"
        response = requests.get(templates_url, headers=headers)
        
        if response.status_code == 200:
            templates_data = response.json()
            
            # Filter for flow templates (templates with FLOW buttons)
            flow_templates = []
            for template in templates_data.get('data', []):
                components = template.get('components', [])
                for component in components:
                    # The component type from Meta is uppercase 'BUTTONS'
                    if component.get('type') == 'BUTTONS':
                        buttons = component.get('buttons', [])
                        for button in buttons:
                            if button.get('type') == 'FLOW':
                                flow_templates.append({
                                    'name': template.get('name'),
                                    'status': template.get('status'),
                                    'flow_id': button.get('flow_id'),
                                    'button_text': button.get('text'),
                                    # Pass components to the frontend for better preview
                                    'components': template.get('components')
                                })
                                break # Found the FLOW button, move to next template
            
            return JsonResponse({
                'status': 'success',
                'flow_templates': flow_templates
            })
        else:
            return JsonResponse({
                'status': 'error', 
                'message': 'Failed to fetch templates',
                'response': response.json()
            }, status=response.status_code)
            
    except Exception as e:
        logger.error(f"Error getting flow templates: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def send_flow_view(request):
    """
    Renders the page for sending a Flow template.
    It fetches all contacts to populate the recipient dropdown.
    """
    contacts = ChatContact.objects.all().order_by('name')
    context = {
        'contacts': contacts
    }
    return render(request, 'registration/chat/send_flow.html', context)
