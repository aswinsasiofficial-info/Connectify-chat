from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

@login_required
def profile(request):
    if request.method == 'POST':
        if 'delete_account' in request.POST:
            user = request.user
            user.delete()
            return redirect('login')
        
        avatar = request.FILES.get('avatar')
        if avatar:
            request.user.profile.avatar = avatar
            request.user.profile.save()
            return redirect('profile')
    return render(request, 'profile.html')
