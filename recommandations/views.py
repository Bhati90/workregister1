from django.shortcuts import render, redirect
from django.views.generic import ListView
from django.db.models import Q, Count, Sum, F, DecimalField
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict
from decimal import Decimal

from .models import Crop
from .utils import UnitConverter, SKUMatcher
from schedule.models import Farmer
from tasks.models import FarmerTaskStatus
from inventory.models import Product, ProductSKU
from cropcycle.models import TaskProduct


class ProductDemandAnalysisView(ListView):
    """Analyze product demand vs available stock with SKU matching"""
    model = Product
    template_name = 'product_demand_analysis.html'
    context_object_name = 'products'
    paginate_by = 50

    def get_queryset(self):
        today = timezone.now().date()
        
        # Get date range for filtering
        days_ahead = int(self.request.GET.get('days_ahead', 7))
        end_date = today + timedelta(days=days_ahead)
        
        # Get all upcoming pending tasks
        upcoming_tasks = FarmerTaskStatus.objects.filter(
            status='PENDING',
            planned_start_date__gte=today,
            planned_start_date__lte=end_date
        ).select_related(
            'farmer_crop_cycle__farmer',
            'schedule_task'
        )
        
        # Filter by farmer if specified
        farmer = self.request.GET.get('farmer')
        if farmer:
            upcoming_tasks = upcoming_tasks.filter(farmer_crop_cycle__farmer_id=farmer)
        
        # Filter by crop if specified
        crop = self.request.GET.get('crop')
        if crop:
            upcoming_tasks = upcoming_tasks.filter(
                farmer_crop_cycle__crop_variety__crop_id=crop
            )
        
        # Build product demand dictionary
        product_demand = defaultdict(lambda: {
            'farmers': {},
            'tasks': [],
            'total_quantity': {},
            'urgency_breakdown': {'urgent': 0, 'this_week': 0, 'later': 0},
            'farmer_breakdown': {},
            'farmer_requirements': []  # **NEW: For SKU matching**
        })
        
        for task in upcoming_tasks:
            farmer = task.farmer_crop_cycle.farmer
            
            for task_product in task.schedule_task.taskproduct_set.all():
                product = task_product.product
                product_id = product.id
                
                # Calculate actual quantity needed for this farmer's farm size
                actual_quantity = task_product.calculate_total_for_farmer(farmer)
                unit = task_product.dosage_unit
                
                # Track farmers
                product_demand[product_id]['farmers'][farmer.id] = farmer
                
                # Track tasks
                product_demand[product_id]['tasks'].append({
                    'task': task,
                    'farmer': farmer,
                    'dosage_per_area': task_product.dosage_amount,
                    'actual_quantity': actual_quantity,
                    'unit': unit,
                    'farm_size': farmer.farm_size,
                    'farm_unit': farmer.farm_size_unit,
                })
                
                # Aggregate total quantity by unit
                if unit not in product_demand[product_id]['total_quantity']:
                    product_demand[product_id]['total_quantity'][unit] = Decimal('0')
                product_demand[product_id]['total_quantity'][unit] += actual_quantity
                
                # Urgency breakdown
                days_until = (task.planned_start_date - today).days
                if days_until <= 3:
                    product_demand[product_id]['urgency_breakdown']['urgent'] += 1
                elif days_until <= 7:
                    product_demand[product_id]['urgency_breakdown']['this_week'] += 1
                else:
                    product_demand[product_id]['urgency_breakdown']['later'] += 1
                
                # Farmer breakdown
                if farmer.id not in product_demand[product_id]['farmer_breakdown']:
                    product_demand[product_id]['farmer_breakdown'][farmer.id] = {
                        'farmer': farmer,
                        'total_needed': Decimal('0'),
                        'unit': unit,
                        'tasks': []
                    }
                    # **NEW: Add to farmer requirements for SKU matching**
                    product_demand[product_id]['farmer_requirements'].append({
                        'farmer': farmer,
                        'quantity': Decimal('0'),
                        'unit': unit
                    })
                
                # Update farmer totals
                product_demand[product_id]['farmer_breakdown'][farmer.id]['total_needed'] += actual_quantity
                product_demand[product_id]['farmer_breakdown'][farmer.id]['tasks'].append({
                    'task': task,
                    'quantity': actual_quantity
                })
                
                # **Update farmer requirements**
                for farmer_req in product_demand[product_id]['farmer_requirements']:
                    if farmer_req['farmer'].id == farmer.id:
                        farmer_req['quantity'] += actual_quantity
                        break
        
        # Get products that have demand
        products_with_demand = Product.objects.filter(
            id__in=product_demand.keys()
        ).select_related('company', 'category').prefetch_related('skus')
        
        # Filter by specific product if requested
        product_filter = self.request.GET.get('product')
        if product_filter:
            products_with_demand = products_with_demand.filter(id=product_filter)
        
        # Attach demand data to products
        product_list = []
        for product in products_with_demand:
            demand_data = product_demand[product.id]
            
            # Get primary quantity
            total_quantities = demand_data['total_quantity']
            primary_unit = list(total_quantities.keys())[0] if total_quantities else 'units'
            primary_quantity = float(total_quantities.get(primary_unit, 0))
            
            # **NEW: Find optimal SKUs using PER-FARMER calculation**
            available_skus = product.skus.all()
            sku_recommendations = SKUMatcher.get_best_combination(
                farmer_requirements=demand_data['farmer_requirements'],
                available_skus=available_skus,
                max_combinations=3
            )
            
            # Calculate total stock in base units
            converter = UnitConverter()
            total_stock_base = 0
            for sku in available_skus:
                sku_amount, sku_unit = SKUMatcher.parse_sku_size(sku.size)
                if sku_amount and sku_unit and converter.are_compatible(primary_unit, sku_unit):
                    sku_base, _ = converter.convert_to_base(sku_amount, sku_unit)
                    total_stock_base += sku_base * sku.stock_quantity
            
            # Convert back to primary unit for comparison
            if total_stock_base > 0:
                primary_base, _ = converter.convert_to_base(primary_quantity, primary_unit)
                conversion_factor = primary_base / primary_quantity if primary_quantity > 0 else 1
                total_stock_primary = total_stock_base / conversion_factor if conversion_factor > 0 else 0
            else:
                total_stock_primary = 0
            
            # Calculate stock status
            if total_stock_primary == 0:
                stock_status_val = 'OUT_OF_STOCK'
            elif primary_quantity > total_stock_primary:
                stock_status_val = 'INSUFFICIENT'
            elif any(sku.is_low_stock() for sku in available_skus):
                stock_status_val = 'LOW_STOCK'
            else:
                stock_status_val = 'SUFFICIENT'
            
            product.demand_info = {
                'farmer_count': len(demand_data['farmers']),
                'farmers': list(demand_data['farmers'].values()),
                'farmer_breakdown': list(demand_data['farmer_breakdown'].values()),
                'task_count': len(demand_data['tasks']),
                'tasks': demand_data['tasks'],
                'total_quantity': total_quantities,
                'primary_quantity': primary_quantity,
                'primary_unit': primary_unit,
                'urgency': demand_data['urgency_breakdown'],
                'total_stock_primary': total_stock_primary,
                'stock_status': stock_status_val,
                'shortage': max(0, primary_quantity - total_stock_primary),
                'surplus': max(0, total_stock_primary - primary_quantity),
                'sku_recommendations': sku_recommendations,
            }
            
            # Apply stock status filter
            stock_status = self.request.GET.get('stock_status')
            if stock_status:
                if stock_status == 'insufficient' and stock_status_val != 'INSUFFICIENT':
                    continue
                elif stock_status == 'low' and stock_status_val not in ['LOW_STOCK', 'INSUFFICIENT', 'OUT_OF_STOCK']:
                    continue
                elif stock_status == 'out' and stock_status_val != 'OUT_OF_STOCK':
                    continue
            
            product_list.append(product)
        
        # Sort
        sort_by = self.request.GET.get('sort', 'urgency')
        if sort_by == 'urgency':
            product_list.sort(key=lambda p: p.demand_info['urgency']['urgent'], reverse=True)
        elif sort_by == 'shortage':
            product_list.sort(key=lambda p: p.demand_info['shortage'], reverse=True)
        elif sort_by == 'farmers':
            product_list.sort(key=lambda p: p.demand_info['farmer_count'], reverse=True)
        elif sort_by == 'name':
            product_list.sort(key=lambda p: p.name)
        
        return product_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        
        # Filter options
        context['farmers'] = Farmer.objects.all().order_by('name')
        context['crops'] = Crop.objects.all().order_by('name')
        context['all_products'] = Product.objects.all().order_by('name')
        
        # Current filters
        context['filters'] = {
            'farmer': self.request.GET.get('farmer', ''),
            'crop': self.request.GET.get('crop', ''),
            'product': self.request.GET.get('product', ''),
            'days_ahead': self.request.GET.get('days_ahead', '7'),
            'stock_status': self.request.GET.get('stock_status', ''),
            'sort': self.request.GET.get('sort', 'urgency'),
        }
        
        # Calculate summary statistics
        products = self.get_queryset()
        
        context['summary'] = {
            'total_products': len(products),
            'out_of_stock': sum(1 for p in products if p.demand_info['stock_status'] == 'OUT_OF_STOCK'),
            'insufficient': sum(1 for p in products if p.demand_info['stock_status'] == 'INSUFFICIENT'),
            'low_stock': sum(1 for p in products if p.demand_info['stock_status'] == 'LOW_STOCK'),
            'total_farmers': len(set(farmer.id for p in products for farmer in p.demand_info['farmers'])),
            'urgent_tasks': sum(p.demand_info['urgency']['urgent'] for p in products),
        }
        
        return context
