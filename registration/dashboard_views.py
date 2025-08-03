from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Q, Avg
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
import json
import csv

from .models import IndividualLabor, Mukkadam, Transport, Others

@method_decorator(staff_member_required, name='dispatch')
class DashboardView(View):
    template_name = 'registration/dashboard.html'

    def get(self, request):
        # Get overall statistics
        stats = self.get_overall_stats()

        # Get recent registrations
        recent_registrations = self.get_recent_registrations()

        # Get registration trends (last 30 days)
        trends = self.get_registration_trends()

        # Get location data for map
        location_data = self.get_location_data()

        context = {
            'stats': stats,
            'recent_registrations': recent_registrations,
            'trends': trends,
            'location_data': location_data,
        }

        return render(request, self.template_name, context)

    def get_overall_stats(self):
        """Get overall registration statistics"""
        total_individual = IndividualLabor.objects.count()
        total_mukkadam = Mukkadam.objects.count()
        total_transport = Transport.objects.count()
        total_others = Others.objects.count()
        total_all = total_individual + total_mukkadam + total_transport + total_others

        # Recent registrations (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_individual = IndividualLabor.objects.filter(created_at__gte=week_ago).count()
        recent_mukkadam = Mukkadam.objects.filter(created_at__gte=week_ago).count()
        recent_transport = Transport.objects.filter(created_at__gte=week_ago).count()
        recent_others = Others.objects.filter(created_at__gte=week_ago).count()
        total_recent = recent_individual + recent_mukkadam + recent_transport + recent_others

        # Locations with GPS data
        locations_count = (
            IndividualLabor.objects.filter(location__isnull=False).count() +
            Mukkadam.objects.filter(location__isnull=False).count() +
            Transport.objects.filter(location__isnull=False).count() +
            Others.objects.filter(location__isnull=False).count()
        )

        # Photos captured
        photos_count = (
            IndividualLabor.objects.filter(photo__isnull=False).exclude(photo='').count() +
            Mukkadam.objects.filter(photo__isnull=False).exclude(photo='').count() +
            Transport.objects.filter(photo__isnull=False).exclude(photo='').count() +
            Others.objects.filter(photo__isnull=False).exclude(photo='').count()
        )

        return {
            'total_all': total_all,
            'total_individual': total_individual,
            'total_mukkadam': total_mukkadam,
            'total_transport': total_transport,
            'total_others': total_others,
            'total_recent': total_recent,
            'recent_individual': recent_individual,
            'recent_mukkadam': recent_mukkadam,
            'recent_transport': recent_transport,
            'recent_others': recent_others,
            'locations_count': locations_count,
            'photos_count': photos_count,
            'location_percentage': round((locations_count / total_all * 100) if total_all > 0 else 0, 1),
            'photo_percentage': round((photos_count / total_all * 100) if total_all > 0 else 0, 1),
        }

    def get_recent_registrations(self, limit=10):
        """Get most recent registrations across all categories"""
        registrations = []

        # Get recent from each category
        recent_individual = list(IndividualLabor.objects.select_related().order_by('-created_at')[:limit])
        recent_mukkadam = list(Mukkadam.objects.select_related().order_by('-created_at')[:limit])
        recent_transport = list(Transport.objects.select_related().order_by('-created_at')[:limit])
        recent_others = list(Others.objects.select_related().order_by('-created_at')[:limit])

        # Add category info
        for item in recent_individual:
            item.category_name = 'Individual Labor'
            item.category_icon = 'fas fa-user-hard-hat'
            item.category_color = 'primary'
            registrations.append(item)

        for item in recent_mukkadam:
            item.category_name = 'Mukkadam'
            item.category_icon = 'fas fa-users-cog'
            item.category_color = 'success'
            registrations.append(item)

        for item in recent_transport:
            item.category_name = 'Transport'
            item.category_icon = 'fas fa-truck'
            item.category_color = 'warning'
            registrations.append(item)

        for item in recent_others:
            item.category_name = 'Others'
            item.category_icon = 'fas fa-handshake'
            item.category_color = 'info'
            registrations.append(item)

        # Sort by created_at and limit
        registrations.sort(key=lambda x: x.created_at, reverse=True)
        return registrations[:limit]

    def get_registration_trends(self):
        """Get registration trends for the last 30 days"""
        thirty_days_ago = timezone.now() - timedelta(days=30)

        trends = []
        for i in range(30):
            date = thirty_days_ago + timedelta(days=i)
            date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date_start + timedelta(days=1)

            count_individual = IndividualLabor.objects.filter(
                created_at__gte=date_start, created_at__lt=date_end
            ).count()
            count_mukkadam = Mukkadam.objects.filter(
                created_at__gte=date_start, created_at__lt=date_end
            ).count()
            count_transport = Transport.objects.filter(
                created_at__gte=date_start, created_at__lt=date_end
            ).count()
            count_others = Others.objects.filter(
                created_at__gte=date_start, created_at__lt=date_end
            ).count()

            trends.append({
                'date': date.strftime('%Y-%m-%d'),
                'individual': count_individual,
                'mukkadam': count_mukkadam,
                'transport': count_transport,
                'others': count_others,
                'total': count_individual + count_mukkadam + count_transport + count_others
            })

        return trends

    def get_location_data(self):
        """Get location data for map visualization"""
        locations = []

        # Individual Labor locations
        for item in IndividualLabor.objects.filter(location__isnull=False):
            locations.append({
                'lat': item.location.y,
                'lng': item.location.x,
                'name': item.full_name,
                'category': 'Individual Labor',
                'village': item.village,
                'taluka': item.taluka,
                'phone': item.mobile_number,
                'color': '#007bff',
                'icon': 'user-hard-hat'
            })

        # Mukkadam locations
        for item in Mukkadam.objects.filter(location__isnull=False):
            locations.append({
                'lat': item.location.y,
                'lng': item.location.x,
                'name': item.full_name,
                'category': 'Mukkadam',
                'village': item.village,
                'taluka': item.taluka,
                'phone': item.mobile_number,
                'color': '#28a745',
                'icon': 'users-cog',
                'workers': getattr(item, 'providing_labour_count', 0)
            })

        # Transport locations
        for item in Transport.objects.filter(location__isnull=False):
            locations.append({
                'lat': item.location.y,
                'lng': item.location.x,
                'name': item.full_name,
                'category': 'Transport',
                'village': item.village,
                'taluka': item.taluka,
                'phone': item.mobile_number,
                'color': '#ffc107',
                'icon': 'truck',
                'vehicle': item.vehicle_type,
                'capacity': item.people_capacity
            })

        # Others locations
        for item in Others.objects.filter(location__isnull=False):
            locations.append({
                'lat': item.location.y,
                'lng': item.location.x,
                'name': item.full_name,
                'category': 'Others',
                'village': item.village,
                'taluka': item.taluka,
                'phone': item.mobile_number,
                'color': '#17a2b8',
                'icon': 'handshake',
                'business': item.business_name
            })

        return locations

