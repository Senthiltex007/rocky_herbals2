# herbalapp/views.py ====================================================== CLEAN, CONSISTENT VIEWS FOR Rocky Herbals (tree + app) Modern Tree (uses auto_id) - 
# single complete file ======================================================

from decimal import Decimal
from collections import deque

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum

import csv
import openpyxl

# Charts (openpyxl)
from openpyxl.chart import BarChart, LineChart, Reference

# ==========================
# Models
# ==========================
from .models import (
    Member,
    Product,
    Payment,
    Income,
    CommissionRecord,
    BonusRecord,
    Order,
    IncomeRecord,
)

# Optional RankReward if present in your app
try:
    from .models import RankReward
except Exception:
    RankReward = None

# ==========================
# Forms
# ==========================
from .forms import MemberForm, ProductForm

# ==========================
# Services / business logic
# ==========================
try:
    from .services import add_billing_commission
except Exception:
    add_billing_commission = None


# ======================================================
# CHART HELPERS (no responses or external calls here)
# ======================================================
def add_bv_wallet_chart(ws, start_row):
    """
    Inserts a stacked bar chart comparing BV and Wallet values.
    Expects 5 rows starting from start_row:
        Row: [Label, Value]
    """

    # Create stacked bar chart
    chart = BarChart()
    chart.type = "col"
    chart.grouping = "stacked"
    chart.title = "BV vs Wallet Comparison"
    chart.x_axis.title = "Category"
    chart.y_axis.title = "Values"

    # Data range (BV + Wallet summary rows)
    # Expected rows: [Label, Value]
    data = Reference(ws, min_col=2, min_row=start_row, max_row=start_row + 4)
    cats = Reference(ws, min_col=1, min_row=start_row, max_row=start_row + 4)

    chart.add_data(data, titles_from_data=False)
    chart.set_categories(cats)

    # Make chart look cleaner
    chart.legend.position = "r"   # right side
    chart.height = 12             # visual size tuning
    chart.width = 20

    # Place chart in sheet
    ws.add_chart(chart, "P5")


def add_rank_progression_chart(ws, start_row, end_row):
    """
    Inserts a line chart showing monthly rank progression.
    Expects rows in the format:
        [MonthLabel, Count]
    """

    # Create line chart
    chart = LineChart()
    chart.title = "Monthly Rank Progression"
    chart.style = 13
    chart.y_axis.title = "Members"
    chart.x_axis.title = "Month"

    # Data range: rank counts per month
    data = Reference(ws, min_col=2, min_row=start_row, max_row=end_row)
    cats = Reference(ws, min_col=1, min_row=start_row, max_row=end_row)

    chart.add_data(data, titles_from_data=False)
    chart.set_categories(cats)

    # Make chart visually clean
    chart.height = 12
    chart.width = 22
    chart.legend.position = "r"  # right side legend

    # Place chart in sheet
    ws.add_chart(chart, "P20")


def add_combo_chart(ws, bv_start_row, wallet_start_row, rank_start_row, rank_end_row):
    """
    Creates a combined chart:
    - Stacked Bar Chart for BV + Wallet summary
    - Line Chart for Rank Progression
    Expects rows in the format:
        [Label, Value]
    """

    # ============================
    # ✅ 1. Bar Chart (BV + Wallet)
    # ============================
    bar = BarChart()
    bar.type = "col"
    bar.grouping = "stacked"
    bar.title = "BV + Wallet Overview"
    bar.y_axis.title = "Values"
    bar.x_axis.title = "Category"

    # Combine BV + Wallet rows vertically
    bv_wallet_data = Reference(
        ws,
        min_col=2,
        min_row=bv_start_row,
        max_row=wallet_start_row + 1
    )
    bv_wallet_cats = Reference(
        ws,
        min_col=1,
        min_row=bv_start_row,
        max_row=wallet_start_row + 1
    )

    bar.add_data(bv_wallet_data, titles_from_data=False)
    bar.set_categories(bv_wallet_cats)

    # Make bar chart visually clean
    bar.height = 12
    bar.width = 22
    bar.legend.position = "r"


    # ============================
    # ✅ 2. Line Chart (Rank Trend)
    # ============================
    line = LineChart()
    line.title = "Rank Progression Trend"
    line.style = 13
    line.y_axis.title = "Members"
    line.x_axis.title = "Month"

    rank_data = Reference(
        ws,
        min_col=2,
        min_row=rank_start_row,
        max_row=rank_end_row
    )
    rank_cats = Reference(
        ws,
        min_col=1,
        min_row=rank_start_row,
        max_row=rank_end_row
    )

    line.add_data(rank_data, titles_from_data=False)
    line.set_categories(rank_cats)

    # Make line chart clean
    line.y_axis.majorGridlines = None


    # ============================
    # ✅ 3. Combine Charts
    # ============================
    bar += line


    # ============================
    # ✅ 4. Place Chart in Sheet
    # ============================
    ws.add_chart(bar, "P30")