# class ProductDemandAnalysisView(ListView):
#     """Analyze product demand vs available stock"""
#     model = Product
#     template_name = 'product_demand_analysis.html'
#     context_object_name = 'products'
#     paginate_by = 50

#     def get_queryset(self):
#         today = timezone.now().date()
        
#         # Get date range for filtering
#         days_ahead = int(self.request.GET.get('days_ahead', 7))
#         end_date = today + timedelta(days=days_ahead)
        
#         # Get all upcoming pending tasks
#         upcoming_tasks = FarmerTaskStatus.objects.filter(
#             status='PENDING',
#             planned_start_date__gte=today,
#             planned_start_date__lte=end_date
#         ).select_related(
#             'farmer_crop_cycle__farmer',
#             'schedule_task'
#         )
        
#         # Filter by farmer if specified
#         farmer = self.request.GET.get('farmer')
#         if farmer:
#             upcoming_tasks = upcoming_tasks.filter(farmer_crop_cycle__farmer_id=farmer)
        
#         # Filter by crop if specified
#         crop = self.request.GET.get('crop')
#         if crop:
#             upcoming_tasks = upcoming_tasks.filter(
#                 farmer_crop_cycle__crop_variety__crop_id=crop
#             )
        
#         # Build product demand dictionary
#         product_demand = defaultdict(lambda: {
#             'farmers': set(),
#             'tasks': [],
#             'total_quantity': {},  # unit -> quantity
#             'urgency_breakdown': {'urgent': 0, 'this_week': 0, 'later': 0}
#         })
        
