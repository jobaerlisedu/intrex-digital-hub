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
                # 1. Check or create active session record
                active_sess, created = ActiveSession.objects.get_or_create(
                    session_key=session_key,
                    defaults={
                        'user': request.user,
                        'ip_address': get_client_ip(request),
                        'user_agent': request.META.get('HTTP_USER_AGENT', '')[:255]
                    }
                )

                # 2. Check for idle timeout (30 minutes)
                idle_limit = timedelta(minutes=30)
                if not created and (now - active_sess.last_activity) > idle_limit:
                    # Session has expired due to inactivity
                    log_action_async(
                        user=request.user,
                        action='SESSION_TIMEOUT',
                        module='auth',
                        description=f"User session expired due to 30-minute idle timeout.",
                        ip_address=get_client_ip(request)
                    )
                    # Delete the active session and logout
                    active_sess.delete()
                    logout(request)
                    messages.warning(request, "Your session has expired due to inactivity. Please log in again.")
                    return redirect('login')
                
                # 3. Update last activity timestamp
                active_sess.last_activity = now
                active_sess.save(update_fields=['last_activity'])
        
        response = self.get_response(request)
        return response
