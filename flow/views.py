# contact_app/views.py

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt # Import csrf_exempt
# from corsheaders.decorators import cors_exempt       # Import cors_exempt
import json

from django.shortcuts import render # Make sure render is imported

def home_page(request):
    return render(request, 'contact_app/home.html', {'message': 'Welcome to my Contact App!'})

# from .models import Flow, Message, ChatContact # Make sure these are imported
from registration.models import ChatContact, Message
from .models import Flows as Flow
from .models import UserFlowSessions as UserFlowSession
from registration.whats_app import send_whatsapp_message, save_outgoing_message, upload_media_for_template_handle
from django.utils import timezone
import os
import mimetypes
import logging
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.http import HttpResponse
logger = logging.getLogger(__name__)

import requests
API_VERSION = 'v19.0'
META_API_URL = f"https://graph.facebook.com/{API_VERSION}"

PHONE_NUMBER_ID = 705449502657013


META_ACCESS_TOKEN="EAAhMBt21QaMBPCyLtJj6gwjDy6Gai4fZApb3MXuZBZCCm0iSEd8ZCZCJdkRt4cOtvhyeFLZCNUwitFaLZA3ZCwv7enN6FBFgDMAOKl7LMx0J2kCjy6Qd6AqnbnhB2bo2tgsdGmn9ZCN5MD6yCgE3shuP62t1spfSB6ZALy1QkNLvIaeWZBcvPH00HHpyW6US4kil2ENZADL4ZCvDLVWV9seSbZCxXYzVCezIenCjhSYtoKTIlJ"
        
WABA_ID = "1477047197063313"

@csrf_exempt
def whatsapp_webhook_view(request):
    """Handles all incoming WhatsApp events, prioritizing dynamic flows."""
    # ** NEW LOG 1: Check if the view is being hit at all **
    logger.info("====== WEBHOOK URL HAS BEEN HIT ======")
    
    if request.method == 'POST':
        # ** NEW LOG 2: Check if the request body is being read **
        logger.info("====== Webhook is a POST request. Attempting to read body. ======")
        
        data = json.loads(request.body)
        logger.info(f"====== INCOMING WEBHOOK BODY ======\n{json.dumps(data, indent=2)}")
        try:
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    if 'messages' in value:
                        for msg in value.get('messages', []):
                            # ... (Your message saving logic remains the same) ...
                            contact, _ = ChatContact.objects.get_or_create(wa_id=msg['from'])
                            contact.last_contact_at = timezone.now()
                            contact.save()
                            message_type = msg.get('type')
                            # ... (The rest of your code to save the incoming message instance) ...
                            
                            # --- START: FLOW ENGINE TRIGGER ---
                            replied_to_wamid = msg.get('context', {}).get('id')
                            user_input = None

                            if message_type == 'button':
                                user_input = msg.get('button', {}).get('text')
                            elif message_type == 'interactive' and msg.get('interactive', {}).get('type') == 'button_reply':
                                user_input = msg.get('interactive', {}).get('button_reply', {}).get('title')
                            
                            logger.info(f"DEBUG-FLOW: Extracted user_input='{user_input}' and replied_to_wamid='{replied_to_wamid}'")

                            if user_input and replied_to_wamid:
                                flow_handled = try_execute_flow_step(contact, user_input, replied_to_wamid)
                                if flow_handled:
                                    logger.info("DEBUG-FLOW: Flow was successfully handled. Skipping fallback logic.")
                                    continue # Go to the next message

                            # --- FALLBACK LOGIC ---
                            # ... (Your existing hardcoded command logic goes here) ...
                            # ... (It will run only if flow_handled is False) ...
                            
                    elif 'statuses' in value:
                        # ... (Your status update logic) ...
                        pass
        except Exception as e:
            logger.error(f"Error in webhook: {e}", exc_info=True)
        return JsonResponse({"status": "success"}, status=200)


# contact_app/views.py

# ... (keep all your other imports: JsonResponse, csrf_exempt, models, etc.)
import logging
logger = logging.getLogger(__name__)

# ... (keep your whatsapp_webhook_view and other views)

