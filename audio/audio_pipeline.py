import os
import sqlite3
import json
import time
import wave
import subprocess
from pathlib import Path
from google.cloud import speech
from google.cloud import storage
from google.cloud import translate_v2 as translate
import vertexai
from vertexai.generative_models import GenerativeModel
import librosa
import soundfile as sf
import numpy as np

# --- CONFIGURATION ---
PROJECT_ID = "healthy-saga-392716"
LOCATION = "us-central1"
BUCKET_NAME = "healthy-saga-392716-audio-files"
AUDIO_FOLDER = "audio_files"
PROCESSED_FOLDER = "processed_audio"
DATABASE_NAME = "results.db"

# --- INITIALIZE SERVICES ---
vertexai.init(project=PROJECT_ID, location=LOCATION)
speech_client = speech.SpeechClient()
storage_client = storage.Client(project=PROJECT_ID)
translate_client = translate.Client()
# Using the best available model for text generation
llm_model = GenerativeModel("gemini-2.0-flash-exp")

def setup_folders():
    """Create necessary folders"""
    os.makedirs(PROCESSED_FOLDER, exist_ok=True)
    os.makedirs(AUDIO_FOLDER, exist_ok=True)

def setup_database():
    """Creates the SQLite database and table if they don't exist."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS call_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_language TEXT,
            marathi_transcript TEXT,
            english_transcript TEXT,
            intent TEXT,
            entities TEXT,
            confidence_score REAL,
            processing_time REAL,
            audio_duration REAL,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_audio_info(file_path):
    """Get detailed audio file information"""
    try:
        # Load audio file to get properties
        y, sr = librosa.load(file_path, sr=None)
        duration = librosa.get_duration(y=y, sr=sr)
        
        print(f"  📊 Audio Info:")
        print(f"    - Duration: {duration:.2f} seconds ({duration/60:.1f} minutes)")
        print(f"    - Sample Rate: {sr} Hz")
        print(f"    - Channels: {y.ndim}")
        
        return {
            'duration': duration,
            'sample_rate': sr,
            'channels': y.ndim
        }
    except Exception as e:
        print(f"  ⚠️ Could not analyze audio: {e}")
        return None

def preprocess_audio(input_path, output_path):
    """
    Preprocess audio for optimal Speech-to-Text recognition
    - Convert to mono
    - Normalize sample rate to 16kHz (optimal for speech recognition)
    - Apply noise reduction
    - Normalize volume
    """
    print(f"  🔧 Preprocessing audio...")
    
    try:
        # Load audio
        y, sr = librosa.load(input_path, sr=None, mono=False)
        
        # Convert to mono if stereo
        if len(y.shape) > 1:
            y = librosa.to_mono(y)
            print(f"    ✅ Converted to mono")
        
        # Resample to 16kHz (optimal for speech recognition)
        target_sr = 16000
        if sr != target_sr:
            y = librosa.resample(y, orig_sr=sr, target_sr=target_sr)
            sr = target_sr
            print(f"    ✅ Resampled to {target_sr} Hz")
        
        # Normalize audio
        y = librosa.util.normalize(y)
        print(f"    ✅ Normalized volume")
        
        # Apply noise reduction (simple spectral gating)
        # Get noise profile from first 0.5 seconds
        noise_sample = y[:int(0.5 * sr)]
        noise_threshold = np.percentile(np.abs(noise_sample), 95)
        
        # Simple noise gate
        y = np.where(np.abs(y) > noise_threshold * 0.1, y, y * 0.1)
        print(f"    ✅ Applied noise reduction")
        
        # Save preprocessed audio as WAV (best for Google Speech-to-Text)
        sf.write(output_path, y, sr, format='WAV', subtype='PCM_16')
        print(f"    ✅ Saved preprocessed audio: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"    ❌ Preprocessing failed: {e}")
        return False

def upload_to_gcs(file_path, bucket_name):
    """Uploads a local file to a Google Cloud Storage bucket with retry logic."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            bucket = storage_client.get_bucket(bucket_name)
            blob_name = f"audio_processing/{os.path.basename(file_path)}"
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(file_path)
            gcs_uri = f"gs://{bucket_name}/{blob_name}"
            print(f"  ☁️ Uploaded to GCS: {gcs_uri}")
            return gcs_uri
        except Exception as e:
            print(f"  ⚠️ Upload attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                print(f"  ❌ Failed to upload after {max_retries} attempts")
                return None

def transcribe_marathi_audio_enhanced(audio_file_path, gcs_bucket_name, audio_duration):
    """
    Enhanced Marathi audio transcription with optimized settings for long audio files
    """
    print(f"🎙️ Starting enhanced Marathi transcription...")
    start_time = time.time()

    # Upload to GCS
    gcs_uri = upload_to_gcs(audio_file_path, gcs_bucket_name)
    if not gcs_uri:
        return None, 0

    audio = speech.RecognitionAudio(uri=gcs_uri)

    # Optimized configuration for Marathi long-form audio
    config = speech.RecognitionConfig(
        # Audio format
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        audio_channel_count=1,
        
        # Language settings
        language_code="mr-IN",  # Primary: Marathi (India)
        alternative_language_codes=["hi-IN", "en-IN"],  # Fallbacks
        
        # Model selection (best for longer audio)
        model="latest_long",  # Best for long-form audio
        use_enhanced=True,    # Enhanced model for better accuracy
        
        # Transcription features
        enable_automatic_punctuation=True,
        enable_word_time_offsets=True,
        enable_word_confidence=True,
        enable_speaker_diarization=True,
        diarization_speaker_count=2,  # Assuming customer service call
        
        # Quality settings
        max_alternatives=3,  # Get multiple alternatives
        profanity_filter=False,
        
        # Context for better recognition
        speech_contexts=[
            speech.SpeechContext(
                phrases=[
                    # Agricultural terms in Marathi
                    "शेतकरी", "शेती", "पीक", "कापणी", "लागवड", "बागायत", 
                    "फवारणी", "खत", "बियाणे", "जमीन", "हेक्टर", "एकर",
                    "कापूस", "भात", "ज्वारी", "बाजरी", "गहू", "तूर",
                    
                    # Business/Service terms
                    "किंमत", "पैसे", "रुपये", "काम", "वेळ", "दिवस", "तास",
                    "बुकिंग", "सेवा", "कंपनी", "ऑफिस", "फोन", "मोबाइल",
                    
                    # Common conversation words
                    "मला", "तुम्हाला", "आम्हाला", "कधी", "कुठे", "काय", "कसे",
                    "होय", "नाही", "ठीक", "बरं", "चांगले", "वाईट"
                ],
                boost=15.0  # High boost for agriculture-specific terms
            ),
            speech.SpeechContext(
                phrases=[
                    # Numbers and quantities
                    "एक", "दोन", "तीन", "चार", "पाच", "दहा", "वीस", "पन्नास", "शंभर", "हजार"
                ],
                boost=10.0
            )
        ]
    )

    try:
        print("  ⏳ Starting long-running transcription...")
        print(f"  📊 Expected processing time: {audio_duration/60*2:.1f} minutes")
        
        # Use long running recognize for files > 1 minute
        operation = speech_client.long_running_recognize(config=config, audio=audio)
        
        # Calculate timeout based on audio duration (allow 3x the audio length + 300s base)
        timeout_seconds = max(int(audio_duration * 3 + 300), 900)  # Minimum 15 minutes
        print(f"  ⏱️ Timeout set to: {timeout_seconds/60:.1f} minutes")
        
        response = operation.result(timeout=timeout_seconds)

        if not response.results:
            print("  ❌ No speech could be transcribed from the audio")
            return None, 0

        # Process all results with advanced combination
        print(f"  📝 Processing {len(response.results)} transcription segments...")
        
        full_transcript = ""
        confidence_scores = []
        word_count = 0
        
        for i, result in enumerate(response.results):
            if result.alternatives:
                # Use the best alternative
                best_alternative = result.alternatives[0]
                segment_text = best_alternative.transcript.strip()
                segment_confidence = best_alternative.confidence
                
                # Add segment with proper spacing
                if full_transcript and not full_transcript.endswith(" "):
                    full_transcript += " "
                full_transcript += segment_text
                
                confidence_scores.append(segment_confidence)
                word_count += len(segment_text.split())
                
                print(f"    Segment {i+1}: {len(segment_text)} chars (confidence: {segment_confidence:.3f})")

        # Calculate overall metrics
        average_confidence = np.mean(confidence_scores) if confidence_scores else 0
        processing_time = time.time() - start_time
        
        print(f"  ✅ Transcription completed!")
        print(f"  📊 Results:")
        print(f"    - Total length: {len(full_transcript)} characters")
        print(f"    - Word count: {word_count} words")
        print(f"    - Average confidence: {average_confidence:.3f}")
        print(f"    - Processing time: {processing_time:.1f} seconds")
        print(f"    - Transcription rate: {audio_duration/processing_time:.1f}x realtime")
        
        # Show preview of transcript
        preview = full_transcript[:200] + "..." if len(full_transcript) > 200 else full_transcript
        print(f"  📖 Preview: {preview}")
        
        return full_transcript.strip(), average_confidence

    except Exception as e:
        print(f"  ❌ Transcription error: {str(e)}")
        return None, 0

def translate_marathi_to_english_enhanced(marathi_text):
    """
    Enhanced translation with multiple methods and quality checks
    """
    if not marathi_text or len(marathi_text.strip()) < 3:
        print("  ⚠️ Text too short for translation")
        return None

    print(f"  🌐 Translating {len(marathi_text)} characters...")

    # Method 1: Google Cloud Translation API (Primary)
    try:
        # For very long text, split into chunks
        max_chunk_size = 5000  # Google Translate API limit
        
        if len(marathi_text) > max_chunk_size:
            print(f"  📄 Splitting text into chunks for translation...")
            
            # Split by sentences/periods for better context preservation
            sentences = marathi_text.split('.')
            chunks = []
            current_chunk = ""
            
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 1 <= max_chunk_size:
                    current_chunk += sentence + "."
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence + "."
            
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            print(f"  📝 Processing {len(chunks)} chunks...")
            
            translated_chunks = []
            for i, chunk in enumerate(chunks):
                try:
                    result = translate_client.translate(
                        chunk,
                        source_language='mr',
                        target_language='en'
                    )
                    translated_chunks.append(result['translatedText'])
                    print(f"    ✅ Chunk {i+1}/{len(chunks)} translated")
                    time.sleep(0.1)  # Small delay to avoid rate limits
                except Exception as e:
                    print(f"    ⚠️ Chunk {i+1} failed: {e}")
                    translated_chunks.append(f"[Translation failed for segment {i+1}]")
            
            english_text = " ".join(translated_chunks)
            
        else:
            # Single translation for shorter text
            result = translate_client.translate(
                marathi_text,
                source_language='mr',
                target_language='en'
            )
            english_text = result['translatedText']
        
        print(f"  ✅ Translation via Cloud API completed")
        print(f"  📊 Translated length: {len(english_text)} characters")
        
        return english_text

    except Exception as e:
        print(f"  ⚠️ Cloud Translation failed: {e}")
        print("  🔄 Falling back to Gemini translation...")

    # Method 2: Gemini 2.0 Flash (Advanced fallback)
    try:
        # For very long text, use summarization approach with Gemini
        if len(marathi_text) > 8000:
            prompt = f"""
            You are an expert Marathi to English translator with deep knowledge of agricultural and business terminology.

            Task: Translate this long Marathi conversation to natural, fluent English while preserving ALL important information.

            Guidelines:
            - Maintain complete meaning and context
            - Preserve all business details, names, numbers, dates
            - Use natural English expressions
            - Keep agricultural/farming terminology accurate
            - Maintain conversational tone and structure
            - Do NOT summarize or omit any information
            - Output ONLY the English translation

            Marathi Text (Length: {len(marathi_text)} chars):
            "{marathi_text}"

            Complete English Translation:
            """
        else:
            prompt = f"""
            Translate this Marathi text to perfect English:

            Rules:
            - Complete, accurate translation
            - Natural English flow
            - Preserve all details
            - Output only the translation

            Marathi: "{marathi_text}"

            English:
            """

        response = llm_model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.1,  # Low temperature for accuracy
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 8192
            }
        )
        
        english_text = response.text.strip()
        
        # Clean up response
        if english_text.startswith('"') and english_text.endswith('"'):
            english_text = english_text[1:-1]
        
        print(f"  ✅ Translation via Gemini 2.0 completed")
        print(f"  📊 Translated length: {len(english_text)} characters")
        
        return english_text

    except Exception as e:
        print(f"  ❌ Gemini translation also failed: {e}")
        return None

