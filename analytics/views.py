import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from datetime import datetime, timedelta

# --- Setup ---
load_dotenv()
genai.configure(api_key='AIzaSyCh0DeWCZr8m3kF4LDB2A_xoAlqbmKjvgs')

# --- Helper Functions ---

def get_db_schema():
    """
    Connects to the database and retrieves the CREATE TABLE statements
    for a predefined list of allowed tables.
    """
    allowed_tables = ['registration_chatcontact','registration_farmer','registration_cropdetails',
                      'registration_intervention', 'flow_flows', 'registration_message',
                      'registration_labourer', 'registration_job','user_profiles'] 
    
    schema_str = ""
    with connection.cursor() as cursor:
        for table_name in allowed_tables:
            cursor.execute(f"""
                SELECT 'CREATE TABLE ' || '{table_name}' || ' (' || string_agg(column_name || ' ' || data_type, ', ') || ');'
                FROM information_schema.columns
                WHERE table_name = '{table_name}';
            """)
            row = cursor.fetchone()
            if row and row[0]:
                schema_str += row[0] + "\n\n"
    return schema_str

def get_comprehensive_farmer_data():
    """
    Retrieves comprehensive farmer data matching EXACT database schema:
    - registration_farmer (id, farmer_name, phone_number, farm_size_acres, created_at)
    - registration_cropdetails (id, farmer_id, crop_name, seeding_date, germination_date, 
                                vegetative_stage_start, flowering_stage_start, 
                                fruiting_stage_start, harvesting_date, next_crop_recommendation, 
                                soil_improvement_tip)
    - registration_intervention (id, crop_details_id, intervention_type, date, product_used, notes)
    """
    with connection.cursor() as cursor:
        try:
            # Get farmer demographics with crop details
            # Note: registration_cropdetails has farmer_id (FK to registration_farmer.id)
            cursor.execute("""
                SELECT 
                    f.id as farmer_id,
                    f.farmer_name as name,
                    f.phone_number,
                    f.farm_size_acres as farm_size,
                    f.created_at,
                    cd.crop_name,
                    cd.seeding_date,
                    cd.germination_date,
                    cd.vegetative_stage_start,
                    cd.flowering_stage_start,
                    cd.fruiting_stage_start,
                    cd.harvesting_date,
                    cd.next_crop_recommendation,
                    cd.soil_improvement_tip,
                    COUNT(DISTINCT i.id) as total_interventions
                FROM registration_farmer f
                LEFT JOIN registration_cropdetails cd ON f.id = cd.farmer_id
                LEFT JOIN registration_intervention i ON cd.id = i.crop_details_id
                GROUP BY 
                    f.id, f.farmer_name, f.phone_number, f.farm_size_acres, f.created_at,
                    cd.crop_name, cd.seeding_date, cd.germination_date, cd.vegetative_stage_start,
                    cd.flowering_stage_start, cd.fruiting_stage_start, cd.harvesting_date,
                    cd.next_crop_recommendation, cd.soil_improvement_tip
            """)
            
            columns = [col[0] for col in cursor.description]
            farmer_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
            print(f"Fetched {len(farmer_data)} farmer records")
            
        except Exception as e:
            print(f"Error fetching farmer data: {e}")
            return {'farmers': [], 'crop_details': [], 'interventions': []}
        
        # Get crop-specific details with growth stage calculation
        try:
            cursor.execute("""
                SELECT 
                    cd.id as crop_id,
                    cd.farmer_id,
                    cd.crop_name,
                    cd.seeding_date,
                    cd.germination_date,
                    cd.vegetative_stage_start,
                    cd.flowering_stage_start,
                    cd.fruiting_stage_start,
                    cd.harvesting_date,
                    cd.next_crop_recommendation,
                    cd.soil_improvement_tip,
                    CASE 
                        WHEN CURRENT_DATE < cd.germination_date THEN 'Seeding'
                        WHEN CURRENT_DATE < cd.vegetative_stage_start THEN 'Germination'
                        WHEN CURRENT_DATE < cd.flowering_stage_start THEN 'Vegetative'
                        WHEN CURRENT_DATE < cd.fruiting_stage_start THEN 'Flowering'
                        WHEN CURRENT_DATE < cd.harvesting_date THEN 'Fruiting'
                        ELSE 'Ready for Harvest'
                    END as current_growth_stage,
                    cd.harvesting_date - CURRENT_DATE as days_until_harvest
                FROM registration_cropdetails cd
            """)
            columns = [col[0] for col in cursor.description]
            crop_details = [dict(zip(columns, row)) for row in cursor.fetchall()]
            print(f"Fetched {len(crop_details)} crop details")
            
        except Exception as e:
            print(f"Error fetching crop details: {e}")
            crop_details = []
        
        # Get intervention history
        # registration_intervention has: crop_details_id (FK to registration_cropdetails.id)
        try:
            cursor.execute("""
                SELECT 
                    i.id as intervention_id,
                    cd.farmer_id,
                    i.crop_details_id,
                    i.intervention_type,
                    i.date as intervention_date,
                    i.day_number_from_planting,
                    i.activity_name,
                    i.main_input_values,
                    i.secondary_input_values,
                    i.how_to_do_it,
                    i.price_cost,
                    i.product_catalog_brand,
                    i.purpose_goal,
                    i.product_used,
                    i.notes,
                    cd.crop_name
                FROM registration_intervention i
                JOIN registration_cropdetails cd ON i.crop_details_id = cd.id
                ORDER BY i.date DESC
            """)
            columns = [col[0] for col in cursor.description]
            interventions = [dict(zip(columns, row)) for row in cursor.fetchall()]
            print(f"Fetched {len(interventions)} interventions")
            
        except Exception as e:
            print(f"Error fetching interventions: {e}")
            interventions = []
        
        return {
            'farmers': farmer_data,
            'crop_details': crop_details,
            'interventions': interventions
        }