#         for task in upcoming_tasks:
#             for task_product in task.schedule_task.taskproduct_set.all():
#                 product = task_product.product
#                 product_id = product.id
                
#                 product_demand[product_id]['farmers'].add(task.farmer_crop_cycle.farmer)
#                 product_demand[product_id]['tasks'].append({
#                     'task': task,
#                     'dosage': task_product.dosage_amount,
#                     'unit': task_product.dosage_unit,
#                 })
                
#                 # Aggregate quantity by unit
#                 unit = task_product.dosage_unit
#                 if unit not in product_demand[product_id]['total_quantity']:
#                     product_demand[product_id]['total_quantity'][unit] = 0
#                 product_demand[product_id]['total_quantity'][unit] += float(task_product.dosage_amount)
                
#                 # Urgency breakdown
#                 days_until = (task.planned_start_date - today).days
#                 if days_until <= 3:
#                     product_demand[product_id]['urgency_breakdown']['urgent'] += 1
#                 elif days_until <= 7:
#                     product_demand[product_id]['urgency_breakdown']['this_week'] += 1
#                 else:
#                     product_demand[product_id]['urgency_breakdown']['later'] += 1
        
#         # Get products that have demand
#         products_with_demand = Product.objects.filter(
#             id__in=product_demand.keys()
#         ).select_related('company', 'category').prefetch_related('skus')
        
#         # Filter by specific product if requested
#         product_filter = self.request.GET.get('product')
#         if product_filter:
#             products_with_demand = products_with_demand.filter(id=product_filter)
        
#         # Filter by stock status
#         stock_status = self.request.GET.get('stock_status')
        
#         # Attach demand data to products
#         product_list = []
#         for product in products_with_demand:
#             demand_data = product_demand[product.id]
            
#             # Calculate total stock across all SKUs
#             total_stock = product.get_total_stock()
            
#             # Get primary quantity (use first unit or most common)
#             total_quantities = demand_data['total_quantity']
#             primary_unit = list(total_quantities.keys())[0] if total_quantities else 'units'
#             primary_quantity = total_quantities.get(primary_unit, 0)
            
#             # Calculate stock status
#             if total_stock == 0:
#                 stock_status_val = 'OUT_OF_STOCK'
#             elif primary_quantity > total_stock:
#                 stock_status_val = 'INSUFFICIENT'
#             elif product.is_low_stock():
#                 stock_status_val = 'LOW_STOCK'
#             else:
#                 stock_status_val = 'SUFFICIENT'
            
