# registration/views.py

import base64
import uuid
import json
import logging
import math
import json
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from collections import defaultdict
from operator import itemgetter
from decimal import Decimal, InvalidOperation
from dateutil.parser import isoparse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from datetime import date, timedelta
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


# registration/views.py

# ... (imports)

# ADD contact_number to each leader
DUMMY_TEAM_LEADERS = [
    {'id': 1, 'name': 'Ramesh Patil', 'contact_number': '9876543210', 'avatar': 'https://i.pravatar.cc/150?u=kishor'},
    {'id': 2, 'name': 'Suresh Kadam', 'contact_number': '9876543211', 'avatar': 'https://i.pravatar.cc/150?u=kishor'},
    {'id': 3, 'name': 'Ganesh More', 'contact_number': '9876543212', 'avatar': 'https://i.pravatar.cc/150?u=kishor'},
    {'id': 4, 'name': 'Kishor Pawar', 'contact_number': '9876543213', 'avatar': 'https://i.pravatar.cc/150?u=kishor'},
]

DUMMY_LABORERS = [
    {'id': 101, 'name': 'Sunil Pawar', 'contact': '9876500101', 'location': 'Ojhar', 'skills': ['Pruning', 'Harvesting'], 'availability': 'Available', 'rating': 4.5, 'avatar': 'https://i.pravatar.cc/150?u=vikas'},
    {'id': 102, 'name': 'Anil Kumar', 'contact': '9876500102', 'location': 'Dindori', 'skills': ['Weeding', 'Spraying'], 'availability': 'On Job', 'rating': 4.2, 'avatar': 'https://i.pravatar.cc/150?u=vikas'},
    {'id': 103, 'name': 'Mahesh Shinde', 'contact': '9876500103', 'location': 'Pimpalgaon', 'skills': ['Harvesting', 'Tractor Operation'], 'availability': 'Available', 'rating': 4.8, 'avatar': 'https://i.pravatar.cc/150?u=vikas'},
    {'id': 104, 'name': 'Vikas Rathod', 'contact': '9876500104', 'location': 'Lasalgaon', 'skills': ['Pruning'], 'availability': 'Available', 'rating': 4.0, 'avatar': 'https://i.pravatar.cc/150?u=vikas'},
    {'id': 105, 'name': 'Prakash Jadhav', 'contact': '9876500105', 'location': 'Sinnar', 'skills': ['Weeding'], 'availability': 'Not Available', 'rating': 3.9, 'avatar': 'https://i.pravatar.cc/150?u=prakash'},
]

# --- ADD THIS NEW VIEW ---
# @method_decorator(staff_member_required, name='dispatch')
@login_required
def laborer_records_view(request):
    context = {
        'laborers': DUMMY_LABORERS
    }
    return render(request, 'registration/laborer_records.html', context)
# This is the full dataset we'll use for demonstration.
# In a real app, this would come from your database.

