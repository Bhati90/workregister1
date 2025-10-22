# orders/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count, Sum, F
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import datetime, timedelta

from .models import (Order, OrderItem, Farmer, OrderStatusHistory, 
                     OrderPayment, NotificationTemplate, OrderNotification)
from inventory.models import ProductSKU, StockHistory


def inventory_update_dashboard(request):
    """
    Dashboard showing all pending inventory updates.
    Groups by product for easy review.
    """
    # Get all completed orders that need inventory update
    pending_orders = Order.objects.filter(
        status__in=['COMPLETED', 'DELIVERED'],
        inventory_updated=False
    ).prefetch_related(
        'items__sku__product',
        'farmer'
    ).order_by('-created_at')
    
    # Group items by product
    product_summary = {}
    order_details = []
    
    for order in pending_orders:
        order_info = {
            'order': order,
            'items': []
        }
        
        for item in order.items.all():
            sku = item.sku
            product_key = f"{sku.product.id}_{sku.id}"
            
            # Add to product summary
            if product_key not in product_summary:
                product_summary[product_key] = {
                    'product': sku.product,
                    'sku': sku,
                    'total_quantity': 0,
                    'order_count': 0,
                    'total_value': 0,
                    'current_stock': sku.stock_quantity,
                    'projected_stock': sku.stock_quantity,
                    'orders': []
                }
            
            product_summary[product_key]['total_quantity'] += item.quantity
            product_summary[product_key]['total_value'] += float(item.total_price)
            product_summary[product_key]['projected_stock'] -= item.quantity
            product_summary[product_key]['orders'].append({
                'order_number': order.order_number,
                'order_id': order.id,
                'quantity': item.quantity,
                'farmer_name': order.farmer.name
            })
            
            # Add to order details
            order_info['items'].append({
                'sku': sku,
                'quantity': item.quantity,
                'current_stock': sku.stock_quantity,
                'after_update': sku.stock_quantity - item.quantity,
                'is_sufficient': sku.stock_quantity >= item.quantity
            })
        
        # Count unique products in summary
        for key in product_summary:
            if any(o['order_id'] == order.id for o in product_summary[key]['orders']):
                product_summary[key]['order_count'] = len(
                    set(o['order_id'] for o in product_summary[key]['orders'])
                )
        
        order_details.append(order_info)
    
    # Convert to list and sort
    product_list = sorted(
        product_summary.values(),
        key=lambda x: x['total_quantity'],
        reverse=True
    )
    
    # Check for stock issues
    stock_issues = []
    for prod in product_list:
        if prod['projected_stock'] < 0:
            stock_issues.append({
                'product': prod['product'],
                'sku': prod['sku'],
                'shortage': abs(prod['projected_stock']),
                'required': prod['total_quantity'],
                'available': prod['current_stock']
            })
    
    context = {
        'pending_orders': pending_orders,
        'order_details': order_details,
        'product_summary': product_list,
        'stock_issues': stock_issues,
        'total_orders': pending_orders.count(),
        'total_products': len(product_list),
        'has_stock_issues': len(stock_issues) > 0,
    }
    
    return render(request, 'order/inventory_update_dashboard.html', context)


def product_wise_inventory_view(request):
    """
    View showing product-wise pending inventory updates
    """
    # Get all SKUs that have pending updates
    pending_items = OrderItem.objects.filter(
        order__status__in=['COMPLETED', 'DELIVERED'],
        order__inventory_updated=False
    ).select_related(
        'sku__product',
        'order__farmer'
    ).order_by('sku__product__name', 'sku__size')
    
    # Group by SKU
    sku_summary = {}
    
    for item in pending_items:
        sku_id = str(item.sku.id)
        
        if sku_id not in sku_summary:
            sku_summary[sku_id] = {
                'sku': item.sku,
                'product': item.sku.product,
                'current_stock': item.sku.stock_quantity,
                'total_pending': 0,
                'order_count': 0,
                'total_value': 0,
                'orders': [],
                'projected_stock': item.sku.stock_quantity,
            }
        
        sku_summary[sku_id]['total_pending'] += item.quantity
        sku_summary[sku_id]['total_value'] += float(item.total_price)
        sku_summary[sku_id]['projected_stock'] -= item.quantity
        sku_summary[sku_id]['orders'].append({
            'order': item.order,
            'quantity': item.quantity,
            'value': float(item.total_price)
        })
    
    # Update order count
    for sku_id in sku_summary:
        sku_summary[sku_id]['order_count'] = len(sku_summary[sku_id]['orders'])
    
    # Convert to list
    products = sorted(
        sku_summary.values(),
        key=lambda x: x['total_pending'],
        reverse=True
    )
    
    context = {
        'products': products,
        'total_skus': len(products),
    }
    
    return render(request, 'order/product_wise_inventory.html', context)