def try_execute_flow_step(contact, user_input, replied_to_wamid):
    """
    Finds and executes the next step in a flow using a session-based approach.
    This version only triggers flows marked as active.
    """
    try:
        flow = None
        current_node = None

        # 1. CHECK FOR AN ACTIVE SESSION
        session = UserFlowSession.objects.filter(contact=contact).first()

        if session:
            # User is already in a flow.
            flow = session.flow
            if not flow.is_active:
                logger.warning(f"Contact {contact.wa_id} is in a session for an INACTIVE flow '{flow.name}'. Deleting session.")
                session.delete()
                return False # Stop execution

            flow_data = flow.flow_data
            nodes = flow_data.get('nodes', [])
            current_node = next((n for n in nodes if n.get('id') == session.current_node_id), None)
            logger.info(f"Found active session for contact {contact.wa_id} in flow '{flow.name}' at node '{session.current_node_id}'")

        else:
            # NO SESSION: This must be the start of a new flow.
            try:
                original_message = Message.objects.get(wamid=replied_to_wamid, direction='outbound', message_type='template')
                template_name = original_message.text_content.replace("Sent template: ", "").strip()
                
                # --- MODIFIED LOGIC ---
                # Find the most recently updated ACTIVE flow for this trigger template
                possible_flows = Flow.objects.filter(template_name=template_name, is_active=True).order_by('-updated_at')
                
                if not possible_flows.exists():
                    logger.warning(f"No ACTIVE flow found with trigger template: {template_name}")
                    return False
                
                flow = possible_flows.first()
                # --- END MODIFIED LOGIC ---
                
                flow_data = flow.flow_data
                nodes = flow_data.get('nodes', [])
                current_node = next((n for n in nodes if n.get('type') == 'templateNode' and n.get('data', {}).get('selectedTemplateName') == template_name), None)
                
                logger.info(f"Starting new session for contact {contact.wa_id} with flow '{flow.name}'")

            except Message.DoesNotExist:
                logger.warning(f"No active session and original message for wamid {replied_to_wamid} is not a trigger template.")
                return False

        # 2. FIND THE NEXT STEP
        if not flow or not current_node:
            logger.error(f"Could not determine a flow or current node for contact {contact.wa_id}")
            if session: session.delete() # Clean up broken session
            return False

        edges = flow.flow_data.get('edges', [])
        next_edge = next((e for e in edges if e.get('source') == current_node.get('id') and e.get('sourceHandle') == user_input), None)
        
        if not next_edge:
            # --- HELPFUL DEBUG LOG ---
            logger.warning(f"No outgoing edge found from node '{current_node.get('id')}' for input '{user_input}'. Checking available handles:")
            for edge in edges:
                if edge.get('source') == current_node.get('id'):
                    logger.info(f"  - Available sourceHandle: '{edge.get('sourceHandle')}'")
            # --- END DEBUG LOG ---
            return False

        nodes = flow.flow_data.get('nodes', [])
        target_node_id = next_edge.get('target')
        target_node = next((n for n in nodes if n.get('id') == target_node_id), None)
        
        if not target_node:
            logger.error(f"Edge points to a non-existent target node ID: '{target_node_id}'")
            return False

        # 3. CONSTRUCT AND SEND THE MESSAGE (This part remains the same)
        node_type = target_node.get('type')
        node_data = target_node.get('data', {})
        payload = {"messaging_product": "whatsapp", "to": contact.wa_id}
        message_type_to_save = 'unknown'
        text_content_to_save = f"Flow Step: {node_type}"
        # ... (All your elif blocks for textNode, templateNode, imageNode, buttonsNode are correct and go here) ...
        if node_type == 'textNode':
            message_text = node_data.get('text', '...')
            payload.update({"type": "text", "text": {"body": message_text}})
            message_type_to_save = 'text'
            text_content_to_save = message_text
        
        elif node_type == 'templateNode':
            target_template_name = node_data.get('selectedTemplateName')
            if not target_template_name:
                logger.error("Flow Error: Target node is a template but no template name is selected.")
                return False
            components = []
            if 'headerUrl' in node_data and node_data['headerUrl']:
                components.append({
                    "type": "header", "parameters": [{"type": "image", "image": { "link": node_data['headerUrl'] }}]
                })
            body_params = []
            for i in range(1, 10):
                var_key = f'bodyVar{i}'
                if var_key in node_data and node_data[var_key]:
                    body_params.append({ "type": "text", "text": node_data[var_key] })
                else:
                    break
            if body_params:
                components.append({ "type": "body", "parameters": body_params })
            payload.update({
                "type": "template",
                "template": {"name": target_template_name, "language": { "code": "en_US" }, "components": components }
            })
            message_type_to_save = 'template'
            text_content_to_save = f"Sent template: {target_template_name}"
            
        elif node_type == 'imageNode':
            image_url = node_data.get('imageUrl')
            caption = node_data.get('caption')
            if not image_url:
                logger.error(f"Flow Error: Image node for contact {contact.wa_id} has no URL.")
                return False
            payload.update({"type": "image", "image": {"link": image_url, "caption": caption}})
            message_type_to_save = 'image'
            text_content_to_save = caption or "Sent an image"
            
        elif node_type == 'buttonsNode':
            body_text = node_data.get('text')
            buttons = node_data.get('buttons', [])
            if not body_text or not buttons:
                logger.error(f"Flow Error: Buttons node for contact {contact.wa_id} is missing text or buttons.")
                return False
            action = {"buttons": []}
            for btn in buttons:
                action["buttons"].append({"type": "reply", "reply": {"id": btn.get('text'), "title": btn.get('text')}})
            payload.update({
                "type": "interactive",
                "interactive": {"type": "button", "body": { "text": body_text }, "action": action}
            })
            message_type_to_save = 'interactive'
            text_content_to_save = body_text
        else:
            return False
            
        # 4. SEND MESSAGE AND MANAGE SESSION
        success, response_data = send_whatsapp_message(payload)
        
        if success:
            save_outgoing_message(contact=contact, wamid=response_data['messages'][0]['id'], message_type=message_type_to_save, text_content=text_content_to_save)
            
            # --- MODIFIED LOGIC WITH DEBUG LOGS ---
            target_has_outputs = any(e for e in edges if e.get('source') == target_node_id)
            logger.info(f"DEBUG-SESSION: Checking for outputs from target_node_id: '{target_node_id}'. Has outputs: {target_has_outputs}")

            if target_has_outputs:
                UserFlowSession.objects.update_or_create(
                    contact=contact,
                    defaults={'flow': flow, 'current_node_id': target_node_id}
                )
                logger.info(f"Session for {contact.wa_id} updated to node '{target_node_id}'")
            else:
                if session:
                    session.delete()
                logger.info(f"Flow ended for {contact.wa_id} because node has no outputs. Session deleted.")
            # --- END MODIFIED LOGIC ---
            
            return True
        else:
            logger.error(f"Flow step failed for contact {contact.wa_id}. API Response: {response_data}")
            return False

    except Exception as e:
        logger.error(f"CRITICAL FLOW ERROR: {e}", exc_info=True)
        return False