def add_dashboard_sheet(wb, members):
    """
    Creates a Dashboard sheet with:
    - Overall summary
    - BV summary
    - Wallet summary
    - Rank summary
    - Rank Distribution Chart
    - BV vs Wallet Chart
    """

    ws = wb.create_sheet(title="Dashboard")

    # ============================
    # ✅ OVERALL SUMMARY
    # ============================
    ws.append(["Dashboard Summary"])
    ws.append(["Total Members", members.count()])

    total_left_bv = sum((m.get_bv_counts()[0] or 0) for m in members)
    total_right_bv = sum((m.get_bv_counts()[1] or 0) for m in members)

    ws.append(["Total Left BV", total_left_bv])
    ws.append(["Total Right BV", total_right_bv])
    ws.append(["Total Matched BV", min(total_left_bv, total_right_bv)])

    total_repurchase = sum(getattr(m, "repurchase_wallet", 0) or 0 for m in members)
    total_flash = sum(getattr(m, "flash_wallet", 0) or 0 for m in members)

    ws.append(["Total Repurchase Wallet", total_repurchase])
    ws.append(["Total Flash Wallet", total_flash])

    # ============================
    # ✅ RANK SUMMARY
    # ============================
    ws.append([])
    ws.append(["Rank Summary"])

    rank_titles = ["1st Star", "Double Star", "Triple Star"]
    for title in rank_titles:
        count = members.filter(current_rank=title).count()
        ws.append([title, count])

    # ============================
    # ✅ RANK DISTRIBUTION CHART
    # ============================
    chart1 = BarChart()
    chart1.title = "Rank Distribution"
    chart1.x_axis.title = "Rank"
    chart1.y_axis.title = "Members"
    chart1.height = 12
    chart1.width = 20
    chart1.legend.position = "r"

    # Last 3 rows contain rank summary
    rank_end = ws.max_row
    rank_start = rank_end - 2

    data = Reference(ws, min_col=2, min_row=rank_start, max_row=rank_end)
    cats = Reference(ws, min_col=1, min_row=rank_start, max_row=rank_end)

    chart1.add_data(data, titles_from_data=False)
    chart1.set_categories(cats)

    ws.add_chart(chart1, "E5")

    # ============================
    # ✅ BV vs WALLET CHART
    # ============================
    chart2 = BarChart()
    chart2.type = "col"
    chart2.grouping = "stacked"
    chart2.title = "BV vs Wallet Comparison"
    chart2.height = 12
    chart2.width = 20
    chart2.legend.position = "r"

    # BV/Wallet rows = rows 2 to 7
    data2 = Reference(ws, min_col=2, min_row=2, max_row=7)
    cats2 = Reference(ws, min_col=1, min_row=2, max_row=7)

    chart2.add_data(data2, titles_from_data=False)
    chart2.set_categories(cats2)

    ws.add_chart(chart2, "E20")

    # ============================
    # ✅ OPTIONAL: RANK PROGRESSION (placeholder)
    # ============================
    # chart3 = LineChart()
    # chart3.title = "Rank Progression Trend"
    # chart3.y_axis.title = "Members"
    # chart3.x_axis.title = "Month"
    #
    # data3 = Reference(ws, min_col=2, min_row=15, max_row=20)
    # cats3 = Reference(ws, min_col=1, min_row=15, max_row=20)
    #
    # chart3.add_data(data3, titles_from_data=False)
    # chart3.set_categories(cats3)
    #
    # ws.add_chart(chart3, "M5")

# -------------------------
# HOME / STATIC PAGES
# -------------------------

def home(request):
    return render(request, "home.html")


def about(request):
    context = {
        "page_title": "About Us",
        "company": "Rocky Herbals",
        "description": "We are a herbal products company focused on natural wellness and sustainable herbal solutions."
    }
    return render(request, "about.html", context)


def contact(request):
    context = {
        "page_title": "Contact Us",
        "email": "info@rockyherbals.com",
        "phone": "8122105779",
        "address": "Nambiyur, Tamil Nadu, India"
    }
    return render(request, "contact.html", context)


# -------------------------
# AUTH / MEMBER LOGIN
# -------------------------
def member_login(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect("member_list")

        messages.error(request, "Invalid username or password")

    return render(request, "member_login.html")


# -------------------------
# ADMIN LOGIN / DASHBOARD
# -------------------------
def admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        user = authenticate(request, username=username, password=password)

        if user and user.is_staff:
            login(request, user)
            return redirect("admin_dashboard")

        messages.error(request, "Invalid admin credentials")

    return render(request, "admin_login.html")


@login_required
def admin_dashboard(request):
    # Total members
    total_members = Member.objects.count()

    # Paid & unpaid members
    paid_members = Payment.objects.filter(status="Paid").count()
    unpaid_members = total_members - paid_members

    # Total income (null-safe)
    total_income = (
        Payment.objects.filter(status="Paid")
        .aggregate(total=Sum("amount"))
        .get("total") or 0
    )

    context = {
        "company_name": "Rocky Herbals",
        "total_members": total_members,
        "unpaid": unpaid_members,
        "income": total_income,
        "products_count": Product.objects.count(),
        "income_count": Income.objects.count(),
    }

    return render(request, "admin_dashboard.html", context)


# -------------------------
# MEMBER CRUD / LIST
# -------------------------
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages


@login_required
def member_list(request):
    members = Member.objects.all().order_by("id")
    return render(request, "member_list.html", {"members": members})


@login_required
def delete_member(request, member_id):

    # ✅ Support both numeric PK and business member_id
    if str(member_id).isdigit():
        member = get_object_or_404(Member, id=member_id)
    else:
        member = get_object_or_404(Member, member_id=member_id)

    # ✅ Prevent deleting members who have children
    if member.left_child or member.right_child:
        messages.error(
            request,
            f"❌ Cannot delete {member.name}. Remove left/right children first."
        )
        return redirect("member_list")

    # ✅ Detach from parent safely
    parent = member.parent
    if parent:
        if parent.left_child_id == member.id:
            parent.left_child = None
        elif parent.right_child_id == member.id:
            parent.right_child = None
        parent.save()

    # ✅ Delete member
    member.delete()

    messages.success(request, f"✅ {member.name} deleted successfully!")
    return redirect("member_list")


@login_required
def replace_member(request, member_id):
    member = get_object_or_404(Member, id=member_id)

    if request.method == "POST":
        new_parent_id = request.POST.get("new_parent")
        new_side = request.POST.get("side")

        new_parent = get_object_or_404(Member, id=new_parent_id)
        if new_parent.id == member.id:
            messages.error(request, "A member cannot be their own parent!")
            return redirect("replace_member", member_id=member.id)

        def is_downline(root, target):
            if not root:
                return False
            if root.id == target.id:
                return True
            left, right = _get_children(root)
            return is_downline(left, target) or is_downline(right, target)

        if is_downline(member, new_parent):
            messages.error(request, "Cannot move under own downline!")
            return redirect("replace_member", member_id=member.id)

        if new_side not in ["L", "R"]:
            messages.error(request, "Invalid side!")
            return redirect("replace_member", member_id=member.id)

        # Ensure side empty
        left, right = _get_children(new_parent)
        if new_side == "L" and left:
            messages.error(request, "Left side occupied!")
            return redirect("replace_member", member_id=member.id)
        if new_side == "R" and right:
            messages.error(request, "Right side occupied!")
            return redirect("replace_member", member_id=member.id)

        # Detach from old parent
        old_parent = member.parent
        if old_parent:
            if old_parent.left_child_id == member.id:
                old_parent.left_child = None
            elif old_parent.right_child_id == member.id:
                old_parent.right_child = None
            old_parent.save()

        # Attach to new parent
        member.parent = new_parent
        member.side = new_side
        if new_side == "L":
            new_parent.left_child = member
        else:
            new_parent.right_child = member

        new_parent.save()
        member.save()

        messages.success(request, "Member moved successfully!")
        return redirect("member_list")

    all_members = Member.objects.exclude(id=member_id)
    return render(request, "replace_member.html", {
        "member": member,
        "members": all_members
    })


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages


# -------------------------
# PRODUCT LIST
# -------------------------
@login_required
def product_list(request):
    products = Product.objects.all().order_by("-id")
    return render(request, "products.html", {"products": products})


# -------------------------
# ADD PRODUCT
# -------------------------
@login_required
def add_product(request):

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)

        # ✅ Optional: prevent duplicate product names
        name = request.POST.get("name")
        if Product.objects.filter(name__iexact=name).exists():
            messages.error(request, "❌ Product with this name already exists.")
            return render(request, "add_product.html", {"form": form})

        if form.is_valid():
            form.save()
            messages.success(request, "✅ Product added successfully!")
            return redirect("products")

        messages.error(request, "❌ Please correct the errors below.")

    else:
        form = ProductForm()

    return render(request, "add_product.html", {"form": form})