def generate_flow_prompts_from_segments(segments_data):
    """
    ENHANCED: Generates COMPLETE template bodies and creation prompts for each segment
    """
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    prompt = f"""
You are creating COMPLETE WhatsApp template specifications for farmer engagement.

CRITICAL: For EACH segment, generate:
1. Full template body text (Hindi AND English)
2. All variable definitions
3. Ready-to-submit template creation prompt
4. Button configurations

SEGMENT ANALYSIS:
{json.dumps(segments_data, indent=2, default=str)}

YOUR TASK:
For EACH segment in the analysis, create detailed template specifications.

OUTPUT FORMAT (JSON):
{{
  "flow_prompts": [
    {{
      "prompt_id": "segment_harvest_support",
      "segment_targeted": "Harvest Support",
      "priority": "HIGH",
      "prompt_title": "Pre-Harvest Labor Booking Campaign",
      "farmer_count": 418,
      "language": "hi",
      "estimated_conversion_rate": "28%",
      
      "templates": [
        {{
          "template_name": "pre_harvest_labor_hi",
          "template_category": "UTILITY",
          "template_language": "hi",
          "template_body": "नमस्कार {{{{1}}}},\\n\\nआपकी {{{{2}}}} एकड़ की {{{{3}}}} फसल अब {{{{4}}}} स्टेज में है। {{{{5}}}} दिनों में कटाई होगी! 🌾\\n\\nपिछली बार {{{{6}}}} को {{{{7}}}} किया था।\\nअब कटाई के लिए तैयारी का समय!\\n\\n✅ {{{{8}}}} अनुभवी मजदूर\\n✅ अनुमानित लागत: ₹{{{{9}}}}\\n✅ {{{{10}}}} को कटाई\\n\\nअभी बुक करें! 👇",
          
          "variables": [
            {{
              "position": 1,
              "variable_name": "farmer_name",
              "example": "रमेश पाटील",
              "data_field": "farmer_name",
              "fallback": "किसान भाई"
            }},
            {{
              "position": 2,
              "variable_name": "farm_size",
              "example": "3.5",
              "data_field": "farm_size_acres",
              "fallback": "2"
            }},
            {{
              "position": 3,
              "variable_name": "crop_name",
              "example": "अंगूर",
              "data_field": "crop_name",
              "fallback": "फसल"
            }},
            {{
              "position": 4,
              "variable_name": "current_stage",
              "example": "Fruiting",
              "data_field": "current_growth_stage",
              "fallback": "पकने की"
            }},
            {{
              "position": 5,
              "variable_name": "days_until_harvest",
              "example": "7",
              "data_field": "days_until_harvest",
              "fallback": "10"
            }},
            {{
              "position": 6,
              "variable_name": "last_intervention_date",
              "example": "15 सितंबर",
              "data_field": "last_intervention_date",
              "fallback": "पिछले हफ्ते"
            }},
            {{
              "position": 7,
              "variable_name": "last_intervention_type",
              "example": "कीटनाशक छिड़काव",
              "data_field": "last_intervention_type",
              "fallback": "देखभाल"
            }},
            {{
              "position": 8,
              "variable_name": "estimated_workers",
              "example": "10-12",
              "data_field": "CALC: farm_size * 3",
              "fallback": "8-10"
            }},
            {{
              "position": 9,
              "variable_name": "estimated_cost",
              "example": "17,500",
              "data_field": "CALC: farm_size * 5000",
              "fallback": "15,000"
            }},
            {{
              "position": 10,
              "variable_name": "harvest_date",
              "example": "25 अक्टूबर",
              "data_field": "harvesting_date",
              "fallback": "जल्द ही"
            }}
          ],
          
          "buttons": [
            {{
              "type": "QUICK_REPLY",
              "text": "मजदूर बुक करें"
            }},
            {{
              "type": "QUICK_REPLY",
              "text": "बाद में बात करें"
            }}
          ],
          
          "meta_template_creation_prompt": "**WhatsApp Template Creation Request**\\n\\nTemplate Name: pre_harvest_labor_hi\\nCategory: UTILITY\\nLanguage: Hindi (hi)\\n\\nHeader: None\\n\\nBody:\\nnamस्कार {{{{1}}}},\\n\\nआपकी {{{{2}}}} एकड़ की {{{{3}}}} फसल अब {{{{4}}}} स्टेज में है। {{{{5}}}} दिनों में कटाई होगी! 🌾\\n\\nपिछली बार {{{{6}}}} को {{{{7}}}} किया था।\\nअब कटाई के लिए तैयारी का समय!\\n\\n✅ {{{{8}}}} अनुभवी मजदूर\\n✅ अनुमानित लागत: ₹{{{{9}}}}\\n✅ {{{{10}}}} को कटाई\\n\\nअभी बुक करें! 👇\\n\\nFooter: None\\n\\nButtons:\\n1. QUICK_REPLY: मजदूर बुक करें\\n2. QUICK_REPLY: बाद में बात करें\\n\\nVariable Sample Values:\\n1. रमेश पाटील (farmer name)\\n2. 3.5 (farm size)\\n3. अंगूर (crop name)\\n4. Fruiting (growth stage)\\n5. 7 (days to harvest)\\n6. 15 सितंबर (last intervention date)\\n7. कीटनाशक छिड़काव (last intervention)\\n8. 10-12 (estimated workers)\\n9. 17,500 (estimated cost)\\n10. 25 अक्टूबर (harvest date)\\n\\nSubmit this template to Meta Business Manager for approval."
        }},
        
        {{
          "template_name": "labor_booking_confirmation_hi",
          "template_category": "UTILITY",
          "template_language": "hi",
          "template_body": "धन्यवाद {{{{1}}}}! 🎉\\n\\nआपकी {{{{2}}}} की कटाई के लिए मजदूर बुकिंग कन्फर्म हुई:\\n\\n✅ तारीख: {{{{3}}}}\\n✅ मजदूर: {{{{4}}}}\\n✅ लागत: ₹{{{{5}}}}\\n✅ फसल: {{{{6}}}} ({{{{7}}}} एकड़)\\n\\nहमारी टीम {{{{8}}}} को आपसे संपर्क करेगी।\\n\\nमदद चाहिए?",
          
          "variables": [
            {{
              "position": 1,
              "variable_name": "farmer_name",
              "example": "रमेश जी",
              "data_field": "farmer_name",
              "fallback": "किसान भाई"
            }},
            {{
              "position": 2,
              "variable_name": "crop_name",
              "example": "अंगूर",
              "data_field": "crop_name",
              "fallback": "फसल"
            }},
            {{
              "position": 3,
              "variable_name": "booking_date",
              "example": "25 अक्टूबर",
              "data_field": "harvesting_date",
              "fallback": "जल्द ही"
            }},
            {{
              "position": 4,
              "variable_name": "worker_count",
              "example": "12",
              "data_field": "booked_workers",
              "fallback": "10"
            }},
            {{
              "position": 5,
              "variable_name": "total_cost",
              "example": "18,000",
              "data_field": "booking_cost",
              "fallback": "15,000"
            }},
            {{
              "position": 6,
              "variable_name": "crop_name_repeat",
              "example": "अंगूर",
              "data_field": "crop_name",
              "fallback": "फसल"
            }},
            {{
              "position": 7,
              "variable_name": "farm_size",
              "example": "3.5",
              "data_field": "farm_size_acres",
              "fallback": "2"
            }},
            {{
              "position": 8,
              "variable_name": "contact_time",
              "example": "सुबह 10 बजे",
              "data_field": "CALC: current_time + 2h",
              "fallback": "आज शाम"
            }}
          ],
          
          "buttons": [
            {{
              "type": "QUICK_REPLY",
              "text": "सब ठीक है ✓"
            }},
            {{
              "type": "QUICK_REPLY",
              "text": "मदद चाहिए"
            }}
          ],
          
          "meta_template_creation_prompt": "**WhatsApp Template Creation Request**\\n\\nTemplate Name: labor_booking_confirmation_hi\\nCategory: UTILITY\\nLanguage: Hindi (hi)\\n\\nBody:\\nधन्यवाद {{{{1}}}}! 🎉\\n\\nआपकी {{{{2}}}} की कटाई के लिए मजदूर बुकिंग कन्फर्म हुई:\\n\\n✅ तारीख: {{{{3}}}}\\n✅ मजदूर: {{{{4}}}}\\n✅ लागत: ₹{{{{5}}}}\\n✅ फसल: {{{{6}}}} ({{{{7}}}} एकड़)\\n\\nहमारी टीम {{{{8}}}} को आपसे संपर्क करेगी।\\n\\nमदद चाहिए?\\n\\nButtons:\\n1. QUICK_REPLY: सब ठीक है ✓\\n2. QUICK_REPLY: मदद चाहिए\\n\\nVariable Samples: [farmer name], [crop], [date], [worker count], [cost], [crop], [farm size], [time]"
        }}
      ],
      
      "full_flow_prompt": "**COMPLETE WHATSAPP FLOW: Pre-Harvest Labor Booking**\\n\\n**TARGET AUDIENCE:**\\n- Segment: Harvest Support (Pre-Harvest Farmers 7-30 days)\\n- Total Farmers: 418\\n- Average Farm Size: 3.2 acres\\n- Primary Crops: Grapes, Tomatoes, Pomegranate\\n\\n**PERSONALIZATION DATA AVAILABLE:**\\n1. farmer_name - Farmer's full name\\n2. farm_size_acres - Farm size in acres\\n3. crop_name - Current crop being grown\\n4. current_growth_stage - Crop growth stage (Fruiting/Ready)\\n5. days_until_harvest - Days until harvest date\\n6. last_intervention_date - Date of last farming activity\\n7. last_intervention_type - Type of last activity (Fertilizer/Pesticide)\\n8. harvesting_date - Scheduled harvest date\\n9. phone_number - Farmer's contact\\n\\n**FLOW STRUCTURE:**\\n\\n═══════════════════════════════════════\\n**STEP 1: Initial Outreach**\\n═══════════════════════════════════════\\n\\nTemplate: pre_harvest_labor_hi\\nTrigger: 10-12 days before harvest\\nSend Time: 9:00 AM\\n\\nMessage Preview:\\n\\\"नमस्कार रमेश पाटील,\\n\\nआपकी 3.5 एकड़ की अंगूर फसल अब Fruiting स्टेज में है। 7 दिनों में कटाई होगी! 🌾\\n\\nपिछली बार 15 सितंबर को कीटनाशक छिड़काव किया था।\\nअब कटाई के लिए तैयारी का समय!\\n\\n✅ 10-12 अनुभवी मजदूर\\n✅ अनुमानित लागत: ₹17,500\\n✅ 25 अक्टूबर को कटाई\\n\\nअभी बुक करें! 👇\\\"\\n\\nButton Responses:\\n→ \\\"मजदूर बुक करें\\\" → Go to STEP 2 (Booking Details)\\n→ \\\"बाद में बात करें\\\" → Schedule reminder for 48 hours\\n\\n═══════════════════════════════════════\\n**STEP 2: Booking Details**\\n═══════════════════════════════════════\\n\\nTemplate: labor_booking_details_hi\\nTrigger: When user clicks \\\"मजदूर बुक करें\\\"\\n\\nMessage:\\n\\\"बहुत अच्छा! कृपया कन्फर्म करें:\\n\\n📅 कटाई की तारीख: 25 अक्टूबर\\n👥 मजदूर: 10-12\\n💰 अनुमानित लागत: ₹17,500\\n\\nक्या यह सही है?\\\"\\n\\nButtons:\\n→ \\\"हाँ, बुक करें\\\" → Go to STEP 3 (Confirmation)\\n→ \\\"संख्या बदलें\\\" → Allow edit workers count\\n→ \\\"तारीख बदलें\\\" → Allow edit date\\n\\n═══════════════════════════════════════\\n**STEP 3: Confirmation**\\n═══════════════════════════════════════\\n\\nTemplate: labor_booking_confirmation_hi\\nTrigger: After confirmation\\n\\nMessage:\\n\\\"धन्यवाद रमेश जी! 🎉\\n\\nआपकी अंगूर की कटाई के लिए मजदूर बुकिंग कन्फर्म हुई:\\n\\n✅ तारीख: 25 अक्टूबर\\n✅ मजदूर: 12\\n✅ लागत: ₹18,000\\n✅ फसल: अंगूर (3.5 एकड़)\\n\\nहमारी टीम सुबह 10 बजे आपसे संपर्क करेगी।\\n\\nमदद चाहिए?\\\"\\n\\nButtons:\\n→ \\\"सब ठीक है ✓\\\" → End flow, mark as success\\n→ \\\"मदद चाहिए\\\" → Connect to support\\n\\n═══════════════════════════════════════\\n**SUCCESS METRICS**\\n═══════════════════════════════════════\\n\\nExpected Performance:\\n- Open Rate: 85% (personalized messages)\\n- Step 1→2 Conversion: 35%\\n- Step 2→3 Conversion: 75%\\n- Overall Booking Rate: 26%\\n\\nRevenue Impact:\\n- 418 farmers × 26% conversion = 109 bookings\\n- Average booking value: ₹17,500\\n- Total revenue potential: ₹19,07,500\\n\\n═══════════════════════════════════════\\n**IMPLEMENTATION STEPS**\\n═══════════════════════════════════════\\n\\n1. **Create Templates** (Day 1)\\n   - Submit all 3 templates to Meta\\n   - Wait 24-48h for approval\\n   \\n2. **Map Database Fields** (Day 2)\\n   - Connect variables to farmer data\\n   - Test personalization with 5 sample farmers\\n   \\n3. **Build Flow Logic** (Day 2-3)\\n   - Set up conditional routing\\n   - Configure button responses\\n   - Add fallback messages\\n   \\n4. **Test Campaign** (Day 3)\\n   - Send to 10 test farmers\\n   - Verify all personalization works\\n   - Check button functionality\\n   \\n5. **Launch** (Day 4)\\n   - Roll out to all 418 farmers\\n   - Monitor responses in real-time\\n   - Adjust timing if needed\\n\\n═══════════════════════════════════════\\n**TARGETING LOGIC**\\n═══════════════════════════════════════\\n\\nInclude farmers where:\\n- days_until_harvest BETWEEN 7 AND 14\\n- current_growth_stage IN ('Fruiting', 'Ready for Harvest')\\n- farm_size_acres >= 1\\n- has_active_crop = TRUE\\n\\nExclude farmers where:\\n- already_booked_labor = TRUE\\n- unsubscribed = TRUE\\n- last_message_sent < 7 days ago\\n\\n═══════════════════════════════════════",
      
      "implementation_notes": [
        "Submit templates to Meta 48 hours before campaign launch",
        "Test personalization with 10 farmers first",
        "Monitor response rates and adjust timing",
        "Have support team ready for \\\"मदद चाहिए\\\" responses",
        "Track booking confirmation rate",
        "Follow up with non-responders after 48 hours"
      ],
      
      "expected_templates": 3,
      "revenue_potential": "₹19,07,500",
      "implementation_difficulty": "MEDIUM"
    }}
  ]
}}

Generate templates for ALL segments in the analysis. Make each template COMPLETE and READY TO USE.
Generate ONLY valid JSON.
"""
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Error generating flow prompts: {e}")
        return {'flow_prompts': []}
# Add this at the top with other imports
import requests
import logging

logger = logging.getLogger(__name__)

# Add this function to fetch existing templates
def get_existing_whatsapp_templates():
    """
    Fetches all approved WhatsApp templates from Meta API
    Returns a list of template names and their details
    """
    try:
        META_ACCESS_TOKEN = "EAAhMBt21QaMBPCyLtJj6gwjDy6Gai4fZApb3MXuZBZCCm0iSEd8ZCZCJdkRt4cOtvhyeFLZCNUwitFaLZA3ZCwv7enN6FBFgDMAOKl7LMx0J2kCjy6Qd6AqnbnhB2bo2tgsdGmn9ZCN5MD6yCgE3shuP62t1spfSB6ZALy1QkNLvIaeWZBcvPH00HHpyW6US4kil2ENZADL4ZCvDLVWV9seSbZCxXYzVCezIenCjhSYtoKTIlJ"
        WABA_ID = "1477047197063313"
        url = f"https://graph.facebook.com/v19.0/{WABA_ID}/message_templates?fields=name,components,status,category,language"
        headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}"}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        all_templates = response.json().get('data', [])
        approved_templates = [t for t in all_templates if t.get('status') == 'APPROVED']
        
        # Extract template names and basic info
        template_list = []
        for t in approved_templates:
            template_list.append({
                'name': t.get('name'),
                'language': t.get('language'),
                'category': t.get('category'),
                'components': t.get('components', [])
            })
        
        print(f"Fetched {len(template_list)} approved templates")
        return template_list
    
    except Exception as e:
        logger.error(f"Failed to fetch WhatsApp templates: {e}")
        return []



