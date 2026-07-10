"""
Investment Module — Django Admin

This module uses Firestore as its sole data store. Django ModelAdmin is
not applicable because there are no Django ORM models for investment data.

Operational data is managed through the SPA UI and REST API.
Firebase Console or a future Firestore Admin UI can be used for
emergency data access.
"""

# No admin registrations — Firebase-only architecture.