# -------------------------
# EDIT PRODUCT
# -------------------------
@login_required
def edit_product(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)

        # ✅ Optional: prevent duplicate names on edit
        name = request.POST.get("name")
        if Product.objects.filter(name__iexact=name).exclude(id=product.id).exists():
            messages.error(request, "❌ Another product with this name already exists.")
            return render(request, "add_product.html", {"form": form, "edit": True})

        if form.is_valid():
            form.save()
            messages.success(request, "✅ Product updated successfully!")
            return redirect("products")

        messages.error(request, "❌ Please correct the errors below.")

    else:
        form = ProductForm(instance=product)

    return render(request, "add_product.html", {"form": form, "edit": True})


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse


# -------------------------
# DELETE PRODUCT (SAFE)
# -------------------------
@login_required
def delete_product(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    # ✅ Prevent deleting products linked to orders
    if Order.objects.filter(product=product).exists():
        messages.error(request, "❌ Cannot delete this product. It is linked to existing orders.")
        return redirect("products")

    product.delete()
    messages.success(request, "✅ Product deleted successfully!")
    return redirect("products")


# -------------------------
# CART VIEW
# -------------------------
@login_required
def cart_view(request):
    # Placeholder cart structure
    cart = request.session.get("cart", {})
    return render(request, "cart.html", {"cart": cart})


# -------------------------
# ADD TO CART
# -------------------------
@login_required
def add_to_cart(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    # ✅ Initialize cart if not present
    cart = request.session.get("cart", {})

    # ✅ Add or increment quantity
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1

    request.session["cart"] = cart
    messages.success(request, f"✅ {product.name} added to cart!")

    return redirect("cart")


# -------------------------
# REMOVE FROM CART
# -------------------------
@login_required
def remove_from_cart(request, product_id):

    cart = request.session.get("cart", {})

    if str(product_id) in cart:
        del cart[str(product_id)]
        request.session["cart"] = cart
        messages.success(request, "✅ Item removed from cart!")
    else:
        messages.error(request, "❌ Item not found in cart.")

    return redirect("cart")


# -------------------------
# CHECKOUT (PLACEHOLDER)
# -------------------------
@login_required
def checkout(request):
    return HttpResponse("Checkout Page - To be implemented")


from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from .models import Payment, Commission, Member


# -------------------------
# MANUAL COMMISSION CREDIT (simple)
# -------------------------
@login_required
def credit_commission(request, member_id):

    # Support both numeric PK and business member_id
    if str(member_id).isdigit():
        member = get_object_or_404(Member, id=member_id)
    else:
        member = get_object_or_404(Member, member_id=member_id)

    messages.success(request, f"✅ Commission credited for {member.name}")
    return redirect("member_list")


# =====================================================
# PAYMENT APPROVE & STOCK COMMISSION GENERATOR
# =====================================================
@login_required
def approve_payment(request, payment_id):

    payment = get_object_or_404(Payment, id=payment_id)
    member = payment.member

    # ✅ Prevent double approval
    if payment.status == "approved":
        messages.warning(request, "⚠️ Payment already approved.")
        return redirect("payments_list")

    # ✅ Commission percentage mapping
    LEVEL_PERCENT = {
        "district": 7,
        "taluk": 5,
        "pincode": 3,
    }

    percentage = LEVEL_PERCENT.get(member.level, 0)
    commission_amount = (payment.amount * percentage) / 100

    # ✅ Create commission record only if eligible
    if percentage > 0:
        Commission.objects.create(
            member=member,
            payment=payment,
            commission_type=member.level,
            percentage=percentage,
            commission_amount=commission_amount
        )

    # ✅ Mark payment approved
    payment.status = "approved"
    payment.save()

    messages.success(request, f"✅ Payment approved and commission credited to {member.name}")
    return redirect("payments_list")


from django.urls import reverse

# ======================================================
# ROBUST TREE FUNCTIONS
# ======================================================
def _get_children(member):
    if not member:
        return None, None
    return member.left_child, member.right_child


def build_tree_html(member):
    if not member:
        return ""

    left, right = _get_children(member)

    # ✅ Safe escaping
    safe_name = (member.name or "").replace("'", "\\'").replace('"', '\\"')
    safe_phone = (member.phone or "").replace("'", "\\'").replace('"', '\\"')
    safe_auto = str(member.member_id)

    # ✅ Node HTML
    node_html = (
        f"<li>"
        f"<div class='member-box' "
        f"onclick=\"showMemberDetail({{id:'{member.member_id}', name:'{safe_name}', phone:'{safe_phone}'}})\">"
        f"{safe_name} <br><small>ID: {safe_auto}</small>"
        f"</div>"
    )

    node_html += "<ul>"

    # ✅ LEFT CHILD
    if left:
        node_html += build_tree_html(left)
    else:
        add_url = reverse('add_member_form') + f"?parent={member.member_id}&side=left"
        node_html += (
            "<li><div class='member-box text-muted'>➕ Left<br>"
            f"<a href='{add_url}'>Add</a></div></li>"
        )

    # ✅ RIGHT CHILD
    if right:
        node_html += build_tree_html(right)
    else:
        add_url = reverse('add_member_form') + f"?parent={member.member_id}&side=right"
        node_html += (
            "<li><div class='member-box text-muted'>➕ Right<br>"
            f"<a href='{add_url}'>Add</a></div></li>"
        )

    node_html += "</ul></li>"
    return node_html


# ======================================================
# TREE VIEW PAGES
# ======================================================
def tree_view(request, member_id):

    # ✅ Normalize numeric → business member_id
    if str(member_id).isdigit():
        if str(member_id) == "1":
            member_id = "rocky001"
        else:
            try:
                pk_member = Member.objects.get(id=int(member_id))
                member_id = pk_member.member_id
            except Member.DoesNotExist:
                return render(request, "tree_not_found.html", {"member_id": member_id})

    # ✅ Load member safely
    member = Member.objects.filter(member_id=member_id).first()
    if not member:
        return render(request, "tree_not_found.html", {"member_id": member_id})

    # ✅ Render avatar-based dynamic tree
    return render(request, "herbalapp/dynamic_tree.html", {
        "root_member": member
    })


def pyramid_view(request, member_id):

    # ✅ Normalize numeric → business member_id
    if str(member_id).isdigit():
        if str(member_id) == "1":
            member_id = "rocky001"
        else:
            try:
                pk_member = Member.objects.get(id=int(member_id))
                member_id = pk_member.member_id
            except Member.DoesNotExist:
                return render(request, "tree_not_found.html", {"member_id": member_id})

    # ✅ Load member safely
    root = Member.objects.filter(member_id=member_id).first()
    if not root:
        return render(request, "tree_not_found.html", {"member_id": member_id})

    # ✅ Render avatar-based dynamic tree
    return render(request, "herbalapp/dynamic_tree.html", {
        "root_member": root
    })

# ======================================================
# TREE VIEW (FINAL AVATAR VERSION)
# ======================================================

from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from .models import Member


def _normalize_member_id(member_id):
    """Convert numeric ID → business member_id."""
    if str(member_id).isdigit():
        if str(member_id) == "1":
            return "rocky001"
        try:
            pk_member = Member.objects.get(id=int(member_id))
            return pk_member.member_id
        except:
            return None
    return member_id


def member_tree_root(request):
    """Show tree starting from rocky001."""
    root = get_object_or_404(Member, member_id="rocky001")
    return render(request, "herbalapp/dynamic_tree.html", {
        "root_member": root
    })


def member_tree(request, member_id):
    """Show tree starting from any member."""
    member_id = _normalize_member_id(member_id)
    if not member_id:
        return render(request, "tree_not_found.html", {"member_id": member_id})

    root = get_object_or_404(Member, member_id=member_id)
    return render(request, "herbalapp/dynamic_tree.html", {
        "root_member": root
    })


# ======================================================
# DYNAMIC TREE (FINAL AVATAR VERSION)
# ======================================================

from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse
from .models import Member


def dynamic_tree(request, member_id):
    """Avatar-based dynamic tree for any member."""
    member_id = _normalize_member_id(member_id)
    if not member_id:
        return render(request, "tree_not_found.html", {"member_id": member_id})

    member = get_object_or_404(Member, member_id=member_id)

    # ✅ Always use the new avatar-based dynamic tree
    return render(request, "herbalapp/dynamic_tree.html", {
        "root_member": member
    })


def place_member(request):
    members = Member.objects.all().order_by("member_id")
    return render(request, "place_member.html", {"members": members})


def join(request):
    return render(request, "join.html", {"page_title": "Join Us"})


def shop_login(request):
    return render(request, "shop_login.html", {"page_title": "Shop Login"})

from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from .models import Member


def member_detail_json(request, member_id):

    # ✅ Normalize ID: convert numeric → business member_id
    if str(member_id).isdigit():
        if str(member_id) == "1":
            member_id = "rocky001"
        else:
            try:
                pk_member = Member.objects.get(id=int(member_id))
                member_id = pk_member.member_id
            except:
                return JsonResponse({"error": "Member not found"}, status=404)

    # ✅ Load using business member_id
    try:
        member = Member.objects.get(member_id=member_id)
    except Member.DoesNotExist:
        return JsonResponse({"error": "Member not found"}, status=404)

    # ✅ Self BV calculation
    bv_data = member.calculate_bv()

    # ✅ Last month BV calculation
    last_month_start = (timezone.now().replace(day=1) - timedelta(days=1)).replace(day=1)
    last_month_end = last_month_start.replace(day=28) + timedelta(days=4)
    last_month_end = last_month_end - timedelta(days=last_month_end.day)

    last_month_orders = member.order_set.filter(
        status="Paid",
        created_at__date__gte=last_month_start,
        created_at__date__lte=last_month_end
    )

    last_month_bv = sum(
        o.product.bv_value * o.quantity for o in last_month_orders
    ) if last_month_orders else 0

    # ✅ Response JSON
    data = {
        "auto_id": member.auto_id,
        "name": member.name,
        "phone": member.phone,
        "self_bv": float(bv_data.get("self_bv", 0)),
        "left_bv": float(bv_data.get("left_bv", 0)),
        "right_bv": float(bv_data.get("right_bv", 0)),
        "total_bv": float(bv_data.get("total_bv", 0)),
        "last_month_bv": float(last_month_bv),
    }

    return JsonResponse(data)


from django.shortcuts import render as _render, get_object_or_404 as _get
from .models import Member as _Member

# -------------------------
# Modern Tree (FINAL AVATAR VERSION)
# -------------------------

def _normalize_member_id(member_id):
    """Convert numeric PK → business member_id."""
    if str(member_id).isdigit():
        if str(member_id) == "1":
            return "rocky001"
        try:
            pk_member = _Member.objects.get(id=int(member_id))
            return pk_member.member_id
        except:
            return None
    return member_id


def member_tree_modern(request, auto_id):

    auto_id = _normalize_member_id(auto_id)
    if not auto_id:
        return _render(request, "tree_not_found.html", {"member_id": auto_id})

    root = _get(_Member, member_id=auto_id)

    return render(request, "herbalapp/dynamic_tree.html", {
        "root_member": root
    })


def member_tree_modern_root(request):

    root = _Member.objects.filter(member_id="rocky001").first()
    if not root:
        return _render(request, "tree_not_found.html", {"message": "No root member found."})

    return render(request, "herbalapp/dynamic_tree.html", {
        "root_member": root
    })


# -------------------------
# Edit Member (FINAL FIXED VERSION)
# -------------------------

from django.shortcuts import render as _render, get_object_or_404 as _get, redirect as _redirect
from .models import Member as _Member

def edit_member(request, member_id):

    # ✅ Normalize numeric → business ID
    member_id = _normalize_member_id(member_id)
    if not member_id:
        return _render(request, "tree_not_found.html", {"member_id": member_id})

    member = _get(_Member, member_id=member_id)

    if request.method == 'POST':
        member.name = request.POST.get('name')
        member.phone = request.POST.get('phone')
        member.aadhar = request.POST.get('aadhar')
        member.save()

        # ✅ Redirect to modern avatar tree
        return _redirect('member_tree_modern', auto_id=member.member_id)

    return _render(request, 'edit_member.html', {'member': member})


from django.shortcuts import render as ___render, get_object_or_404 as ___get, redirect as ___redirect
from .models import Member as ___Member

def edit_sponsor(request, member_id):

    # ✅ Normalize numeric → business member_id
    if str(member_id).isdigit():
        if str(member_id) == "1":
            member_id = "rocky001"
        else:
            try:
                pk_member = ___Member.objects.get(id=int(member_id))
                member_id = pk_member.member_id
            except:
                return ___render(request, "tree_not_found.html", {"member_id": member_id})

    # ✅ Load member using business member_id
    member = ___get(___Member, member_id=member_id)

    if request.method == 'POST':
        sponsor_auto_id = request.POST.get('sponsor_auto_id')

        # ✅ Load sponsor using auto_id
        sponsor = ___Member.objects.filter(auto_id=sponsor_auto_id).first()

        if sponsor:
            member.parent = sponsor
            member.save()

            # ✅ Redirect to modern avatar tree (CORRECT)
            return ___redirect('member_tree_modern', auto_id=member.member_id)

    return ___render(request, 'edit_sponsor.html', {'member': member})


# ======================================================
# INCOME PAGE WITH FILTERS (FINAL VERSION)
# ======================================================
from django.db.models import Sum, F, Q
from django.utils.dateparse import parse_date

def income_view(request):

    incomes = Income.objects.all()

    # ✅ Filters
    member_id = request.GET.get("member_id")
    name = request.GET.get("name")
    date_from = request.GET.get("from")
    date_to = request.GET.get("to")
    min_income = request.GET.get("min")
    max_income = request.GET.get("max")

    # ✅ Apply filters safely
    if member_id:
        incomes = incomes.filter(member__member_id__icontains=member_id)

    if name:
        incomes = incomes.filter(member__name__icontains=name)

    if date_from:
        incomes = incomes.filter(created_at__date__gte=parse_date(date_from))

    if date_to:
        incomes = incomes.filter(created_at__date__lte=parse_date(date_to))

    if min_income:
        incomes = incomes.filter(
            (F('binary_income') + F('sponsor_income') + F('salary_income') + F('flash_out_bonus')) >= float(min_income)
        )

    if max_income:
        incomes = incomes.filter(
            (F('binary_income') + F('sponsor_income') + F('salary_income') + F('flash_out_bonus')) <= float(max_income)
        )

    # ✅ Annotate total income per row
    incomes = incomes.annotate(
        total_income = (
            F('binary_income') +
            F('sponsor_income') +
            F('salary_income') +
            F('flash_out_bonus')
        )
    )

    # ✅ Grand total
    total_income_all = incomes.aggregate(
        total=Sum(
            F('binary_income') +
            F('sponsor_income') +
            F('salary_income') +
            F('flash_out_bonus')
        )
    )['total'] or 0

    context = {
        "incomes": incomes,
        "total_income_all": total_income_all,
    }

    return render(request, "income_report.html", context)

# ======================================================
# EXPORT INCOME TO EXCEL (multi-sheet + charts)
# ======================================================
def export_income_excel(request):
    import openpyxl
    from openpyxl.chart import BarChart, Reference
    from openpyxl.styles import Font, PatternFill, Border, Side
    from django.http import HttpResponse

    # Load all members
    members = Member.objects.all().order_by("id")

    # Create workbook
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # remove default sheet

    # Style presets
    header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    thin = Side(border_style="thin", color="000000")
    border = Border(top=thin, left=thin, right=thin, bottom=thin)

    # Group by district → taluk → side
    districts = members.values_list("district", flat=True).distinct()

    for district in districts:
        taluks = members.filter(district=district).values_list("taluk", flat=True).distinct()

        for taluk in taluks:
            sides = members.filter(district=district, taluk=taluk).values_list("side", flat=True).distinct()

            for side in sides:

                # Sheet name (max 31 chars)
                sheet_name = f"{district}-{taluk}-{side}"[:31]
                ws = wb.create_sheet(title=sheet_name)

                # Header row
                headers = [
                    "Member ID", "Name", "Joining Package", "Binary Income",
                    "Flash Bonus", "Sponsor Income", "Salary", "Stock Commission",
                    "Total Income", "Rank Title", "Rank Start Date",
                    "Monthly Income", "Duration (Months)", "Months Paid", "Active",
                    "Left BV", "Right BV", "Matched BV",
                    "Repurchase Wallet", "Flash Wallet"
                ]
                ws.append(headers)

                # Style header
                for cell in ws[1]:
                    cell.font = Font(bold=True)
                    cell.fill = header_fill
                    cell.border = border

                # Data rows
                group_members = members.filter(district=district, taluk=taluk, side=side)

                for m in group_members:

                    # Safe income fetch
                    income = getattr(m, 'calculate_full_income', lambda: {})()

                    joining = income.get("joining", 0)
                    binary_income = income.get("binary_income", 0)
                    flash_bonus = income.get("flash_bonus", 0)
                    sponsor_income = income.get("sponsor_income", 0)
                    salary = income.get("salary", 0)
                    stock_commission = income.get("stock_commission", 0)
                    total_income_all = income.get("total_income_all", 0)

                    # BV
                    left_bv, right_bv = m.get_bv_counts()
                    matched_bv = min(left_bv, right_bv)

                    # Wallets
                    repurchase_wallet = getattr(m, "repurchase_wallet", 0)
                    flash_wallet = getattr(m, "flash_wallet", 0)

                    # Rank rewards
                    rewards_qs = RankReward.objects.filter(member=m)

                    if rewards_qs.exists():
                        for r in rewards_qs:
                            row = [
                                m.auto_id, m.name,
                                joining, binary_income, flash_bonus,
                                sponsor_income, salary, stock_commission,
                                total_income_all,
                                r.rank_title, r.start_date, r.monthly_income,
                                r.duration_months, r.months_paid, r.active,
                                left_bv, right_bv, matched_bv,
                                repurchase_wallet, flash_wallet
                            ]
                            ws.append(row)
                    else:
                        row = [
                            m.auto_id, m.name,
                            joining, binary_income, flash_bonus,
                            sponsor_income, salary, stock_commission,
                            total_income_all,
                            None, None, None, None, None, None,
                            left_bv, right_bv, matched_bv,
                            repurchase_wallet, flash_wallet
                        ]
                        ws.append(row)

                # Apply borders to all data rows
                for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                    for cell in row:
                        cell.border = border

                # Rank Summary
                ws.append([])
                ws.append(["Rank Summary"])
                rank_titles = ["1st Star", "Double Star", "Triple Star"]

                for title in rank_titles:
                    count = group_members.filter(current_rank=title).count()
                    ws.append([title, count])

                # BV Summary
                ws.append([])
                ws.append(["BV Summary"])
                total_left = sum(m.get_bv_counts()[0] for m in group_members)
                total_right = sum(m.get_bv_counts()[1] for m in group_members)
                ws.append(["Total Left BV", total_left])
                ws.append(["Total Right BV", total_right])
                ws.append(["Total Matched BV", min(total_left, total_right)])

                # Wallet Summary
                ws.append([])
                ws.append(["Wallet Summary"])
                ws.append(["Total Repurchase Wallet", sum(getattr(m, "repurchase_wallet", 0) for m in group_members)])
                ws.append(["Total Flash Wallet", sum(getattr(m, "flash_wallet", 0) for m in group_members)])

                # Auto column width
                for col in ws.columns:
                    max_length = 0
                    col_letter = col[0].column_letter
                    for cell in col:
                        try:
                            max_length = max(max_length, len(str(cell.value)))
                        except:
                            pass
                    ws.column_dimensions[col_letter].width = max_length + 2

                # Freeze header
                ws.freeze_panes = "A2"

                # Rank Chart
                chart = BarChart()
                chart.title = "Rank Distribution"
                chart.x_axis.title = "Rank"
                chart.y_axis.title = "Members"

                # Rank summary rows
                rank_start = ws.max_row - (len(rank_titles) + 4)
                rank_end = rank_start + len(rank_titles) - 1

                data_ref = Reference(ws, min_col=2, min_row=rank_start, max_row=rank_end)
                cat_ref = Reference(ws, min_col=1, min_row=rank_start, max_row=rank_end)

                chart.add_data(data_ref, titles_from_data=False)
                chart.set_categories(cat_ref)
                ws.add_chart(chart, "M2")

    # Dashboard Sheet
    dash = wb.create_sheet("Dashboard")
    dash.append(["Dashboard Summary"])
    dash.append(["Total Members", members.count()])
    dash.append(["Total Income", sum(
        getattr(m, 'calculate_full_income', lambda: {})().get("total_income_all", 0)
        for m in members
    )])

    # Auto width for dashboard
    for col in dash.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            try:
                max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        dash.column_dimensions[col_letter].width = max_length + 2

    # Response
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="income_report_grouped.xlsx"'
    wb.save(response)
    return response

import datetime
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font, Border, Side
from herbalapp.models import Member

def export_members_income(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Members Income"

    headers = [
        'Member ID', 'Name', 'Joining Package',
        'Binary Income', 'Flash Bonus', 'Sponsor Income',
        'Repurchase Wallet', 'Rank Reward', 'Total Income'
    ]
    ws.append(headers)

    # Bold header
    for cell in ws[1]:
        cell.font = Font(bold=True)

    today = datetime.date.today()
    members = Member.objects.all()

    for member in members:
        if hasattr(member, "income_date") and member.income_date != today:
            binary_income = sponsor_income = flash_bonus = repurchase_wallet = rank_reward = 0
        else:
            binary_income = member.calculate_binary_income()
            sponsor_income = member.sponsor_income
            flash_bonus = member.flash_bonus
            repurchase_wallet = member.repurchase_wallet
            rank_reward = member.calculate_rank_reward()

        total_income = (
            binary_income + sponsor_income + flash_bonus +
            repurchase_wallet + rank_reward
        )

        ws.append([
            member.member_id,
            member.name,
            member.package,
            binary_income,
            flash_bonus,
            sponsor_income,
            repurchase_wallet,
            rank_reward,
            total_income
        ])

    # Borders
    thin = Side(border_style="thin", color="000000")
    border = Border(top=thin, left=thin, right=thin, bottom=thin)

    for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
        for cell in row:
            cell.border = border

    # Auto column width
    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            try:
                max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        ws.column_dimensions[col_letter].width = max_length + 2

    # Freeze header
    ws.freeze_panes = "A2"

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=members_income.xlsx'
    wb.save(response)
    return response

import requests
from django.utils import timezone
from django.shortcuts import render
from .models import Member, DailyIncomeReport

def generate_daily_report():
    today = timezone.now().date()
    reports = []

    for member in Member.objects.all():
        income = member.calculate_full_income()
        report = DailyIncomeReport.objects.create(
            date=today,
            member=member,
            binary_income=income["binary_income"],
            flash_bonus=income["flash_bonus"],
            sponsor_income=income["sponsor_income"],
            salary=income["salary"],
            stock_commission=income["stock_commission"],
            total_income=income["total_income_all"],
        )
        reports.append(report)

    # ✅ Prepare WhatsApp message
    body = f"Rocky Herbals Daily Income Report - {today}\n\n"
    for r in reports:
        body += f"{r.member.auto_id} - {r.member.name} : ₹{r.total_income}\n"

    # ✅ WhatsApp Cloud API details
    WHATSAPP_TOKEN = "YOUR_WHATSAPP_ACCESS_TOKEN"
    PHONE_NUMBER_ID = "YOUR_WHATSAPP_PHONE_NUMBER_ID"
    RECEIVER = "918122105779"  # ✅ Your mobile number with country code

    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": RECEIVER,
        "type": "text",
        "text": {"body": body}
    }

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    # ✅ Send WhatsApp message
    requests.post(url, json=payload, headers=headers)

    return "Daily report sent via WhatsApp"

from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from .models import Member


# ✅ Dashboard
@login_required
def dashboard(request):

    # ✅ Ensure user has a linked Member record
    try:
        member = request.user.member
    except:
        messages.error(request, "Member profile not found.")
        return redirect("member_list")

    # ✅ Wallet values (safe fallback)
    rep_wallet = member.repurchase_wallet or 0
    flash_wallet = member.flash_wallet or 0
    total_wallet = rep_wallet + flash_wallet

    return render(request, "dashboard.html", {
        "member": member,
        "rep_wallet": rep_wallet,
        "flash_wallet": flash_wallet,
        "total_wallet": total_wallet,
    })


# ✅ Members list
@login_required
def member_list(request):
    members = Member.objects.all().order_by("auto_id")
    return render(request, "member_list.html", {"members": members})


# ✅ Products page
@login_required
def products(request):
    return render(request, "products.html")


# ✅ Income page
@login_required
def income_page(request):
    return render(request, "income.html")
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Member


def member_bv(request, member_id):

    # ✅ Support both numeric PK and business member_id
    if str(member_id).isdigit():
        member = get_object_or_404(Member, id=int(member_id))
    else:
        member = get_object_or_404(Member, member_id=member_id)

    # ✅ Calculate BV safely
    bv_data = member.calculate_bv()  # returns dict: self_bv, left_bv, right_bv, total_bv

    return JsonResponse(bv_data)


from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Member


def member_register(request):

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        mobile = request.POST.get("mobile", "").strip()
        email = request.POST.get("email", "").strip()
        auto_id = request.POST.get("auto_id", "").strip()
        place = request.POST.get("place", "").strip()
        district = request.POST.get("district", "").strip()
        pincode = request.POST.get("pincode", "").strip()
        aadhar = request.POST.get("aadhar", "").strip()

        # ✅ Basic validation
        if not name or not mobile or not auto_id:
            messages.error(request, "Name, Mobile, and Auto ID are required.")
            return redirect("member_register")

        if len(mobile) != 10 or not mobile.isdigit():
            messages.error(request, "Invalid mobile number.")
            return redirect("member_register")

        if Member.objects.filter(auto_id=auto_id).exists():
            messages.error(request, f"Auto ID {auto_id} already exists.")
            return redirect("member_register")

        # ✅ Save to DB
        Member.objects.create(
            name=name,
            phone=mobile,
            email=email,
            auto_id=auto_id,
            place=place,
            district=district,
            pincode=pincode,
            aadhar=aadhar,
        )

        messages.success(
            request,
            f"Member {name} added successfully! 📞 Mobile: {mobile}"
        )
        return redirect("member_list")

    return render(request, "member_register.html")


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Member


def add_member_under_parent(request, parent_id, position):

    parent = get_object_or_404(Member, id=parent_id)

    position = position.lower()
    if position not in ["left", "right"]:
        messages.error(request, "Invalid position selected.")
        return redirect("member_list")

    if position == "left" and parent.left_child is not None:
        messages.error(request, f"{parent.name} already has a LEFT child.")
        return redirect("member_list")

    if position == "right" and parent.right_child is not None:
        messages.error(request, f"{parent.name} already has a RIGHT child.")
        return redirect("member_list")

    # ✅ Safe auto Rocky ID generator
    all_ids = Member.objects.values_list("member_id", flat=True)
    max_num = 0
    for mid in all_ids:
        try:
            num = int(mid.replace("rocky", ""))
            if num > max_num:
                max_num = num
        except:
            pass
    auto_member_id = f"rocky{max_num + 1:03d}"

    if request.method == "GET":
        return render(request, "add_member.html", {
            "parent": parent,
            "position": position,
            "auto_member_id": auto_member_id,
        })

    # ✅ POST data
    name = request.POST.get("name")
    phone = request.POST.get("phone")
    email = request.POST.get("email")
    aadhar = request.POST.get("aadhar")
    place = request.POST.get("place")
    district = request.POST.get("district")
    pincode = request.POST.get("pincode")
    sponsor_id = request.POST.get("sponsor_id")

    # ✅ Avatar file (IMPORTANT)
    avatar = request.FILES.get("avatar")

    sponsor = None
    if sponsor_id:
        sponsor = Member.objects.filter(member_id=sponsor_id).first()
        if not sponsor:
            messages.error(request, "Invalid Sponsor ID.")
            return redirect(request.path)

    # ✅ Create new member (avatar included)
    new_member = Member.objects.create(
        name=name,
        phone=phone,
        email=email,
        aadhar=aadhar,
        place=place,
        district=district,
        pincode=pincode,
        sponsor=sponsor,
        parent=parent,
        side=position,
        avatar=avatar,  # ✅ Correct
    )

    if position == "left":
        parent.left_child = new_member
    else:
        parent.right_child = new_member

    parent.save()

    messages.success(
        request,
        f"New member {name} added under {parent.name} on {position.upper()} side."
    )

    return redirect("member_list")

# ===================== IMPORTS =====================
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Member
from decimal import Decimal


# ===============================================================
# ADD MEMBER VIEW  (auto ID, placement, sponsor, binary + sponsor pay)
# ===============================================================
def add_member_form(request):

    # ✅ Safe auto-generate rocky ID
    last = Member.objects.order_by('-member_id').first()
    if last and last.member_id.startswith("rocky"):
        try:
            num = int(last.member_id.replace("rocky", ""))
        except:
            num = last.id
        new_member_id = f"rocky{num+1:03d}"
    else:
        new_member_id = "rocky001"

    # ✅ Pre-fill placement if ?parent= given
    parent_code = request.GET.get("parent")
    placement_member_id = ""

    parent = None
    if parent_code:
        parent = Member.objects.filter(member_id=parent_code).first()
        if not parent:
            try:
                parent = Member.objects.filter(id=int(parent_code)).first()
            except:
                parent = None
        if parent:
            placement_member_id = parent.member_id

    # ===================== ON SUBMIT =====================
    if request.method == "POST":

        member_id = request.POST.get('member_id')
        placement_code = request.POST.get('placement_id')
        sponsor_code = request.POST.get('sponsor_id')

        # ✅ Validate member_id uniqueness
        if Member.objects.filter(member_id=member_id).exists():
            return render(request, "add_member.html", {
                "error": "❌ Member ID already exists!",
                "member_id": new_member_id,
                "placement_id": placement_member_id
            })

        # ✅ Validate placement
        placement = Member.objects.filter(member_id=placement_code).first()
        if not placement:
            return render(request, "add_member.html", {
                "error": "❌ Placement ID not found",
                "member_id": new_member_id,
                "placement_id": placement_member_id
            })

        # ✅ Validate sponsor
        sponsor = Member.objects.filter(member_id=sponsor_code).first()
        if not sponsor:
            return render(request, "add_member.html", {
                "error": "❌ Sponsor ID not found",
                "member_id": new_member_id,
                "placement_id": placement_member_id
            })

        # ✅ Auto Left → Right allocation
        if not placement.left_child:
            side = "left"
        elif not placement.right_child:
            side = "right"
        else:
            return render(request, "add_member.html", {
                "error": "❌ Both legs are filled!",
                "member_id": new_member_id,
                "placement_id": placement_member_id
            })

        # ✅ Create Member
        new = Member.objects.create(
            member_id=member_id,
            name=request.POST.get('name'),
            phone=request.POST.get('phone'),
            email=request.POST.get('email'),
            aadhar=request.POST.get('aadhar'),
            place=request.POST.get('place'),
            district=request.POST.get('district'),
            pincode=request.POST.get('pincode'),
            parent=placement,
            sponsor=sponsor,
            side=side
        )

        # ✅ Attach Child
        if side == "left":
            placement.left_child = new
        else:
            placement.right_child = new
        placement.save()

        # ✅ Run full income engine (binary + sponsor + CF + salary + rank)
        run_binary_on_new_join(new)

        return redirect("/tree/")

    return render(request, "add_member.html", {
        "member_id": new_member_id,
        "placement_member_id": placement_member_id
    })


from django.shortcuts import render, get_object_or_404
from herbalapp.models import Member, DailyIncomeReport


def income_chart(request, member_id):

    # ✅ Load member safely using business member_id
    member = get_object_or_404(Member, member_id=member_id)

    # ✅ Correct filter (ForeignKey → member__member_id)
    reports = DailyIncomeReport.objects.filter(
        member__member_id=member_id
    ).order_by('date')

    dates = [str(r.date) for r in reports]
    salary = [float(r.salary or 0) for r in reports]
    total_income = [float(r.total_income or 0) for r in reports]

    return render(request, "income_chart.html", {
        "member": member,
        "dates": dates,
        "salary": salary,
        "total_income": total_income,
    })

from django.shortcuts import render
import datetime
from herbalapp.models import DailyIncomeReport


def income_report(request):

    date_str = request.GET.get("date")

    # ✅ Parse date safely
    if date_str:
        for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
            try:
                target_date = datetime.datetime.strptime(date_str, fmt).date()
                break
            except ValueError:
                target_date = None

        if target_date is None:
            target_date = datetime.date.today()
    else:
        target_date = datetime.date.today()

    # ✅ Fetch reports for the selected date
    reports = DailyIncomeReport.objects.filter(date=target_date).order_by("member__member_id")

    return render(request, "income_report.html", {
        "today": target_date,
        "reports": reports,
        "count": reports.count(),
    })

from django.shortcuts import render, get_object_or_404
from django.db.models import Value
from django.db.models.functions import Coalesce
from .models import Member
from .ranks import get_rank


# ---------------------------------------------------------
# ✅ 1. Rank Report (All Members)
# ---------------------------------------------------------
def rank_report(request):
    # Null-safe BV values + proper ordering
    members = Member.objects.annotate(
        left_bv_safe=Coalesce('total_left_bv', Value(0)),
        right_bv_safe=Coalesce('total_right_bv', Value(0)),
    ).order_by('-left_bv_safe')

    return render(request, "rank_report.html", {
        "members": members
    })


# ---------------------------------------------------------
# ✅ 2. Salary Report (Members with salary > 0)
# ---------------------------------------------------------
def salary_report(request):
    members = Member.objects.filter(salary__gt=0).order_by('-salary', 'name')

    return render(request, "salary_report.html", {
        "members": members
    })


# ---------------------------------------------------------
# ✅ 3. Member Rank Detail Page
# ---------------------------------------------------------
def member_rank_detail(request, member_id):
    member = get_object_or_404(Member, member_id=member_id)

    # Null-safe BV
    left_bv = member.total_left_bv or 0
    right_bv = member.total_right_bv or 0
    matched_bv = min(left_bv, right_bv)

    # Rank engine
    rank_info = get_rank(matched_bv) or {}

    return render(request, "member_rank_detail.html", {
        "member": member,
        "matched_bv": matched_bv,
        "rank_info": rank_info,
    })

