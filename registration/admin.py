from django.contrib import admin
from django.utils.html import format_html
from .models import IndividualLabor, Mukkadam, Transport, Others

# @admin.register(IndividualLabor)
# class IndividualLaborAdmin(admin.ModelAdmin):
#     list_display = [
#         'full_name', 'mobile_number', 'village', 'taluka',
#         'gender', 'age', 'employment_type', 'expected_wage',
#         'location_display', 'data_sharing_agreement', 'created_at'
#     ]
#     list_filter = [
#         'gender', 'employment_type', 'willing_to_migrate',
#         'want_training', 'data_sharing_agreement', 'taluka', 'created_at'
#     ]
#     search_fields = ['full_name', 'mobile_number', 'whatsapp_number', 'village', 'taluka']
#     readonly_fields = ['created_at', 'updated_at', 'photo_preview', 'location_info']

#     fieldsets = (
#         ('Basic Information', {
#             'fields': (
#                 'full_name', 'mobile_number', 'whatsapp_number',
#                 'taluka', 'village', 'home_address', 'photo', 'photo_preview'
#             )
#         }),
#         ('Location Information', {
#             'fields': ('location_info', 'location_accuracy', 'location_timestamp'),
#             'classes': ('collapse',)
#         }),
#         ('Personal Details', {
#             'fields': ('gender', 'age', 'primary_source_income')
#         }),
#         ('Skills', {
#             'fields': (
#                 'skill_pruning', 'skill_harvesting', 'skill_dipping',
#                 'skill_thinning', 'skill_none', 'skill_other'
#             ),
#             'classes': ('collapse',)
#         }),
#         ('Employment Preferences', {
#             'fields': (
#                 'employment_type', 'willing_to_migrate', 'expected_wage',
#                 'availability', 'want_training'
#             )
#         }),
#         ('Communication Preferences', {
#             'fields': (
#                 'comm_mobile_app', 'comm_whatsapp', 'comm_calling',
#                 'comm_sms', 'comm_other'
#             ),
#             'classes': ('collapse',)
#         }),
#         ('Household Information', {
#             'fields': ('adult_men_seeking_employment', 'adult_women_seeking_employment')
#         }),
#         ('Referrals', {
#             'fields': ('can_refer_others', 'referral_name', 'referral_contact'),
#             'classes': ('collapse',)
#         }),
#         ('System', {
#             'fields': ('data_sharing_agreement', 'created_at', 'updated_at'),
#             'classes': ('collapse',)
#         })
#     )

#     def photo_preview(self, obj):
#         if obj.photo:
#             return format_html('<img src="{}" width="100" height="100" style="border-radius: 50%;" />', obj.photo.url)
#         return "No photo uploaded"
#     photo_preview.short_description = 'Photo Preview'

#     def location_display(self, obj):
#         if obj.location:
#             return f"{obj.location.y:.6f}, {obj.location.x:.6f}"
#         return "No location"
#     location_display.short_description = 'GPS Location'

#     def location_info(self, obj):
#         if obj.location:
#             html = f'''
#             <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6;">
#                 <h4 style="margin-top: 0; color: #495057;">📍 Location Details</h4>
#                 <p><strong>Coordinates:</strong> {obj.location.y:.6f}, {obj.location.x:.6f}</p>
#                 <p><strong>Accuracy:</strong> {obj.get_location_accuracy_display()}</p>
#                 <p><strong>Captured:</strong> {obj.location_timestamp.strftime('%Y-%m-%d %H:%M:%S') if obj.location_timestamp else 'Unknown'}</p>
#                 <a href="https://www.google.com/maps?q={obj.location.y},{obj.location.x}" target="_blank"
#                    style="background: #007bff; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block; margin-top: 10px;">
#                     📱 View on Google Maps
#                 </a>
#             </div>
#             '''
#             return format_html(html)
#         return format_html('<p style="color: #dc3545;">No location data available</p>')
#     location_info.short_description = 'Location Information'

#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related()

# @admin.register(Mukkadam)
# class MukkadamAdmin(admin.ModelAdmin):
#     list_display = [
#         'full_name', 'mobile_number', 'village', 'taluka',
#         'providing_labour_count', 'total_workers_peak', 'expected_charges',
#         'arrange_transport', 'provide_tools', 'location_display', 'created_at'
#     ]
#     list_filter = [
#         'arrange_transport', 'provide_tools', 'data_sharing_agreement',
#         'taluka', 'created_at'
#     ]
#     search_fields = ['full_name', 'mobile_number', 'whatsapp_number', 'village', 'taluka']
#     readonly_fields = ['created_at', 'updated_at', 'photo_preview', 'location_info']

