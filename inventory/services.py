from django.db import transaction
from .models import Product, InventoryLedger


def adjust_stock(product, quantity_change, transaction_type, reference, user):
    with transaction.atomic():
        InventoryLedger.objects.create(
            product=product,
            product_name=product.item_name,
            quantity_change=quantity_change,
            unit_cost=product.unit_price,
            transaction_type=transaction_type,
            reference=reference,
            created_by=user,
        )
        product.quantity += quantity_change
        product.save()
    return product


def get_stock_value():
    products = Product.objects.all()
    return sum(p.quantity * p.unit_price for p in products)