@transaction.atomic
@require_POST
def bulk_update_inventory(request):
    """
    Update inventory for ALL pending orders in one click.
    Validates stock before updating.
    """
    try:
        # Get all pending orders
        pending_orders = Order.objects.filter(
            status__in=['COMPLETED', 'DELIVERED'],
            inventory_updated=False
        ).prefetch_related('items__sku')
        
        if not pending_orders.exists():
            return JsonResponse({
                'success': False,
                'message': 'No pending orders to update'
            })
        
        # First pass: Validate all stock
        stock_requirements = defaultdict(int)
        
        for order in pending_orders:
            for item in order.items.all():
                stock_requirements[item.sku.id] += item.quantity
        
        # Check if all SKUs have sufficient stock
        insufficient_stock = []
        
        for sku_id, required_qty in stock_requirements.items():
            sku = ProductSKU.objects.get(id=sku_id)
            if sku.stock_quantity < required_qty:
                insufficient_stock.append({
                    'product': f"{sku.product.name} ({sku.size})",
                    'required': required_qty,
                    'available': sku.stock_quantity,
                    'shortage': required_qty - sku.stock_quantity
                })
        
        if insufficient_stock:
            return JsonResponse({
                'success': False,
                'message': 'Insufficient stock for some products',
                'issues': insufficient_stock
            })
        
        # Second pass: Update all inventory
        updated_orders = []
        updated_items = 0
        
        for order in pending_orders:
            for item in order.items.all():
                sku = item.sku
                old_stock = sku.stock_quantity
                new_stock = old_stock - item.quantity
                
                # Update stock
                sku.stock_quantity = new_stock
                sku.save()
                
                # Create stock history
                StockHistory.objects.create(
                    sku=sku,
                    transaction_type='SALE',
                    quantity_before=old_stock,
                    quantity_changed=-item.quantity,
                    quantity_after=new_stock,
                    notes=f'Bulk update - Order {order.order_number}',
                    reference_number=order.order_number,
                    performed_by=request.user,
                    unit_price=item.unit_price,
                    total_value=item.total_price
                )
                
                updated_items += 1
            
            # Mark order as inventory updated
            order.inventory_updated = True
            order.save()
            
            # Create status history
            OrderStatusHistory.objects.create(
                order=order,
                old_status=order.status,
                new_status=order.status,
                notes='Inventory updated via bulk update',
                changed_by=request.user
            )
            
            updated_orders.append(order.order_number)
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully updated inventory for {len(updated_orders)} orders',
            'orders_updated': len(updated_orders),
            'items_updated': updated_items,
            'order_numbers': updated_orders
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating inventory: {str(e)}'
        }, status=500)