#     fieldsets = (
#         ('Basic Information', {
#             'fields': (
#                 'full_name', 'mobile_number', 'whatsapp_number',
#                 'taluka', 'village', 'home_address', 'photo', 'photo_preview'
#             )
#         }),
#         ('Location Information', {
#             'fields': ('location_info', 'location_accuracy', 'location_timestamp'),
#             'classes': ('collapse',)
#         }),
#         ('Labor Management', {
#             'fields': (
#                 'providing_labour_count', 'total_workers_peak',
#                 'expected_charges', 'labour_supply_availability'
#             )
#         }),
#         ('Skills Available', {
#             'fields': (
#                 'skill_pruning', 'skill_harvesting', 'skill_dipping',
#                 'skill_thinning', 'skill_none', 'skill_other'
#             ),
#             'classes': ('collapse',)
#         }),
#         ('Services', {
#             'fields': (
#                 'arrange_transport', 'transport_other',
#                 'provide_tools', 'supply_areas'
#             )
#         }),
#         ('System', {
#             'fields': ('data_sharing_agreement', 'created_at', 'updated_at'),
#             'classes': ('collapse',)
#         })
#     )

#     def photo_preview(self, obj):
#         if obj.photo:
#             return format_html('<img src="{}" width="100" height="100" style="border-radius: 50%;" />', obj.photo.url)
#         return "No photo uploaded"
#     photo_preview.short_description = 'Photo Preview'

#     def location_display(self, obj):
#         if obj.location:
#             return f"{obj.location.y:.6f}, {obj.location.x:.6f}"
#         return "No location"
#     location_display.short_description = 'GPS Location'

#     def location_info(self, obj):
#         if obj.location:
#             html = f'''
#             <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6;">
#                 <h4 style="margin-top: 0; color: #495057;">📍 Location Details</h4>
#                 <p><strong>Coordinates:</strong> {obj.location.y:.6f}, {obj.location.x:.6f}</p>
#                 <p><strong>Accuracy:</strong> {obj.get_location_accuracy_display()}</p>
#                 <p><strong>Captured:</strong> {obj.location_timestamp.strftime('%Y-%m-%d %H:%M:%S') if obj.location_timestamp else 'Unknown'}</p>
#                 <a href="https://www.google.com/maps?q={obj.location.y},{obj.location.x}" target="_blank"
#                    style="background: #007bff; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block; margin-top: 10px;">
#                     📱 View on Google Maps
#                 </a>
#             </div>
#             '''
#             return format_html(html)
#         return format_html('<p style="color: #dc3545;">No location data available</p>')
#     location_info.short_description = 'Location Information'

# @admin.register(Transport)
# class TransportAdmin(admin.ModelAdmin):
#     list_display = [
#         'full_name', 'mobile_number', 'village', 'taluka',
#         'vehicle_type', 'people_capacity', 'expected_fair',
#         'location_display', 'created_at'
#     ]
#     list_filter = ['vehicle_type', 'data_sharing_agreement', 'taluka', 'created_at']
#     search_fields = ['full_name', 'mobile_number', 'whatsapp_number', 'village', 'taluka', 'vehicle_type']
#     readonly_fields = ['created_at', 'updated_at', 'photo_preview', 'location_info']

#     fieldsets = (
#         ('Basic Information', {
#             'fields': (
#                 'full_name', 'mobile_number', 'whatsapp_number',
#                 'taluka', 'village', 'home_address', 'photo', 'photo_preview'
#             )
#         }),
#         ('Location Information', {
#             'fields': ('location_info', 'location_accuracy', 'location_timestamp'),
#             'classes': ('collapse',)
#         }),
#         ('Vehicle Information', {
#             'fields': (
#                 'vehicle_type', 'people_capacity', 'expected_fair',
#                 'availability', 'service_areas'
#             )
#         }),
#         ('System', {
#             'fields': ('data_sharing_agreement', 'created_at', 'updated_at'),
#             'classes': ('collapse',)
#         })
#     )

#     def photo_preview(self, obj):
#         if obj.photo:
#             return format_html('<img src="{}" width="100" height="100" style="border-radius: 50%;" />', obj.photo.url)
#         return "No photo uploaded"
#     photo_preview.short_description = 'Photo Preview'