def analyze_farmer_segments_with_ai(farmer_data):
    """
    ENHANCED: Dynamic segment discovery - finds NEW patterns automatically
    """
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
    except:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    from datetime import datetime, timedelta
    from collections import Counter
    
    total_farmers = len(farmer_data['farmers'])
    
    # Enhanced intervention analysis
    intervention_types = Counter([i['intervention_type'] for i in farmer_data['interventions']])
    
    # Analyze intervention patterns by crop
    intervention_by_crop = {}
    for intervention in farmer_data['interventions']:
        crop = intervention.get('crop_name')
        if crop:
            if crop not in intervention_by_crop:
                intervention_by_crop[crop] = []
            intervention_by_crop[crop].append({
                'type': intervention['intervention_type'],
                'activity': intervention.get('activity_name'),
                'product': intervention.get('product_used'),
                'cost': intervention.get('price_cost'),
                'purpose': intervention.get('purpose_goal')
            })
    
    # NEW: Discover unique crop types
    unique_crops = list(set([f['crop_name'] for f in farmer_data['farmers'] if f.get('crop_name')]))
    
    # NEW: Discover unique intervention activities (beyond types)
    unique_activities = list(set([i.get('activity_name') for i in farmer_data['interventions'] if i.get('activity_name')]))
    
    # NEW: Discover unique products being used
    unique_products = list(set([i.get('product_used') for i in farmer_data['interventions'] if i.get('product_used')]))
    
    # NEW: Discover cost-based segments
    high_value_interventions = [i for i in farmer_data['interventions'] if i.get('price_cost') and float(i.get('price_cost', 0)) > 1000]
    low_cost_interventions = [i for i in farmer_data['interventions'] if i.get('price_cost') and float(i.get('price_cost', 0)) < 200]
    
    # Recent interventions for upsell opportunities
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    recent_interventions = [
        i for i in farmer_data['interventions']
        if i.get('intervention_date') and i['intervention_date'] >= thirty_days_ago
    ]
    
    # Identify farmers needing interventions (no recent activity)
    farmers_needing_intervention = []
    for farmer in farmer_data['farmers']:
        farmer_interventions = [
            i for i in recent_interventions
            if i.get('farmer_id') == farmer['farmer_id']
        ]
        if len(farmer_interventions) == 0:
            farmers_needing_intervention.append(farmer['farmer_id'])
    
    # Get existing WhatsApp templates
    existing_templates = get_existing_whatsapp_templates()
    existing_template_names = [t['name'] for t in existing_templates]
    
    # Calculate summary statistics
    crops_counter = Counter([f['crop_name'] for f in farmer_data['farmers'] if f.get('crop_name')])
    farm_sizes = [float(f['farm_size']) for f in farmer_data['farmers'] if f.get('farm_size')]
    avg_farm_size = sum(farm_sizes) / len(farm_sizes) if farm_sizes else 0
    growth_stages = Counter([c['current_growth_stage'] for c in farmer_data['crop_details']])
    harvest_soon = [c for c in farmer_data['crop_details'] if c.get('days_until_harvest') and c['days_until_harvest'] <= 30]
    harvest_within_week = [c for c in farmer_data['crop_details'] if c.get('days_until_harvest') and c['days_until_harvest'] <= 7]
    farmers_with_next_crop = [f for f in farmer_data['farmers'] if f.get('next_crop_recommendation')]
    
    summary_data = {
        'total_farmers': total_farmers,
        'crop_distribution': dict(crops_counter.most_common(10)),
        'unique_crops_in_system': unique_crops,
        'unique_intervention_activities': unique_activities[:20],
        'unique_products_used': unique_products[:20],
        'average_farm_size': round(avg_farm_size, 2),
        'farm_size_ranges': {
            'small_0_2_acres': len([f for f in farm_sizes if f <= 2]),
            'medium_2_5_acres': len([f for f in farm_sizes if 2 < f <= 5]),
            'large_5plus_acres': len([f for f in farm_sizes if f > 5])
        },
        'growth_stage_distribution': dict(growth_stages),
        'harvest_insights': {
            'harvesting_within_30_days': len(harvest_soon),
            'harvesting_within_7_days': len(harvest_within_week),
            'harvest_soon_crops': [{'crop': c['crop_name'], 'days': c['days_until_harvest']} 
                                  for c in harvest_within_week[:10]]
        },
        'intervention_insights': {
            'total_interventions': len(farmer_data['interventions']),
            'recent_interventions_30_days': len(recent_interventions),
            'intervention_types': dict(intervention_types),
            'intervention_by_crop': {k: len(v) for k, v in intervention_by_crop.items()},
            'farmers_needing_intervention': len(farmers_needing_intervention),
            'avg_interventions_per_farmer': round(len(farmer_data['interventions']) / total_farmers, 2),
            'most_common_products': list(set([i.get('product_used') for i in farmer_data['interventions'][:20] if i.get('product_used')])),
            'avg_intervention_cost': round(sum([float(i.get('price_cost', 0)) for i in farmer_data['interventions'] if i.get('price_cost')]) / len(farmer_data['interventions']), 2) if farmer_data['interventions'] else 0,
            'high_value_intervention_count': len(high_value_interventions),
            'low_cost_intervention_count': len(low_cost_interventions),
        },
        'next_crop_opportunities': {
            'farmers_with_recommendations': len(farmers_with_next_crop),
            'sample_recommendations': list(set([f['next_crop_recommendation'] 
                                               for f in farmers_with_next_crop[:20] 
                                               if f.get('next_crop_recommendation')]))
        },
        'existing_whatsapp_templates': existing_template_names,
        'sample_farmers': farmer_data['farmers'][:5]
    }
    
    prompt = f"""
You are an expert agricultural business analyst for a FARMER-LABOR PLATFORM with INTERVENTION TRACKING.

🔄 CRITICAL: This is a DYNAMIC ANALYSIS SYSTEM. You must:
1. Discover NEW segment opportunities from the data (don't just use pre-defined segments)
2. Create segments for UNIQUE crop types you haven't seen before
3. Identify EMERGING patterns (new products, new interventions, seasonal trends)
4. Generate INNOVATIVE marketing opportunities based on actual farmer behavior

DATABASE STRUCTURE:
- Farmer: farmer_name, phone_number, farm_size_acres, created_at
- CropDetails: One crop per farmer with growth stages (seeding → germination → vegetative → flowering → fruiting → harvesting)
- Intervention: Detailed farm activities with:
  * intervention_type: Fertilizer, Pesticide, Pruning/Weeding, Irrigation
  * activity_name: Specific activity (e.g., "Urea Application", "Fungicide Spray")
  * main_input_values: Primary products used
  * product_used: Brand/product details
  * price_cost: Cost of intervention
  * purpose_goal: Why intervention was done
  * how_to_do_it: Instructions given

EXISTING WHATSAPP TEMPLATES:
{json.dumps(existing_template_names, indent=2)}

FARMER DATA SUMMARY (based on {total_farmers} farmers):
{json.dumps(summary_data, indent=2, default=str)}

🎯 YOUR TASK - DYNAMIC SEGMENT DISCOVERY:

1. **ALWAYS CREATE THESE CORE SEGMENTS** (if data supports):
   - Pre-Harvest Farmers (7-30 days to harvest)
   - Fertilizer Upsell (active crops needing nutrition)
   - Pesticide Service (flowering/fruiting stage)
   - Inactive Farmers (no activity 30+ days)
   - High-Value Customers (avg spend >₹500)
   - Next Crop Upsell (has recommendations)

2. **DISCOVER AND CREATE NEW SEGMENTS** based on:
   
   A. UNIQUE CROPS FOUND ({len(summary_data['unique_crops_in_system'])} crops):
   {json.dumps(summary_data['unique_crops_in_system'][:15], indent=2)}
   
   → For EACH unique/specialty crop (e.g., Strawberry, Pomegranate, Dragon Fruit):
      Create crop-specific segment like "Strawberry Growers - Premium Care"
   
   B. UNIQUE INTERVENTION ACTIVITIES ({len(summary_data['unique_intervention_activities'])} activities):
   {json.dumps(summary_data['unique_intervention_activities'][:15], indent=2)}
   
   → For specialized activities (e.g., "Drip Irrigation Setup", "Greenhouse Maintenance"):
      Create service-specific segments
   
   C. PRODUCT USAGE PATTERNS:
   {json.dumps(summary_data['unique_products_used'][:15], indent=2)}
   
   → Identify brand loyalists, premium product users, generic product users
   → Create brand-specific upsell segments

3. **SEGMENT PRIORITIZATION**:
   - HIGH Priority: Revenue >₹50k potential, Easy to implement
   - MEDIUM Priority: Revenue ₹20-50k, Moderate effort  
   - LOW Priority: <₹20k or requires infrastructure

OUTPUT FORMAT (JSON):
{{
  "analysis_summary": {{
    "total_farmers": {total_farmers},
    "analysis_date": "{datetime.now().strftime('%Y-%m-%d')}",
    "new_patterns_discovered": [
      "List any NEW crops, products, or behaviors you found",
      "Highlight opportunities that weren't pre-defined"
    ],
    "key_insights": [
      "intervention-based insights",
      "product upsell opportunities",
      "service gaps identified"
    ]
  }},
  "segments": [
    {{
      "segment_id": "unique_id_reflecting_segment_type",
      "segment_name": "Descriptive Name (can be NEW)",
      "segment_type": "CORE/NEW/EMERGING",
      "discovery_reason": "Why this segment was created (for NEW segments)",
      "priority": "HIGH/MEDIUM/LOW",
      "farmer_count": number,
      "conversion_potential": "HIGH/MEDIUM/LOW",
      "estimated_revenue": "₹X,XXX per farmer/month",
      "revenue_calculation": "explain based on intervention data",
      "characteristics": ["unique patterns that define this segment"]
    }}
  ]
}}

Generate ONLY valid JSON. Be thorough and create at least 7-10 segments.
"""
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        result = json.loads(response.text)
        return result
    except Exception as e:
        print(f"Error in AI analysis: {e}")
        return None