@transaction.atomic
def update_single_order_inventory(request, order_id):
    """
    Update inventory for a single order from the dashboard
    """
    try:
        order = Order.objects.prefetch_related('items__sku').get(id=order_id)
        
        if order.inventory_updated:
            messages.warning(request, f'Inventory already updated for order {order.order_number}')
            return redirect('inventory_update_dashboard')
        
        # Validate stock
        insufficient = []
        for item in order.items.all():
            if item.sku.stock_quantity < item.quantity:
                insufficient.append({
                    'product': f"{item.sku.product.name} ({item.sku.size})",
                    'required': item.quantity,
                    'available': item.sku.stock_quantity
                })
        
        if insufficient:
            for issue in insufficient:
                messages.error(
                    request,
                    f"Insufficient stock: {issue['product']} - "
                    f"Required: {issue['required']}, Available: {issue['available']}"
                )
            return redirect('inventory_update_dashboard')
        
        # Update inventory
        for item in order.items.all():
            sku = item.sku
            old_stock = sku.stock_quantity
            new_stock = old_stock - item.quantity
            
            sku.stock_quantity = new_stock
            sku.save()
            
            # Create stock history
            StockHistory.objects.create(
                sku=sku,
                transaction_type='SALE',
                quantity_before=old_stock,
                quantity_changed=-item.quantity,
                quantity_after=new_stock,
                notes=f'Order {order.order_number} completed',
                reference_number=order.order_number,
                performed_by=request.user,
                unit_price=item.unit_price,
                total_value=item.total_price
            )
        
        # Mark as updated
        order.inventory_updated = True
        order.save()
        
        OrderStatusHistory.objects.create(
            order=order,
            old_status=order.status,
            new_status=order.status,
            notes='Inventory updated',
            changed_by=request.user
        )
        
        messages.success(
            request,
            f'Inventory updated successfully for order {order.order_number}'
        )
        
    except Order.DoesNotExist:
        messages.error(request, 'Order not found')
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
    
    return redirect('inventory_update_dashboard')


def preview_bulk_update(request):
    """
    Preview what will happen when bulk update is triggered
    """
    pending_orders = Order.objects.filter(
        status__in=['COMPLETED', 'DELIVERED'],
        inventory_updated=False
    ).prefetch_related('items__sku__product')
    
    # Calculate impact
    stock_impact = {}
    
    for order in pending_orders:
        for item in order.items.all():
            sku_id = str(item.sku.id)
            
            if sku_id not in stock_impact:
                stock_impact[sku_id] = {
                    'sku': item.sku,
                    'product_name': item.sku.product.name,
                    'size': item.sku.size,
                    'current_stock': item.sku.stock_quantity,
                    'total_deduction': 0,
                    'projected_stock': item.sku.stock_quantity,
                    'orders': []
                }
            
            stock_impact[sku_id]['total_deduction'] += item.quantity
            stock_impact[sku_id]['projected_stock'] -= item.quantity
            stock_impact[sku_id]['orders'].append(order.order_number)
    
    impact_list = list(stock_impact.values())
    
    return JsonResponse({
        'success': True,
        'total_orders': pending_orders.count(),
        'total_products': len(impact_list),
        'impact': impact_list
    })