def extract_intent_and_entities_enhanced(english_transcript):
    """
    Advanced intent classification and entity extraction using Gemini 2.0
    """
    if not english_transcript or len(english_transcript.strip()) < 10:
        print("  ⚠️ Transcript too short for intent analysis")
        return None

    print(f"  🧠 Analyzing intent from {len(english_transcript)} characters...")

    prompt = f"""
    You are an advanced AI system specialized in analyzing agricultural service conversations between service providers and farmers in India.

    Analyze this English conversation transcript (translated from Marathi) and extract detailed insights:

    **PRIMARY INTENTS** (choose the most accurate):
    - create_job: Customer wants to book/hire a specific service
    - schedule_callback: Customer requests a callback/follow-up
    - confirm_interest: Customer shows interest but needs more information
    - negotiate_price: Customer is discussing or negotiating pricing/costs
    - request_information: Customer asking for service details, quotes, or general info
    - complaint_issue: Customer reporting problems or dissatisfaction
    - cancel_reschedule: Customer wants to cancel or reschedule existing booking
    - general_inquiry: General questions about services/company

    **ENTITIES TO EXTRACT** (extract all mentioned):
    - dates: Any specific dates mentioned (format: YYYY-MM-DD or descriptive)
    - location: Farm location, village, district, state
    - crop_type: Specific crops mentioned
    - total_area: Area in acres/hectares/bigha
    - services_needed: Specific services (spraying, harvesting, pruning, etc.)
    - price_estimate: Any costs/prices mentioned
    - phone_number: Contact numbers
    - farmer_name: Customer's name
    - urgency_level: high/medium/low based on conversation urgency
    - equipment_type: Specific machinery/equipment mentioned
    - timing_preference: Preferred timing for service
    - current_crop_stage: Stage of crop growth mentioned
    - issues_problems: Any specific problems or challenges mentioned

    **CONFIDENCE SCORING**:
    - High (0.8-1.0): Clear, unambiguous intent
    - Medium (0.5-0.8): Somewhat clear intent
    - Low (0.0-0.5): Unclear or mixed intent

    **OUTPUT FORMAT**: Return ONLY valid JSON:
    {{
        "intent": "primary_intent_here",
        "confidence": 0.85,
        "reasoning": "Brief explanation of why this intent was chosen",
        "entities": {{
            "dates": ["date1", "date2"],
            "location": "location_name",
            "crop_type": "crop_name",
            "total_area": "X acres",
            "services_needed": ["service1", "service2"],
            "price_estimate": "amount_info",
            "urgency_level": "medium",
            "equipment_type": "equipment_name",
            "timing_preference": "timing_info",
            "issues_problems": ["issue1", "issue2"]
        }},
        "conversation_summary": "Brief 2-3 sentence summary of the main conversation points"
    }}

    Conversation Transcript:
    "{english_transcript}"

    Analysis (JSON only):
    """

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = llm_model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.2,
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_output_tokens": 4096
                }
            )
            
            json_text = response.text.strip()
            
            # Clean up response
            json_text = json_text.replace("```json", "").replace("```", "").strip()
            
            # Find JSON boundaries if there's extra text
            start_idx = json_text.find('{')
            end_idx = json_text.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_text = json_text[start_idx:end_idx]
            
            # Parse JSON
            structured_data = json.loads(json_text)
            
            # Validate and set defaults
            if 'intent' not in structured_data:
                structured_data['intent'] = 'general_inquiry'
            if 'confidence' not in structured_data:
                structured_data['confidence'] = 0.5
            if 'entities' not in structured_data:
                structured_data['entities'] = {}
            if 'reasoning' not in structured_data:
                structured_data['reasoning'] = 'Analysis completed'
            if 'conversation_summary' not in structured_data:
                structured_data['conversation_summary'] = 'Conversation analyzed'
            
            print(f"  ✅ Intent Analysis Completed:")
            print(f"    - Intent: {structured_data['intent']}")
            print(f"    - Confidence: {structured_data['confidence']:.2f}")
            print(f"    - Key entities: {len(structured_data['entities'])} found")
            print(f"    - Reasoning: {structured_data['reasoning']}")
            
            return structured_data

        except json.JSONDecodeError as e:
            print(f"  ⚠️ Attempt {attempt + 1}: JSON parsing error - {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                print("  ❌ Failed to parse intent analysis")
                return {
                    "intent": "general_inquiry",
                    "confidence": 0.0,
                    "entities": {},
                    "reasoning": "Analysis parsing failed",
                    "conversation_summary": "Could not analyze conversation"
                }
        except Exception as e:
            print(f"  ⚠️ Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                print("  ❌ All intent analysis attempts failed")
                return None

def process_audio_file_enhanced(filepath, bucket_name):
    """Enhanced main processing function with comprehensive error handling and quality checks."""
    filename = os.path.basename(filepath)
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    print(f"\n{'='*60}")
    print(f"🎵 PROCESSING: {filename}")
    print(f"{'='*60}")
    overall_start_time = time.time()

    try:
        # STEP 1: Analyze original audio
        print("\n📊 STEP 1: Audio Analysis")
        audio_info = get_audio_info(filepath)
        audio_duration = audio_info['duration'] if audio_info else 0
        
        if audio_duration < 1:
            print("  ❌ Audio too short or unreadable")
            cursor.execute(
                "INSERT INTO call_records (filename, status, audio_duration) VALUES (?, ?, ?)", 
                (filename, "AUDIO_TOO_SHORT", 0)
            )
            conn.commit()
            conn.close()
            return
        
        # STEP 2: Preprocess audio
        print(f"\n🔧 STEP 2: Audio Preprocessing")
        processed_filename = f"processed_{filename.rsplit('.', 1)[0]}.wav"
        processed_path = os.path.join(PROCESSED_FOLDER, processed_filename)
        
        if not preprocess_audio(filepath, processed_path):
            print("  ❌ Audio preprocessing failed")
            cursor.execute(
                "INSERT INTO call_records (filename, status, audio_duration) VALUES (?, ?, ?)", 
                (filename, "PREPROCESSING_FAILED", audio_duration)
            )
            conn.commit()
            conn.close()
            return
        
        # STEP 3: Enhanced Marathi transcription
        print(f"\n🎙️ STEP 3: Enhanced Marathi Transcription")
        marathi_transcript, confidence = transcribe_marathi_audio_enhanced(processed_path, bucket_name, audio_duration)
        
        if not marathi_transcript or len(marathi_transcript.strip()) < 10:
            print("  ❌ Transcription failed or too short")
            cursor.execute(
                "INSERT INTO call_records (filename, status, audio_duration) VALUES (?, ?, ?)", 
                (filename, "TRANSCRIPTION_FAILED", audio_duration)
            )
            conn.commit()
            conn.close()
            return
        
        print(f"  📝 Marathi transcript: {len(marathi_transcript)} characters")
        
        # STEP 4: Enhanced English translation
        print(f"\n🌐 STEP 4: Enhanced Translation")
        english_transcript = translate_marathi_to_english_enhanced(marathi_transcript)
        
        if not english_transcript or len(english_transcript.strip()) < 10:
            print("  ❌ Translation failed or too short")
            cursor.execute(
                "INSERT INTO call_records (filename, original_language, marathi_transcript, status, audio_duration) VALUES (?, ?, ?, ?, ?)", 
                (filename, "mr-IN", marathi_transcript, "TRANSLATION_FAILED", audio_duration)
            )
            conn.commit()
            conn.close()
            return
        
        print(f"  📝 English transcript: {len(english_transcript)} characters")
        
        # STEP 5: Enhanced intent and entity extraction
        print(f"\n🧠 STEP 5: Advanced Intent Analysis")
        structured_data = extract_intent_and_entities_enhanced(english_transcript)
        
        if not structured_data:
            print("  ❌ Intent extraction failed")
            cursor.execute(
                "INSERT INTO call_records (filename, original_language, marathi_transcript, english_transcript, status, audio_duration) VALUES (?, ?, ?, ?, ?, ?)", 
                (filename, "mr-IN", marathi_transcript, english_transcript, "INTENT_EXTRACTION_FAILED", audio_duration)
            )
            conn.commit()
            conn.close()
            return
        
        intent = structured_data.get('intent', 'unknown')
        entities = structured_data.get('entities', {})
        intent_confidence = structured_data.get('confidence', 0.0)
        
        # STEP 6: Execute appropriate action
        print(f"\n⚡ STEP 6: Action Execution")
        action_mapper = {
            'create_job': create_job_api,
            'schedule_callback': schedule_callback_api,
            'confirm_interest': update_crm_api,
            'negotiate_price': update_crm_api,
            'request_information': send_quote_api,
            'complaint_issue': log_complaint_api,
            'cancel_reschedule': update_crm_api,
            'general_inquiry': update_crm_api
        }

        action_function = action_mapper.get(intent)
        if action_function:
            status = action_function(entities)
        else:
            status = f"NO_ACTION_FOR_{intent.upper()}"
            print(f"  ⚠️ No action defined for intent: {intent}")
        
        # STEP 7: Save comprehensive results to database
        print(f"\n💾 STEP 7: Save Results")
        total_processing_time = time.time() - overall_start_time
        
        cursor.execute('''
            INSERT INTO call_records 
            (filename, original_language, marathi_transcript, english_transcript, intent, entities, confidence_score, processing_time, audio_duration, status) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            filename, 
            "mr-IN", 
            marathi_transcript, 
            english_transcript, 
            intent, 
            json.dumps(structured_data, ensure_ascii=False, indent=2), 
            intent_confidence, 
            total_processing_time, 
            audio_duration,
            status
        ))
        
        conn.commit()
        conn.close()
        
        # Cleanup processed audio file
        try:
            os.remove(processed_path)
        except:
            pass
        
        print(f"\n✅ PROCESSING COMPLETED SUCCESSFULLY!")
        print(f"  📊 Summary:")
        print(f"    - Audio Duration: {audio_duration:.1f} seconds")
        print(f"    - Processing Time: {total_processing_time:.1f} seconds")
        print(f"    - Transcription Quality: {confidence:.2f}")
        print(f"    - Intent Confidence: {intent_confidence:.2f}")
        print(f"    - Final Status: {status}")
        print(f"    - Marathi Length: {len(marathi_transcript)} chars")
        print(f"    - English Length: {len(english_transcript)} chars")

    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        cursor.execute(
            "INSERT INTO call_records (filename, status, audio_duration) VALUES (?, ?, ?)", 
            (filename, f"ERROR_{str(e)[:50]}", audio_duration if 'audio_duration' in locals() else 0)
        )
        conn.commit()
        conn.close()

# API Functions (Enhanced with better logging)
def create_job_api(entities):
    """Enhanced job creation API simulation"""
    print(f"  🔧 ACTION: Creating agricultural service job")
    print(f"    📋 Details: {json.dumps(entities, indent=2, ensure_ascii=False)}")
    return "JOB_CREATED_SUCCESS"

def schedule_callback_api(entities):
    """Enhanced callback scheduling API simulation"""
    print(f"  📞 ACTION: Scheduling callback")
    print(f"    📋 Details: {json.dumps(entities, indent=2, ensure_ascii=False)}")
    return "CALLBACK_SCHEDULED_SUCCESS"

def update_crm_api(entities):
    """Enhanced CRM update API simulation"""
    print(f"  📊 ACTION: Updating CRM system")
    print(f"    📋 Details: {json.dumps(entities, indent=2, ensure_ascii=False)}")
    return "CRM_UPDATED_SUCCESS"

def send_quote_api(entities):
    """Enhanced quote sending API simulation"""
    print(f"  💰 ACTION: Sending price quote")
    print(f"    📋 Details: {json.dumps(entities, indent=2, ensure_ascii=False)}")
    return "QUOTE_SENT_SUCCESS"

def log_complaint_api(entities):
    """Enhanced complaint logging API simulation"""
    print(f"  ⚠️ ACTION: Logging customer complaint")
    print(f"    📋 Details: {json.dumps(entities, indent=2, ensure_ascii=False)}")
    return "COMPLAINT_LOGGED_SUCCESS"

def print_detailed_database_summary():
    """Enhanced database summary with detailed statistics"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    print(f"\n{'='*60}")
    print("📊 DETAILED PROCESSING SUMMARY")
    print(f"{'='*60}")
    
    # Overall statistics
    cursor.execute("SELECT COUNT(*) FROM call_records")
    total_files = cursor.fetchone()[0]
    
    cursor.execute("SELECT status, COUNT(*) FROM call_records GROUP BY status ORDER BY COUNT(*) DESC")
    status_results = cursor.fetchall()
    
    print(f"\n📈 Overall Statistics:")
    print(f"  Total Files Processed: {total_files}")
    
    print(f"\n📋 Status Breakdown:")
    for status, count in status_results:
        percentage = (count / total_files * 100) if total_files > 0 else 0
        print(f"  {status}: {count} files ({percentage:.1f}%)")
    
    # Success rate analysis
    cursor.execute("SELECT COUNT(*) FROM call_records WHERE status LIKE '%SUCCESS%'")
    successful = cursor.fetchone()[0]
    success_rate = (successful / total_files * 100) if total_files > 0 else 0
    
    print(f"\n✅ Success Rate: {success_rate:.1f}% ({successful}/{total_files})")
    
    # Processing time statistics
    cursor.execute("SELECT AVG(processing_time), MIN(processing_time), MAX(processing_time) FROM call_records WHERE processing_time IS NOT NULL")
    time_stats = cursor.fetchone()
    if time_stats[0]:
        avg_time, min_time, max_time = time_stats
        print(f"\n⏱️ Processing Time Statistics:")
        print(f"  Average: {avg_time:.1f} seconds")
        print(f"  Minimum: {min_time:.1f} seconds")
        print(f"  Maximum: {max_time:.1f} seconds")
    
    # Audio duration statistics
    cursor.execute("SELECT AVG(audio_duration), MIN(audio_duration), MAX(audio_duration) FROM call_records WHERE audio_duration IS NOT NULL AND audio_duration > 0")
    duration_stats = cursor.fetchone()
    if duration_stats[0]:
        avg_duration, min_duration, max_duration = duration_stats
        print(f"\n🎵 Audio Duration Statistics:")
        print(f"  Average: {avg_duration/60:.1f} minutes")
        print(f"  Minimum: {min_duration/60:.1f} minutes")
        print(f"  Maximum: {max_duration/60:.1f} minutes")
    
    # Confidence score statistics
    cursor.execute("SELECT AVG(confidence_score), MIN(confidence_score), MAX(confidence_score) FROM call_records WHERE confidence_score IS NOT NULL")
    confidence_stats = cursor.fetchone()
    if confidence_stats[0]:
        avg_conf, min_conf, max_conf = confidence_stats
        print(f"\n🎯 Confidence Score Statistics:")
        print(f"  Average: {avg_conf:.3f}")
        print(f"  Minimum: {min_conf:.3f}")
        print(f"  Maximum: {max_conf:.3f}")
    
    # Intent distribution
    cursor.execute("SELECT intent, COUNT(*) FROM call_records WHERE intent IS NOT NULL GROUP BY intent ORDER BY COUNT(*) DESC")
    intent_results = cursor.fetchall()
    if intent_results:
        print(f"\n🧠 Intent Distribution:")
        for intent, count in intent_results:
            print(f"  {intent}: {count} calls")
    
    # Recent successful processing examples
    cursor.execute("""
        SELECT filename, audio_duration, processing_time, confidence_score, intent 
        FROM call_records 
        WHERE status LIKE '%SUCCESS%' 
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    recent_success = cursor.fetchall()
    
    if recent_success:
        print(f"\n🏆 Recent Successful Processing:")
        for filename, duration, proc_time, confidence, intent in recent_success:
            duration_min = duration/60 if duration else 0
            print(f"  📁 {filename}")
            print(f"    Duration: {duration_min:.1f}min | Processing: {proc_time:.1f}s | Confidence: {confidence:.2f} | Intent: {intent}")
    
    conn.close()

def validate_requirements():
    """Check if all required libraries are available"""
    required_libs = [
        'librosa', 'soundfile', 'numpy', 
        'google.cloud.speech', 'google.cloud.storage', 
        'google.cloud.translate', 'vertexai'
    ]
    
    missing_libs = []
    for lib in required_libs:
        try:
            __import__(lib.replace('.', '/'))
        except ImportError:
            missing_libs.append(lib)
    
    if missing_libs:
        print(f"❌ Missing required libraries: {', '.join(missing_libs)}")
        print("Please install them using:")
        for lib in missing_libs:
            if lib == 'librosa':
                print("  pip install librosa soundfile")
            elif lib == 'google.cloud.speech':
                print("  pip install google-cloud-speech google-cloud-storage google-cloud-translate")
            elif lib == 'vertexai':
                print("  pip install google-cloud-aiplatform")
        return False
    
    return True

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print("🚀 ENHANCED MARATHI AUDIO PROCESSING PIPELINE v2.0")
    print("=" * 60)
    print("✨ Features:")
    print("  - Advanced audio preprocessing")
    print("  - Optimized Marathi Speech-to-Text")
    print("  - Enhanced translation (Cloud API + Gemini 2.0)")
    print("  - Advanced intent analysis")
    print("  - Comprehensive error handling")
    print("=" * 60)
    
    # Validate requirements
    if not validate_requirements():
        print("Please install missing dependencies and try again.")
        exit(1)
    
    # Check bucket configuration
    if BUCKET_NAME == "your-unique-bucket-name-goes-here":
        print("❌ ERROR: Please update the BUCKET_NAME in the script!")
        exit(1)
    
    # Check audio folder
    if not os.path.exists(AUDIO_FOLDER):
        print(f"❌ Error: Audio folder '{AUDIO_FOLDER}' not found.")
        print(f"Please create the folder and add your Marathi audio files.")
        exit(1)
    
    # Setup
    setup_folders()
    setup_database()
    print(f"✅ Database '{DATABASE_NAME}' is ready")
    print(f"✅ Processing folder '{PROCESSED_FOLDER}' is ready")
    
    # Get audio files
    supported_formats = ('.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg')
    audio_files = [f for f in os.listdir(AUDIO_FOLDER) if f.lower().endswith(supported_formats)]
    
    if not audio_files:
        print(f"⚠️ No supported audio files found in '{AUDIO_FOLDER}' folder.")
        print(f"Supported formats: {', '.join(supported_formats)}")
        exit(1)
    
    print(f"📁 Found {len(audio_files)} audio files to process")
    print(f"Supported formats: {', '.join(supported_formats)}")
    
    # Estimate total processing time
    total_estimated_time = len(audio_files) * 5  # Rough estimate: 5 minutes per file
    print(f"⏱️ Estimated total processing time: {total_estimated_time/60:.1f} hours")
    print(f"   (Actual time depends on audio duration and system performance)")
    
    # Process each file
    start_time = time.time()
    for i, filename in enumerate(audio_files, 1):
        print(f"\n{'='*20} FILE {i}/{len(audio_files)} {'='*20}")
        file_path = os.path.join(AUDIO_FOLDER, filename)
        process_audio_file_enhanced(file_path, BUCKET_NAME)
        
        # Show progress
        elapsed = time.time() - start_time
        if i > 1:
            avg_time_per_file = elapsed / i
            remaining_files = len(audio_files) - i
            estimated_remaining = avg_time_per_file * remaining_files
            print(f"⏱️ Progress: {i}/{len(audio_files)} | Elapsed: {elapsed/60:.1f}min | ETA: {estimated_remaining/60:.1f}min")
    
    # Final summary
    total_time = time.time() - start_time
    print(f"\n{'='*60}")
    print("🎉 PROCESSING PIPELINE COMPLETED!")
    print(f"{'='*60}")
    print(f"⏱️ Total processing time: {total_time/60:.1f} minutes ({total_time/3600:.1f} hours)")
    print(f"📊 Average time per file: {total_time/len(audio_files)/60:.1f} minutes")
    
    print_detailed_database_summary()
    
    print(f"\n💾 Results saved in: {DATABASE_NAME}")
    print(f"📁 Check the database for complete transcription and analysis results")
    print(f"🔍 Use SQLite browser or run SQL queries to explore the data")
    
    print(f"\n📝 Sample SQL queries:")
    print(f"  SELECT * FROM call_records WHERE status LIKE '%SUCCESS%';")
    print(f"  SELECT intent, COUNT(*) FROM call_records GROUP BY intent;")
    print(f"  SELECT * FROM call_records ORDER BY confidence_score DESC LIMIT 10;")




# import os
# import sqlite3
# import json
# from google.cloud import speech
# import vertexai
# from vertexai.generative_models import GenerativeModel

# # --- CONFIGURATION ---
# PROJECT_ID = "healthy-saga-392716"  # IMPORTANT: Change this
# LOCATION = "us-central1"
# AUDIO_FOLDER = "audio_files"  # Create a folder named 'audio_files' and put your audio there
# DATABASE_NAME = "results.db"

# # --- INITIALIZE SERVICES ---
# vertexai.init(project=PROJECT_ID, location=LOCATION)
# speech_client = speech.SpeechClient()
# llm_model = GenerativeModel("gemini-2.0-flash-001")
# def setup_database():
#     """Creates the SQLite database and table if they don't exist."""
#     conn = sqlite3.connect(DATABASE_NAME)
#     cursor = conn.cursor()
#     cursor.execute('''
#         CREATE TABLE IF NOT EXISTS call_records (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             filename TEXT NOT NULL,
#             language_code TEXT,
#             transcript TEXT,
#             intent TEXT,
#             entities TEXT,
#             status TEXT
#         )
#     ''')
#     conn.commit()
#     conn.close()

# def transcribe_and_detect_language(audio_file_path):
#     """
#     Transcribes audio and automatically detects the language from a given list.
#     """
#     print(f"🔄 Processing file: {os.path.basename(audio_file_path)}")
#     with open(audio_file_path, "rb") as audio_file:
#         content = audio_file.read()

#     audio = speech.RecognitionAudio(content=content)
#     file_extension = os.path.splitext(audio_file_path)[1].lower()
#     # The key change for language detection is adding alternative_language_codes
#     if file_extension == ".mp3":
#         config = speech.RecognitionConfig(
#             encoding=speech.RecognitionConfig.AudioEncoding.MP3,
#             # sample_rate_hertz is not needed for MP3, the file has a header.
#             language_code="en-US",
#             alternative_language_codes=["hi-IN", "mr-IN", "gu-IN"],
#             enable_automatic_punctuation=True,
#         )
#     else: # Assume WAV or other uncompressed format
#         config = speech.RecognitionConfig(
#             encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
#             sample_rate_hertz=16000, # You might need to adjust this for your WAV files
#             language_code="en-US",
#             alternative_language_codes=["hi-IN", "mr-IN", "gu-IN"],
#             enable_automatic_punctuation=True,
#         )
#     # --- END OF THE FIX ---
#     try:
#         response = speech_client.recognize(config=config, audio=audio)
#         if not response.results:
#             print("  ⚠️ No speech could be transcribed.")
#             return None, None
        
#         # The API puts the result for the detected language first.
#         result = response.results[0]
#         detected_language = result.language_code
#         transcript = result.alternatives[0].transcript
        
#         print(f"  🗣️ Language Detected: {detected_language}")
#         print(f"  📜 Transcript: {transcript[:80]}...") # Print first 80 chars
#         return transcript, detected_language
#     except Exception as e:
#         print(f"  ❌ Error during transcription: {e}")
#         return None, None

# def extract_content_from_text(transcript):
#     """Uses Gemini to extract structured data from a transcript."""
#     if not transcript:
#         return None
    
#     prompt = f"""
#     Analyze the following conversation transcript. Identify the primary intent and extract key entities.
#     Possible intents: 'create_job', 'schedule_callback', 'confirm_interest', 'not_interested'.
#     Entities: 'date', 'time', 'worker_count', 'location', 'price', 'phone_number'.
#     Provide your output ONLY as a clean JSON object.

#     Transcript: "{transcript}"
#     JSON Output:
#     """
#     try:
#         response = llm_model.generate_content(prompt)
#         # Clean up the response to get pure JSON
#         json_text = response.text.strip().replace("```json", "").replace("```", "")
#         return json.loads(json_text)
#     except Exception as e:
#         print(f"  ❌ Error during content extraction: {e}")
#         return None

# # --- MOCK API FUNCTIONS (Replace these with your real API calls) ---
# def create_job_api(entities):
#     print(f"  ✅ ACTION: Calling Job Creation API. Details: {entities}")
#     return "SUCCESS"

# def schedule_callback_api(entities):
#     print(f"  ✅ ACTION: Calling Scheduler API for callback. Details: {entities}")
#     return "SUCCESS"

# def update_crm_api(entities):
#     print(f"  ✅ ACTION: Calling CRM Update API. Details: {entities}")
#     return "SUCCESS"

# def log_uninterested_api(entities):
#     print(f"  ✅ ACTION: Logging 'Not Interested' in CRM. Details: {entities}")
#     return "SUCCESS"

# def process_audio_file(filepath):
#     """Main processing function for a single audio file."""
#     filename = os.path.basename(filepath)
#     conn = sqlite3.connect(DATABASE_NAME)
#     cursor = conn.cursor()

#     transcript, lang_code = transcribe_and_detect_language(filepath)
#     if not transcript:
#         cursor.execute("INSERT INTO call_records (filename, status) VALUES (?, ?)", (filename, "TRANSCRIPTION_FAILED"))
#         conn.commit()
#         conn.close()
#         return

#     structured_data = extract_content_from_text(transcript)
#     if not structured_data:
#         cursor.execute("INSERT INTO call_records (filename, language_code, transcript, status) VALUES (?, ?, ?, ?)", 
#                        (filename, lang_code, transcript, "NLU_FAILED"))
#         conn.commit()
#         conn.close()
#         return

#     intent = structured_data.get('intent', 'unknown')
#     entities = structured_data.get('entities', {})

#     # The Action Dispatcher: maps intent string to the function to be called
#     action_mapper = {
#         'create_job': create_job_api,
#         'schedule_callback': schedule_callback_api,
#         'confirm_interest': update_crm_api,
#         'not_interested': log_uninterested_api
#     }

#     action_function = action_mapper.get(intent)
#     status = "ACTION_FAILED"
#     if action_function:
#         status = action_function(entities) # Call the appropriate mock API function
#     else:
#         print(f"  ⚠️ No action defined for intent: '{intent}'")
#         status = "NO_ACTION_DEFINED"
    
#     # Store everything in the database
#     cursor.execute(
#         "INSERT INTO call_records (filename, language_code, transcript, intent, entities, status) VALUES (?, ?, ?, ?, ?, ?)",
#         (filename, lang_code, transcript, intent, json.dumps(entities), status)
#     )
#     conn.commit()
#     conn.close()
#     print(f"  💾 Results for {filename} saved to database.")

# # --- MAIN EXECUTION ---
# if __name__ == "__main__":
#     if not os.path.exists(AUDIO_FOLDER):
#         print(f"Error: Folder '{AUDIO_FOLDER}' not found. Please create it and add your audio files.")
#     else:
#         setup_database()
#         print(f"Database '{DATABASE_NAME}' is ready.")
#         print("-" * 30)

#         for filename in os.listdir(AUDIO_FOLDER):
#             if filename.endswith((".wav", ".mp3", ".flac", ".raw")): # Add other formats if needed
#                 file_path = os.path.join(AUDIO_FOLDER, filename)
#                 process_audio_file(file_path)
#                 print("-" * 30)