#             product.demand_info = {
#                 'farmer_count': len(demand_data['farmers']),
#                 'farmers': list(demand_data['farmers']),
#                 'task_count': len(demand_data['tasks']),
#                 'tasks': demand_data['tasks'],
#                 'total_quantity': total_quantities,
#                 'primary_quantity': primary_quantity,
#                 'primary_unit': primary_unit,
#                 'urgency': demand_data['urgency_breakdown'],
#                 'total_stock': total_stock,
#                 'stock_status': stock_status_val,
#                 'shortage': max(0, primary_quantity - total_stock),
#                 'surplus': max(0, total_stock - primary_quantity),
#             }
            
#             # Apply stock status filter
#             if stock_status:
#                 if stock_status == 'insufficient' and stock_status_val != 'INSUFFICIENT':
#                     continue
#                 elif stock_status == 'low' and stock_status_val not in ['LOW_STOCK', 'INSUFFICIENT', 'OUT_OF_STOCK']:
#                     continue
#                 elif stock_status == 'out' and stock_status_val != 'OUT_OF_STOCK':
#                     continue
            
#             product_list.append(product)
        
#         # Sort by urgency and shortage
#         sort_by = self.request.GET.get('sort', 'urgency')
#         if sort_by == 'urgency':
#             product_list.sort(key=lambda p: p.demand_info['urgency']['urgent'], reverse=True)
#         elif sort_by == 'shortage':
#             product_list.sort(key=lambda p: p.demand_info['shortage'], reverse=True)
#         elif sort_by == 'farmers':
#             product_list.sort(key=lambda p: p.demand_info['farmer_count'], reverse=True)
#         elif sort_by == 'name':
#             product_list.sort(key=lambda p: p.name)
        
#         return product_list

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['current_language'] = self.request.session.get('language', 'en')
        
#         # Filter options
#         context['farmers'] = Farmer.objects.all().order_by('name')
#         context['crops'] = Crop.objects.all().order_by('name')
#         context['all_products'] = Product.objects.all().order_by('name')
        
#         # Current filters
#         context['filters'] = {
#             'farmer': self.request.GET.get('farmer', ''),
#             'crop': self.request.GET.get('crop', ''),
#             'product': self.request.GET.get('product', ''),
#             'days_ahead': self.request.GET.get('days_ahead', '7'),
#             'stock_status': self.request.GET.get('stock_status', ''),
#             'sort': self.request.GET.get('sort', 'urgency'),
#         }
        
#         # Calculate summary statistics
#         products = self.get_queryset()
        
#         context['summary'] = {
#             'total_products': len(products),
#             'out_of_stock': sum(1 for p in products if p.demand_info['stock_status'] == 'OUT_OF_STOCK'),
#             'insufficient': sum(1 for p in products if p.demand_info['stock_status'] == 'INSUFFICIENT'),
#             'low_stock': sum(1 for p in products if p.demand_info['stock_status'] == 'LOW_STOCK'),
#             'total_farmers': len(set(farmer for p in products for farmer in p.demand_info['farmers'])),
#             'urgent_tasks': sum(p.demand_info['urgency']['urgent'] for p in products),
#         }
        
#         return context