ALL_JOBS_DATA = [
      {'id': 11, 'status': 'Completed', 'title': 'June Pruning', 'workers_needed': 8, 'duration_days': 5, 'finalized_leader': {'name': 'Ramesh Patil', 'final_price': 530}, 'completion_date': date(2025, 6, 15), 'sent_to': [{'leader_id': 1, 'response': 'Accepted', 'quoted_price': 530}, {'leader_id': 2, 'response': 'Rejected'}]},
    {'id': 12, 'status': 'Completed', 'title': 'July Weeding', 'workers_needed': 10, 'duration_days': 3, 'finalized_leader': {'name': 'Suresh Kadam', 'final_price': 480}, 'completion_date': date(2025, 7, 20), 'sent_to': [{'leader_id': 1, 'response': 'Rejected'}, {'leader_id': 2, 'response': 'Accepted', 'quoted_price': 480}, {'leader_id': 3, 'response': 'Accepted', 'quoted_price': 490}]},
    {'id': 13, 'status': 'Completed', 'title': 'July HCN Spray', 'workers_needed': 5, 'duration_days': 2, 'finalized_leader': {'name': 'Ramesh Patil', 'final_price': 600}, 'completion_date': date(2025, 7, 28), 'sent_to': [{'leader_id': 1, 'response': 'Accepted', 'quoted_price': 600}, {'leader_id': 4, 'response': 'Accepted', 'quoted_price': 610}]},
    {'id': 14, 'status': 'Ongoing', 'title': 'August Harvesting', 'workers_needed': 15, 'duration_days': 10, 'finalized_leader': {'name': 'Ganesh More', 'final_price': 550}, 'sent_to': [{'leader_id': 3, 'response': 'Accepted', 'quoted_price': 550}]},
    {'id': 17, 'status': 'Open for Bidding', 'title': 'Tractor Operation', 'bids': [{'leader_name': 'Kishor Pawar', 'bid_price': 1150}, {'leader_name': 'Ramesh Patil', 'bid_price': 1180}]},

       # --- Jobs for the Bidding System (These are the ones that should appear) ---
    {'id': 7, 'created_at': date.today(), 'required_by_date': date.today() + timedelta(days=3), 'title': 'Urgent Tractor Operation', 'status': 'Open for Bidding', 'status_class': 'pending', 'location': 'Nashik City', 'duration_days': 1, 'workers_needed': 2, 'initial_price': 1200, 'bids': [
        {'leader_name': 'Kishor Pawar', 'bid_price': 1150, 'timestamp': '2 hours ago'},
        {'leader_name': 'Ramesh Patil', 'bid_price': 1180, 'timestamp': '1 hour ago'},
    ]},
    {'id': 8, 'created_at': date.today() - timedelta(days=1), 'required_by_date': date.today() + timedelta(days=6), 'title': 'Pesticide Spraying', 'status': 'Open for Bidding', 'status_class': 'pending', 'location': 'Igatpuri', 'duration_days': 2, 'workers_needed': 4, 'initial_price': 600, 'bids': []}, # No bids yet
    
    # A new job, less than 2 days old, waiting for allocation.
    {'id': 1, 'created_at': date.today(), 'required_by_date': date.today() + timedelta(days=5), 'title': 'NEW: Pruning - Skilled', 'status': 'Pending', 'status_class': 'pending', 'competition': 'Good Chance', 'competition_class': 'good-chance', 'dates': 'Fixed Dates', 'location': 'Ojhar, Niphad', 'duration_days': 3, 'workers_needed': 8, 'rate': 520, 'contact_number': '9876543210'},
      {'id': 11, 'created_at': date.today(), 'required_by_date': date.today() + timedelta(days=5), 'title': 'NEW: Pruning - Skilled', 'status': 'Pending', 'status_class': 'pending', 'competition': 'Good Chance', 'competition_class': 'good-chance', 'dates': 'Fixed Dates', 'location': 'Ojhar, Niphad', 'duration_days': 3, 'workers_needed': 8, 'rate': 520, 'contact_number': '9876543210'},

    # An older job, also waiting for allocation.
    {'id': 6, 'created_at': date.today() - timedelta(days=3), 'required_by_date': date.today() + timedelta(days=3), 'title': 'OLD: Pending Allocation Job', 'status': 'Pending', 'status_class': 'pending', 'competition': 'Moderate', 'competition_class': 'moderate', 'dates': 'Fixed Dates', 'location': 'Yeola, Yeola', 'duration_days': 7, 'workers_needed': 4, 'rate': 470, 'contact_number': '9876543215'},
    
    # A job where requests were sent and we are waiting for responses.
    {'id': 2, 'created_at': date.today() - timedelta(days=3), 'required_by_date': date.today() + timedelta(days=2), 'title': 'Urgent Weeding', 'status': 'Waiting for Response', 'status_class': 'allocated', 'competition': 'High Competition', 'competition_class': 'high-competition', 'dates': 'Urgent', 'location': 'Dindori, Dindori', 'duration_days': 4, 'workers_needed': 10, 'rate': 450, 'contact_number': '9876543211', 
     'sent_to': [
         {'leader_id': 1, 'name': 'Ramesh Patil', 'response': 'Accepted', 'quoted_price': 460, 'available_workers': ['Sunil', 'Anil', 'Mahesh', 'Vikas', 'Prakash']},
         {'leader_id': 2, 'name': 'Suresh Kadam', 'response': 'Rejected', 'reason': 'Team already booked'},
         {'leader_id': 3, 'name': 'Ganesh More', 'response': 'Pending'},
     ]},

    # A job that has been finalized with a leader and is now in progress.
    {'id': 3, 'created_at': date.today() - timedelta(days=5), 'required_by_date': date.today() + timedelta(days=12), 'title': 'HCN Application Team', 'status': 'Ongoing', 'status_class': 'ongoing', 'competition': 'High Competition', 'competition_class': 'high-competition', 'dates': 'Fixed Dates', 'location': 'Lasalgaon, Niphad', 'duration_days': 2, 'workers_needed': 5, 'rate': 480, 'contact_number': '9876543212', 
     'finalized_leader': {'name': 'Ganesh More', 'final_price': 490, 'workers': ['Amit', 'Raju', 'Pintu', 'Sonu', 'Monu']}},
    
    # A job that has been completed.
    {'id': 5, 'created_at': date.today() - timedelta(days=10), 'required_by_date': date.today() - timedelta(days=2), 'title': 'Weeding and Cleanup', 'status': 'Completed', 'status_class': 'completed', 'competition': 'Low', 'competition_class': 'good-chance', 'dates': 'Fixed Dates', 'location': 'Sinnar, Sinnar', 'duration_days': 5, 'workers_needed': 6, 'rate': 430, 'contact_number': '9876543214'},
]

