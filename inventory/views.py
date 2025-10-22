# # inventory/views.py
# from django.shortcuts import render, get_object_or_404, redirect
# from django.views.generic import ListView, DetailView, CreateView, UpdateView
# from django.contrib.auth.mixins import LoginRequiredMixin
# from django.db.models import Q, Count, Prefetch
# from django.urls import reverse_lazy
# from django.http import JsonResponse
# from .models import Product, ProductCategory, Company, ProductSKU
# from recommandations.models import CropSpecificBenefit
# from django.shortcuts import render, redirect, get_object_or_404
# from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
# from django.urls import reverse_lazy
# from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count, Sum, Prefetch
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from .models import (Product, ProductCategory, Company, ProductSKU, 
                     StockHistory, StockAlert)

from recommandations.models import CropSpecificBenefit

from django.db import models
import logging
from django.views.decorators.http import require_POST
import json

logger = logging.getLogger(__name__)

class ProductCreateView(CreateView):
    """Create a new product with image upload support"""
    model = Product
    template_name = 'product_form.html'
    fields = ['name', 'name_mr', 'company', 'category', 'technical_composition',
              'description', 'description_mr', 'application_method', 'application_method_mr',
              'precautions', 'precautions_mr', 'purpose', 'purpose_mr', 
              'benefits', 'benefits_mr', 'low_stock_threshold']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        context['companies'] = Company.objects.all().order_by('name')
        context['categories'] = ProductCategory.objects.all().order_by('name')
        return context
    
    @transaction.atomic
    def form_valid(self, form):
        product = form.save()
        
        # Process SKUs with initial stock and image uploads
        sku_counter = 0
        while f'sku_size_{sku_counter}' in self.request.POST:
            size = self.request.POST.get(f'sku_size_{sku_counter}')
            price = self.request.POST.get(f'sku_price_{sku_counter}')
            mrp = self.request.POST.get(f'sku_mrp_{sku_counter}')
            stock = self.request.POST.get(f'sku_stock_{sku_counter}')
            reorder_level = self.request.POST.get(f'sku_reorder_{sku_counter}', 10)
            
            # IMPORTANT: Get image from request.FILES instead of request.POST
            image_file = self.request.FILES.get(f'sku_image_{sku_counter}')
            
            if size and price:
                stock_qty = int(stock) if stock else 0
                
                # Create SKU with uploaded image
                sku = ProductSKU.objects.create(
                    product=product,
                    size=size,
                    price=float(price),
                    mrp=float(mrp) if mrp else None,
                    stock_quantity=stock_qty,
                    reorder_level=int(reorder_level),
                    image=image_file  # Assign the uploaded file directly to ImageField
                )
                
                logger.info(f"Created SKU {sku.id} with image: {sku.image.name if sku.image else 'No image'}")
                
                # Create initial stock history entry
                if stock_qty > 0:
                    StockHistory.objects.create(
                        sku=sku,
                        transaction_type='INITIAL',
                        quantity_before=0,
                        quantity_changed=stock_qty,
                        quantity_after=stock_qty,
                        notes='Initial stock entry',
                        performed_by=self.request.user if self.request.user.is_authenticated else None,
                        unit_price=float(price)
                    )
                
                # Check for low stock alert
                if sku.is_low_stock():
                    StockAlert.objects.create(
                        sku=sku,
                        alert_type='LOW_STOCK' if stock_qty > 0 else 'OUT_OF_STOCK',
                        stock_level_at_alert=stock_qty,
                        threshold_level=sku.reorder_level
                    )
            
            sku_counter += 1
        
        messages.success(
            self.request,
            'Product created successfully!' if self.request.session.get('language', 'en') == 'en'
            else 'उत्पादन यशस्वीरित्या तयार केले!'
        )
        
        return redirect('product_detail', pk=product.pk)