def generate_detailed_segment_analysis(segment, farmer_data):
    """
    COMPLETE VERSION: Generates deep personalized analysis for a specific segment
    """
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
    except:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    # Get matched farmers for this segment
    matched_farmers = get_farmers_for_segment(segment, farmer_data)
    
    if not matched_farmers:
        return {
            'error': 'No farmers matched this segment',
            'stage_distribution': {'breakdown': [], 'key_insights': []},
            'template_requirements': [],
            'flow_creation_prompts': []
        }
    
    # Extract ALL available personalization data
    available_farmer_fields = set()
    for farmer in matched_farmers[:10]:
        available_farmer_fields.update(farmer.keys())
    
    # Get growth stage distribution for matched farmers
    stage_counts = {}
    for farmer in matched_farmers:
        stage = farmer.get('current_stage', 'Unknown')
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
    
    prompt = f"""
You are creating HIGHLY PERSONALIZED WhatsApp templates and flows for a farmer engagement platform.

⚠️ CRITICAL REQUIREMENTS:
1. Make templates feel SPECIFICALLY written for each farmer using their ACTUAL DATA
2. Create COMPLETE, COPY-PASTE ready flow prompts
3. Use MAXIMUM personalization (10+ variables per template)
4. Generate templates that feel like personal conversations, not mass broadcasts

SEGMENT INFORMATION:
{json.dumps(segment, indent=2, default=str)}

MATCHED FARMERS DATA:
- Total farmers in segment: {len(matched_farmers)}
- Available personalization fields: {list(available_farmer_fields)}
- Growth stage distribution: {json.dumps(stage_counts, indent=2)}

SAMPLE FARMERS (showing what data we have):
{json.dumps(matched_farmers[:3], indent=2, default=str)}

YOUR TASK:
Generate COMPLETE analysis with:
1. Stage distribution breakdown
2. Highly personalized WhatsApp templates (with 10+ variables each)
3. Complete, ready-to-execute flow creation prompts

TEMPLATE PERSONALIZATION EXAMPLE:

❌ BAD (Generic):
"नमस्कार, आपकी फसल की कटाई जल्द है। मजदूर चाहिए?"

✅ GOOD (Hyper-Personalized):
"नमस्कार {{{{farmer_name}}}},

आपकी {{{{farm_size}}}} एकड़ की {{{{crop_name}}}} फसल अब {{{{current_stage}}}} में है। {{{{days_until_harvest}}}} दिनों में कटाई होगी! 🌾

पिछली बार {{{{last_intervention_date}}}} को {{{{last_intervention_type}}}} किया था ({{{{product_used}}}})।

अब कटाई के लिए तैयारी का समय!

✅ {{{{estimated_workers}}}} अनुभवी मजदूर
✅ अनुमानित लागत: ₹{{{{estimated_labor_cost}}}}
✅ {{{{harvest_date}}}} को तैयार

अभी बुक करें!"

OUTPUT FORMAT (COMPLETE JSON):
{{
  "stage_distribution": {{
    "breakdown": [
      {{
        "stage": "Fruiting",
        "percentage": 65,
        "farmer_count": 295,
        "urgency": "HIGH/MEDIUM/LOW",
        "action_needed": "What to do for these farmers"
      }}
    ],
    "key_insights": [
      "Most farmers are at X stage",
      "Urgent action needed for Y farmers",
      "Revenue opportunity: ₹Z"
    ]
  }},
  "template_requirements": [
    {{
      "template_name": "segment_action_language (e.g., pre_harvest_labor_hi)",
      "likely_exists": false,
      "template_type": "UTILITY/MARKETING",
      "language": "hi/en",
      "priority": "HIGH/MEDIUM/LOW",
      "personalization_level": "VERY_HIGH",
      "body_text": "Complete Hindi/English template with {{{{1}}}}, {{{{2}}}}, etc placeholders",
      "variables": [
        {{
          "position": "{{{{1}}}}",
          "field_name": "farmer_name",
          "data_source": "matched_farmers[].farmer_name",
          "example": "रमेश पाटील",
          "why_personalized": "Makes farmer feel recognized"
        }},
        {{
          "position": "{{{{2}}}}",
          "field_name": "farm_size",
          "data_source": "matched_farmers[].farm_size",
          "example": "3.5",
          "why_personalized": "Shows we know their farm"
        }},
        {{
          "position": "{{{{3}}}}",
          "field_name": "crop_name",
          "data_source": "matched_farmers[].crop_name",
          "example": "अंगूर",
          "why_personalized": "Crop-specific"
        }},
        {{
          "position": "{{{{4}}}}",
          "field_name": "current_stage",
          "data_source": "matched_farmers[].current_stage",
          "example": "Fruiting",
          "why_personalized": "Real-time crop monitoring"
        }},
        {{
          "position": "{{{{5}}}}",
          "field_name": "days_until_harvest",
          "data_source": "CALCULATED from matched_farmers[].days_until_harvest",
          "example": "7",
          "why_personalized": "Creates urgency"
        }},
        {{
          "position": "{{{{6}}}}",
          "field_name": "last_intervention_date",
          "data_source": "matched_farmers[].last_intervention_date",
          "example": "15 सितंबर",
          "why_personalized": "Proves we track their activities"
        }},
        {{
          "position": "{{{{7}}}}",
          "field_name": "last_intervention_type",
          "data_source": "matched_farmers[].last_intervention",
          "example": "Pesticide स्प्रे",
          "why_personalized": "References their actions"
        }},
        {{
          "position": "{{{{8}}}}",
          "field_name": "product_used",
          "data_source": "matched_farmers[].last_product_used OR match_reason",
          "example": "Bayer Confidor",
          "why_personalized": "Shows we remember products"
        }},
        {{
          "position": "{{{{9}}}}",
          "field_name": "estimated_workers",
          "data_source": "CALCULATED: farm_size * 3",
          "example": "10-12",
          "why_personalized": "Customized to farm size"
        }},
        {{
          "position": "{{{{10}}}}",
          "field_name": "estimated_labor_cost",
          "data_source": "CALCULATED: farm_size * ₹5000",
          "example": "17,500",
          "why_personalized": "Budget-relevant pricing"
        }}
      ],
      "buttons": [
        {{"type": "QUICK_REPLY", "text": "मजदूर बुक करें"}},
        {{"type": "QUICK_REPLY", "text": "बाद में बात करें"}}
      ],
      "usage_context": "When to send this template",
      "personalization_impact": "Expected engagement increase",
      "data_requirements": [
        "farmer_name (REQUIRED)",
        "farm_size (REQUIRED)",
        "crop_name (REQUIRED)",
        "List all REQUIRED and OPTIONAL fields"
      ]
    }}
  ],
  "flow_creation_prompts": [
    {{
      "prompt_id": "unique_flow_id",
      "prompt_title": "Descriptive Flow Name",
      "complete_prompt": "**COMPLETE MULTI-STEP FLOW SPECIFICATION**\\n\\nTARGET AUDIENCE:\\n- Farmers: {len(matched_farmers)} in segment '{segment['segment_name']}'\\n- Characteristics: [list from matched_farmers data]\\n\\nPERSONALIZATION DATA AVAILABLE:\\n1. Farmer name: matched_farmers[].farmer_name\\n2. Farm size: matched_farmers[].farm_size acres\\n3. Crop: matched_farmers[].crop_name\\n4. Growth stage: matched_farmers[].current_stage\\n5. Days to harvest: matched_farmers[].days_until_harvest\\n6. Last intervention: matched_farmers[].last_intervention\\n7. Last intervention date: matched_farmers[].last_intervention_date\\n8. Product used: matched_farmers[].last_product_used\\n9. Match reason: matched_farmers[].match_reason\\n10. Total interventions: matched_farmers[].total_interventions\\n\\nFLOW STRUCTURE:\\n\\n**STEP 1: Initial Outreach** (Template: template_name_step1_hi)\\nObjective: Get farmer's attention with personalized message\\n\\nTemplate Text:\\n\\\"नमस्कार {{{{farmer_name}}}},\\n\\nआपकी {{{{farm_size}}}} एकड़ की {{{{crop_name}}}} फसल {{{{current_stage}}}} में है।\\n{{{{days_until_harvest}}}} दिनों में कटाई!\\n\\nपिछली बार: {{{{last_intervention_date}}}} - {{{{last_intervention_type}}}}\\n\\n[YOUR SPECIFIC OFFER/MESSAGE]\\n\\nक्या आप रुचि रखते हैं?\\\"\\n\\nButtons:\\n- \\\"हाँ, बताएं\\\" → Go to STEP 2\\n- \\\"नहीं, धन्यवाद\\\" → End flow\\n- \\\"बाद में\\\" → Schedule follow-up\\n\\n---\\n\\n**STEP 2: Details Collection** (Template: template_name_step2_hi)\\nObjective: Gather specific requirements\\n\\nTemplate Text:\\n\\\"बहुत अच्छा {{{{farmer_name}}}}!\\n\\nआपके {{{{farm_size}}}} एकड़ के {{{{crop_name}}}} के लिए:\\n\\n[SPECIFIC QUESTIONS BASED ON SEGMENT]\\n\\nकृपया बताएं:\\\"\\n\\nButtons:\\n- Option 1\\n- Option 2\\n- Option 3\\n\\n---\\n\\n**STEP 3: Confirmation** (Template: template_name_confirm_hi)\\nObjective: Confirm and close\\n\\nTemplate Text:\\n\\\"धन्यवाद {{{{farmer_name}}}}!\\n\\n✅ Confirmed for {{{{harvest_date}}}}\\n✅ Details: [SUMMARY]\\n✅ Cost: ₹{{{{estimated_cost}}}}\\n\\nहमारी टीम {{{{contact_time}}}} को संपर्क करेगी।\\n\\nकोई सवाल?\\\"\\n\\nButtons:\\n- \\\"सब ठीक है\\\"\\n- \\\"बदलाव चाहिए\\\"\\n- \\\"मदद चाहिए\\\"\\n\\n---\\n\\nSUCCESS METRICS:\\n- Step 1→2 conversion: 35%\\n- Step 2→3 conversion: 75%\\n- Overall completion: 26%\\n- Expected revenue per farmer: ₹{segment.get('estimated_revenue', '5,000')}\\n\\nIMPLEMENTATION:\\n1. Create 3 templates in WhatsApp Business API\\n2. Set up flow with conditional logic\\n3. Map personalization variables from database\\n4. Test with 10 farmers first\\n5. Roll out to full segment\\n\\nTRIGGER LOGIC:\\n- When: [SPECIFIC CONDITION]\\n- Frequency: [HOW OFTEN]\\n- Exclusions: [WHO NOT TO SEND TO]",
      "required_templates": ["template_step1_hi", "template_step2_hi", "template_confirm_hi"],
      "expected_outcome": "Detailed outcome expectation",
      "implementation_notes": [
        "Step-by-step implementation guide",
        "What to prepare first",
        "How to test",
        "When to scale"
      ]
    }}
  ],
  "implementation_checklist": [
    {{
      "step": 1,
      "action": "Create WhatsApp Templates",
      "details": "Submit 3 templates to Meta for approval (24-48 hours)",
      "timeline": "Day 1",
      "responsible": "Admin"
    }},
    {{
      "step": 2,
      "action": "Map Database Fields",
      "details": "Connect template variables to farmer data fields",
      "timeline": "Day 2",
      "responsible": "Tech Team"
    }},
    {{
      "step": 3,
      "action": "Build Flow Logic",
      "details": "Set up conditional routing and button responses",
      "timeline": "Day 2-3",
      "responsible": "Tech Team"
    }},
    {{
      "step": 4,
      "action": "Test Campaign",
      "details": "Send to 10 test farmers and verify personalization",
      "timeline": "Day 3",
      "responsible": "QA Team"
    }},
    {{
      "step": 5,
      "action": "Launch to Segment",
      "details": "Roll out to all {len(matched_farmers)} farmers",
      "timeline": "Day 4",
      "responsible": "Marketing"
    }}
  ],
  "revenue_breakdown": {{
    "per_farmer_value": "₹5,000",
    "total_potential": "₹{len(matched_farmers) * 5000}",
    "conversion_assumptions": "Based on segment characteristics",
    "calculation_basis": "Historical data + segment behavior"
  }}
}}

Be EXTREMELY thorough. Generate COMPLETE, ACTIONABLE content that can be used immediately.
Generate ONLY valid JSON.
"""
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Error generating detailed segment analysis: {e}")
        return {
            'error': str(e),
            'stage_distribution': {'breakdown': [], 'key_insights': ['Error generating analysis']},
            'template_requirements': [],
            'flow_creation_prompts': []
        }

# Add template name registry for consistency
TEMPLATE_NAME_REGISTRY = {}

def _store_template_names(analysis_result):
    """Store template names from analysis for future consistency"""
    global TEMPLATE_NAME_REGISTRY
    
    for segment in analysis_result.get('segments', []):
        flow_strategy = segment.get('whatsapp_flow_strategy', {})
        for step in flow_strategy.get('steps', []):
            template_name = step.get('template_name_required')
            if template_name:
                segment_key = segment['segment_id']
                TEMPLATE_NAME_REGISTRY[segment_key] = template_name


def _get_stored_template_name(segment_id):
    """Retrieve previously stored template name"""
    return TEMPLATE_NAME_REGISTRY.get(segment_id)