# This view now handles the 2-day rule for 'Latest' vs 'Pending'
# @method_decorator(staff_member_required, name='dispatch')
@login_required
def job_requests_view(request):
    today = date.today()
    two_days_ago = today - timedelta(days=2)

    latest_jobs, pending_jobs, ongoing_jobs, completed_jobs = [], [], [], []

    for job in ALL_JOBS_DATA:
        if job['status'] == 'Completed':
            completed_jobs.append(job)
        elif job['status'] == 'Pending' and job['created_at'] >= two_days_ago:
            latest_jobs.append(job)
        elif job['status'] == 'Pending' and job['created_at'] < two_days_ago:
            pending_jobs.append(job)
        elif job['status'] in ['Ongoing', 'Team Allocated', 'Waiting for Response']:
            ongoing_jobs.append(job)

    latest_jobs.sort(key=lambda j: j['created_at'], reverse=True)
    
    context = {
        'all_jobs': ALL_JOBS_DATA,
        'latest_jobs': latest_jobs,
        'pending_jobs': pending_jobs,
        'ongoing_jobs': ongoing_jobs,
        'completed_jobs': completed_jobs,
        'team_leaders': DUMMY_TEAM_LEADERS, # Pass leaders to the template
        'today_date': today.isoformat(),
    }
    return render(request, 'registration/job_requests.html', context)

# @method_decorator(staff_member_required, name='dispatch')
@login_required
def job_response_view(request, job_id):
    job_data = next((job for job in ALL_JOBS_DATA if job['id'] == job_id), None)
    
    if not job_data:
        return redirect('registration:job_requests')

    context = {'job': job_data}
    return render(request, 'registration/job_response_screen.html', context)


# @method_decorator(staff_member_required, name='dispatch')
@login_required
def bidding_dashboard_view(request):
    # Find all jobs that are currently open for bidding
    bidding_jobs = [job for job in ALL_JOBS_DATA if job.get('status') == 'Open for Bidding']
    context = {
        'bidding_jobs': bidding_jobs
    }
    return render(request, 'registration/bidding_dashboard.html', context)

# @method_decorator(staff_member_required, name='dispatch')
@login_required
def view_bids_view(request, job_id):
    # Find the specific job by its ID
    job_data = next((job for job in ALL_JOBS_DATA if job.get('id') == job_id), None)
    
    if not job_data:
        return redirect('registration:bidding_dashboard')

    # Sort the bids by the lowest price first
    sorted_bids = sorted(job_data.get('bids', []), key=itemgetter('bid_price'))
    
    context = {
        'job': job_data,
        'bids': sorted_bids,
    }
    return render(request, 'registration/view_bids.html', context)


