# 欢迎程序
# 为了极简，视图直接写在 urls.py 里
from django.urls import path
from django.http import HttpResponse

def welcome(request):
    return HttpResponse("Welcome to Django on Docker! (Python 3.12)")

urlpatterns = [
    path('', welcome),
]