@method_decorator(staff_member_required, name='dispatch')
class CategoryDetailView(View):
    template_name = 'registration/category_detail.html'

    def get(self, request, category):
        # Pagination
        page = request.GET.get('page', 1)
        search = request.GET.get('search', '')

        # Get model and data based on category
        if category == 'individual-labor':
            model = IndividualLabor
            queryset = model.objects.all()
            category_name = 'Individual Labor'
            category_icon = 'fas fa-user-hard-hat'
        elif category == 'mukkadam':
            model = Mukkadam
            queryset = model.objects.all()
            category_name = 'Mukkadam'
            category_icon = 'fas fa-users-cog'
        elif category == 'transport':
            model = Transport
            queryset = model.objects.all()
            category_name = 'Transport'
            category_icon = 'fas fa-truck'
        elif category == 'others':
            model = Others
            queryset = model.objects.all()
            category_name = 'Others'
            category_icon = 'fas fa-handshake'
        else:
            return render(request, '404.html', status=404)

        # Apply search filter
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(mobile_number__icontains=search) |
                Q(village__icontains=search) |
                Q(taluka__icontains=search)
            )

        # Order by most recent
        queryset = queryset.order_by('-created_at')

        # Pagination
        paginator = Paginator(queryset, 20)
        registrations = paginator.get_page(page)

        # Get category-specific statistics
        category_stats = self.get_category_stats(model)

        context = {
            'category': category,
            'category_name': category_name,
            'category_icon': category_icon,
            'registrations': registrations,
            'search': search,
            'category_stats': category_stats,
        }

        return render(request, self.template_name, context)

    def get_category_stats(self, model):
        """Get statistics specific to the category"""
        total_count = model.objects.count()
        with_location = model.objects.filter(location__isnull=False).count()
        with_photo = model.objects.filter(photo__isnull=False).exclude(photo='').count()

        # Recent registrations (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_count = model.objects.filter(created_at__gte=week_ago).count()

        stats = {
            'total_count': total_count,
            'with_location': with_location,
            'with_photo': with_photo,
            'recent_count': recent_count,
            'location_percentage': round((with_location / total_count * 100) if total_count > 0 else 0, 1),
            'photo_percentage': round((with_photo / total_count * 100) if total_count > 0 else 0, 1),
        }

        # Category-specific stats
        if model == IndividualLabor:
            stats.update({
                'avg_age': model.objects.aggregate(Avg('age'))['age__avg'] or 0,
                'male_count': model.objects.filter(gender='male').count(),
                'female_count': model.objects.filter(gender='female').count(),
                'want_training': model.objects.filter(want_training=True).count(),
            })
        elif model == Mukkadam:
            stats.update({
                'avg_workers': model.objects.aggregate(Avg('providing_labour_count'))['providing_labour_count__avg'] or 0,
                'with_transport': model.objects.exclude(arrange_transport='no').count(),
                'provide_tools': model.objects.filter(provide_tools=True).count(),
            })
        elif model == Transport:
            stats.update({
                'avg_capacity': model.objects.aggregate(Avg('people_capacity'))['people_capacity__avg'] or 0,
                'vehicle_types': model.objects.values('vehicle_type').annotate(count=Count('vehicle_type')),
            })
        elif model == Others:
            stats.update({
                'interested_referrals': model.objects.filter(interested_referrals=True).count(),
                'know_mukadams': model.objects.filter(know_mukadams_labourers=True).count(),
            })

        return stats

