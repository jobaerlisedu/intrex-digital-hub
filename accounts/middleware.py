from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib import messages
from django.utils import timezone
from accounts.models import ActiveSession, get_client_ip, log_action_async
from datetime import timedelta

class ActiveSessionMiddleware:
    """
    Middleware to track active user sessions and enforce automatic 30-minute idle session timeouts.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            session_key = request.session.session_key
            if session_key:
                now = timezone.now()
                idle_limit = timedelta(minutes=30)
                cutoff = now - idle_limit

                # Atomic upsert with timeout enforcement — prevents duplicate session records
                updated = ActiveSession.objects.filter(
                    session_key=session_key
                ).filter(
                    last_activity__gte=cutoff
                ).update(
                    last_activity=now,
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                )

                if updated == 0:
                    # Either no record exists, or session expired
                    ActiveSession.objects.filter(session_key=session_key).delete()
                    ActiveSession.objects.create(
                        session_key=session_key,
                        user=request.user,
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                    )

                    # If the session was expired (record existed but too old), log and logout
                    expired = ActiveSession.objects.filter(
                        session_key=session_key,
                        last_activity__lt=cutoff,
                    ).first()
                    if expired:
                        expired.delete()
                        log_action_async(
                            user=request.user,
                            action='SESSION_TIMEOUT',
                            module='auth',
                            description="User session expired due to 30-minute idle timeout.",
                            ip_address=get_client_ip(request),
                        )
                        logout(request)
                        messages.warning(request, "Your session has expired due to inactivity. Please log in again.")
                        return redirect('login')
        
        response = self.get_response(request)
        return response