# ==============================================================================
# @method_decorator(staff_member_required, name='dispatch')
@login_required
def leader_records_view(request):
    leader_stats = {
        leader['id']: {
            'id': leader['id'], # <--- THIS IS THE FIX: We add the id to the dictionary itself
            'name': leader['name'],
            'avatar': leader['avatar'],
            'jobs_completed': 0,
            'total_workers_managed': 0,
            'bids_placed': 0,
            'bids_rejected': 0,
            'bids_won': 0,
            'total_earnings': 0,
            'bid_prices': [], # To calculate average
            'completed_jobs_history': []
        }
        for leader in DUMMY_TEAM_LEADERS
    }
    for job in ALL_JOBS_DATA:
        if job.get('finalized_leader'):
            leader_name = job['finalized_leader']['name']
            leader = next((l for l in DUMMY_TEAM_LEADERS if l['name'] == leader_name), None)
            if leader:
                leader_id = leader['id']
                leader_stats[leader_id]['bids_won'] += 1
                if job['status'] == 'Completed':
                    leader_stats[leader_id]['jobs_completed'] += 1
                    job_earning = job['finalized_leader']['final_price'] * job['duration_days']
                    leader_stats[leader_id]['total_earnings'] += job_earning
    
    context = {'leader_records': list(leader_stats.values())}
    return render(request, 'registration/leader_records.html', context)
# registration/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q # Required for complex lookups
from .models import BaseRegistration, IndividualLabor, Mukkadam, Transport, Others
from itertools import chain
from operator import attrgetter

# ... (keep all your existing views) ...