class ProductUpdateView(UpdateView):
    """Update an existing product with image upload support"""
    model = Product
    template_name = 'product_form.html'
    fields = ['name', 'name_mr', 'company', 'category', 'technical_composition',
              'description', 'description_mr', 'application_method', 'application_method_mr',
              'precautions', 'precautions_mr', 'purpose', 'purpose_mr',
              'benefits', 'benefits_mr', 'low_stock_threshold']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        context['companies'] = Company.objects.all().order_by('name')
        context['categories'] = ProductCategory.objects.all().order_by('name')
        return context
    
    @transaction.atomic
    def form_valid(self, form):
        logger.info("=== FORM VALID CALLED ===")
        product = form.save()
        existing_sku_ids = []
        
        # Debug: Print all POST and FILES data
        logger.info("=== POST DATA ===")
        for key in sorted(self.request.POST.keys()):
            if key.startswith('sku_'):
                logger.info(f"{key}: {self.request.POST.get(key)}")
        
        logger.info("=== FILES DATA ===")
        for key in sorted(self.request.FILES.keys()):
            if key.startswith('sku_'):
                logger.info(f"{key}: {self.request.FILES.get(key)}")
        
        # Process SKUs with stock tracking and image uploads
        sku_counter = 0
        while f'sku_size_{sku_counter}' in self.request.POST:
            sku_id = self.request.POST.get(f'sku_id_{sku_counter}')
            size = self.request.POST.get(f'sku_size_{sku_counter}')
            price = self.request.POST.get(f'sku_price_{sku_counter}')
            mrp = self.request.POST.get(f'sku_mrp_{sku_counter}')
            new_stock = self.request.POST.get(f'sku_stock_{sku_counter}')
            reorder_level = self.request.POST.get(f'sku_reorder_{sku_counter}', 10)
            
            # IMPORTANT: Get image from request.FILES
            image_file = self.request.FILES.get(f'sku_image_{sku_counter}')
            
            logger.info(f"\n--- Processing SKU {sku_counter} ---")
            logger.info(f"sku_id: {sku_id}, size: {size}, price: {price}, new_stock: {new_stock}")
            logger.info(f"image_file: {image_file.name if image_file else 'No new image'}")
            
            if size and price:
                new_stock_qty = int(new_stock) if new_stock else 0
                
                if sku_id:
                    try:
                        # Update existing SKU
                        sku = ProductSKU.objects.select_for_update().get(id=sku_id, product=product)
                        old_stock = sku.stock_quantity
                        
                        logger.info(f"Found SKU {sku_id}: current stock={old_stock}, new stock={new_stock_qty}")
                        
                        # Update ALL fields including stock
                        sku.size = size
                        sku.price = float(price)
                        sku.mrp = float(mrp) if mrp else None
                        sku.reorder_level = int(reorder_level)
                        sku.stock_quantity = new_stock_qty
                        
                        # Update image only if new file is uploaded
                        if image_file:
                            # Delete old image if exists (optional - uncomment if you want to delete old images)
                            # if sku.image:
                            #     sku.image.delete(save=False)
                            
                            sku.image = image_file
                            logger.info(f"New image uploaded: {image_file.name}")
                        
                        # Save the SKU with updated fields
                        sku.save()
                        logger.info(f"SKU {sku.id} saved to database")
                        
                        # Verify the save
                        sku.refresh_from_db()
                        logger.info(f"Verified: SKU {sku.id} now has stock_quantity={sku.stock_quantity} in DB")
                        logger.info(f"Image path: {sku.image.url if sku.image else 'No image'}")
                        
                        # Create stock history if changed
                        if old_stock != new_stock_qty:
                            stock_change = new_stock_qty - old_stock
                            logger.info(f"Stock changed by {stock_change}. Creating history entry.")
                            
                            history = StockHistory.objects.create(
                                sku=sku,
                                transaction_type='ADJUSTMENT',
                                quantity_before=old_stock,
                                quantity_changed=stock_change,
                                quantity_after=new_stock_qty,
                                notes='Stock adjusted via product edit',
                                performed_by=self.request.user if self.request.user.is_authenticated else None,
                                unit_price=float(price)
                            )
                            logger.info(f"Created history entry {history.id}")
                            
                            # Check for stock alerts
                            if sku.is_low_stock() and old_stock > sku.reorder_level:
                                alert = StockAlert.objects.create(
                                    sku=sku,
                                    alert_type='LOW_STOCK' if new_stock_qty > 0 else 'OUT_OF_STOCK',
                                    stock_level_at_alert=new_stock_qty,
                                    threshold_level=sku.reorder_level
                                )
                                logger.info(f"Created alert {alert.id}")
                        else:
                            logger.info("No stock change detected")
                        
                        existing_sku_ids.append(sku.id)
                        
                    except ProductSKU.DoesNotExist:
                        logger.error(f"SKU with id {sku_id} not found!")
                        messages.error(self.request, f"SKU with id {sku_id} not found!")
                        
                else:
                    # Create new SKU
                    logger.info(f"Creating new SKU: size={size}, price={price}, stock={new_stock_qty}")
                    
                    new_sku = ProductSKU.objects.create(
                        product=product,
                        size=size,
                        price=float(price),
                        mrp=float(mrp) if mrp else None,
                        stock_quantity=new_stock_qty,
                        reorder_level=int(reorder_level),
                        image=image_file  # Assign uploaded file to ImageField
                    )
                    
                    logger.info(f"Created new SKU {new_sku.id} with stock {new_sku.stock_quantity}")
                    logger.info(f"New SKU image: {new_sku.image.name if new_sku.image else 'No image'}")
                    
                    # Create initial stock history
                    if new_stock_qty > 0:
                        history = StockHistory.objects.create(
                            sku=new_sku,
                            transaction_type='INITIAL',
                            quantity_before=0,
                            quantity_changed=new_stock_qty,
                            quantity_after=new_stock_qty,
                            notes='Initial stock for new SKU',
                            performed_by=self.request.user if self.request.user.is_authenticated else None,
                            unit_price=float(price)
                        )
                        logger.info(f"Created initial history {history.id}")
                    
                    existing_sku_ids.append(new_sku.id)
            
            sku_counter += 1
        
        logger.info(f"\nProcessed {sku_counter} SKUs. Existing IDs: {existing_sku_ids}")
        
        # Delete SKUs that were removed
        deleted = ProductSKU.objects.filter(product=product).exclude(id__in=existing_sku_ids)
        deleted_count = deleted.count()
        if deleted_count > 0:
            logger.info(f"Deleting {deleted_count} SKUs: {list(deleted.values_list('id', flat=True))}")
            
            # Optional: Delete associated images before deleting SKUs
            for sku in deleted:
                if sku.image:
                    sku.image.delete(save=False)
                    
        deleted.delete()
        
        messages.success(
            self.request,
            'Product updated successfully!' if self.request.session.get('language', 'en') == 'en'
            else 'उत्पादन यशस्वीरित्या अपडेट केले!'
        )
        
        logger.info(f"Redirecting to product_detail for product {product.pk}")
        return redirect('product_detail', pk=product.pk)
    
    def form_invalid(self, form):
        logger.error("=== FORM INVALID ===")
        logger.error(f"Form errors: {form.errors}")
        logger.error(f"Form data: {form.data}")
        messages.error(
            self.request,
            f'Form validation failed. Please check the errors above.'
        )
        return super().form_invalid(form)
    