#     def location_display(self, obj):
#         if obj.location:
#             return f"{obj.location.y:.6f}, {obj.location.x:.6f}"
#         return "No location"
#     location_display.short_description = 'GPS Location'

#     def location_info(self, obj):
#         if obj.location:
#             html = f'''
#             <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6;">
#                 <h4 style="margin-top: 0; color: #495057;">📍 Location Details</h4>
#                 <p><strong>Coordinates:</strong> {obj.location.y:.6f}, {obj.location.x:.6f}</p>
#                 <p><strong>Accuracy:</strong> {obj.get_location_accuracy_display()}</p>
#                 <p><strong>Captured:</strong> {obj.location_timestamp.strftime('%Y-%m-%d %H:%M:%S') if obj.location_timestamp else 'Unknown'}</p>
#                 <a href="https://www.google.com/maps?q={obj.location.y},{obj.location.x}" target="_blank"
#                    style="background: #007bff; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block; margin-top: 10px;">
#                     📱 View on Google Maps
#                 </a>
#             </div>
#             '''
#             return format_html(html)
#         return format_html('<p style="color: #dc3545;">No location data available</p>')
#     location_info.short_description = 'Location Information'

# @admin.register(Others)
# class OthersAdmin(admin.ModelAdmin):
#     list_display = [
#         'full_name', 'mobile_number', 'village', 'taluka',
#         'business_name', 'interested_referrals', 'know_mukadams_labourers',
#         'location_display', 'created_at'
#     ]
#     list_filter = [
#         'interested_referrals', 'know_mukadams_labourers',
#         'data_sharing_agreement', 'taluka', 'created_at'
#     ]
#     search_fields = [
#         'full_name', 'mobile_number', 'whatsapp_number',
#         'village', 'taluka', 'business_name'
#     ]
#     readonly_fields = ['created_at', 'updated_at', 'photo_preview', 'location_info']

#     fieldsets = (
#         ('Basic Information', {
#             'fields': (
#                 'full_name', 'mobile_number', 'whatsapp_number',
#                 'taluka', 'village', 'home_address', 'photo', 'photo_preview'
#             )
#         }),
#         ('Location Information', {
#             'fields': ('location_info', 'location_accuracy', 'location_timestamp'),
#             'classes': ('collapse',)
#         }),
#         ('Business Information', {
#             'fields': (
#                 'business_name', 'interested_referrals',
#                 'help_description', 'know_mukadams_labourers'
#             )
#         }),
#         ('System', {
#             'fields': ('data_sharing_agreement', 'created_at', 'updated_at'),
#             'classes': ('collapse',)
#         })
#     )

#     def photo_preview(self, obj):
#         if obj.photo:
#             return format_html('<img src="{}" width="100" height="100" style="border-radius: 50%;" />', obj.photo.url)
#         return "No photo uploaded"
#     photo_preview.short_description = 'Photo Preview'

#     def location_display(self, obj):
#         if obj.location:
#             return f"{obj.location.y:.6f}, {obj.location.x:.6f}"
#         return "No location"
#     location_display.short_description = 'GPS Location'

#     def location_info(self, obj):
#         if obj.location:
#             html = f'''
#             <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6;">
#                 <h4 style="margin-top: 0; color: #495057;">📍 Location Details</h4>
#                 <p><strong>Coordinates:</strong> {obj.location.y:.6f}, {obj.location.x:.6f}</p>
#                 <p><strong>Accuracy:</strong> {obj.get_location_accuracy_display()}</p>
#                 <p><strong>Captured:</strong> {obj.location_timestamp.strftime('%Y-%m-%d %H:%M:%S') if obj.location_timestamp else 'Unknown'}</p>
#                 <a href="https://www.google.com/maps?q={obj.location.y},{obj.location.x}" target="_blank"
#                    style="background: #007bff; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block; margin-top: 10px;">
#                     📱 View on Google Maps
#                 </a>
#             </div>
#             '''
#             return format_html(html)
#         return format_html('<p style="color: #dc3545;">No location data available</p>')
#     location_info.short_description = 'Location Information'

# # Customize admin site headers
# admin.site.site_header = "Labor Management System Admin"
# admin.site.site_title = "Labor Management Admin"
# admin.site.index_title = "Welcome to Labor Management System Administration"

# # registration/admin.py
# from django.contrib import admin
# from .models import TeamLeader, Laborer, Job, JobAssignment

