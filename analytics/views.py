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
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

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
def analyze_farmer_segments_with_ai(farmer_data):
    """
    Uses AI to automatically analyze farmer data and create actionable segments
    with specific flow recommendations.
    OPTIMIZED: Sends summary statistics instead of all raw data to avoid quota issues.
    """
    # Try with flash model first, fallback to flash-exp if needed
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')  # More stable, higher quota
    except:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    # Create a summary instead of sending all raw data (to save tokens)
    from datetime import datetime, timedelta
    from collections import Counter
    
    total_farmers = len(farmer_data['farmers'])
    
    # Calculate summary statistics
    crops_counter = Counter([f['crop_name'] for f in farmer_data['farmers'] if f.get('crop_name')])
    farm_sizes = [float(f['farm_size']) for f in farmer_data['farmers'] if f.get('farm_size')]
    avg_farm_size = sum(farm_sizes) / len(farm_sizes) if farm_sizes else 0
    
    # Growth stage distribution
    growth_stages = Counter([c['current_growth_stage'] for c in farmer_data['crop_details']])
    
    # Days until harvest distribution
    harvest_soon = [c for c in farmer_data['crop_details'] if c.get('days_until_harvest') and c['days_until_harvest'] <= 30]
    harvest_within_week = [c for c in farmer_data['crop_details'] if c.get('days_until_harvest') and c['days_until_harvest'] <= 7]
    
    # Intervention activity
    recent_interventions = [i for i in farmer_data['interventions'] 
                           if i.get('intervention_date') and 
                           (datetime.now().date() - i['intervention_date']).days <= 30]
    
    intervention_types = Counter([i['intervention_type'] for i in farmer_data['interventions']])
    
    # Farmers with next crop recommendation
    farmers_with_next_crop = [f for f in farmer_data['farmers'] if f.get('next_crop_recommendation')]
    
    summary_data = {
        'total_farmers': total_farmers,
        'crop_distribution': dict(crops_counter.most_common(10)),
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
        'intervention_activity': {
            'recent_interventions_30_days': len(recent_interventions),
            'intervention_types': dict(intervention_types),
            'avg_interventions_per_farmer': round(len(farmer_data['interventions']) / total_farmers, 2)
        },
        'next_crop_opportunities': {
            'farmers_with_recommendations': len(farmers_with_next_crop),
            'sample_recommendations': list(set([f['next_crop_recommendation'] 
                                               for f in farmers_with_next_crop[:20] 
                                               if f.get('next_crop_recommendation')]))
        },
        'sample_farmers': farmer_data['farmers'][:5]  # Just send 5 examples instead of 500
    }
    
    prompt = f"""
You are an expert agricultural business analyst for a FARMER-LABOR PLATFORM. Analyze the SUMMARY statistics below and create actionable customer segments with specific WhatsApp flow recommendations.

DATABASE STRUCTURE:
- Farmer: farmer_name, phone_number, farm_size_acres, created_at
- CropDetails: One crop per farmer with growth stages (seeding → germination → vegetative → flowering → fruiting → harvesting)
- Intervention: Activities like Fertilizer, Pesticide, Pruning/Weeding linked to crops

FARMER DATA SUMMARY (based on {total_farmers} farmers):
{json.dumps(summary_data, indent=2, default=str)}

YOUR TASK:
1. Identify different farmer segments based on the statistics above:
   - Crop growth stage distribution
   - Farm size ranges (small/medium/large)
   - Intervention frequency and activity
   - Approaching harvest dates (7-30 days)
   - Next crop recommendation availability

2. IMPORTANT SEGMENTS TO CREATE:
   - "Pre-Harvest Farmers" - {len(harvest_soon)} farmers approaching harvest, need labor services
   - "Active Growers" - farmers with recent interventions, engaged and ready for upsell
   - "Harvest Ready This Week" - {len(harvest_within_week)} farmers harvesting soon, URGENT labor needs
   - "Next Crop Ready" - {len(farmers_with_next_crop)} farmers with recommendations, ready for new cycle
   - "Small Farm Owners" - potential for cooperative services
   - "Large Farm Owners" - premium service opportunity

3. For EACH segment, provide detailed WhatsApp flow strategy with Hindi & English message samples.

OUTPUT FORMAT (JSON):
{{
  "analysis_summary": {{
    "total_farmers": {total_farmers},
    "analysis_date": "{datetime.now().strftime('%Y-%m-%d')}",
    "key_insights": ["insight based on the data", "insight 2", "insight 3"]
  }},
  "segments": [
    {{
      "segment_id": "unique_id",
      "segment_name": "Descriptive Name",
      "priority": "HIGH/MEDIUM/LOW",
      "farmer_count": number,
      "conversion_potential": "HIGH/MEDIUM/LOW",
      "estimated_revenue": "₹X,XXX per farmer/month",
      "characteristics": ["based on data"],
      "farmer_ids": [],
      "recommended_actions": [
        {{
          "action_type": "flow/template/campaign",
          "action_name": "Specific action",
          "timing": "immediate/weekly/monthly",
          "expected_outcome": "what you'll achieve"
        }}
      ],
      "whatsapp_flow_strategy": {{
        "flow_type": "onboarding/retention/upsell/reactivation",
        "flow_name": "Suggested flow name",
        "trigger": "What triggers this flow",
        "steps": [
          {{
            "step_number": 1,
            "template_type": "greeting/offer/survey/reminder",
            "message_intent": "What this achieves",
            "sample_text_hindi": "नमस्कार {{{{farmer_name}}}}, आपकी {{{{crop_name}}}} फसल...",
            "sample_text_english": "Hello {{{{farmer_name}}}}, your {{{{crop_name}}}} crop...",
            "buttons": ["Button 1", "Button 2"],
            "expected_response": "What farmer should do"
          }}
        ],
        "success_metrics": ["metric1", "metric2"]
      }},
      "contact_strategy": {{
        "best_time": "morning/afternoon/evening",
        "frequency": "daily/weekly/monthly",
        "channel_preference": "whatsapp"
      }}
    }}
  ],
  "immediate_opportunities": [
    {{
      "opportunity": "Description",
      "target_segment": "segment_id",
      "potential_revenue": "₹X,XXX",
      "implementation_difficulty": "easy/medium/hard",
      "action_items": ["step1", "step2"]
    }}
  ],
  "automation_recommendations": [
    {{
      "automation_type": "Type",
      "description": "What it does",
      "target_segments": ["segment1", "segment2"],
      "implementation_priority": "HIGH/MEDIUM/LOW"
    }}
  ]
}}

Focus on ACTIONABLE insights. Use the statistics to size segments accurately.
Generate ONLY valid JSON.
"""
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Error in AI analysis: {e}")
        return None


