from django.urls import path, include

app_routers = [
    ('hrm/', 'hrm.api.urls'),
    ('inventory/', 'inventory.api.urls'),
    ('billing/', 'billing.api.urls'),
    ('training/', 'training.api.urls'),
    ('solutions/', 'solutions.api.urls'),
    ('investment/', 'investment.api.urls'),
]

urlpatterns = [path(prefix, include(module)) for prefix, module in app_routers]
