import json
import os
from django.conf import settings


def vite_assets(request):
    """
    Context processor that provides Vite asset URLs.

    In DEBUG mode, returns the Vite dev server URL.
    In production, reads the manifest and returns the hashed bundle URL.
    """
    ctx = {
        'use_vite_dev': settings.DEBUG,
        'vite_dev_url': 'http://localhost:5173',
        'vite_js_url': '',
        'vite_css_url': '',
    }

    if settings.DEBUG:
        ctx['vite_js_url'] = 'http://localhost:5173/static_src/js/main.js'
    else:
        manifest_path = os.path.join(settings.BASE_DIR, 'static', 'dist', 'manifest.json')
        if os.path.exists(manifest_path):
            with open(manifest_path) as f:
                manifest = json.load(f)
            for key, value in manifest.items():
                if key.endswith('main.js'):
                    ctx['vite_js_url'] = settings.STATIC_URL + 'dist/' + value['file']
                elif key.endswith('.css'):
                    ctx['vite_css_url'] = settings.STATIC_URL + 'dist/' + value['file']

    return ctx
