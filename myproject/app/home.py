from django.shortcuts import render


def index(request):
    # Xử lý logic cho trang chủ ở đây
    return render(request, 'app/index.html')