class ProductDetailView(DetailView):
    """Server-side rendered detail view with stock, images and benefits"""
    model = Product
    template_name = 'product_details.html'
    context_object_name = 'product'

    def get_queryset(self):
        return Product.objects.select_related(
            'company', 'category'
        ).prefetch_related(
            'skus',
            'crop_benefits__crop',
            Prefetch(
                'skus__stock_history',
                queryset=StockHistory.objects.select_related('performed_by').order_by('-transaction_date')
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        
        # Get stock statistics
        skus = self.object.skus.all()
        context['total_stock'] = sum(sku.stock_quantity for sku in skus)
        context['low_stock_skus'] = [sku for sku in skus if sku.is_low_stock()]
        context['out_of_stock_skus'] = [sku for sku in skus if sku.stock_quantity == 0]
        
        # Get SKUs with images for gallery
        context['skus_with_images'] = [sku for sku in skus if sku.image]
        
        # Get recent stock movements
        context['recent_stock_history'] = (
            StockHistory.objects.filter(sku__product=self.object)
            .select_related('sku', 'performed_by')
            .order_by('-transaction_date')[:20]
        )

        # Get active alerts
        context['active_alerts'] = StockAlert.objects.filter(
            sku__product=self.object,
            status='ACTIVE'
        ).select_related('sku')
        
        # Get related products
        context['related_products'] = Product.objects.filter(
            category=self.object.category
        ).exclude(
            id=self.object.id
        ).select_related('company', 'category').prefetch_related('skus')[:6]
        
        return context


class InventoryListView(ListView):
    """Enhanced inventory list with stock visibility and images"""
    model = Product
    template_name = 'inventory_list.html'
    context_object_name = 'products'
    paginate_by = 20

    def get_queryset(self):
        queryset = Product.objects.select_related(
            'company', 'category'
        ).prefetch_related(
            'skus',
            Prefetch('crop_benefits', queryset=CropSpecificBenefit.objects.select_related('crop'))
        ).annotate(
            total_stock=Sum('skus__stock_quantity')
        )

        # Search filter - now includes purpose and benefits
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(name_mr__icontains=search) |
                Q(technical_composition__icontains=search) |
                Q(company__name__icontains=search) |
                Q(description__icontains=search) |
                Q(purpose__icontains=search) |
                Q(benefits__icontains=search)
            )

        # Category filter
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category_id=category)

        # Company filter
        company = self.request.GET.get('company')
        if company:
            queryset = queryset.filter(company_id=company)
        
        # Stock filter
        stock_filter = self.request.GET.get('stock_status')
        if stock_filter == 'low':
            # Filter products with any low stock SKU
            low_stock_product_ids = ProductSKU.objects.filter(
                stock_quantity__lte=models.F('reorder_level')
            ).values_list('product_id', flat=True)
            queryset = queryset.filter(id__in=low_stock_product_ids)
        elif stock_filter == 'out':
            queryset = queryset.filter(skus__stock_quantity=0).distinct()

        # Sorting
        sort = self.request.GET.get('sort', 'name')
        if sort == 'stock_asc':
            queryset = queryset.order_by('total_stock')
        elif sort == 'stock_desc':
            queryset = queryset.order_by('-total_stock')
        else:
            queryset = queryset.order_by(sort)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        
        # Add filter options
        context['categories'] = ProductCategory.objects.all().order_by('name')
        context['companies'] = Company.objects.all().order_by('name')
        
        # Enhanced statistics
        context['total_products'] = Product.objects.count()
        context['total_categories'] = ProductCategory.objects.count()
        context['total_companies'] = Company.objects.count()
        context['total_skus'] = ProductSKU.objects.count()
        context['total_stock_value'] = ProductSKU.objects.aggregate(
            total=Sum(models.F('stock_quantity') * models.F('price'))
        )['total'] or 0
        context['low_stock_count'] = ProductSKU.objects.filter(
            stock_quantity__lte=models.F('reorder_level')
        ).count()
        context['out_of_stock_count'] = ProductSKU.objects.filter(stock_quantity=0).count()
        
        # Preserve filters
        context['filters'] = {
            'search': self.request.GET.get('search', ''),
            'category': self.request.GET.get('category', ''),
            'company': self.request.GET.get('company', ''),
            'stock_status': self.request.GET.get('stock_status', ''),
            'sort': self.request.GET.get('sort', 'name'),
        }
        
        return context


