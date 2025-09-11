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

# contact_app/views.py

# Make sure all necessary models and libraries are imported at the top of the file

@csrf_exempt
def whatsapp_webhook_view(request):
    """Handles all incoming WhatsApp events, prioritizing dynamic flows."""
    # 1. HANDLE WEBHOOK VERIFICATION (for initial setup with Meta)
    # 2. PROCESS INCOMING POST REQUESTS FROM META
    if request.method == 'POST':
        logger.info("====== WEBHOOK URL HAS BEEN HIT ======")
        logger.info("====== Webhook is a POST request. Attempting to read body. ======")
        
        data = json.loads(request.body)
        logger.info(f"====== INCOMING WEBHOOK BODY ======\n{json.dumps(data, indent=2)}")
        try:
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    
                    # 3. HANDLE INCOMING MESSAGES
                    if 'messages' in value:
                        for msg in value.get('messages', []):
                            contact, _ = ChatContact.objects.get_or_create(wa_id=msg['from'])
                            contact.last_contact_at = timezone.now()
                            contact.save()
                            
                            # 3a. Save Incoming Message to DB
                            message_type = msg.get('type')
                            text_content = ""
                            if message_type == 'text':
                                text_content = msg.get('text', {}).get('body')
                            elif message_type == 'interactive':
                                # This handles both button and list replies
                                text_content = msg.get('interactive', {}).get('button_reply', {}).get('title') or \
                                               msg.get('interactive', {}).get('list_reply', {}).get('title')
                            
                            Message.objects.create(
                                contact=contact,
                                wamid=msg.get('id'),
                                direction='inbound',
                                message_type=message_type,
                                text_content=text_content,
                                timestamp=timezone.datetime.fromtimestamp(int(msg.get('timestamp')))
                            )

                            # 3b. Process User Input and Trigger Flows
                            replied_to_wamid = msg.get('context', {}).get('id')
                            user_input = text_content # We use the text_content we just extracted

                            logger.info(f"DEBUG-FLOW: Extracted user_input='{user_input}' and replied_to_wamid='{replied_to_wamid}'")

                            if user_input and replied_to_wamid:
                                # This function now contains the smart session logic
                                flow_handled = try_execute_flow_step(contact, user_input, replied_to_wamid)
                                if flow_handled:
                                    logger.info("DEBUG-FLOW: Flow was successfully handled. Skipping fallback logic.")
                                    continue
                    
                    # 4. HANDLE MESSAGE STATUS UPDATES
                    elif 'statuses' in value:
                        for status_update in value.get('statuses', []):
                            wamid_to_update = status_update.get('id')
                            new_status = status_update.get('status')
                            
                            # Find the outgoing message and update its status
                            Message.objects.filter(wamid=wamid_to_update, direction='outbound').update(
                                delivery_status=new_status,
                                updated_at=timezone.now()
                            )
                            logger.info(f"Updated status for wamid {wamid_to_update} to '{new_status}'")

        except Exception as e:
            logger.error(f"Error in webhook: {e}", exc_info=True)
            
    return JsonResponse({"status": "success"}, status=200)


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


def try_execute_flow_step(contact, user_input, replied_to_wamid):
    """
    Finds and executes the next step in a flow using a session-based approach.
    """
    try :
        flow = None
        current_node = None

        # 1. CHECK FOR AN ACTIVE SESSION
        session = UserFlowSession.objects.filter(contact=contact).first()

        if session:
            # User is already in a flow.
            flow = session.flow
            flow_data = flow.flow_data
            nodes = flow_data.get('nodes', [])
            current_node = next((n for n in nodes if n.get('id') == session.current_node_id), None)
            logger.info(f"Found active session for contact {contact.wa_id} in flow '{flow.name}' at node '{session.current_node_id}'")

        else:
            # NO SESSION: This must be the start of a new flow.
            try:
                original_message = Message.objects.get(wamid=replied_to_wamid, direction='outbound', message_type='template')
                template_name = original_message.text_content.replace("Sent template: ", "").strip()
                
                possible_flows = Flow.objects.filter(is_active=True, template_name=template_name).order_by('-updated_at')
                if not possible_flows.exists():
                    logger.warning(f"No active flow found with trigger template: {template_name}")
                    return False
                
                flow = possible_flows.first()
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
            if session: session.delete()
            return False

        edges = flow.flow_data.get('edges', [])
        next_edge = next((e for e in edges if e.get('source') == current_node.get('id') and e.get('sourceHandle') == user_input), None)
        
        if not next_edge:
            logger.warning(f"No outgoing edge found from node '{current_node.get('id')}' for input '{user_input}'")
            return False

        nodes = flow.flow_data.get('nodes', [])
        target_node_id = next_edge.get('target')
        target_node = next((n for n in nodes if n.get('id') == target_node_id), None)
        
        if not target_node:
            logger.error(f"Edge points to a non-existent target node ID: '{target_node_id}'")
            return False

        # 3. CONSTRUCT AND SEND THE MESSAGE (This part is unchanged)
        node_type = target_node.get('type')
        node_data = target_node.get('data', {})
        payload = {"messaging_product": "whatsapp", "to": contact.wa_id}
        message_type_to_save = 'unknown'
        text_content_to_save = f"Flow Step: {node_type}"

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
                "template": {"name": target_template_name, "language": { "code": "en" }, "components": components }
            })
            message_type_to_save = 'template'
            text_content_to_save = f"Sent template: {target_template_name}"
            
        elif node_type == 'imageNode':
            meta_media_id = node_data.get('metaMediaId') # We will now store the Meta Media ID
            caption = node_data.get('caption')
            if not meta_media_id:
                logger.error(f"Flow Error: Image node for contact {contact.wa_id} has no URL.")
                return False
            payload.update({"type": "image", "image": {"id": meta_media_id, "caption": caption}})
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
            
            current_node_type = current_node.get('type')
            target_has_outputs = any(e for e in edges if e.get('source') == target_node_id)
        
            if current_node_type == 'buttonsNode':
                logger.info(f"User selected from a buttonsNode menu. Session remains at node {current_node.get('id')}.")
                # We don't update or delete the session. We leave it as is.
            
            # If the next node also has outputs, we advance the session state
            elif target_has_outputs:
                UserFlowSession.objects.update_or_create(
                    contact=contact,
                    defaults={'flow': flow, 'current_node_id': target_node_id}
                )
                logger.info(f"Session for {contact.wa_id} updated to node '{target_node_id}'")

            # Otherwise, this is the end of a branch, so we delete the session.
            else:
                if session:
                    session.delete()
                logger.info(f"Flow branch ended for {contact.wa_id}. Session deleted.")
            
            return True
        else:
            logger.error(f"Flow step failed for contact {contact.wa_id}. API Response: {response_data}")
            return False

    except Exception as e:
            logger.error(f"CRITICAL FLOW ERROR: {e}", exc_info=True)
            return False




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



def get_flows_list_api(request):
    """API endpoint to get a list of all saved flows."""
    flows = Flow.objects.all().order_by('-updated_at')
    data = [{'id': f.id, 'name': f.name, 'template_name': f.template_name, 'updated_at': f.updated_at} for f in flows]
    return JsonResponse(data, safe=False)



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