class ProductRecommendationView(ListView):
    """Show product recommendations for farmers based on current stage"""
    model = FarmerTaskStatus
    template_name = 'product_recommendations.html'
    context_object_name = 'recommendations'
    paginate_by = 20

    def get_queryset(self):
        today = timezone.now().date()
        next_week = today + timedelta(days=7)
        
        # Get upcoming pending tasks
        queryset = FarmerTaskStatus.objects.filter(
            status='PENDING',
            planned_start_date__lte=next_week
        ).select_related(
            'farmer_crop_cycle__farmer',
            'farmer_crop_cycle__crop_variety__crop',
            'schedule_task'
        ).prefetch_related(
            'schedule_task__taskproduct_set__product__skus',
            'schedule_task__taskproduct_set__product__crop_benefits'
        )

        # Filter by farmer
        farmer = self.request.GET.get('farmer')
        if farmer:
            queryset = queryset.filter(farmer_crop_cycle__farmer_id=farmer)

        # Filter by crop
        crop = self.request.GET.get('crop')
        if crop:
            queryset = queryset.filter(farmer_crop_cycle__crop_variety__crop_id=crop)

        # Filter by product
        product = self.request.GET.get('product')
        if product:
            queryset = queryset.filter(schedule_task__products__id=product)

        # Filter by urgency
        urgency = self.request.GET.get('urgency')
        if urgency == 'urgent':
            queryset = queryset.filter(planned_start_date__lte=today + timedelta(days=3))
        elif urgency == 'this_week':
            queryset = queryset.filter(planned_start_date__lte=next_week)

        return queryset.order_by('planned_start_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        context['farmers'] = Farmer.objects.all().order_by('name')
        context['crops'] = Crop.objects.all().order_by('name')
        
        # **ADD: Products for filtering**
        context['products'] = Product.objects.all().order_by('name')
        
        context['filters'] = {
            'farmer': self.request.GET.get('farmer', ''),
            'crop': self.request.GET.get('crop', ''),
            'product': self.request.GET.get('product', ''),  # **NEW**
            'urgency': self.request.GET.get('urgency', ''),
        }
        
        # Calculate statistics from the filtered queryset
        today = timezone.now().date()
        full_queryset = self.get_queryset()
        
        # Count urgent tasks (next 3 days)
        context['urgent_count'] = full_queryset.filter(
            planned_start_date__lte=today + timedelta(days=3)
        ).count()
        
        # Count total unique products recommended across all tasks
        total_products = 0
        for task in full_queryset:
            total_products += task.schedule_task.products.count()
        context['total_products_count'] = total_products
        
        return context


def set_language(request, lang_code):
    """Set language preference"""
    if lang_code in ['en', 'mr']:
        request.session['language'] = lang_code
    return redirect(request.META.get('HTTP_REFERER', 'product_recommendations'))


# from django.shortcuts import render
# from django.views.generic import ListView
# from django.db.models import Q, Count
# from django.shortcuts import redirect
# from django.utils import timezone
# from datetime import timedelta
# from .models import  Crop
# from schedule.models import Farmer
# from tasks.models import FarmerTaskStatus

# # Create your views here.
# class ProductRecommendationView(ListView):
#     """Show product recommendations for farmers based on current stage"""
#     model = FarmerTaskStatus
#     template_name = 'product_recommendations.html'
#     context_object_name = 'recommendations'
#     paginate_by = 20

#     def get_queryset(self):
#         today = timezone.now().date()
#         next_week = today + timedelta(days=7)
        
#         # Get upcoming pending tasks
#         queryset = FarmerTaskStatus.objects.filter(
#             status='PENDING',
#             planned_start_date__lte=next_week
#         ).select_related(
#             'farmer_crop_cycle__farmer',
#             'farmer_crop_cycle__crop_variety__crop',
#             'schedule_task'
#         ).prefetch_related(
#             'schedule_task__taskproduct_set__product__skus',
#             'schedule_task__taskproduct_set__product__crop_benefits'
#         )

#         # Filter by farmer
#         farmer = self.request.GET.get('farmer')
#         if farmer:
#             queryset = queryset.filter(farmer_crop_cycle__farmer_id=farmer)

#         # Filter by crop
#         crop = self.request.GET.get('crop')
#         if crop:
#             queryset = queryset.filter(farmer_crop_cycle__crop_variety__crop_id=crop)

#         # Filter by urgency
#         urgency = self.request.GET.get('urgency')
#         if urgency == 'urgent':
#             queryset = queryset.filter(planned_start_date__lte=today + timedelta(days=3))
#         elif urgency == 'this_week':
#             queryset = queryset.filter(planned_start_date__lte=next_week)

#         return queryset.order_by('planned_start_date')

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['current_language'] = self.request.session.get('language', 'en')
#         context['farmers'] = Farmer.objects.all().order_by('name')
#         context['crops'] = Crop.objects.all().order_by('name')
        
#         context['filters'] = {
#             'farmer': self.request.GET.get('farmer', ''),
#             'crop': self.request.GET.get('crop', ''),
#             'urgency': self.request.GET.get('urgency', ''),
#         }
        
#         # **ADD THIS: Calculate statistics from the filtered queryset**
#         today = timezone.now().date()
#         full_queryset = self.get_queryset()
        
#         # Count urgent tasks (next 3 days)
#         context['urgent_count'] = full_queryset.filter(
#             planned_start_date__lte=today + timedelta(days=3)
#         ).count()
        
#         # Count total unique products recommended across all tasks
#         total_products = 0
#         for task in full_queryset:
#             total_products += task.schedule_task.products.count()
#         context['total_products_count'] = total_products
        
#         return context

# def set_language(request, lang_code):
#     """Set language preference"""
#     if lang_code in ['en', 'mr']:
#         request.session['language'] = lang_code
#     return redirect(request.META.get('HTTP_REFERER', 'farmer_list'))