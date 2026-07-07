"""
SPA Fragment Middleware for Intrex ERP

When a request includes the header X-SPA-Fragment: true,
this middleware intercepts the HTML response, extracts the
content inside #spa-content, and returns a minimal JSON/HTML
response containing only the fragment — no full page re-render.

This enables the SPA router to fetch only the content portion
of each page, dramatically reducing payload and render time.
"""

import re
from django.utils.deprecation import MiddlewareMixin


class SPAFragmentMiddleware(MiddlewareMixin):
    """
    Middleware that extracts content fragments for SPA navigation.

    When the X-SPA-Fragment header is present:
    1. The view renders the full template as normal
    2. This middleware processes the response HTML
    3. Extracts the #spa-content div, title, and extra CSS/JS
    4. Returns a minimal JSON response with those fragments
    """

    def process_response(self, request, response):
        # Only process HTML responses with the SPA header
        if request.headers.get('X-SPA-Fragment') != 'true':
            return response

        content_type = response.get('Content-Type', '')
        if 'text/html' not in content_type:
            return response

        html = response.content.decode('utf-8')

        # Extract title
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        title = title_match.group(1) if title_match else 'Intrex ERP'

        # Extract content block (no comment marker needed)
        content_match = re.search(
            r'<div[^>]*id="spa-content"[^>]*>(.*?)</div>',
            html,
            re.DOTALL | re.IGNORECASE
        )
        content_html = content_match.group(1) if content_match else html

        # Extract page-specific styles (data-spa-style)
        extra_css = ''
        css_matches = re.findall(
            r'<style[^>]*data-spa-style[^>]*>(.*?)</style>',
            html,
            re.DOTALL | re.IGNORECASE
        )
        if css_matches:
            extra_css = '\n'.join(css_matches)

        # Extract page-specific scripts (data-spa-script)
        extra_js = ''
        js_matches = re.findall(
            r'<script[^>]*data-spa-script[^>]*>(.*?)</script>',
            html,
            re.DOTALL | re.IGNORECASE
        )
        if js_matches:
            extra_js = '\n'.join(js_matches)

        # Build fragment response
        from django.http import JsonResponse
        return JsonResponse({
            'content': content_html,
            'title': title,
            'extra_css': extra_css,
            'extra_js': extra_js,
        })
