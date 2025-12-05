# herbalapp/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.db.models import Sum
from django.contrib.auth.decorators import login_required

from .models import Member, Payment, Income, Product
from .forms import MemberForm, ProductForm


# -----------------------------------
# Member Login / Register
# -----------------------------------
def member_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect("member_list")
        else:
            messages.error(request, "Invalid username or password")

    return render(request, "member_login.html")


def member_register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if Member.objects.filter(name=username).exists():
            messages.error(request, "Username already taken!")
        else:
            new_member = Member(name=username, email=email)
            new_member.save()
            messages.success(request, "Member registered! Please login.")
            return redirect("member_login")

    return render(request, "member_register.html")


# -----------------------------------
# Dashboard + Common Views
# -----------------------------------
def home(request):
    return render(request, "home.html", {"company_name": "Rocky Herbals"})


def admin_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect("admin_dashboard")
        else:
            return render(request, "adminlogin.html", {"error": "Invalid credentials"})

    return render(request, "adminlogin.html")


@login_required
def admin_dashboard(request):
    total_members = Member.objects.count()
    paid = Payment.objects.filter(status="Paid").count()
    unpaid = total_members - paid

    income = Payment.objects.filter(status="Paid").aggregate(total=Sum("amount"))[
        "total"
    ] or 0

    context = {
        "company_name": "Rocky Herbals",
        "total_members": total_members,
        "paid": paid,
        "unpaid": unpaid,
        "income": income,
        "products_count": Product.objects.count(),
        "income_count": Income.objects.count(),
    }

    return render(request, "admin_dashboard.html", context)


# -----------------------------------
# Member Management
# -----------------------------------
def add_member(request):
    next_id = (Member.objects.last().id + 1) if Member.objects.exists() else 1

    if request.method == "POST":
        form = MemberForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("member_list")
    else:
        form = MemberForm()

    return render(request, "add_member.html", {"form": form, "next_id": next_id})


def member_list(request):
    members = Member.objects.all()
    return render(request, "member_list.html", {"members": members})


# -----------------------------------
# Product Views
# -----------------------------------
def product_list(request):
    products = Product.objects.all().order_by("-created_at")
    return render(request, "products.html", {"products": products})


def add_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Product added successfully!")
            return redirect("products")
        else:
            messages.error(request, "Error adding product.")
    else:
        form = ProductForm()

    return render(request, "add_product.html", {"form": form})


def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        product.delete()
        messages.success(request, "Product deleted!")
        return redirect("products")

    return redirect("products")


# =====================================================
# MLM PYRAMID BINARY TREE VIEWS
# =====================================================

def member_tree(request):
    root = Member.objects.filter(parent__isnull=True).first()
    return render(request, "member_tree.html", {"root": root})


def place_member_view(request):
    parent_id = request.GET.get("parent_id")
    side = request.GET.get("side")

    parent = Member.objects.filter(id=parent_id).first() if parent_id else None

    if request.method == "POST":

        child = Member.objects.create(
            name=request.POST.get("name"),
            email=request.POST.get("email"),
            aadhar_number=request.POST.get("aadhar_number"),
            mobile_number=request.POST.get("mobile_number"),
            district=request.POST.get("district"),
            taluk=request.POST.get("taluk"),
            pincode=request.POST.get("pincode"),
            parent=parent,
            position=side,
        )

        if parent:
            if side == "L":
                parent.left_child = child
            else:
                parent.right_child = child
            parent.save()

        return redirect("member_tree")

    return render(request, "place_member.html", {"parent": parent, "side": side})


@login_required
def delete_member(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    parent = member.parent

    if request.method == "POST":
        if parent:
            if parent.left_child_id == member.id:
                parent.left_child = None
            if parent.right_child_id == member.id:
                parent.right_child = None
            parent.save()

        member.delete()
        messages.success(request, f"Member {member.name} deleted successfully")
        return redirect("member_tree")

    return render(request, "confirm_delete.html", {"member": member})


@login_required
def replace_member(request, member_id):
    member = get_object_or_404(Member, pk=member_id)

    if request.method == "POST":
        member.name = request.POST.get("name")
        member.email = request.POST.get("email")
        member.aadhar_number = request.POST.get("aadhar_number")
        member.mobile_number = request.POST.get("mobile_number")
        member.district = request.POST.get("district")
        member.taluk = request.POST.get("taluk")
        member.pincode = request.POST.get("pincode")
        member.save()

        messages.success(request, "Member data updated!")
        return redirect("member_tree")

    return render(request, "replace_member.html", {"member": member})


# -----------------------------------
# Static Pages
# -----------------------------------
def about(request):
    return render(request, "about.html")


def shop_login(request):
    return render(request, "shop_login.html")


def contact(request):
    return render(request, "contact.html")


def join(request):
    return render(request, "join.html")

from django.shortcuts import render, redirect, get_object_or_404
from .models import Member


def member_tree(request):
    """
    Show the full binary tree starting from the root (first member).
    """
    try:
        root = Member.objects.filter(parent__isnull=True).first()
    except Member.DoesNotExist:
        root = None

    return render(request, "member_tree.html", {
        "root": root
    })