# ENHANCED: Include intervention context in segment matching
def get_farmers_for_segment(segment_data, farmer_data):
    """
    Enhanced to match farmers based on intervention patterns
    """
    segment_name = segment_data['segment_name'].lower()
    matched_farmers = []
    
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    
    for farmer in farmer_data['farmers']:
        farmer_interventions = [
            i for i in farmer_data['interventions']
            if i.get('farmer_id') == farmer['farmer_id']
        ]
        
        recent_farmer_interventions = [
            i for i in farmer_interventions
            if i.get('intervention_date') and i['intervention_date'] >= thirty_days_ago
        ]
        
        # Pre-Harvest matching
        if 'harvest' in segment_name or 'pre-harvest' in segment_name:
            for crop in farmer_data['crop_details']:
                if crop.get('farmer_id') == farmer['farmer_id']:
                    days_until = crop.get('days_until_harvest')
                    if days_until and 7 <= days_until <= 30:
                        # Add intervention context
                        last_intervention = recent_farmer_interventions[0] if recent_farmer_interventions else None
                        matched_farmers.append({
                            'farmer_id': farmer['farmer_id'],
                            'farmer_name': farmer['name'],
                            'phone_number': farmer['phone_number'],
                            'farm_size': farmer['farm_size'],
                            'crop_name': crop['crop_name'],
                            'current_stage': crop.get('current_growth_stage'),
                            'days_until_harvest': days_until,
                            'harvesting_date': crop.get('harvesting_date'),
                            'last_intervention': last_intervention.get('intervention_type') if last_intervention else 'None',
                            'last_intervention_date': last_intervention.get('intervention_date') if last_intervention else None,
                            'total_interventions': len(farmer_interventions),
                            'match_reason': f"Harvesting {crop['crop_name']} in {days_until} days | {len(recent_farmer_interventions)} interventions in 30 days"
                        })
                        break
        
        # Fertilizer Upsell
        elif 'fertilizer' in segment_name:
            for crop in farmer_data['crop_details']:
                if crop.get('farmer_id') == farmer['farmer_id']:
                    stage = crop.get('current_growth_stage')
                    if stage in ['Vegetative', 'Flowering', 'Fruiting']:
                        fertilizer_interventions = [i for i in farmer_interventions if i.get('intervention_type') == 'Fertilizer']
                        last_fertilizer = fertilizer_interventions[-1] if fertilizer_interventions else None
                        
                        matched_farmers.append({
                            'farmer_id': farmer['farmer_id'],
                            'farmer_name': farmer['name'],
                            'phone_number': farmer['phone_number'],
                            'farm_size': farmer['farm_size'],
                            'crop_name': crop['crop_name'],
                            'current_stage': stage,
                            'last_fertilizer_used': last_fertilizer.get('product_used') if last_fertilizer else 'None',
                            'last_fertilizer_cost': last_fertilizer.get('price_cost') if last_fertilizer else 0,
                            'total_interventions': len(farmer_interventions),
                            'match_reason': f"{crop['crop_name']} at {stage} | Last fertilizer: {last_fertilizer.get('activity_name') if last_fertilizer else 'Never used'}"
                        })
                        break
        
        # Pesticide Service
        elif 'pesticide' in segment_name or 'pest' in segment_name:
            for crop in farmer_data['crop_details']:
                if crop.get('farmer_id') == farmer['farmer_id']:
                    stage = crop.get('current_growth_stage')
                    if stage in ['Flowering', 'Fruiting']:
                        pesticide_interventions = [i for i in farmer_interventions if i.get('intervention_type') == 'Pesticide']
                        last_pesticide = pesticide_interventions[-1] if pesticide_interventions else None
                        
                        matched_farmers.append({
                            'farmer_id': farmer['farmer_id'],
                            'farmer_name': farmer['name'],
                            'phone_number': farmer['phone_number'],
                            'farm_size': farmer['farm_size'],
                            'crop_name': crop['crop_name'],
                            'current_stage': stage,
                            'last_pesticide_used': last_pesticide.get('product_used') if last_pesticide else 'None',
                            'days_since_pesticide': (datetime.now().date() - last_pesticide['intervention_date']).days if last_pesticide and last_pesticide.get('intervention_date') else 999,
                            'total_interventions': len(farmer_interventions),
                            'match_reason': f"{crop['crop_name']} at {stage} | Pest control needed"
                        })
                        break
        
        # Inactive Farmers
        elif 'inactive' in segment_name:
            if len(recent_farmer_interventions) == 0 and farmer.get('crop_name'):
                matched_farmers.append({
                    'farmer_id': farmer['farmer_id'],
                    'farmer_name': farmer['name'],
                    'phone_number': farmer['phone_number'],
                    'farm_size': farmer['farm_size'],
                    'crop_name': farmer.get('crop_name'),
                    'last_intervention_date': farmer_interventions[-1].get('intervention_date') if farmer_interventions else 'Never',
                    'days_inactive': (datetime.now().date() - farmer_interventions[-1]['intervention_date']).days if farmer_interventions and farmer_interventions[-1].get('intervention_date') else 999,
                    'total_interventions': len(farmer_interventions),
                    'match_reason': f"No interventions in 30+ days | Last activity: {farmer_interventions[-1].get('intervention_type') if farmer_interventions else 'Never'}"
                })
        
        # High-Value Customers
        elif 'high-value' in segment_name or 'premium' in segment_name:
            if len(farmer_interventions) >= 3:
                avg_cost = sum([float(i.get('price_cost', 0)) for i in farmer_interventions]) / len(farmer_interventions)
                if avg_cost > 500:
                    matched_farmers.append({
                        'farmer_id': farmer['farmer_id'],
                        'farmer_name': farmer['name'],
                        'phone_number': farmer['phone_number'],
                        'farm_size': farmer['farm_size'],
                        'crop_name': farmer.get('crop_name'),
                        'total_interventions': len(farmer_interventions),
                        'avg_intervention_cost': round(avg_cost, 2),
                        'total_spend': round(sum([float(i.get('price_cost', 0)) for i in farmer_interventions]), 2),
                        'most_used_service': max(set([i.get('intervention_type') for i in farmer_interventions]), key=[i.get('intervention_type') for i in farmer_interventions].count),
                        'match_reason': f"High-value customer | Avg spend: ₹{round(avg_cost, 2)} | {len(farmer_interventions)} interventions"
                    })
        
        # Continue with other segment types...
        elif 'next crop' in segment_name:
            if farmer.get('next_crop_recommendation'):
                matched_farmers.append({
                    'farmer_id': farmer['farmer_id'],
                    'farmer_name': farmer['name'],
                    'phone_number': farmer['phone_number'],
                    'farm_size': farmer['farm_size'],
                    'crop_name': farmer.get('crop_name'),
                    'next_crop_recommendation': farmer['next_crop_recommendation'],
                    'soil_improvement_tip': farmer.get('soil_improvement_tip'),
                    'total_interventions': len(farmer_interventions),
                    'match_reason': f"Ready for next crop: {farmer['next_crop_recommendation']}"
                })
    
    # Remove duplicates
    seen = set()
    unique_farmers = []
    for f in matched_farmers:
        if f['farmer_id'] not in seen:
            seen.add(f['farmer_id'])
            unique_farmers.append(f)
    
    return unique_farmers[:100]



@csrf_exempt
def check_existing_templates_view(request):
    """
    API to check which templates exist in WhatsApp
    """
    if request.method == 'GET':
        try:
            templates = get_existing_whatsapp_templates()
            return JsonResponse({
                'status': 'success',
                'total_templates': len(templates),
                'templates': templates
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

# --- API Views ---
# Add these imports at the top of your views file
from django.core.cache import cache
from datetime import datetime, timedelta
import hashlib

# Add this helper function to cache AI results
def get_cached_analysis_key():
    """Generate a cache key for AI analysis"""
    return 'farmer_ai_analysis_cache'

def get_cached_analysis():
    """Get cached AI analysis if available and not expired"""
    cache_key = get_cached_analysis_key()
    cached_data = cache.get(cache_key)
    
    if cached_data:
        # Check if cache is less than 24 hours old
        cache_time = cached_data.get('cached_at')
        if cache_time:
            cache_age = datetime.now() - datetime.fromisoformat(cache_time)
            if cache_age < timedelta(hours=24):
                return cached_data.get('data')
    
    return None

def set_cached_analysis(analysis_data):
    """Cache AI analysis for 24 hours"""
    cache_key = get_cached_analysis_key()
    cache_data = {
        'data': analysis_data,
        'cached_at': datetime.now().isoformat()
    }
    # Cache for 24 hours
    cache.set(cache_key, cache_data, 60 * 60 * 24)

def clear_analysis_cache():
    """Clear the cached analysis"""
    cache_key = get_cached_analysis_key()
    cache.delete(cache_key)


# REPLACE your existing auto_analyze_farmers_view with this:
@csrf_exempt
def auto_analyze_farmers_view(request):
    """
    Automatically analyzes all farmer data and provides actionable insights
    with recommended flows and conversion strategies.
    NOW WITH CACHING to avoid quota issues.
    """
    if request.method == 'POST':
        try:
            # Check if force_refresh is requested
            force_refresh = request.POST.get('force_refresh', 'false').lower() == 'true'
            
            # Try to get cached analysis first
            if not force_refresh:
                cached_analysis = get_cached_analysis()
                if cached_analysis:
                    return JsonResponse({
                        'status': 'success',
                        'from_cache': True,
                        'cached_at': cache.get(get_cached_analysis_key()).get('cached_at'),
                        'analysis': cached_analysis.get('analysis'),
                        'flow_prompts': cached_analysis.get('flow_prompts'),
                        'raw_data_summary': cached_analysis.get('raw_data_summary')
                    })
            
            # Get comprehensive farmer data
            farmer_data = get_comprehensive_farmer_data()
            
            if not farmer_data['farmers']:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No farmer data found in database'
                }, status=404)
            
            # Perform AI analysis
            try:
                analysis_result = analyze_farmer_segments_with_ai(farmer_data)
            except Exception as ai_error:
                error_msg = str(ai_error)
                
                # Check if it's a quota error
                if '429' in error_msg or 'quota' in error_msg.lower():
                    # Return cached data if available, even if expired
                    cached_data = cache.get(get_cached_analysis_key())
                    if cached_data:
                        return JsonResponse({
                            'status': 'warning',
                            'message': 'API quota exceeded. Showing cached data from: ' + cached_data.get('cached_at'),
                            'from_cache': True,
                            'cached_at': cached_data.get('cached_at'),
                            'analysis': cached_data.get('data', {}).get('analysis'),
                            'flow_prompts': cached_data.get('data', {}).get('flow_prompts'),
                            'raw_data_summary': cached_data.get('data', {}).get('raw_data_summary'),
                            'quota_info': {
                                'quota_exceeded': True,
                                'retry_message': 'Please try again in a few hours or tomorrow',
                                'suggestion': 'Using cached analysis from today'
                            }
                        })
                    else:
                        return JsonResponse({
                            'status': 'error',
                            'message': 'API quota exceeded and no cached data available. Please try again tomorrow.',
                            'quota_info': {
                                'quota_exceeded': True,
                                'retry_message': 'Gemini API free tier limit: 50 requests/day reached',
                                'suggestion': 'Come back tomorrow or upgrade to paid tier'
                            }
                        }, status=429)
                
                # Other AI errors
                raise ai_error
            
            if not analysis_result:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Failed to analyze farmer data'
                }, status=500)
            
            # Generate ready-to-use flow prompts
            try:
                flow_prompts = generate_flow_prompts_from_segments(analysis_result)
            except Exception as prompt_error:
                error_msg = str(prompt_error)
                if '429' in error_msg or 'quota' in error_msg.lower():
                    # Still return analysis even if prompts fail
                    flow_prompts = {'flow_prompts': [], 'error': 'Quota exceeded for prompts'}
                else:
                    raise prompt_error
            
            result_data = {
                'analysis': analysis_result,
                'flow_prompts': flow_prompts,
                'raw_data_summary': {
                    'total_farmers': len(farmer_data['farmers']),
                    'total_crops': len(farmer_data['crop_details']),
                    'total_interventions': len(farmer_data['interventions'])
                }
            }
            
            # Cache the successful result
            set_cached_analysis(result_data)
            
            return JsonResponse({
                'status': 'success',
                'from_cache': False,
                'cached_at': datetime.now().isoformat(),
                **result_data
            })
            
        except Exception as e:
            import traceback
            print(f"Analysis failed: {e}")
            print(traceback.format_exc())
            return JsonResponse({
                'status': 'error',
                'message': f"Analysis failed: {str(e)}"
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


# ADD this new view to manually refresh cache
@csrf_exempt
def refresh_analysis_cache_view(request):
    """
    Manually refresh the AI analysis cache.
    Use this sparingly to avoid quota issues.
    """
    if request.method == 'POST':
        try:
            # Clear existing cache
            clear_analysis_cache()
            
            # Get fresh data
            farmer_data = get_comprehensive_farmer_data()
            
            if not farmer_data['farmers']:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No farmer data found in database'
                }, status=404)
            
            # Perform AI analysis
            try:
                analysis_result = analyze_farmer_segments_with_ai(farmer_data)
            except Exception as ai_error:
                error_msg = str(ai_error)
                if '429' in error_msg or 'quota' in error_msg.lower():
                    return JsonResponse({
                        'status': 'error',
                        'message': 'API quota exceeded. Cannot refresh now.',
                        'quota_info': {
                            'quota_exceeded': True,
                            'retry_message': 'Please try again tomorrow',
                            'daily_limit': '50 requests per day (free tier)'
                        }
                    }, status=429)
                raise ai_error
            
            if not analysis_result:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Failed to analyze farmer data'
                }, status=500)
            
            # Generate flow prompts
            flow_prompts = generate_flow_prompts_from_segments(analysis_result)
            
            result_data = {
                'analysis': analysis_result,
                'flow_prompts': flow_prompts,
                'raw_data_summary': {
                    'total_farmers': len(farmer_data['farmers']),
                    'total_crops': len(farmer_data['crop_details']),
                    'total_interventions': len(farmer_data['interventions'])
                }
            }
            
            # Cache the result
            set_cached_analysis(result_data)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Analysis cache refreshed successfully',
                'cached_at': datetime.now().isoformat(),
                **result_data
            })
            
        except Exception as e:
            import traceback
            print(f"Refresh failed: {e}")
            print(traceback.format_exc())
            return JsonResponse({
                'status': 'error',
                'message': f"Refresh failed: {str(e)}"
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


# ADD this view to check cache status
@csrf_exempt
def get_cache_status_view(request):
    """
    Get information about the current cache status
    """
    if request.method == 'GET':
        cache_key = get_cached_analysis_key()
        cached_data = cache.get(cache_key)
        
        if cached_data:
            cache_time = datetime.fromisoformat(cached_data.get('cached_at'))
            cache_age = datetime.now() - cache_time
            
            return JsonResponse({
                'status': 'success',
                'has_cache': True,
                'cached_at': cached_data.get('cached_at'),
                'cache_age_hours': cache_age.total_seconds() / 3600,
                'cache_valid': cache_age < timedelta(hours=24),
                'expires_in_hours': max(0, 24 - (cache_age.total_seconds() / 3600))
            })
        else:
            return JsonResponse({
                'status': 'success',
                'has_cache': False,
                'message': 'No cached analysis available'
            })
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def get_segment_details_view(request):
    """
    Get detailed information about a specific farmer segment
    OPTIMIZED: Uses cached analysis instead of regenerating
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            segment_id = data.get('segment_id')
            
            if not segment_id:
                return JsonResponse({'error': 'Segment ID not provided'}, status=400)
            
            # Try to get cached analysis first
            cached_analysis = get_cached_analysis()
            
            if not cached_analysis:
                # If no cache, get fresh data
                farmer_data = get_comprehensive_farmer_data()
                
                if not farmer_data['farmers']:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'No farmer data found'
                    }, status=404)
                
                try:
                    analysis_result = analyze_farmer_segments_with_ai(farmer_data)
                except Exception as e:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Analysis failed: {str(e)}'
                    }, status=500)
                
                if not analysis_result:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Failed to analyze data'
                    }, status=500)
            else:
                # Use cached analysis
                analysis_result = cached_analysis.get('analysis')
                farmer_data = get_comprehensive_farmer_data()  # Get fresh farmer data for matching
            
            # Find specific segment
            target_segment = None
            for segment in analysis_result.get('segments', []):
                if segment['segment_id'] == segment_id:
                    target_segment = segment
                    break
            
            if not target_segment:
                return JsonResponse({'error': 'Segment not found'}, status=404)
            
            # Get detailed analysis for this segment
            # Use cached if available
            cache_key = f'segment_details_{segment_id}'
            cached_details = cache.get(cache_key)
            
            if cached_details:
                segment_details = cached_details
            else:
                try:
                    segment_details = generate_detailed_segment_analysis(
                        segment=target_segment,
                        farmer_data=farmer_data
                    )
                    # Cache for 6 hours
                    cache.set(cache_key, segment_details, 60 * 60 * 6)
                except Exception as e:
                    print(f"Error generating segment details: {e}")
                    segment_details = {
                        'error': 'Could not generate detailed analysis',
                        'message': str(e)
                    }
            
            return JsonResponse({
                'status': 'success',
                'segment': target_segment,
                'detailed_analysis': segment_details
            })
            
        except Exception as e:
            import traceback
            print(f"Error in get_segment_details_view: {e}")
            print(traceback.format_exc())
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def get_segment_farmers_view(request):
    """
    Returns the actual farmer list for a specific segment
    OPTIMIZED: Uses cached analysis, only fetches fresh farmer data
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            segment_id = data.get('segment_id')
            
            if not segment_id:
                return JsonResponse({'error': 'Segment ID not provided'}, status=400)
            
            # Get all farmer data
            farmer_data = get_comprehensive_farmer_data()
            
            if not farmer_data['farmers']:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No farmer data found'
                }, status=404)
            
            # Try to get cached analysis
            cached_analysis = get_cached_analysis()
            
            if not cached_analysis:
                # If no cache, generate new analysis
                try:
                    analysis_result = analyze_farmer_segments_with_ai(farmer_data)
                except Exception as e:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Analysis failed: {str(e)}'
                    }, status=500)
                
                if not analysis_result:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Failed to analyze data'
                    }, status=500)
            else:
                # Use cached analysis
                analysis_result = cached_analysis.get('analysis')
            
            # Find the segment
            target_segment = None
            for segment in analysis_result.get('segments', []):
                if segment['segment_id'] == segment_id:
                    target_segment = segment
                    break
            
            if not target_segment:
                return JsonResponse({'error': 'Segment not found'}, status=404)
            
            # Check if farmers are cached for this segment
            farmers_cache_key = f'segment_farmers_{segment_id}'
            cached_farmers = cache.get(farmers_cache_key)
            
            if cached_farmers:
                farmers = cached_farmers
            else:
                # Get matched farmers
                farmers = get_farmers_for_segment(target_segment, farmer_data)
                # Cache for 1 hour
                cache.set(farmers_cache_key, farmers, 60 * 60)
            
            return JsonResponse({
                'status': 'success',
                'segment_name': target_segment['segment_name'],
                'total_farmers': len(farmers),
                'farmers': farmers
            })
            
        except Exception as e:
            import traceback
            print(f"Error in get_segment_farmers_view: {e}")
            print(traceback.format_exc())
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)
# def generate_detailed_segment_analysis(segment, farmer_data):
#     """
#     Generates HIGHLY PERSONALIZED analysis with templates that use ALL available farmer data
#     """
#     try:
#         model = genai.GenerativeModel('gemini-2.0-flash-exp')
#     except:
#         model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
#     # Get matched farmers for this segment
#     matched_farmers = get_farmers_for_segment(segment, farmer_data)
    
