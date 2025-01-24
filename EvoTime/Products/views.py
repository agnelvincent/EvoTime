from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth import authenticate, login , logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from user_home.models import CustomUser, Address
from admin_home.models import Brand , Category , Product , ProductVariant
from admin_home.models import Product
from django.contrib.auth.hashers import make_password
from django.views.decorators.cache import never_cache
import re
from django.contrib.auth import login
from django.utils.crypto import get_random_string
from datetime import datetime, timedelta
from django.urls import reverse
from django.http import JsonResponse
