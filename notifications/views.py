from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST


@login_required
def inbox(request):
    items = request.user.notifications.all()[:50]
    return render(request, "notifications/inbox.html", {"items": items})


@login_required
@require_POST
def mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect("notifications:inbox")