class OrderDashboardView( ListView):
    """Dashboard showing order summary and statistics"""
    model = Order
    template_name = 'order/dashboard.html'
    context_object_name = 'recent_orders'
    paginate_by = 10
    
    def get_queryset(self):
        return Order.objects.select_related('farmer').prefetch_related('items').order_by('-created_at')[:10]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        
        # Overall statistics
        context['total_orders'] = Order.objects.count()
        context['pending_orders'] = Order.objects.filter(status='PENDING').count()
        context['confirmed_orders'] = Order.objects.filter(status='CONFIRMED').count()
        context['in_transit_orders'] = Order.objects.filter(status__in=['SHIPPED', 'IN_TRANSIT', 'OUT_FOR_DELIVERY']).count()
        context['completed_orders'] = Order.objects.filter(status='COMPLETED').count()
        context['delivered_orders'] = Order.objects.filter(status='DELIVERED').count()
        
        # Financial statistics
        context['total_revenue'] = Order.objects.filter(
            status__in=['COMPLETED', 'DELIVERED']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        context['pending_payments'] = Order.objects.exclude(
            payment_status='PAID'
        ).aggregate(total=Sum(F('total_amount') - F('paid_amount')))['total'] or 0
        
        # Today's statistics
        today = timezone.now().date()
        context['today_orders'] = Order.objects.filter(created_at__date=today).count()
        context['today_revenue'] = Order.objects.filter(
            created_at__date=today,
            status__in=['COMPLETED', 'DELIVERED']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Orders needing attention
        context['inventory_update_needed'] = Order.objects.filter(
            status__in=['COMPLETED', 'DELIVERED'],
            inventory_updated=False
        ).count()
        
        # Recent activities
        context['recent_status_changes'] = OrderStatusHistory.objects.select_related(
            'order', 'changed_by'
        ).order_by('-created_at')[:10]

         # Inventory update statistics
        pending_inventory_orders = Order.objects.filter(
            status__in=['COMPLETED', 'DELIVERED'],
            inventory_updated=False
        )
        
        context['inventory_update_needed'] = pending_inventory_orders.count()
        
        # Product-wise pending summary (top 5)
        from collections import defaultdict
        product_pending = defaultdict(int)
        
        for order in pending_inventory_orders.prefetch_related('items__sku__product'):
            for item in order.items.all():
                key = f"{item.sku.product.name} ({item.sku.size})"
                product_pending[key] += item.quantity
        
        context['top_pending_products'] = sorted(
            product_pending.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Stock shortage warnings
        from inventory.models import ProductSKU
        stock_requirements = defaultdict(int)
        
        for order in pending_inventory_orders:
            for item in order.items.all():
                stock_requirements[item.sku.id] += item.quantity
        
        stock_issues = []
        for sku_id, required in stock_requirements.items():
            sku = ProductSKU.objects.get(id=sku_id)
            if sku.stock_quantity < required:
                stock_issues.append({
                    'product': f"{sku.product.name} ({sku.size})",
                    'required': required,
                    'available': sku.stock_quantity,
                    'shortage': required - sku.stock_quantity
                })
        
        context['inventory_stock_issues'] = stock_issues
        context['has_inventory_issues'] = len(stock_issues) > 0
        
        
        return context


class OrderListView( ListView):
    """List all orders with filters"""
    model = Order
    template_name = 'order_list.html'
    context_object_name = 'orders'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Order.objects.select_related('farmer').prefetch_related('items__sku__product')
        
        # Status filter
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Payment status filter
        payment_status = self.request.GET.get('payment_status')
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search) |
                Q(farmer__name__icontains=search) |
                Q(farmer__phone__icontains=search) |
                Q(tracking_number__icontains=search)
            )
        
        # Date range
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        # Inventory update needed
        inventory_filter = self.request.GET.get('inventory_update')
        if inventory_filter == 'needed':
            queryset = queryset.filter(
                status__in=['COMPLETED', 'DELIVERED'],
                inventory_updated=False
            )
        
        # Sorting
        sort = self.request.GET.get('sort', '-created_at')
        queryset = queryset.order_by(sort)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        context['status_choices'] = Order.ORDER_STATUS
        context['payment_status_choices'] = Order.PAYMENT_STATUS
        
        # Preserve filters
        context['filters'] = {
            'search': self.request.GET.get('search', ''),
            'status': self.request.GET.get('status', ''),
            'payment_status': self.request.GET.get('payment_status', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'inventory_update': self.request.GET.get('inventory_update', ''),
            'sort': self.request.GET.get('sort', '-created_at'),
        }
        
        return context


class OrderDetailView( DetailView):
    """Detailed view of a single order"""
    model = Order
    template_name = 'order_details.html'
    context_object_name = 'order'
    
    def get_queryset(self):
        return Order.objects.select_related('farmer', 'created_by', 'assigned_to').prefetch_related(
            'items__sku__product',
            'status_history__changed_by',
            'payments__recorded_by',
            'notifications'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        
        # Projected stock impact
        if not self.object.inventory_updated:
            context['stock_impact'] = self.object.get_projected_stock_impact()
        
        # Available notification templates
        context['notification_templates'] = NotificationTemplate.objects.filter(is_active=True)
        
        return context


class OrderCreateView(CreateView):
    """Create a new order"""
    model = Order
    template_name = 'order_form.html'
    fields = ['farmer', 'payment_method', 'delivery_address', 'delivery_contact', 
              'expected_delivery_date', 'discount', 'delivery_charges', 'notes']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        context['farmers'] = Farmer.objects.filter().order_by('name')
        context['products'] = ProductSKU.objects.select_related('product').filter(
            stock_quantity__gt=0
        ).order_by('product__name')
        return context
    
    @transaction.atomic
    def form_valid(self, form):
        order = form.save(commit=False)
        order.created_by = self.request.user
        order.status = 'PENDING'
        order.save()
        
        # Process order items
        item_counter = 0
        while f'item_sku_{item_counter}' in self.request.POST:
            sku_id = self.request.POST.get(f'item_sku_{item_counter}')
            quantity = self.request.POST.get(f'item_quantity_{item_counter}')
            unit_price = self.request.POST.get(f'item_price_{item_counter}')
            discount = self.request.POST.get(f'item_discount_{item_counter}', 0)
            
            if sku_id and quantity and unit_price:
                sku = ProductSKU.objects.get(id=sku_id)
                OrderItem.objects.create(
                    order=order,
                    sku=sku,
                    quantity=int(quantity),
                    unit_price=float(unit_price),
                    discount=float(discount) if discount else 0
                )
            
            item_counter += 1
        
        # Calculate totals
        order.calculate_totals()
        
        # Create status history
        OrderStatusHistory.objects.create(
            order=order,
            new_status='PENDING',
            notes='Order created',
            changed_by=self.request.user
        )
        
        messages.success(
            self.request,
            f'Order {order.order_number} created successfully!'
        )
        
        return redirect('order_detail', pk=order.pk)


class OrderUpdateView(UpdateView):
    """Update order details"""
    model = Order
    template_name = 'order_form.html'
    fields = ['farmer', 'status', 'payment_method', 'payment_status', 
              'delivery_address', 'delivery_contact', 'expected_delivery_date',
              'courier_name', 'tracking_number', 'discount', 'delivery_charges', 
              'notes', 'assigned_to']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        context['farmers'] = Farmer.objects.filter().order_by('name')
        context['products'] = ProductSKU.objects.select_related('product').order_by('product__name')
        return context
    
    def form_valid(self, form):
        old_status = Order.objects.get(pk=self.object.pk).status
        order = form.save()
        
        # Track status change
        if old_status != order.status:
            OrderStatusHistory.objects.create(
                order=order,
                old_status=old_status,
                new_status=order.status,
                notes=f'Status changed from {old_status} to {order.status}',
                changed_by=self.request.user
            )
        
        messages.success(self.request, f'Order {order.order_number} updated successfully!')
        return redirect('order_detail', pk=order.pk)


def update_order_status(request, pk):
    """Update order status and send notification"""
    if request.method == 'POST':
        order = get_object_or_404(Order, pk=pk)
        old_status = order.status
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        send_notification = request.POST.get('send_notification') == 'on'
        
        if new_status and new_status != old_status:
            order.status = new_status
            
            # Special handling for delivered/completed
            if new_status == 'DELIVERED' and not order.actual_delivery_date:
                order.actual_delivery_date = timezone.now().date()
            
            order.save()
            
            # Create status history
            status_history = OrderStatusHistory.objects.create(
                order=order,
                old_status=old_status,
                new_status=new_status,
                notes=notes,
                changed_by=request.user
            )
            
            # Send notification if requested
            if send_notification:
                send_order_notification(order, new_status, request.user)
            
            messages.success(request, f'Order status updated to {order.get_status_display()}')
        
        return redirect('order_detail', pk=pk)
    
    return redirect('order_detail', pk=pk)


@transaction.atomic
def complete_order_and_update_inventory(request, pk):
    """Mark order as completed and update inventory"""
    order = get_object_or_404(Order, pk=pk)
    
    if not order.can_update_inventory():
        messages.error(request, 'Cannot update inventory for this order!')
        return redirect('order_detail', pk=pk)
    
    # Update inventory for each item
    for item in order.items.all():
        sku = item.sku
        old_stock = sku.stock_quantity
        new_stock = old_stock - item.quantity
        
        if new_stock < 0:
            messages.error(
                request,
                f'Insufficient stock for {sku.product.name} ({sku.size}). Available: {old_stock}, Required: {item.quantity}'
            )
            return redirect('order_detail', pk=pk)
        
        # Update stock
        sku.stock_quantity = new_stock
        sku.save()
        
        # Create stock history
        StockHistory.objects.create(
            sku=sku,
            transaction_type='SALE',
            quantity_before=old_stock,
            quantity_changed=-item.quantity,
            quantity_after=new_stock,
            notes=f'Stock deducted for order {order.order_number}',
            reference_number=order.order_number,
            performed_by=request.user,
            unit_price=item.unit_price,
            total_value=item.total_price
        )
    
    # Mark order as inventory updated
    order.inventory_updated = True
    order.status = 'COMPLETED'
    order.save()
    
    # Create status history
    OrderStatusHistory.objects.create(
        order=order,
        old_status=order.status,
        new_status='COMPLETED',
        notes='Order completed and inventory updated',
        changed_by=request.user
    )
    
    messages.success(
        request,
        f'Order {order.order_number} completed and inventory updated successfully!'
    )
    
    return redirect('order_detail', pk=pk)


def send_order_notification(order, status, user):
    """Send notification to farmer about order status"""
    # Map status to notification type
    status_notification_map = {
        'CONFIRMED': 'ORDER_CONFIRMED',
        'PACKED': 'ORDER_PACKED',
        'SHIPPED': 'ORDER_SHIPPED',
        'OUT_FOR_DELIVERY': 'OUT_FOR_DELIVERY',
        'DELIVERED': 'ORDER_DELIVERED',
        'CANCELLED': 'ORDER_CANCELLED',
    }
    
    notification_type = status_notification_map.get(status)
    if not notification_type:
        return
    
    try:
        template = NotificationTemplate.objects.get(
            notification_type=notification_type,
            is_active=True
        )
        
        # Render template with order data
        language = 'mr'  # Default to Marathi for farmers, can be made dynamic
        rendered = template.render(order, language)
        
        # Create notification record
        notification = OrderNotification.objects.create(
            order=order,
            template=template,
            notification_type=notification_type,
            subject=rendered['subject'],
            message=rendered['message'],
            language=language,
            sent_via='SMS',  # Default to SMS
            is_sent=False,  # Will be updated when actually sent
            delivery_status='QUEUED'
        )
        
        # Here you would integrate with SMS/WhatsApp API
        # For now, just mark as sent (simulation)
        notification.is_sent = True
        notification.delivery_status = 'SENT'
        notification.save()
        
        # Update status history
        OrderStatusHistory.objects.filter(
            order=order,
            new_status=status
        ).update(notification_sent=True)
        
        return notification
        
    except NotificationTemplate.DoesNotExist:
        return None


def preview_notification(request, pk):
    """Preview notification before sending"""
    order = get_object_or_404(Order, pk=pk)
    template_id = request.GET.get('template_id')
    language = request.GET.get('language', 'en')
    
    if template_id:
        template = get_object_or_404(NotificationTemplate, pk=template_id)
        rendered = template.render(order, language)
        
        return JsonResponse({
            'success': True,
            'subject': rendered['subject'],
            'message': rendered['message']
        })
    
    return JsonResponse({'success': False, 'error': 'Template not found'})


def send_custom_notification(request, pk):
    """Send custom notification to farmer"""
    if request.method == 'POST':
        order = get_object_or_404(Order, pk=pk)
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        language = request.POST.get('language', 'en')
        
        # Create notification record
        notification = OrderNotification.objects.create(
            order=order,
            notification_type='CUSTOM',
            subject=subject,
            message=message,
            language=language,
            sent_via='SMS',
            is_sent=True,  # Simulated
            delivery_status='SENT'
        )
        
        messages.success(request, 'Notification sent successfully!')
        return redirect('order_detail', pk=pk)
    
    return redirect('order_detail', pk=pk)


def add_order_payment(request, pk):
    """Add payment to order"""
    if request.method == 'POST':
        order = get_object_or_404(Order, pk=pk)
        
        amount = float(request.POST.get('amount', 0))
        payment_method = request.POST.get('payment_method')
        transaction_id = request.POST.get('transaction_id', '')
        notes = request.POST.get('notes', '')
        
        if amount > 0:
            OrderPayment.objects.create(
                order=order,
                amount=amount,
                payment_method=payment_method,
                transaction_id=transaction_id,
                notes=notes,
                recorded_by=request.user
            )
            
            messages.success(request, f'Payment of ₹{amount} recorded successfully!')
        else:
            messages.error(request, 'Invalid payment amount!')
        
        return redirect('order_detail', pk=pk)
    
    return redirect('order_detail', pk=pk)


class FarmerListView(ListView):
    """List all farmers"""
    model = Farmer
    template_name = 'farmer_lists.html'
    context_object_name = 'farmers'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Farmer.objects.all()
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(phone__icontains=search) |
                Q(village__icontains=search) |
                Q(district__icontains=search)
            )
        
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(is_active=(status == 'active'))
        
        return queryset.order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        context['total_farmers'] = Farmer.objects.count()
        context['active_farmers'] = Farmer.objects.filter(is_active=True).count()
        return context


class FarmerDetailView( DetailView):
    """Detailed view of a farmer"""
    model = Farmer
    template_name = 'schedule/templates/farmer_detail.html'
    context_object_name = 'farmer'
    
    def get_queryset(self):
        return Farmer.objects.prefetch_related('orders__items')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        
        # Farmer's order statistics
        farmer_orders = self.object.orders.all()
        context['total_orders'] = farmer_orders.count()
        context['completed_orders'] = farmer_orders.filter(status='COMPLETED').count()
        context['pending_orders'] = farmer_orders.filter(status='PENDING').count()
        context['total_spent'] = farmer_orders.filter(
            status__in=['COMPLETED', 'DELIVERED']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        context['pending_payments'] = farmer_orders.exclude(
            payment_status='PAID'
        ).aggregate(total=Sum(F('total_amount') - F('paid_amount')))['total'] or 0
        
        # Recent orders
        context['recent_orders'] = farmer_orders.order_by('-created_at')[:10]
        
        return context


class FarmerCreateView( CreateView):
    """Create a new farmer"""
    model = Farmer
    template_name = 'farmer_form.html'
    fields = ['name', 'name_mr', 'phone', 'alternate_phone', 'email',
              'address_line1', 'address_line2', 'village', 'taluka', 'district',
              'state', 'pincode', 'farm_size_acres', 'primary_crop', 'notes']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        return context
    
    def form_valid(self, form):
        farmer = form.save()
        messages.success(self.request, f'Farmer {farmer.name} created successfully!')
        return redirect('farmer_detail', pk=farmer.pk)


class FarmerUpdateView(UpdateView):
    """Update farmer details"""
    model = Farmer
    template_name = 'farmer_form.html'
    fields = ['name', 'name_mr', 'phone', 'alternate_phone', 'email',
              'address_line1', 'address_line2', 'village', 'taluka', 'district',
              'state', 'pincode', 'farm_size_acres', 'primary_crop', 'is_active', 'notes']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        return context
    
    def form_valid(self, form):
        farmer = form.save()
        messages.success(self.request, f'Farmer {farmer.name} updated successfully!')
        return redirect('farmer_detail', pk=farmer.pk)


# API Views for AJAX calls

def get_sku_details(request, sku_id):
    """Get SKU details for order form"""
    sku = get_object_or_404(ProductSKU, pk=sku_id)
    
    return JsonResponse({
        'success': True,
        'sku_id': str(sku.id),
        'product_name': sku.product.name,
        'size': sku.size,
        'price': float(sku.price),
        'mrp': float(sku.mrp) if sku.mrp else None,
        'stock_quantity': sku.stock_quantity,
        'reorder_level': sku.reorder_level
    })


def get_farmer_details(request, farmer_id):
    """Get farmer details for order form"""
    farmer = get_object_or_404(Farmer, pk=farmer_id)
    
    return JsonResponse({
        'success': True,
        'farmer_id': str(farmer.id),
        'name': farmer.name,
        'phone': farmer.phone,
        'address': f"{farmer.address_line1}, {farmer.village}, {farmer.taluka}, {farmer.district} - {farmer.pincode}"
    })