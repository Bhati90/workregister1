from decimal import Decimal
import math

class UnitConverter:
    """Convert between different units for products"""
    
    # Conversion factors to base units (grams for weight, milliliters for volume)
    WEIGHT_CONVERSIONS = {
        'gm': 1,
        'g': 1,
        'gram': 1,
        'kg': 1000,
        'kilogram': 1000,
    }
    
    VOLUME_CONVERSIONS = {
        'ml': 1,
        'milliliter': 1,
        'ltr': 1000,
        'l': 1000,
        'liter': 1000,
        'litre': 1000,
    }
    
    @classmethod
    def normalize_unit(cls, unit):
        """Normalize unit string"""
        return unit.lower().strip()
    
    @classmethod
    def convert_to_base(cls, amount, unit):
        """Convert amount to base unit (grams or milliliters)"""
        unit = cls.normalize_unit(unit)
        
        if unit in cls.WEIGHT_CONVERSIONS:
            return float(amount) * cls.WEIGHT_CONVERSIONS[unit], 'gm'
        elif unit in cls.VOLUME_CONVERSIONS:
            return float(amount) * cls.VOLUME_CONVERSIONS[unit], 'ml'
        
        # Unknown unit, return as-is
        return float(amount), unit
    
    @classmethod
    def are_compatible(cls, unit1, unit2):
        """Check if two units are compatible for conversion"""
        unit1 = cls.normalize_unit(unit1)
        unit2 = cls.normalize_unit(unit2)
        
        weight_compatible = unit1 in cls.WEIGHT_CONVERSIONS and unit2 in cls.WEIGHT_CONVERSIONS
        volume_compatible = unit1 in cls.VOLUME_CONVERSIONS and unit2 in cls.VOLUME_CONVERSIONS
        
        return weight_compatible or volume_compatible


class SKUMatcher:
    """Match required quantities with available SKUs"""
    
    @staticmethod
    def parse_sku_size(size_string):
        """Parse SKU size string like '25kg', '1 Ltr', '100gm' into amount and unit"""
        import re
        
        # Remove extra spaces
        size_string = size_string.strip()
        
        # Match patterns like "25kg", "1 Ltr", "100 gm"
        match = re.match(r'(\d+\.?\d*)\s*([a-zA-Z]+)', size_string)
        
        if match:
            amount = float(match.group(1))
            unit = match.group(2)
            return amount, unit
        
        return None, None
    
    @staticmethod
    def find_optimal_skus_per_farmer(farmer_requirements, available_skus):
        """
        Calculate SKU needs per farmer (can't split packs between farmers)
        
        Args:
            farmer_requirements: list of {'farmer', 'quantity', 'unit'}
            available_skus: QuerySet of ProductSKU objects
            
        Returns:
            list of SKU options with per-farmer calculations
        """
        converter = UnitConverter()
        
        sku_options = []
        
        for sku in available_skus:
            sku_amount, sku_unit = SKUMatcher.parse_sku_size(sku.size)
            
            if not sku_amount or not sku_unit:
                continue
            
            # Check if first farmer's unit is compatible
            if not farmer_requirements:
                continue
                
            first_unit = farmer_requirements[0]['unit']
            if not converter.are_compatible(first_unit, sku_unit):
                continue
            
            # Convert SKU to base unit
            sku_base, base_unit = converter.convert_to_base(sku_amount, sku_unit)
            
            # Calculate for each farmer
            total_units_needed = 0
            total_quantity_provided = 0
            total_quantity_required = 0
            farmer_details = []
            
            for farmer_req in farmer_requirements:
                farmer_quantity = float(farmer_req['quantity'])
                farmer_unit = farmer_req['unit']
                
                # Convert farmer requirement to base unit
                farmer_base, _ = converter.convert_to_base(farmer_quantity, farmer_unit)
                
                # How many SKU units does THIS farmer need? (round up - can't split packs)
                units_for_farmer = math.ceil(farmer_base / sku_base)
                
                total_units_needed += units_for_farmer
                total_quantity_provided += (sku_base * units_for_farmer)
                total_quantity_required += farmer_base
                
                farmer_details.append({
                    'farmer': farmer_req['farmer'],
                    'quantity_needed': farmer_quantity,
                    'units_needed': units_for_farmer,
                    'quantity_provided': (sku_base * units_for_farmer)
                })
            
            # Calculate waste percentage based on total
            if total_quantity_required > 0:
                waste_percentage = ((total_quantity_provided - total_quantity_required) / total_quantity_required) * 100
            else:
                waste_percentage = 0
            
            # Calculate efficiency (prefer less waste, prefer sizes closer to need)
            # Penalty for excessive waste
            if waste_percentage > 1000:  # More than 10x waste
                efficiency = 0
            else:
                efficiency = 100 - min(waste_percentage / 10, 50)  # Cap waste penalty at 50
                
                # Bonus for having enough stock
                if sku.stock_quantity >= total_units_needed:
                    efficiency += 25
            
            sku_options.append({
                'sku': sku,
                'sku_amount': sku_amount,
                'sku_unit': sku_unit,
                'sku_base_amount': sku_base,
                'units_needed': total_units_needed,
                'total_quantity_required_base': total_quantity_required,
                'total_quantity_provided_base': total_quantity_provided,
                'waste_percentage': waste_percentage,
                'efficiency': efficiency,
                'in_stock': sku.stock_quantity >= total_units_needed,
                'stock_available': sku.stock_quantity,
                'stock_shortage': max(0, total_units_needed - sku.stock_quantity),
                'farmer_details': farmer_details,
                'base_unit': base_unit
            })
        
        # Sort by efficiency (best first)
        sku_options.sort(key=lambda x: x['efficiency'], reverse=True)
        
        return sku_options
    
    @staticmethod
    def get_best_combination(farmer_requirements, available_skus, max_combinations=3):
        """
        Get best SKU combinations considering per-farmer needs
        
        Args:
            farmer_requirements: list of {'farmer', 'quantity', 'unit'}
            available_skus: QuerySet of ProductSKU objects
        """
        options = SKUMatcher.find_optimal_skus_per_farmer(farmer_requirements, available_skus)
        
        return options[:max_combinations]