from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Message, Status, StatusView
from django.db.models import Q, Max, Count, Exists, OuterRef
from django.utils import timezone
from django.http import JsonResponse
import json

@login_required
def home(request):
    users = User.objects.exclude(id=request.user.id)
    # Add unread counts for each user
    for user in users:
        user.unread_count = Message.objects.filter(
            sender=user,
            receiver=request.user,
            is_read=False
        ).count()
    return render(request, 'chat.html', {
        'users': users
    })

@login_required
def status_list(request):
    # Group statuses by user
    status_users = User.objects.filter(statuses__expires_at__gt=timezone.now()).distinct()
    
    status_data = []
    for user in status_users:
        all_status_count = Status.objects.filter(user=user, expires_at__gt=timezone.now()).count()
        viewed_count = StatusView.objects.filter(viewer=request.user, status__user=user, status__expires_at__gt=timezone.now()).count()
        has_new = all_status_count > viewed_count
        
        status_data.append({
            'user': user,
            'has_new': has_new,
            'latest_status': Status.objects.filter(user=user, expires_at__gt=timezone.now()).first()
        })

    return render(request, 'status_list.html', {
        'status_data': status_data
    })

@login_required
def chat_room(request, username):
    other_user = get_object_or_404(User, username=username)
    users = User.objects.exclude(id=request.user.id)
    
    # Mark messages as read when opening the room
    Message.objects.filter(
        sender=other_user,
        receiver=request.user,
        is_read=False
    ).update(is_read=True)

    # Add unread counts for sidebar
    for user in users:
        user.unread_count = Message.objects.filter(
            sender=user,
            receiver=request.user,
            is_read=False
        ).count()
    
    messages = Message.objects.filter(
        (Q(sender=request.user) & Q(receiver=other_user)) |
        (Q(sender=other_user) & Q(receiver=request.user))
    ).order_by('timestamp')
    
    # Also include status data for the header/sidebar if needed
    status_users = User.objects.filter(statuses__expires_at__gt=timezone.now()).distinct()
    status_data = []
    for user in status_users:
        all_status_count = Status.objects.filter(user=user, expires_at__gt=timezone.now()).count()
        viewed_count = StatusView.objects.filter(viewer=request.user, status__user=user, status__expires_at__gt=timezone.now()).count()
        has_new = all_status_count > viewed_count
        status_data.append({'user': user, 'has_new': has_new})

    return render(request, 'chat.html', {
        'users': users,
        'other_user': other_user,
        'chat_messages': messages,
        'status_data': status_data
    })

@login_required
def create_status(request):
    if request.method == 'POST':
        image = request.FILES.get('image')
        text = request.POST.get('text')
        caption = request.POST.get('caption')
        
        if image or text:
            Status.objects.create(
                user=request.user,
                image=image,
                text=text,
                caption=caption
            )
            return redirect('home')
            
    return render(request, 'create_status.html')

@login_required
def view_status(request, username):
    user = get_object_or_404(User, username=username)
    statuses = Status.objects.filter(user=user, expires_at__gt=timezone.now()).order_by('created_at')
    
    if not statuses.exists():
        return redirect('home')
        
    # Mark as viewed
    for status in statuses:
        StatusView.objects.get_or_create(status=status, viewer=request.user)
        
    return render(request, 'status_viewer.html', {
        'status_user': user,
        'statuses': statuses
    })

@login_required
def media_view(request):
    # Get all messages involving the user that have images
    messages_with_images = Message.objects.filter(
        (Q(sender=request.user) | Q(receiver=request.user)) & 
        Q(image__isnull=False)
    ).exclude(image='').order_by('-timestamp')
    
    return render(request, 'media.html', {
        'media_messages': messages_with_images
    })