def stock_history_view(request, sku_id):
    """View complete stock history for a specific SKU"""
    sku = get_object_or_404(ProductSKU, id=sku_id)
    history = StockHistory.objects.filter(sku=sku).select_related('performed_by').order_by('-transaction_date')
    
    context = {
        'sku': sku,
        'history': history,
        'current_language': request.session.get('language', 'en')
    }
    
    return render(request, 'stock_history.html', context)


def set_language(request, lang_code):
    """Set language preference in session and reload page"""
    if lang_code in ['en', 'mr']:
        request.session['language'] = lang_code
    
    # Redirect back to

@require_POST
def add_company(request):
    try:
        data = json.loads(request.body)
        company_name = data.get('name', '').strip()
        
        if not company_name:
            return JsonResponse({'success': False, 'error': 'Company name required'})
        
        company, created = Company.objects.get_or_create(name=company_name)
        
        return JsonResponse({
            'success': True,
            'company': {'id': company.id, 'name': company.name}
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
# def set_language(request, lang_code):
#     """Set language preference"""
#     if lang_code in ['en', 'mr']:
#         request.session['language'] = lang_code
#     return redirect(request.META.get('HTTP_REFERER', 'inventory_list'))

# class ProductCreateView(CreateView):
#     """Create a new product"""
#     model = Product
#     template_name = 'product_form.html'
#     fields = ['name', 'name_mr', 'company', 'category', 'technical_composition']
    
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['current_language'] = self.request.session.get('language', 'en')
#         context['companies'] = Company.objects.all().order_by('name')
#         context['categories'] = ProductCategory.objects.all().order_by('name')
#         return context
    
#     def form_valid(self, form):
#         # Save the product first
#         product = form.save()
        
#         # Process SKUs
#         sku_counter = 0
#         while f'sku_size_{sku_counter}' in self.request.POST:
#             size = self.request.POST.get(f'sku_size_{sku_counter}')
#             price = self.request.POST.get(f'sku_price_{sku_counter}')
#             mrp = self.request.POST.get(f'sku_mrp_{sku_counter}')
#             stock = self.request.POST.get(f'sku_stock_{sku_counter}')
            
#             if size and price:
#                 ProductSKU.objects.create(
#                     product=product,
#                     size=size,
#                     price=float(price),
#                     mrp=float(mrp) if mrp else None,
#                     stock_quantity=int(stock) if stock else None
#                 )
#             sku_counter += 1
        
#         messages.success(
#             self.request,
#             'Product created successfully!' if self.request.session.get('language', 'en') == 'en'
#             else 'उत्पादन यशस्वीरित्या तयार केले!'
#         )
        
#         return redirect('product_detail', pk=product.pk)
    
#     def get_success_url(self):
#         return reverse_lazy('product_detail', kwargs={'pk': self.object.pk})


# class ProductUpdateView(UpdateView):
#     """Update an existing product"""
#     model = Product
#     template_name = 'product_form.html'
#     fields = ['name', 'name_mr', 'company', 'category', 'technical_composition']
    
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['current_language'] = self.request.session.get('language', 'en')
#         context['companies'] = Company.objects.all().order_by('name')
#         context['categories'] = ProductCategory.objects.all().order_by('name')
#         return context
    
#     def form_valid(self, form):
#         product = form.save()
        
#         # Delete existing SKUs that aren't in the form
#         existing_sku_ids = []
        
#         # Process SKUs
#         sku_counter = 0
#         while f'sku_size_{sku_counter}' in self.request.POST:
#             sku_id = self.request.POST.get(f'sku_id_{sku_counter}')
#             size = self.request.POST.get(f'sku_size_{sku_counter}')
#             price = self.request.POST.get(f'sku_price_{sku_counter}')
#             mrp = self.request.POST.get(f'sku_mrp_{sku_counter}')
#             stock = self.request.POST.get(f'sku_stock_{sku_counter}')
            
#             if size and price:
#                 if sku_id:
#                     # Update existing SKU
#                     sku = ProductSKU.objects.get(id=sku_id, product=product)
#                     sku.size = size
#                     sku.price = float(price)
#                     sku.mrp = float(mrp) if mrp else None
#                     sku.stock_quantity = int(stock) if stock else None
#                     sku.save()
#                     existing_sku_ids.append(sku.id)
#                 else:
#                     # Create new SKU
#                     new_sku = ProductSKU.objects.create(
#                         product=product,
#                         size=size,
#                         price=float(price),
#                         mrp=float(mrp) if mrp else None,
#                         stock_quantity=int(stock) if stock else None
#                     )
#                     existing_sku_ids.append(new_sku.id)
            
#             sku_counter += 1
        
#         # Delete SKUs that were removed
#         ProductSKU.objects.filter(product=product).exclude(id__in=existing_sku_ids).delete()
        
#         messages.success(
#             self.request,
#             'Product updated successfully!' if self.request.session.get('language', 'en') == 'en'
#             else 'उत्पादन यशस्वीरित्या अपडेट केले!'
#         )
        
#         return redirect('product_detail', pk=product.pk)
    
#     def get_success_url(self):
#         return reverse_lazy('product_detail', kwargs={'pk': self.object.pk})



# class ProductDetailView(DetailView):
#     """Server-side rendered detail view for a single product"""
#     model = Product
#     template_name = 'product_details.html'
#     context_object_name = 'product'

#     def get_queryset(self):
#         return Product.objects.select_related(
#             'company', 'category'
#         ).prefetch_related(
#             'skus',
#             'crop_benefits__crop',
#             'schedule_tasks'
#         )

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
        
#         # Get language preference
#         context['current_language'] = self.request.session.get('language', 'en')
        
#         # Get related products from same category
#         context['related_products'] = Product.objects.filter(
#             category=self.object.category
#         ).exclude(
#             id=self.object.id
#         ).select_related('company', 'category').prefetch_related('skus')[:6]
        
#         return context

# class InventoryListView( ListView):
#     """Server-side rendered list view for inventory with filtering"""
#     model = Product
#     template_name = 'inventory_list.html'
#     context_object_name = 'products'
#     paginate_by = 20

#     def get_queryset(self):
#         queryset = Product.objects.select_related(
#             'company', 'category'
#         ).prefetch_related(
#             'skus',
#             Prefetch('crop_benefits', queryset=CropSpecificBenefit.objects.select_related('crop'))
#         )

#         # Search filter
#         search = self.request.GET.get('search')
#         if search:
#             queryset = queryset.filter(
#                 Q(name__icontains=search) |
#                 Q(technical_composition__icontains=search) |
#                 Q(company__name__icontains=search)
#             )

#         # Category filter
#         category = self.request.GET.get('category')
#         if category:
#             queryset = queryset.filter(category_id=category)

#         # Company filter
#         company = self.request.GET.get('company')
#         if company:
#             queryset = queryset.filter(company_id=company)

#         # Sorting
#         sort = self.request.GET.get('sort', 'name')
#         queryset = queryset.order_by(sort)

#         return queryset

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
        
#         # Get language preference from session or default to English
#         lang = self.request.session.get('language', 'en')
#         context['current_language'] = lang
        
#         # Add filter options
#         context['categories'] = ProductCategory.objects.all().order_by('name')
#         context['companies'] = Company.objects.all().order_by('name')
        
#         # Add statistics
#         context['total_products'] = Product.objects.count()
#         context['total_categories'] = ProductCategory.objects.count()
#         context['total_companies'] = Company.objects.count()
#         context['total_skus'] = ProductSKU.objects.count()
        
#         # Preserve filters in pagination
#         context['filters'] = {
#             'search': self.request.GET.get('search', ''),
#             'category': self.request.GET.get('category', ''),
#             'company': self.request.GET.get('company', ''),
#             'sort': self.request.GET.get('sort', 'name'),
#         }
        
#         return context


# # class ProductDetailView( DetailView):
# #     """Server-side rendered detail view for a single product"""
# #     model = Product
# #     template_name = 'product_details.html'
# #     context_object_name = 'product'

# #     def get_queryset(self):
# #         return Product.objects.select_related(
# #             'company', 'category'
# #         ).prefetch_related(
# #             'skus',
# #             'crop_benefits__crop',
# #             'schedule_tasks__task'
# #         )

# #     def get_context_data(self, **kwargs):
# #         context = super().get_context_data(**kwargs)
        
# #         # Get language preference
# #         context['current_language'] = self.request.session.get('language', 'en')
        
# #         # Get related products from same category
# #         context['related_products'] = Product.objects.filter(
# #             category=self.object.category
# #         ).exclude(
# #             id=self.object.id
# #         ).select_related('company', 'category').prefetch_related('skus')[:6]
        
# #         return context


class ProductDeleteView(DeleteView):
    """Delete a product"""
    model = Product
    success_url = reverse_lazy('inventory_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(
            request,
            'Product deleted successfully!' if request.session.get('language', 'en') == 'en'
            else 'उत्पादन यशस्वीरित्या हटवले!'
        )
        return super().delete(request, *args, **kwargs)
    