#             message_type_to_save = 'interactive'
#             text_content_to_save = body_text
    
#         # --- END OF NEW LOGIC ---
#         else:
#             return False
            
#         success, response_data = send_whatsapp_message(payload)
        
#         if success:
#             save_outgoing_message(contact=contact, wamid=response_data['messages'][0]['id'], message_type=message_type_to_save, text_content=text_content_to_save)
#             logger.info(f"Flow step executed successfully for contact {contact.wa_id}")
#             return True
#         else:
#             logger.error(f"Flow step failed for contact {contact.wa_id}. API Response: {response_data}")
#             return False

#     except (Message.DoesNotExist, Flow.DoesNotExist):
#         logger.warning(f"Could not find original message or flow for wamid {replied_to_wamid}")
#         return False
#     except Exception as e:
#         logger.error(f"CRITICAL FLOW ERROR: {e}", exc_info=True)
#         return False
# contact_app/views.py

# ... (keep all your other imports and views)
# contact_app/views.py

# ... (keep all your other imports and views)

def get_whatsapp_templates_api(request):
    """API endpoint to fetch approved WhatsApp templates for the React frontend."""
    try:
        url = f"https://graph.facebook.com/v19.0/{WABA_ID}/message_templates?fields=name,components,status"
        headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        all_templates = response.json().get('data', [])
        
        templates_data = []
        for t in all_templates:
            if t.get('status') == 'APPROVED':
                buttons = []
                template_components = t.get('components', [])

                # --- THIS IS THE CORRECTED LOGIC ---
                for comp in template_components:
                    # First, find the component with type 'BUTTONS'
                    if comp.get('type') == 'BUTTONS':
                        # Then, loop through the 'buttons' array inside it
                        for btn in comp.get('buttons', []):
                            # Check the type of the INDIVIDUAL button
                            if btn.get('type') == 'QUICK_REPLY':
                                # If it's a quick reply, add it to our list
                                buttons.append({'text': btn.get('text')})

                templates_data.append({
                    'name': t.get('name'),
                    'components': template_components,
                    'buttons': buttons
                })
        
        return JsonResponse(templates_data, safe=False)
    except Exception as e:
        logger.error(f"Failed to fetch templates for API: {e}")
        return JsonResponse({"error": "Could not load templates."}, status=500)

# ... (keep all your other views like save_flow_api etc.)
# ... (keep all your other views like save_flow_api etc.)
# NEW API VIEW 2: To save the flow from React


def get_flows_list_api(request):
    """API endpoint to get a list of all saved flows."""
    flows = Flow.objects.all().order_by('-updated_at')
    data = [{'id': f.id, 'name': f.name, 'template_name': f.template_name, 'updated_at': f.updated_at} for f in flows]
    return JsonResponse(data, safe=False)


# contact_app/views.py

# ...