@login_required
def all_laborers_view(request):
    # Get filter parameters from the URL
    category_filter = request.GET.get('category', '')
    location_filter = request.GET.get('location', '')
    price_filter = request.GET.get('price', '')

    # Fetch initial querysets
    querysets = {
        'individual_labor': IndividualLabor.objects.all(),
        'mukkadam': Mukkadam.objects.all(),
        'transport': Transport.objects.all(),
        'others': Others.objects.all(),
    }
    
    # --- Filtering Logic ---
    # 1. Filter by Category
    if category_filter:
        # If a category is selected, only use that queryset
        all_registrations_list = list(querysets.get(category_filter, []))
    else:
        # Otherwise, combine all of them
        all_registrations_list = list(chain(*querysets.values()))

    # 2. Filter by Location (searches village or taluka)
    if location_filter:
        all_registrations_list = [
            reg for reg in all_registrations_list 
            if location_filter.lower() in reg.village.lower() or location_filter.lower() in reg.taluka.lower()
        ]

    # 3. Filter by Price
    if price_filter:
        min_price, max_price = map(int, price_filter.split('-'))
        filtered_by_price = []
        for reg in all_registrations_list:
            price = 0
            if hasattr(reg, 'expected_wage'): price = reg.expected_wage
            elif hasattr(reg, 'expected_charges'): price = reg.expected_charges
            elif hasattr(reg, 'expected_fair'): price = reg.expected_fair
            
            if price and min_price <= price <= max_price:
                filtered_by_price.append(reg)
        all_registrations_list = filtered_by_price
            
    # Sort the final list by date
    sorted_list = sorted(all_registrations_list, key=attrgetter('created_at'), reverse=True)
    
    # Set up pagination for the final filtered and sorted list
    paginator = Paginator(sorted_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'category_choices': BaseRegistration.CATEGORY_CHOICES, # Pass choices to the template
        # Pass current filter values back to the template to keep them selected
        'current_filters': {
            'category': category_filter,
            'location': location_filter,
            'price': price_filter,
        }
    }
    return render(request, 'registration/all_laborers.html', context)
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout # Import auth functions
from django.contrib.auth.forms import AuthenticationForm # Import the built-in login form

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # After successful login, redirect them to the All Laborers page
                return redirect('registration:leader_dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

def logout_view(request):
    logout(request)
    # After logout, redirect them back to the login page
    return redirect('registration:login')

@login_required
def leader_dashboard_view(request):
    # DUMMY DATA: Simulate jobs assigned to the currently logged-in leader
    assigned_jobs = [
        {'id': 2, 'title': 'Urgent Weeding', 'location': 'Dindori', 'workers_needed': 10, 'status': 'Awaiting Team'},
        {'id': 4, 'title': 'Grape Harvesting', 'location': 'Pimpalgaon', 'workers_needed': 15, 'status': 'In Progress'},
    ]
     # In a real app, this would come from a Notification model in your database
    notifications = [
        {'title': 'New Job Assigned', 'message': 'You have been assigned the "Urgent Weeding" task.', 'received': '5 minutes ago', 'is_read': False},
        {'title': 'Job Completed', 'message': 'The "June Pruning" job has been marked as complete.', 'received': '2 hours ago', 'is_read': False},
        {'title': 'Payment Received', 'message': 'Payment for "July Weeding" has been processed.', 'received': '1 day ago', 'is_read': True},
    ]
     # --- THIS IS THE NEW LOGIC ---
    # Count the unread notifications using a simple Python list comprehension
    unread_count = len([n for n in notifications if not n['is_read']])
    # --- END OF NEW LOGIC ---

    context = {
        'assigned_jobs': assigned_jobs,
        'notifications': notifications,
        'unread_count': unread_count, # Pass the final count to the template
    }
    return render(request, 'registration/leader_dashboard.html', context)

@login_required
def find_laborers_view(request): # Renamed from all_laborers_view
    category_filter = request.GET.get('category', '')
    location_filter = request.GET.get('location', '')
    price_filter = request.GET.get('price', '')

    # Fetch initial querysets
    querysets = {
        'individual_labor': IndividualLabor.objects.all(),
        'mukkadam': Mukkadam.objects.all(),
        'transport': Transport.objects.all(),
        'others': Others.objects.all(),
    }
    
    # --- Filtering Logic ---
    # 1. Filter by Category
    if category_filter:
        # If a category is selected, only use that queryset
        all_registrations_list = list(querysets.get(category_filter, []))
    else:
        # Otherwise, combine all of them
        all_registrations_list = list(chain(*querysets.values()))

    # 2. Filter by Location (searches village or taluka)
    if location_filter:
        all_registrations_list = [
            reg for reg in all_registrations_list 
            if location_filter.lower() in reg.village.lower() or location_filter.lower() in reg.taluka.lower()
        ]

    # 3. Filter by Price
    if price_filter:
        min_price, max_price = map(int, price_filter.split('-'))
        filtered_by_price = []
        for reg in all_registrations_list:
            price = 0
            if hasattr(reg, 'expected_wage'): price = reg.expected_wage
            elif hasattr(reg, 'expected_charges'): price = reg.expected_charges
            elif hasattr(reg, 'expected_fair'): price = reg.expected_fair
            
            if price and min_price <= price <= max_price:
                filtered_by_price.append(reg)
        all_registrations_list = filtered_by_price
            
    # Sort the final list by date
    sorted_list = sorted(all_registrations_list, key=attrgetter('created_at'), reverse=True)
    
    # Set up pagination for the final filtered and sorted list
    paginator = Paginator(sorted_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'category_choices': BaseRegistration.CATEGORY_CHOICES, # Pass choices to the template
        # Pass current filter values back to the template to keep them selected
        'current_filters': {
            'category': category_filter,
            'location': location_filter,
            'price': price_filter,
        }
    }
    return render(request, 'registration/find_laborers.html', context)

@login_required
def find_laborerss_view(request): # Renamed from all_laborers_view
    category_filter = request.GET.get('category', '')
    location_filter = request.GET.get('location', '')
    price_filter = request.GET.get('price', '')

    # Fetch initial querysets
    querysets = {
        'individual_labor': IndividualLabor.objects.all(),
        'mukkadam': Mukkadam.objects.all(),
        'transport': Transport.objects.all(),
        'others': Others.objects.all(),
    }
    
    # --- Filtering Logic ---
    # 1. Filter by Category
    if category_filter:
        # If a category is selected, only use that queryset
        all_registrations_list = list(querysets.get(category_filter, []))
    else:
        # Otherwise, combine all of them
        all_registrations_list = list(chain(*querysets.values()))

    # 2. Filter by Location (searches village or taluka)
    if location_filter:
        all_registrations_list = [
            reg for reg in all_registrations_list 
            if location_filter.lower() in reg.village.lower() or location_filter.lower() in reg.taluka.lower()
        ]

    # 3. Filter by Price
    if price_filter:
        min_price, max_price = map(int, price_filter.split('-'))
        filtered_by_price = []
        for reg in all_registrations_list:
            price = 0
            if hasattr(reg, 'expected_wage'): price = reg.expected_wage
            elif hasattr(reg, 'expected_charges'): price = reg.expected_charges
            elif hasattr(reg, 'expected_fair'): price = reg.expected_fair
            
            if price and min_price <= price <= max_price:
                filtered_by_price.append(reg)
        all_registrations_list = filtered_by_price
            
    # Sort the final list by date
    sorted_list = sorted(all_registrations_list, key=attrgetter('created_at'), reverse=True)
    
    # Set up pagination for the final filtered and sorted list
    paginator = Paginator(sorted_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'category_choices': BaseRegistration.CATEGORY_CHOICES, # Pass choices to the template
        # Pass current filter values back to the template to keep them selected
        'current_filters': {
            'category': category_filter,
            'location': location_filter,
            'price': price_filter,
        }
    }
    return render(request, 'registration/find-laborers.html', context)
    

# @method_decorator(staff_member_required, name='dispatch')
@login_required
def leader_detail_view(request, leader_id):

    leader_info = next((l for l in DUMMY_TEAM_LEADERS if l.get('id') == leader_id), None)
    if not leader_info:
        return redirect('registration:leader_records')

    # --- 1. Calculate All KPIs for this specific leader ---
    stats = {
        'jobs_completed': 0, 'total_workers': 0, 'total_earnings': 0, 'bids_placed': 0, 
        'bids_rejected': 0, 'bids_won': 0, 'bid_prices': [], 'completed_jobs_history': []
    }
    monthly_earnings = defaultdict(float)

    for job in ALL_JOBS_DATA:
        # Calculate bidding stats
        if 'sent_to' in job:
            for response in job['sent_to']:
                if response.get('leader_id') == leader_id:
                    stats['bids_placed'] += 1
                    if response.get('response') == 'Rejected':
                        stats['bids_rejected'] += 1
                    elif response.get('response') == 'Accepted':
                        stats['bid_prices'].append(response.get('quoted_price', 0))
        
        # Calculate won & completed stats
        if job.get('finalized_leader') and job['finalized_leader'].get('name') == leader_info['name']:
            stats['bids_won'] += 1
            if job.get('status') == 'Completed':
                stats['jobs_completed'] += 1
                stats['total_workers'] += job.get('workers_needed', 0)
                earning = job['finalized_leader'].get('final_price', 0) * job.get('duration_days', 0)
                stats['total_earnings'] += earning
                stats['completed_jobs_history'].append(job) # Add the whole job dict
                
                # For the earnings chart
                if job.get('completion_date'):
                    month_name = job['completion_date'].strftime("%B %Y")
                    monthly_earnings[month_name] += earning

    # Final calculations for rates and averages
    stats['acceptance_rate'] = round(((stats['bids_placed'] - stats['bids_rejected']) / stats['bids_placed']) * 100) if stats['bids_placed'] > 0 else 0
    stats['win_rate'] = round((stats['bids_won'] / stats['bids_placed']) * 100) if stats['bids_placed'] > 0 else 0
    stats['avg_bid_price'] = round(sum(stats['bid_prices']) / len(stats['bid_prices'])) if stats['bid_prices'] else 0

    # --- 2. Prepare Data for Charts using json.dumps() ---
    
    # Sort monthly earnings for a logical chart
    sorted_months = sorted(monthly_earnings.keys())
    sorted_earnings = [monthly_earnings[month] for month in sorted_months]

    earnings_chart_labels = json.dumps(sorted_months)
    earnings_chart_data = json.dumps(sorted_earnings)
    
    # Bidding Behavior Chart
    bids_lost = stats['bids_placed'] - stats['bids_won'] - stats['bids_rejected']
    bidding_chart_labels = json.dumps(['Bids Won', 'Bids Lost', 'Bids Rejected'])
    bidding_chart_data = json.dumps([stats['bids_won'], bids_lost, stats['bids_rejected']])

    context = {
        'leader': leader_info,
        'stats': stats,
        'earnings_chart_labels': earnings_chart_labels,
        'earnings_chart_data': earnings_chart_data,
        'bidding_chart_labels': bidding_chart_labels,
        'bidding_chart_data': bidding_chart_data
    }
    return render(request, 'registration/leader_detail.html', context)