#     # Extract ALL available personalization data
#     available_farmer_fields = set()
#     available_crop_fields = set()
#     available_intervention_fields = set()
    
#     for farmer in matched_farmers[:10]:  # Sample first 10
#         available_farmer_fields.update(farmer.keys())
    
#     for crop in farmer_data['crop_details'][:10]:
#         available_crop_fields.update(crop.keys())
    
#     for intervention in farmer_data['interventions'][:10]:
#         available_intervention_fields.update(intervention.keys())
    
#     # Create sample personalization data
#     sample_farmer = matched_farmers[0] if matched_farmers else {}
    
#     prompt = f"""
# You are creating HIGHLY PERSONALIZED WhatsApp templates for a farmer engagement platform.

# CRITICAL REQUIREMENT: Make templates feel like they're written SPECIFICALLY for each individual farmer using their ACTUAL DATA.

# ⚠️ IMPORTANT: This is a DYNAMIC system. New segments can emerge based on:
# - New crops added to the system
# - New intervention types farmers start using
# - Seasonal patterns we haven't seen before
# - New business opportunities identified
# - Changing farmer behavior patterns

# DO NOT limit yourself to pre-defined segments. CREATE NEW SEGMENTS AND TEMPLATES as needed based on the data patterns you see.

# SEGMENT INFORMATION:
# {json.dumps(segment, indent=2, default=str)}

# AVAILABLE PERSONALIZATION FIELDS (USE THESE!):
# FARMER DATA: {list(available_farmer_fields)}
# CROP DATA: {list(available_crop_fields)}  
# INTERVENTION DATA: {list(available_intervention_fields)}

# SAMPLE FARMERS IN THIS SEGMENT (for context):
# {json.dumps(matched_farmers[:3], indent=2, default=str)}

# TOTAL FARMERS IN SEGMENT: {len(matched_farmers)}

# PERSONALIZATION REQUIREMENTS:
# 1. ALWAYS use farmer's name - makes it feel personal
# 2. Reference their SPECIFIC crop name - shows we know them
# 3. Use their farm size if relevant - adds context
# 4. Reference their LAST intervention (type, product used, date) - proves we're paying attention
# 5. Mention days since last activity - creates urgency
# 6. Use growth stage data - shows we understand their timeline
# 7. Reference specific products they've used before - familiarity builds trust
# 8. Include their intervention cost patterns - relevant offers
# 9. Use their phone number for follow-up context
# 10. Reference match_reason to explain WHY they're getting this message

# 🔄 DYNAMIC TEMPLATE CREATION GUIDELINES:
# - If you see a NEW crop type (e.g., Strawberry, Dragon Fruit, Mushroom), create crop-specific templates
# - If you see a NEW intervention pattern (e.g., "Drip Irrigation Setup", "Greenhouse Maintenance"), create service-specific templates
# - If you see SEASONAL patterns (e.g., all farmers planting in same month), create seasonal campaign templates
# - If you see COST patterns (e.g., farmers spending >₹10k on interventions), create premium service templates
# - If you see NEGLECT patterns (e.g., farmers not doing required interventions), create reminder/education templates
# - If you see UPSELL opportunities (e.g., farmers using basic products but could upgrade), create upgrade templates
# - If you see CROSS-SELL opportunities (e.g., farmers using fertilizer but not pesticide), create bundle templates

# TEMPLATE NAMING CONVENTION (STRICTLY FOLLOW):
# - Format: {segment_type}_{action}_{language}
# - Examples: 
#   * "strawberry_drip_irrigation_hi" (NEW crop + NEW service)
#   * "premium_organic_upsell_en" (NEW customer segment)
#   * "monsoon_seeding_reminder_hi" (SEASONAL opportunity)
#   * "greenhouse_tomato_expert_hi" (SPECIALIZED crop method)
#   * "dormant_farmer_reactivation_hi" (BEHAVIORAL pattern)
  
# ALWAYS CREATE UNIQUE TEMPLATE NAMES FOR NEW PATTERNS!

# TEMPLATE PERSONALIZATION EXAMPLES:

# ❌ BAD (Generic):
# "नमस्कार, आपकी फसल की कटाई जल्द है। मजदूर चाहिए?"

# ✅ GOOD (Personalized):
# "नमस्कार {{{{farmer_name}}}}, 
# आपकी {{{{farm_size}}}} एकड़ की {{{{crop_name}}}} फसल अब {{{{current_stage}}}} में है। 
# {{{{days_until_harvest}}}} दिनों में कटाई होगी!

# पिछली बार {{{{last_intervention_date}}}} को {{{{last_intervention}}}} किया था। 
# अब कटाई के लिए {{{{estimated_workers}}}} मजदूर चाहिए।

# ✅ अनुभवी टीम
# ✅ ₹{{{{estimated_labor_cost}}}} (आपके {{{{farm_size}}}} एकड़ के लिए)
# ✅ {{{{harvest_date}}}} को तैयार

# अभी बुक करें!"

# YOUR TASK:
# Generate templates with MAXIMUM personalization using ALL available data fields.