@csrf_exempt
def save_flow_api(request):
    """API endpoint to save or update a flow definition from the React frontend."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            flow_name = data.get('name')
            # The 'template_name' is still useful for identifying the trigger
            trigger_template_name = data.get('template_name')
            flow_data = data.get('flow')
            
            if not all([flow_name, flow_data]):
                return JsonResponse({'status': 'error', 'message': 'Missing flow name or flow data.'}, status=400)

            # --- CHANGE THIS LOGIC ---
            # Use the flow's name as the unique identifier to update or create
            flow_obj, created = Flow.objects.update_or_create(
                name=flow_name,
                defaults={
                    'template_name': trigger_template_name, # Save the trigger template
                    'flow_data': flow_data
                }
            )
            # --- END OF CHANGE ---
            
            status_message = "Flow created." if created else "Flow updated."
            return JsonResponse({'status': 'success', 'message': status_message})
        except Exception as e:
            logger.error(f"Error saving flow: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

# --- UPDATE THIS VIEW ---
def get_flows_list_api(request):
    """API endpoint to get a list of all saved flows."""
    flows = Flow.objects.all().order_by('-updated_at')
    # Add the new is_active field to the response
    data = [{
        'id': f.id, 
        'name': f.name, 
        'template_name': f.template_name, 
        'updated_at': f.updated_at,
        'is_active': f.is_active # <-- NEW
    } for f in flows]
    return JsonResponse(data, safe=False)

# --- ADD THESE THREE NEW VIEWS ---
def get_flow_detail_api(request, flow_id):
    """API endpoint to get the full data for a single flow for editing."""
    try:
        flow = Flow.objects.get(pk=flow_id)
        # Return all the data the frontend needs to rebuild the canvas
        data = {
            'id': flow.id,
            'name': flow.name,
            'flow_data': flow.flow_data,
            'is_active': flow.is_active,
        }
        return JsonResponse(data)
    except Flow.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Flow not found.'}, status=404)

@csrf_exempt
def update_flow_status_api(request, flow_id):
    """API endpoint to toggle the active status of a flow."""
    if request.method == 'POST':
        try:
            flow = Flow.objects.get(pk=flow_id)
            data = json.loads(request.body)
            flow.is_active = data.get('is_active', flow.is_active)
            flow.save()
            return JsonResponse({'status': 'success', 'message': 'Status updated.'})
        except Flow.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Flow not found.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

@csrf_exempt
def delete_flow_api(request, flow_id):
    """API endpoint to delete a flow."""
    if request.method == 'DELETE':
        try:
            flow = Flow.objects.get(pk=flow_id)
            flow.delete()
            return JsonResponse({'status': 'success', 'message': 'Flow deleted successfully.'})
        except Flow.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Flow not found.'}, status=404)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)


import requests
import mimetypes # Add this import if not already present
from django.core.files.uploadedfile import InMemoryUploadedFile # Add this import

@csrf_exempt
def upload_image_to_meta_api(request):
    """
    API endpoint to upload an image file directly to Meta's WhatsApp Business API
    and return the Meta Media ID.
    """
    if request.method == 'POST':
        if 'image' not in request.FILES:
            return JsonResponse({'status': 'error', 'message': 'No image file provided.'}, status=400)

        image_file: InMemoryUploadedFile = request.FILES['image']
        
        # Determine content type (e.g., image/jpeg, image/png)
        content_type, _ = mimetypes.guess_type(image_file.name)
        if not content_type or not content_type.startswith('image/'):
            return JsonResponse({'status': 'error', 'message': 'Invalid file type. Only images are allowed.'}, status=400)

        upload_url = f"{META_API_URL}/{PHONE_NUMBER_ID}/media"
        headers = {
            "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        }
        files = {
            'file': (image_file.name, image_file.read(), content_type),
            'type': (None, content_type), # Important for Meta API
            'messaging_product': (None, 'whatsapp'),
        }

        try:
            response = requests.post(upload_url, headers=headers, files=files)
            response.raise_for_status() # Raise an exception for HTTP errors
            meta_response = response.json()
            
            media_id = meta_response.get('id')
            if media_id:
                logger.info(f"Image uploaded to Meta, Media ID: {media_id}")
                return JsonResponse({'status': 'success', 'media_id': media_id})
            else:
                logger.error(f"Meta upload response missing media ID: {meta_response}")
                return JsonResponse({'status': 'error', 'message': 'Meta did not return a media ID.'}, status=500)

        except requests.exceptions.RequestException as e:
            logger.error(f"Error uploading image to Meta: {e}. Response: {response.text if 'response' in locals() else 'No response.'}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': f'Failed to upload image to Meta: {e}'}, status=500)
        except Exception as e:
            logger.error(f"Unexpected error in upload_image_to_meta_api: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {e}'}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