# admin.site.register(TeamLeader)
# admin.site.register(Laborer)
# admin.site.register(Job)
# admin.site.register(JobAssignment)
# registration/admin.py
# registration/admin.py

# registration/admin.py

# registration/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    IndividualLabor, Mukkadam, Transport, Others,
    Job, JobBid, JobAssignment, LaboursAdvancedProfiles  # Corrected: LabourAdvancedProfile (singular)
)

# Base class to share the photo and location methods, fixing the 'photo_preview' error
class BaseRegistrationAdmin(admin.ModelAdmin):
    readonly_fields = ['photo_preview', 'location_info', 'created_at', 'updated_at']

    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width="150" />', obj.photo.url)
        return "No photo uploaded"
    photo_preview.short_description = 'Photo Preview'

    def location_info(self, obj):
        if obj.location:
            map_link = f"https://maps.google.com/?q={obj.location.y},{obj.location.x}"
            return format_html(
                '<b>Coordinates:</b> {lat}, {lng}<br>'
                '<b>Accuracy:</b> {acc}<br>'
                '<a href="{link}" target="_blank">View on Google Maps</a>',
                lat=obj.location.y, lng=obj.location.x,
                acc=obj.get_location_accuracy_display(), link=map_link
            )
        return "No location data available"
    location_info.short_description = 'Location Details'

@admin.register(IndividualLabor)
class IndividualLaborAdmin(BaseRegistrationAdmin): # Inherits from Base to get helper methods
    list_display = ('full_name', 'mobile_number', 'village', 'employment_type', 'expected_wage')
    search_fields = ('full_name', 'mobile_number', 'village', 'taluka')
    fieldsets = (
        ('Basic Information', {'fields': ('full_name', 'mobile_number', 'taluka', 'village', 'photo', 'photo_preview')}),
        ('Personal Details', {'fields': ('gender', 'age')}),
        ('Employment', {'fields': ('employment_type', 'willing_to_migrate', 'expected_wage')}),
        ('Location', {'fields': ('location_info',)}),
    )

@admin.register(Mukkadam)
class MukkadamAdmin(BaseRegistrationAdmin): # Inherits from Base
    list_display = ('full_name', 'mobile_number', 'village', 'user')
    search_fields = ('full_name', 'user__username', 'mobile_number')
    fieldsets = (
        ('Account & Basic Info', {'fields': ('user', 'full_name', 'mobile_number', 'taluka', 'village', 'photo', 'photo_preview')}),
        ('Labor Management', {'fields': ('providing_labour_count', 'total_workers_peak', 'expected_charges')}),
        ('Services', {'fields': ('arrange_transport', 'provide_tools', 'supply_areas')}),
        ('Location', {'fields': ('location_info',)}),
    )

# ... (other admin classes for Transport, Others, etc. can also inherit from BaseRegistrationAdmin)

@admin.register(Transport)
class TransportAdmin(BaseRegistrationAdmin):
    list_display = ('full_name', 'mobile_number', 'vehicle_type', 'people_capacity')
    search_fields = ('full_name', 'mobile_number', 'vehicle_type')

@admin.register(Others)
class OthersAdmin(BaseRegistrationAdmin):
    list_display = ('full_name', 'mobile_number', 'business_name')
    search_fields = ('full_name', 'mobile_number', 'business_name')

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'location', 'status', 'finalized_leader', 'bidding_deadline', 'created_at')
    list_filter = ('status', 'is_urgent')
    search_fields = ('title', 'location', 'finalized_leader__username')

@admin.register(JobBid)
class JobBidAdmin(admin.ModelAdmin):
    list_display = ('job', 'mukadam', 'bid_price', 'workers_provided', 'timestamp')
    list_filter = ('job',)
    search_fields = ('job__title', 'mukadam__full_name')

@admin.register(JobAssignment)
class JobAssignmentAdmin(admin.ModelAdmin):
    list_display = ('job', 'worker', 'assigned_by', 'assigned_at')
    list_filter = ('job',)
    search_fields = ('job__title',)

@admin.register(LaboursAdvancedProfiles)
class LabourAdvancedProfileAdmin(admin.ModelAdmin):
    list_display = ('labour', 'available_from', 'available_to', 'advanced_rate_per_day')
    search_fields = ('labour__full_name',)

# Customize the main admin site headers
admin.site.site_header = "Labor Management System Admin"
admin.site.site_title = "Labor Management Admin"
admin.site.index_title = "Welcome to Labor Management System Administration"