@staff_member_required
def export_data(request, category=None):
    """Export registration data as CSV"""
    response = HttpResponse(content_type='text/csv')

    if category:
        filename = f'{category}_registrations.csv'
    else:
        filename = 'all_registrations.csv'

    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    if category == 'individual-labor':
        # Individual Labor CSV
        writer.writerow(['Name', 'Mobile', 'Village', 'Taluka', 'Gender', 'Age', 'Skills', 'Expected Wage', 'Created'])
        for item in IndividualLabor.objects.all():
            skills = []
            if item.skill_pruning: skills.append('Pruning')
            if item.skill_harvesting: skills.append('Harvesting')
            if item.skill_dipping: skills.append('Dipping')
            if item.skill_thinning: skills.append('Thinning')
            if item.skill_other: skills.append(item.skill_other)

            writer.writerow([
                item.full_name, item.mobile_number, item.village, item.taluka,
                item.gender, item.age, ', '.join(skills), item.expected_wage,
                item.created_at.strftime('%Y-%m-%d %H:%M')
            ])

    elif category == 'mukkadam':
        # Mukkadam CSV
        writer.writerow(['Name', 'Mobile', 'Village', 'Taluka', 'Labor Count', 'Peak Workers', 'Charges', 'Transport', 'Created'])
        for item in Mukkadam.objects.all():
            writer.writerow([
                item.full_name, item.mobile_number, item.village, item.taluka,
                item.providing_labour_count, item.total_workers_peak, item.expected_charges,
                item.arrange_transport, item.created_at.strftime('%Y-%m-%d %H:%M')
            ])

    elif category == 'transport':
        # Transport CSV
        writer.writerow(['Name', 'Mobile', 'Village', 'Taluka', 'Vehicle Type', 'Capacity', 'Fair', 'Created'])
        for item in Transport.objects.all():
            writer.writerow([
                item.full_name, item.mobile_number, item.village, item.taluka,
                item.vehicle_type, item.people_capacity, item.expected_fair,
                item.created_at.strftime('%Y-%m-%d %H:%M')
            ])

    elif category == 'others':
        # Others CSV
        writer.writerow(['Name', 'Mobile', 'Village', 'Taluka', 'Business', 'Interested Referrals', 'Created'])
        for item in Others.objects.all():
            writer.writerow([
                item.full_name, item.mobile_number, item.village, item.taluka,
                item.business_name, item.interested_referrals,
                item.created_at.strftime('%Y-%m-%d %H:%M')
            ])

    else:
        # All categories CSV
        writer.writerow(['Name', 'Mobile', 'Village', 'Taluka', 'Category', 'Created'])

        for item in IndividualLabor.objects.all():
            writer.writerow([item.full_name, item.mobile_number, item.village, item.taluka, 'Individual Labor', item.created_at.strftime('%Y-%m-%d %H:%M')])

        for item in Mukkadam.objects.all():
            writer.writerow([item.full_name, item.mobile_number, item.village, item.taluka, 'Mukkadam', item.created_at.strftime('%Y-%m-%d %H:%M')])

        for item in Transport.objects.all():
            writer.writerow([item.full_name, item.mobile_number, item.village, item.taluka, 'Transport', item.created_at.strftime('%Y-%m-%d %H:%M')])

        for item in Others.objects.all():
            writer.writerow([item.full_name, item.mobile_number, item.village, item.taluka, 'Others', item.created_at.strftime('%Y-%m-%d %H:%M')])

    return response

@staff_member_required
def dashboard_api(request):
    """API endpoint for dashboard data"""
    action = request.GET.get('action')

    if action == 'chart_data':
        # Return chart data for visualization
        stats = DashboardView().get_overall_stats()
        chart_data = {
            'categories': ['Individual Labor', 'Mukkadam', 'Transport', 'Others'],
            'counts': [stats['total_individual'], stats['total_mukkadam'], stats['total_transport'], stats['total_others']],
            'colors': ['#007bff', '#28a745', '#ffc107', '#17a2b8']
        }
        return JsonResponse(chart_data)

    elif action == 'map_data':
        # Return location data for map
        locations = DashboardView().get_location_data()
        return JsonResponse({'locations': locations})

    elif action == 'trends':
        # Return trends data
        trends = DashboardView().get_registration_trends()
        return JsonResponse({'trends': trends})

    return JsonResponse({'error': 'Invalid action'}, status=400)