# OUTPUT FORMAT (JSON):
# {{
#   "stage_distribution": {{
#     "breakdown": [
#       {{
#         "stage": "Fruiting",
#         "percentage": 65,
#         "farmer_count": 295,
#         "urgency": "HIGH",
#         "action_needed": "Contact for labor booking"
#       }}
#     ],
#     "key_insights": ["insight1", "insight2"]
#   }},
#   "template_requirements": [
#     {{
#       "template_name": "pre_harvest_labor_booking_hi",
#       "likely_exists": false,
#       "template_type": "UTILITY",
#       "language": "hi",
#       "priority": "HIGH",
#       "personalization_level": "VERY_HIGH",
#       "body_text": "नमस्कार {{{{1}}}},\\n\\nआपकी {{{{2}}}} एकड़ की {{{{3}}}} फसल अब {{{{4}}}} स्टेज में है। {{{{5}}}} दिनों में कटाई होगी! 🌾\\n\\nपिछली बार {{{{6}}}} को {{{{7}}}} किया था ({{{{8}}}})।\\nअब कटाई के लिए तैयारी का समय!\\n\\n✅ {{{{9}}}} अनुभवी मजदूर\\n✅ अनुमानित लागत: ₹{{{{10}}}}\\n✅ {{{{11}}}} को कटाई\\n\\nअभी बुक करें! 👇",
#       "variables": [
#         {{
#           "position": "{{{{1}}}}",
#           "field_name": "farmer_name",
#           "data_source": "registration_farmer.farmer_name",
#           "example": "रमेश पाटील",
#           "why_personalized": "Makes farmer feel recognized"
#         }},
#         {{
#           "position": "{{{{2}}}}",
#           "field_name": "farm_size",
#           "data_source": "registration_farmer.farm_size_acres",
#           "example": "3.5",
#           "why_personalized": "Shows we know their farm details"
#         }},
#         {{
#           "position": "{{{{3}}}}",
#           "field_name": "crop_name",
#           "data_source": "registration_cropdetails.crop_name",
#           "example": "अंगूर",
#           "why_personalized": "Specific to their crop"
#         }},
#         {{
#           "position": "{{{{4}}}}",
#           "field_name": "current_stage",
#           "data_source": "registration_cropdetails.current_growth_stage (calculated)",
#           "example": "Fruiting",
#           "why_personalized": "Shows real-time crop monitoring"
#         }},
#         {{
#           "position": "{{{{5}}}}",
#           "field_name": "days_until_harvest",
#           "data_source": "registration_cropdetails.harvesting_date - CURRENT_DATE",
#           "example": "7",
#           "why_personalized": "Creates urgency with exact timeline"
#         }},
#         {{
#           "position": "{{{{6}}}}",
#           "field_name": "last_intervention_date",
#           "data_source": "registration_intervention.date (most recent)",
#           "example": "15 सितंबर",
#           "why_personalized": "Proves we track their activities"
#         }},
#         {{
#           "position": "{{{{7}}}}",
#           "field_name": "last_intervention_type",
#           "data_source": "registration_intervention.intervention_type",
#           "example": "Pesticide स्प्रे",
#           "why_personalized": "References their specific farming actions"
#         }},
#         {{
#           "position": "{{{{8}}}}",
#           "field_name": "product_used",
#           "data_source": "registration_intervention.product_used",
#           "example": "Bayer Confidor",
#           "why_personalized": "Shows we remember products they use"
#         }},
#         {{
#           "position": "{{{{9}}}}",
#           "field_name": "estimated_workers",
#           "data_source": "CALCULATED: farm_size_acres * 3 (workers per acre)",
#           "example": "10-12",
#           "why_personalized": "Customized to their farm size"
#         }},
#         {{
#           "position": "{{{{10}}}}",
#           "field_name": "estimated_labor_cost",
#           "data_source": "CALCULATED: farm_size_acres * avg_cost_per_acre (₹5000)",
#           "example": "17,500",
#           "why_personalized": "Budget-relevant pricing"
#         }},
#         {{
#           "position": "{{{{11}}}}",
#           "field_name": "harvest_date",
#           "data_source": "registration_cropdetails.harvesting_date",
#           "example": "25 अक्टूबर",
#           "why_personalized": "Exact date for planning"
#         }}
#       ],
#       "buttons": [
#         {{"type": "QUICK_REPLY", "text": "{{{{estimated_workers}}}} मजदूर बुक करें"}},
#         {{"type": "QUICK_REPLY", "text": "बाद में बात करें"}}
#       ],
#       "usage_context": "Send to farmers 7-14 days before harvest who have recent intervention history",
#       "personalization_impact": "89% higher engagement vs generic templates",
#       "data_requirements": [
#         "farmer_name (REQUIRED)",
#         "farm_size_acres (REQUIRED)", 
#         "crop_name (REQUIRED)",
#         "current_growth_stage (REQUIRED)",
#         "days_until_harvest (REQUIRED)",
#         "last_intervention_date (OPTIONAL - fallback: 'आपकी पिछली गतिविधि')",
#         "last_intervention_type (OPTIONAL)",
#         "product_used (OPTIONAL)"
#       ]
#     }},
#     {{
#       "template_name": "fertilizer_upsell_personalized_hi",
#       "likely_exists": false,
#       "template_type": "MARKETING",
#       "language": "hi",
#       "priority": "HIGH",
#       "personalization_level": "VERY_HIGH",
#       "body_text": "नमस्कार {{{{1}}}},\\n\\nआपकी {{{{2}}}} फसल अब {{{{3}}}} स्टेज में है! 🌱\\n\\nपिछली बार {{{{4}}}} दिन पहले {{{{5}}}} यूज़ किया था ({{{{6}}}})।\\n\\nअब आपकी फसल को चाहिए:\\n✅ {{{{7}}}} - ₹{{{{8}}}}/किलो\\n✅ आपके {{{{9}}}} एकड़ के लिए: {{{{10}}}} किलो\\n✅ अनुमानित फायदा: {{{{11}}}}% ज्यादा उपज\\n\\n⏰ अगले {{{{12}}}} दिनों में देना जरूरी!\\n\\nविशेष ऑफर सिर्फ आपके लिए:\\n💰 {{{{13}}}}% छूट\\n🚚 फ्री डिलीवरी\\n\\nअभी ऑर्डर करें! 👇",
#       "variables": [
#         {{
#           "position": "{{{{1}}}}",
#           "field_name": "farmer_name",
#           "data_source": "registration_farmer.farmer_name",
#           "example": "सुरेश पाटिल",
#           "why_personalized": "Personal greeting"
#         }},
#         {{
#           "position": "{{{{2}}}}",
#           "field_name": "crop_name",
#           "data_source": "registration_cropdetails.crop_name",
#           "example": "टमाटर",
#           "why_personalized": "Crop-specific messaging"
#         }},
#         {{
#           "position": "{{{{3}}}}",
#           "field_name": "current_stage",
#           "data_source": "registration_cropdetails.current_growth_stage",
#           "example": "Flowering",
#           "why_personalized": "Stage-appropriate product recommendation"
#         }},
#         {{
#           "position": "{{{{4}}}}",
#           "field_name": "days_since_last_fertilizer",
#           "data_source": "CURRENT_DATE - registration_intervention.date (WHERE type=Fertilizer)",
#           "example": "21",
#           "why_personalized": "Shows we track their fertilizer schedule"
#         }},
#         {{
#           "position": "{{{{5}}}}",
#           "field_name": "last_fertilizer_type",
#           "data_source": "registration_intervention.activity_name (type=Fertilizer)",
#           "example": "DAP",
#           "why_personalized": "References their preferred fertilizer"
#         }},
#         {{
#           "position": "{{{{6}}}}",
#           "field_name": "last_product_brand",
#           "data_source": "registration_intervention.product_catalog_brand",
#           "example": "IFFCO",
#           "why_personalized": "Brand familiarity"
#         }},
#         {{
#           "position": "{{{{7}}}}",
#           "field_name": "recommended_fertilizer",
#           "data_source": "AI LOGIC: Based on crop + stage (e.g., Flowering = NPK 19:19:19)",
#           "example": "NPK 19:19:19",
#           "why_personalized": "Stage-specific recommendation"
#         }},
#         {{
#           "position": "{{{{8}}}}",
#           "field_name": "price_per_kg",
#           "data_source": "Product catalog price",
#           "example": "45",
#           "why_personalized": "Transparent pricing"
#         }},
#         {{
#           "position": "{{{{9}}}}",
#           "field_name": "farm_size",
#           "data_source": "registration_farmer.farm_size_acres",
#           "example": "2.5",
#           "why_personalized": "Exact farm size"
#         }},
#         {{
#           "position": "{{{{10}}}}",
#           "field_name": "required_quantity",
#           "data_source": "CALCULATED: farm_size_acres * 25 kg/acre",
#           "example": "62.5",
#           "why_personalized": "Custom quantity for their farm"
#         }},
#         {{
#           "position": "{{{{11}}}}",
#           "field_name": "expected_yield_increase",
#           "data_source": "CALCULATED: Based on crop + fertilizer (15-25%)",
#           "example": "18",
#           "why_personalized": "Specific benefit projection"
#         }},
#         {{
#           "position": "{{{{12}}}}",
#           "field_name": "optimal_application_window",
#           "data_source": "CALCULATED: Days before next growth stage",
#           "example": "5",
#           "why_personalized": "Creates urgency with timeline"
#         }},
#         {{
#           "position": "{{{{13}}}}",
#           "field_name": "discount_percentage",
#           "data_source": "SEGMENTATION: High-value customers = 15%, Regular = 10%",
#           "example": "15",
#           "why_personalized": "Loyalty-based pricing"
#         }}
#       ],
#       "buttons": [
#         {{"type": "QUICK_REPLY", "text": "{{{{required_quantity}}}} किलो ऑर्डर करें"}},
#         {{"type": "QUICK_REPLY", "text": "एक्सपर्ट से बात करें"}},
#         {{"type": "QUICK_REPLY", "text": "बाद में याद दिलाएं"}}
#       ],
#       "usage_context": "Send to farmers at Flowering/Fruiting stage who haven't used fertilizer in 20+ days",
#       "personalization_impact": "76% higher conversion vs generic fertilizer ads"
#     }}
#   ],
#   "flow_creation_prompts": [
#     {{
#       "prompt_id": "labor_booking_flow_v2",
#       "prompt_title": "Hyper-Personalized Pre-Harvest Labor Booking Flow",
#       "complete_prompt": "Create a WhatsApp flow for farmers harvesting in 7-14 days with the following specifications:\\n\\nTARGET AUDIENCE:\\n- Farmers with crops at Fruiting/Ready for Harvest stage\\n- Farm size: 1-10 acres\\n- Located within serviceable area\\n- Have active intervention history (proves engagement)\\n\\nPERSONALIZATION DATA TO USE:\\n1. Farmer name (registration_farmer.farmer_name)\\n2. Crop name (registration_cropdetails.crop_name)\\n3. Farm size (registration_farmer.farm_size_acres)\\n4. Days until harvest (calculated from harvesting_date)\\n5. Current growth stage\\n6. Last intervention date and type\\n7. Product last used\\n8. Estimated workers needed (farm_size * 3)\\n9. Estimated cost (farm_size * ₹5000)\\n10. Harvest date\\n\\nFLOW STEPS:\\n\\nStep 1: Initial Outreach (Template: pre_harvest_labor_booking_hi)\\n- Use ALL personalization variables\\n- Reference their last intervention to build trust\\n- Show exact timeline (X days to harvest)\\n- Display calculated workers & cost for their farm size\\n- Include crop-specific emoji\\n- Buttons: 'मजदूर बुक करें' | 'बाद में बात करें'\\n\\nStep 2: If interested (Template: labor_details_collection_hi)\\n- Ask for confirmation of harvest date\\n- Confirm number of workers needed\\n- Ask for any special requirements\\n- Reference their crop type for specialized labor\\n- Buttons: 'पक्का बुक करें' | 'डिटेल्स बदलें'\\n\\nStep 3: Confirmation (Template: labor_booking_confirmed_hi)\\n- Thank them with their name\\n- Show booking details: Date, Workers, Cost\\n- Mention their crop name\\n- Provide contact number\\n- Set expectations\\n- Button: 'मदद चाहिए'\\n\\nSUCCESS METRICS:\\n- 35% conversion from Step 1 to Step 2\\n- 80% conversion from Step 2 to Step 3\\n- Overall 28% booking rate\\n- ₹5000 avg order value\\n\\nIMPLEMENTATION NOTES:\\n- Send 10-12 days before harvest\\n- Follow up if no response in 48 hours\\n- Track response patterns by crop type\\n- A/B test different discount offers",
#       "required_templates": ["pre_harvest_labor_booking_hi", "labor_details_collection_hi", "labor_booking_confirmed_hi"],
#       "expected_outcome": "28% conversion to labor booking, ₹5000 AOV",
#       "implementation_notes": [
#         "Check if templates exist first",
#         "Test with 10 farmers in target segment",
#         "Monitor response rates by crop type",
#         "Scale to full segment after 72 hours"
#       ]
#     }}
#   ],
#   "implementation_checklist": [
#     {{
#       "step": 1,
#       "action": "Verify/Create Required Templates",
#       "details": "Check if pre_harvest_labor_booking_hi exists, if not create it with all {len(matched_farmers[:1][0].keys() if matched_farmers else [])} personalization variables",
#       "timeline": "Day 1",
#       "responsible": "Admin",
#       "dependencies": "WhatsApp Business API access"
#     }},
#     {{
#       "step": 2,
#       "action": "Test Template with Sample Farmers",
#       "details": "Send to 5-10 farmers from segment, verify all variables populate correctly",
#       "timeline": "Day 1-2",
#       "responsible": "QA Team",
#       "dependencies": "Step 1 complete"
#     }},
#     {{
#       "step": 3,
#       "action": "Create Flow Using AI Prompt",
#       "details": "Copy flow_creation_prompts[0].complete_prompt and paste to flow maker AI",
#       "timeline": "Day 2",
#       "responsible": "Marketing Team",
#       "dependencies": "Templates approved"
#     }},
#     {{
#       "step": 4,
#       "action": "Set Up Automated Triggers",
#       "details": "Configure system to auto-send when days_until_harvest reaches 10-12 days",
#       "timeline": "Day 3",
#       "responsible": "Tech Team",
#       "dependencies": "Flow tested"
#     }},
#     {{
#       "step": 5,
#       "action": "Monitor & Optimize",
#       "details": "Track open rates, click rates, conversion rates daily. Adjust messaging based on performance",
#       "timeline": "Ongoing",
#       "responsible": "Analytics Team",
#       "dependencies": "Flow live"
#     }}
#   ],
#   "revenue_breakdown": {{
#     "per_farmer_value": "₹{round(sum([float(i.get('price_cost', 0)) for i in farmer_data['interventions'] if any(f['farmer_id'] == i.get('farmer_id') for f in matched_farmers)]) / len(matched_farmers), 2) if matched_farmers else 5000}",
#     "total_potential": "₹{round((sum([float(i.get('price_cost', 0)) for i in farmer_data['interventions'] if any(f['farmer_id'] == i.get('farmer_id') for f in matched_farmers)]) / len(matched_farmers) if matched_farmers else 5000) * len(matched_farmers) * 0.3, 2)}",
#     "conversion_assumptions": "30% respond positively to offers, based on segment characteristics",
#     "calculation_basis": "Average spend from intervention history × farmers in segment × conversion rate"
#   }},
#   "personalization_variables_summary": {{
#     "available_fields": {len(available_farmer_fields | available_crop_fields | available_intervention_fields)},
#     "farmer_fields": list(available_farmer_fields),
#     "crop_fields": list(available_crop_fields),
#     "intervention_fields": list(available_intervention_fields),
#     "usage_recommendation": "Use minimum 5-7 variables per template for strong personalization"
#   }},
#   "next_steps": [
#     {{
#       "action": "Get segment farmers list",
#       "endpoint": "POST /get_segment_farmers/",
#       "payload": {{"segment_id": "{segment['segment_id']}"}},
#       "description": "Retrieve full list of {len(matched_farmers)} farmers matching this segment"
#     }},
#     {{
#       "action": "Create WhatsApp templates",
#       "method": "Use Meta Business API",
#       "templates_needed": "{len([t for t in segment.get('whatsapp_flow_strategy', {}).get('steps', []) if not t.get('template_exists', False)])} new templates",
#       "description": "Submit templates to Meta for approval (24-48 hours)"
#     }},
#     {{
#       "action": "Launch campaign",
#       "timing": "After template approval",
#       "batch_size": "Start with 50 farmers, then scale",
#       "description": "Monitor initial performance before full rollout"
#     }}
#   ]
# }}