def generate_flow_prompts_from_segments(segments_data):
    """
    Converts AI segment analysis into ready-to-use flow creation prompts.
    """
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    prompt = f"""
Based on the farmer segment analysis, generate specific, ready-to-execute prompts for creating WhatsApp flows.

SEGMENT ANALYSIS:
{json.dumps(segments_data, indent=2)}

Generate detailed prompts that can be directly used to create flows. Each prompt should be complete and actionable.

OUTPUT FORMAT (JSON):
{{
  "flow_prompts": [
    {{
      "prompt_id": "unique_id",
      "segment_targeted": "segment name",
      "priority": "HIGH/MEDIUM/LOW",
      "prompt_title": "Short title",
      "full_prompt": "Complete prompt ready to paste for flow creation",
      "expected_templates": number,
      "language": "hi/en/both",
      "estimated_conversion_rate": "X%",
      "implementation_notes": ["note1", "note2"]
    }}
  ]
}}

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
        return None


# --- API Views ---

@csrf_exempt
def auto_analyze_farmers_view(request):
    """
    Automatically analyzes all farmer data and provides actionable insights
    with recommended flows and conversion strategies.
    """
    if request.method == 'POST':
        try:
            # Get comprehensive farmer data
            farmer_data = get_comprehensive_farmer_data()
            
            if not farmer_data['farmers']:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No farmer data found in database'
                }, status=404)
            
            # Perform AI analysis
            analysis_result = analyze_farmer_segments_with_ai(farmer_data)
            
            if not analysis_result:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Failed to analyze farmer data'
                }, status=500)
            
            # Generate ready-to-use flow prompts
            flow_prompts = generate_flow_prompts_from_segments(analysis_result)
            
            return JsonResponse({
                'status': 'success',
                'analysis': analysis_result,
                'flow_prompts': flow_prompts,
                'raw_data_summary': {
                    'total_farmers': len(farmer_data['farmers']),
                    'total_crops': len(farmer_data['crop_details']),
                    'total_interventions': len(farmer_data['interventions'])
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f"Analysis failed: {str(e)}"
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def get_segment_details_view(request):
    """
    Get detailed information about a specific farmer segment.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            segment_id = data.get('segment_id')
            
            if not segment_id:
                return JsonResponse({'error': 'Segment ID not provided'}, status=400)
            
            # Get full analysis
            farmer_data = get_comprehensive_farmer_data()
            analysis_result = analyze_farmer_segments_with_ai(farmer_data)
            
            # Find specific segment
            target_segment = None
            for segment in analysis_result.get('segments', []):
                if segment['segment_id'] == segment_id:
                    target_segment = segment
                    break
            
            if not target_segment:
                return JsonResponse({'error': 'Segment not found'}, status=404)
            
            # Get farmer details for this segment
            farmer_ids = target_segment.get('farmer_ids', [])
            farmers_in_segment = [
                f for f in farmer_data['farmers'] 
                if f['farmer_id'] in farmer_ids
            ]
            
            return JsonResponse({
                'status': 'success',
                'segment': target_segment,
                'farmers': farmers_in_segment,
                'total_farmers': len(farmers_in_segment)
            })
            
        except Exception as e:
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