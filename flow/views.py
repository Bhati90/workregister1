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
from registration.whats_app import send_whatsapp_message, save_outgoing_message
from django.utils import timezone

import logging
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.http import HttpResponse
logger = logging.getLogger(__name__)

import requests


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

# ==============================================================================
# UPDATED HELPER FUNCTION: Filled with logging to find the failure point
# ==============================================================================
def try_execute_flow_step(contact, user_input, replied_to_wamid):
    """
    Tries to find and execute a step from a saved flow, with detailed logging.
    """
    logger.info("---------- STARTING FLOW EXECUTION ----------")
    try:
        # 1. Find the original message
        logger.info(f"DEBUG-FLOW: 1. Attempting to find original message with wamid='{replied_to_wamid}'")
        original_message = Message.objects.get(wamid=replied_to_wamid, direction='outbound', message_type='template')
        logger.info(f"DEBUG-FLOW:    SUCCESS! Found original message. Text: '{original_message.text_content}'")
        
        # 2. Extract template name
        if "Sent template: " not in original_message.text_content:
            logger.warning("DEBUG-FLOW:    FAILURE! 'Sent template: ' text not found in original message. Cannot determine template name.")
            return False
        template_name = original_message.text_content.replace("Sent template: ", "").strip()
        logger.info(f"DEBUG-FLOW: 2. Extracted template_name='{template_name}'")
        
        # 3. Load the flow from DB
        logger.info(f"DEBUG-FLOW: 3. Attempting to find flow in DB for template_name='{template_name}'")
        flow = Flow.objects.get(template_name=template_name)
        logger.info("DEBUG-FLOW:    SUCCESS! Found flow object in the database.")
        
        flow_data = flow.flow_data
        nodes = flow_data.get('nodes', [])
        edges = flow_data.get('edges', [])
        
        # 4. Find the template node
        logger.info("DEBUG-FLOW: 4. Searching for the 'template' node in the flow data.")
        template_node = next((n for n in nodes if n.get('type') == 'template'), None)
        if not template_node:
            logger.warning("DEBUG-FLOW:    FAILURE! Could not find a node with type='template' in the saved flow JSON.")
            return False
        logger.info(f"DEBUG-FLOW:    SUCCESS! Found template node with id='{template_node.get('id')}'")

        # 5. Find the matching edge
        logger.info(f"DEBUG-FLOW: 5. Searching for an edge from node '{template_node.get('id')}' that matches user_input='{user_input}'")
        next_edge = None
        for edge in edges:
            source_handle = edge.get('sourceHandle')
            logger.info(f"DEBUG-FLOW:    - Checking edge with sourceHandle: '{source_handle}'")
            if edge.get('source') == template_node.get('id') and source_handle == user_input:
                next_edge = edge
                break
        
        if not next_edge:
            logger.warning(f"DEBUG-FLOW:    FAILURE! No edge found with sourceHandle matching '{user_input}'. Check for typos or character encoding issues in the saved flow.")
            return False
        logger.info(f"DEBUG-FLOW:    SUCCESS! Found matching edge. It points to target node id='{next_edge.get('target')}'")

        # 6. Find the target node
        target_node_id = next_edge.get('target')
        target_node = next((n for n in nodes if n.get('id') == target_node_id), None)
        if not target_node:
            logger.warning(f"DEBUG-FLOW:    FAILURE! The edge points to target node '{target_node_id}', but this node was not found in the flow data.")
            return False
        logger.info(f"DEBUG-FLOW: 6. Found target node. Type='{target_node.get('type')}'")
        
         # ** THIS IS THE NEW LOGIC TO SAVE THE SESSION **
        # Before sending the message, update or create the session for this user.
        logger.info(f"DEBUG-FLOW: 7. Saving user session. Contact='{contact.wa_id}', Flow='{template_name}', New Node='{target_node_id}'")
        UserFlowSession.objects.update_or_create(
            contact=contact,
            defaults={
                'flow': flow,
                'current_node_id': target_node_id
            }
        )
        logger.info("DEBUG-FLOW:    SUCCESS! User session saved to database.")
        
        # 7. Construct and send the message
        node_data = target_node.get('data', {})
        message_text = node_data.get('text')
        logger.info(f"DEBUG-FLOW: 7. Preparing to send message with text: '{message_text}'")
        
        payload = {"messaging_product": "whatsapp", "to": contact.wa_id, "type": "text", "text": {"body": message_text}}
        success, response_data = send_whatsapp_message(payload)
        
        if success:
            save_outgoing_message(contact=contact, wamid=response_data['messages'][0]['id'], message_type='text', text_content=message_text)
            logger.info("DEBUG-FLOW:    SUCCESS! Message sent and saved.")
            logger.info("---------- FLOW EXECUTION COMPLETE ----------")
            return True
        else:
            logger.error(f"DEBUG-FLOW:    FAILURE! send_whatsapp_message failed. Response: {response_data}")
            return False
            
    except Message.DoesNotExist:
        logger.warning(f"DEBUG-FLOW:    FAILURE at step 1! The original message with wamid='{replied_to_wamid}' was not found in the database as an outbound template.")
    except Flow.DoesNotExist:
        logger.warning(f"DEBUG-FLOW:    FAILURE at step 3! The flow for template '{template_name}' does not exist in the database.")
    except Exception as e:
        logger.error(f"DEBUG-FLOW:    CRITICAL ERROR! An unexpected exception occurred: {e}", exc_info=True)
    
    logger.info("---------- FLOW EXECUTION FAILED ----------")
    return False

def get_whatsapp_templates_api(request):
    """API endpoint to fetch approved WhatsApp templates for the React frontend."""
    # This logic is copied from your `template_sender_view`
    try:
        
        url = f"https://graph.facebook.com/v19.0/{WABA_ID}/message_templates?fields=name,components,status"
        headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        all_templates = response.json().get('data', [])
        
        # We need to extract button texts for the frontend
        templates_data = []
        for t in all_templates:
            if t.get('status') == 'APPROVED':
                buttons = []
                for comp in t.get('components', []):
                    if comp.get('type') == 'BUTTONS':
                        for btn in comp.get('buttons', []):
                            buttons.append(btn.get('text'))
                templates_data.append({'id': t.get('name'), 'name': t.get('name'), 'buttons': buttons})
        
        json_response = json.dumps(templates_data, ensure_ascii=False)
        return HttpResponse(json_response, content_type="application/json; charset=utf-8")

    except Exception as e:
        logger.error(f"Failed to fetch templates for API: {e}")
        return JsonResponse({"error": "Could not load templates."}, status=500)

# NEW API VIEW 2: To save the flow from React
@csrf_exempt
def save_flow_api(request):
    """API endpoint to save a flow definition from the React frontend."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            template_name = data.get('template_name')
            flow_data = data.get('flow')
            
            if not template_name or not flow_data:
                return JsonResponse({'status': 'error', 'message': 'Missing template_name or flow data.'}, status=400)

            # Use update_or_create to save the flow
            flow_obj, created = Flow.objects.update_or_create(
                template_name=template_name,
                defaults={'flow_data': flow_data}
            )
            
            status_message = "Flow created successfully." if created else "Flow updated successfully."
            return JsonResponse({'status': 'success', 'message': status_message})
        except Exception as e:
            logger.error(f"Error saving flow: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)