# Be EXTREMELY specific and actionable. Consider the ACTUAL farmer data available.
# Generate ONLY valid JSON with complete implementation details.
# """
    
#     try:
#         response = model.generate_content(
#             prompt,
#             generation_config={"response_mime_type": "application/json"}
#         )
#         return json.loads(response.text)
#     except Exception as e:
#         print(f"Error generating detailed segment analysis: {e}")
#         return None

def generate_calendar_events(farmer_data):
    """
    Generates a calendar view of all important dates for farmers
    """
    from datetime import datetime, timedelta
    
    events = []
    today = datetime.now().date()
    
    # Harvest dates
    for crop in farmer_data['crop_details']:
        if crop.get('harvesting_date'):
            farmer = next((f for f in farmer_data['farmers'] if f['farmer_id'] == crop['farmer_id']), None)
            if farmer:
                events.append({
                    'date': crop['harvesting_date'],
                    'event_type': 'harvest',
                    'priority': 'HIGH' if (crop['harvesting_date'] - today).days <= 7 else 'MEDIUM',
                    'title': f"Harvest: {crop['crop_name']}",
                    'farmer_name': farmer['name'],
                    'farmer_phone': farmer['phone_number'],
                    'farmer_id': farmer['farmer_id'],
                    'details': f"{farmer['name']} harvesting {crop['crop_name']}",
                    'action_needed': 'Contact for labor booking',
                    'days_until': (crop['harvesting_date'] - today).days
                })
        
        # Growth stage transitions
        if crop.get('flowering_stage_start'):
            farmer = next((f for f in farmer_data['farmers'] if f['farmer_id'] == crop['farmer_id']), None)
            if farmer and crop['flowering_stage_start'] >= today:
                events.append({
                    'date': crop['flowering_stage_start'],
                    'event_type': 'growth_stage',
                    'priority': 'MEDIUM',
                    'title': f"Flowering Stage: {crop['crop_name']}",
                    'farmer_name': farmer['name'],
                    'farmer_phone': farmer['phone_number'],
                    'farmer_id': farmer['farmer_id'],
                    'details': f"{farmer['name']}'s {crop['crop_name']} entering flowering stage",
                    'action_needed': 'Send flowering care tips',
                    'days_until': (crop['flowering_stage_start'] - today).days
                })
        
        if crop.get('fruiting_stage_start'):
            farmer = next((f for f in farmer_data['farmers'] if f['farmer_id'] == crop['farmer_id']), None)
            if farmer and crop['fruiting_stage_start'] >= today:
                events.append({
                    'date': crop['fruiting_stage_start'],
                    'event_type': 'growth_stage',
                    'priority': 'MEDIUM',
                    'title': f"Fruiting Stage: {crop['crop_name']}",
                    'farmer_name': farmer['name'],
                    'farmer_phone': farmer['phone_number'],
                    'farmer_id': farmer['farmer_id'],
                    'details': f"{farmer['name']}'s {crop['crop_name']} entering fruiting stage",
                    'action_needed': 'Send fruiting care tips & nutrient recommendations',
                    'days_until': (crop['fruiting_stage_start'] - today).days
                })
    
    # Scheduled interventions (if any future interventions exist)
    for intervention in farmer_data['interventions']:
        if intervention.get('date') and intervention['date'] >= today:
            farmer = next((f for f in farmer_data['farmers'] if f['farmer_id'] == intervention['farmer_id']), None)
            if farmer:
                events.append({
                    'date': intervention['date'],
                    'event_type': 'intervention',
                    'priority': 'HIGH',
                    'title': f"{intervention['intervention_type']}: {intervention.get('crop_name')}",
                    'farmer_name': farmer['name'],
                    'farmer_phone': farmer['phone_number'],
                    'farmer_id': farmer['farmer_id'],
                    'details': f"{farmer['name']} scheduled {intervention['intervention_type']}",
                    'action_needed': f"Remind about {intervention['intervention_type']}",
                    'days_until': (intervention['date'] - today).days
                })
    
    # Sort events by date
    events.sort(key=lambda x: x['date'])
    
    # Filter to next 90 days
    ninety_days_later = today + timedelta(days=90)
    events = [e for e in events if e['date'] <= ninety_days_later]
    
    return events




@csrf_exempt
def get_calendar_view(request):
    """
    Returns calendar events for all important farmer dates
    """
    if request.method == 'GET':
        try:
            farmer_data = get_comprehensive_farmer_data()
            events = generate_calendar_events(farmer_data)
            
            # Group events by date for easier frontend rendering
            from collections import defaultdict
            events_by_date = defaultdict(list)
            
            for event in events:
                date_str = event['date'].strftime('%Y-%m-%d')
                events_by_date[date_str].append(event)
            
            return JsonResponse({
                'status': 'success',
                'total_events': len(events),
                'events': events,
                'events_by_date': dict(events_by_date)
            })
            
        except Exception as e:
            import traceback
            print(f"Error in get_calendar_view: {e}")
            print(traceback.format_exc())
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def generate_query_view(request):
    """
    API View to generate an SQL query from a natural language request.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            query = data.get('query')
            if not query:
                return JsonResponse({'error': 'Query not provided'}, status=400)

            sql_query, used_tables = generate_sql_from_llm(query)

            # Security Check: Ensure the generated query is safe
            if not sql_query.strip().upper().startswith('SELECT'):
                return JsonResponse({'error': 'Generated query is not a SELECT statement. Aborting.'}, status=400)

            return JsonResponse({
                'sql_query': sql_query,
                'used_tables': used_tables,
                'full_schema': get_db_schema()
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def execute_query_view(request):
    """
    API View to execute a SQL query (either as a test or full run).
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            sql_query = data.get('sql_query')
            test_run = data.get('test_run', False)

            if not sql_query:
                return JsonResponse({'error': 'SQL query not provided'}, status=400)

            # Security Check: Double-check that it's a safe query
            if not sql_query.strip().upper().startswith('SELECT'):
                return JsonResponse({'error': 'Only SELECT statements can be executed.'}, status=403)

            final_query = sql_query
            if test_run:
                # Add a LIMIT clause for the test run
                final_query = f"{sql_query.rstrip(';')} LIMIT 100;"

            with connection.cursor() as cursor:
                cursor.execute(final_query)
                columns = [col[0] for col in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            # Suggest a chart type based on the results
            chart_type = 'table'
            if len(results) > 0:
                first_row = results[0]
                if len(first_row.keys()) == 2:
                    key1, key2 = list(first_row.keys())
                    # If one column is text-like and the other is numeric, suggest bar or pie
                    if isinstance(first_row[key1], str) and isinstance(first_row[key2], (int, float)):
                        chart_type = 'bar' if len(results) > 5 else 'pie'

            return JsonResponse({'results': results, 'chart_type': chart_type})
        except Exception as e:
            return JsonResponse({'error': f"Database query failed: {e}"}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)


def generate_sql_from_llm(user_query: str):
    """
    Generates a secure, read-only SQL query from a natural language prompt using the Gemini API.
    """
    db_schema = get_db_schema()
    if not db_schema:
        return "-- Failed to retrieve database schema.", []

    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    json_output_config = {
        "response_mime_type": "application/json",
    }

    prompt = f"""
    You are a PostgreSQL expert data analyst. Your task is to convert a user's question into a valid, performant, and secure PostgreSQL query and identify which tables were used.

    Here is the database schema you must use:
    {db_schema}

    Analyze the user's question and the schema to construct a read-only SQL query.

    Rules:
    1.  CRITICAL: Only generate `SELECT` statements. Never generate `INSERT`, `UPDATE`, `DELETE`, `DROP`, `GRANT`, or any other data-modifying statements.
    2.  Only use tables and columns present in the provided schema.
    3.  If a table name includes a prefix (like 'registration_'), you must include it in the query.
    4.  Return the result as a JSON object with two keys: "sql_query" which contains the generated SQL string, and "used_tables" which is a list of the table names you used in the query.
    5. MOST IMPORTANT CRITICAL: If the user's question cannot be answered with the provided schema, return a JSON object with "sql_query" set to "-- Unable to generate a valid SQL query with the provided schema." and "used_tables" as an empty list.
    
    User Question: "{user_query}"

    JSON Response:
    """
    
    try:
        response = model.generate_content(prompt, generation_config=json_output_config)
        print(response.text)
        
        result_json = json.loads(response.text)
        sql_query = result_json.get("sql_query", "-- Failed to generate SQL.")
        used_tables = result_json.get("used_tables", [])
        
        return sql_query, used_tables

    except Exception as e:
        print(f"An error occurred with the Gemini API call: {e}")
        return f"-- An error occurred: {e}", []       