"""
Standalone Django Script to Import Products
Run with: python import_products_script.py

Make sure Django environment is set up:
    import os
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')
    django.setup()
"""

import os
import django
import openpyxl

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'labour_crm.settings')
django.setup()

from django.db import transaction
from inventory.models import Company, ProductCategory, Product, ProductSKU


def import_products_from_excel(file_path):
    """Import all products from Excel file"""
    
    print(f"Loading Excel file: {file_path}")
    workbook = openpyxl.load_workbook(file_path)
    sheet = workbook.active
    
    # Parse data
    products_data = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if not row[0]:  # Skip empty rows
            continue
        
        products_data.append({
            'company_name': row[0],
            'sap_code': row[1],
            'product_name': row[2],
            'molecule': row[3],
            'pack_size': str(row[4]) if row[4] else '',
            'price': float(row[5]) if row[5] else 0
        })
    
    print(f"Found {len(products_data)} products")
    
    # Import with transaction
    with transaction.atomic():
        stats = {
            'companies_created': 0,
            'categories_created': 0,
            'products_created': 0,
            'skus_created': 0
        }
        
        # Create companies
        print("\nCreating companies...")
        companies = {}
        company_names = set(p['company_name'] for p in products_data if p['company_name'])
        
        for idx, company_name in enumerate(company_names, 1):
            company, created = Company.objects.get_or_create(
                name=company_name,
                defaults={'description': 'Auto-imported company'}
            )
            companies[company_name] = company
            if created:
                stats['companies_created'] += 1
            
            if idx % 20 == 0:
                print(f"  Processed {idx}/{len(company_names)} companies...")
        
        # Create categories
        print("\nCreating categories...")
        categories = {}
        molecule_names = set(p['molecule'] for p in products_data if p['molecule'])
        
        for idx, molecule_name in enumerate(molecule_names, 1):
            category, created = ProductCategory.objects.get_or_create(
                name=molecule_name,
                defaults={'description': f'Product category for {molecule_name}'}
            )
            categories[molecule_name] = category
            if created:
                stats['categories_created'] += 1
            
            if idx % 50 == 0:
                print(f"  Processed {idx}/{len(molecule_names)} categories...")
        
        # Create products and SKUs
        print("\nCreating products and SKUs...")
        for idx, product_data in enumerate(products_data, 1):
            company_name = product_data['company_name']
            molecule = product_data['molecule']
            product_name = product_data['product_name']
            pack_size = product_data['pack_size']
            price = product_data['price']
            
            if not all([company_name, molecule, product_name, pack_size]):
                continue
            
            company = companies.get(company_name)
            category = categories.get(molecule)
            
            if not company or not category:
                continue
            
            # Extract base product name
            base_name = product_name.rsplit(' - ', 1)[0].strip()
            
            # Get or create product
            product, created = Product.objects.get_or_create(
                company=company,
                name=base_name,
                defaults={
                    'category': category,
                    'technical_composition': molecule,
                    'description': f'{base_name} - {molecule}',
                }
            )
            
            if created:
                stats['products_created'] += 1
            
            # Create SKU
            sku, sku_created = ProductSKU.objects.get_or_create(
                product=product,
                size=pack_size,
                defaults={
                    'price': price,
                    'mrp': price,
                    'stock_quantity': 0,
                    'reorder_level': 10,
                    'max_stock_level': 100
                }
            )
            
            if sku_created:
                stats['skus_created'] += 1
            
            if idx % 100 == 0:
                print(f"  Processed {idx}/{len(products_data)} products...")
        
        # Print statistics
        print("\n" + "="*60)
        print("IMPORT COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"Companies created:  {stats['companies_created']} (Total: {len(companies)})")
        print(f"Categories created: {stats['categories_created']} (Total: {len(categories)})")
        print(f"Products created:   {stats['products_created']}")
        print(f"SKUs created:       {stats['skus_created']}")
        print("="*60)


if __name__ == '__main__':
    # Update this path to your Excel file
    EXCEL_FILE = 'inventory/list.xlsx'
    
    try:
        import_products_from_excel(EXCEL_FILE)
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()