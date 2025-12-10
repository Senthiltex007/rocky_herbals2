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

# Charts
from openpyxl.chart import BarChart, LineChart, Reference

# Models and forms
from .models import (
    Member, Product, Payment, Income, CommissionRecord,
    BonusRecord, Order, IncomeRecord
)
# Optional RankReward if present in your app
try:
    from .models import RankReward
except Exception:
    RankReward = None

from .forms import MemberForm, ProductForm

# services/additional modules if any
try:
    from .services import add_billing_commission
except Exception:
    add_billing_commission = None


# ======================================================
# CHART HELPERS (no responses or external calls here)
# ======================================================
def add_bv_wallet_chart(ws, start_row):
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

    # Place chart in sheet
    ws.add_chart(chart, "P5")


def add_rank_progression_chart(ws, start_row, end_row):
    # Create line chart
    chart = LineChart()
    chart.title = "Monthly Rank Progression"
    chart.style = 13
    chart.y_axis.title = "Members"
    chart.x_axis.title = "Month"

    # Data range: rank counts per month
    # Expected rows: [MonthLabel, Count]
    data = Reference(ws, min_col=2, min_row=start_row, max_row=end_row)
    cats = Reference(ws, min_col=1, min_row=start_row, max_row=end_row)

    chart.add_data(data, titles_from_data=False)
    chart.set_categories(cats)

    # Place chart in sheet
    ws.add_chart(chart, "P20")


def add_combo_chart(ws, bv_start_row, wallet_start_row, rank_start_row, rank_end_row):
    # Bar chart for BV + Wallet
    bar = BarChart()
    bar.type = "col"
    bar.grouping = "stacked"
    bar.title = "BV + Wallet Overview"
    bar.y_axis.title = "Values"
    bar.x_axis.title = "Category"

    # BV Summary section starts at bv_start_row
    # Wallet Summary section starts at wallet_start_row
    # We'll combine both BV and Wallet labels/values vertically for the chart
    bv_wallet_data = Reference(ws, min_col=2, min_row=bv_start_row, max_row=wallet_start_row + 1)
    bv_wallet_cats = Reference(ws, min_col=1, min_row=bv_start_row, max_row=wallet_start_row + 1)
    bar.add_data(bv_wallet_data, titles_from_data=False)
    bar.set_categories(bv_wallet_cats)

    # Line chart for Rank Progression
    line = LineChart()
    line.title = "Rank Progression Trend"
    line.style = 13
    line.y_axis.title = "Members"
    line.x_axis.title = "Month"

    rank_data = Reference(ws, min_col=2, min_row=rank_start_row, max_row=rank_end_row)
    rank_cats = Reference(ws, min_col=1, min_row=rank_start_row, max_row=rank_end_row)
    line.add_data(rank_data, titles_from_data=False)
    line.set_categories(rank_cats)

    # Combine charts
    bar += line

    # Place chart in sheet
    ws.add_chart(bar, "P30")


def add_dashboard_sheet(wb, members):
    # Create dashboard sheet
    ws = wb.create_sheet(title="Dashboard")

    # Overall Totals
    ws.append(["Dashboard Summary"])
    ws.append(["Total Members", members.count()])

    total_left_bv = sum(m.get_bv_counts()[0] for m in members)
    total_right_bv = sum(m.get_bv_counts()[1] for m in members)
    ws.append(["Total Left BV", total_left_bv])
    ws.append(["Total Right BV", total_right_bv])
    ws.append(["Total Matched BV", min(total_left_bv, total_right_bv)])

    total_repurchase = sum(getattr(m, "repurchase_wallet", 0) for m in members)
    total_flash = sum(getattr(m, "flash_wallet", 0) for m in members)
    ws.append(["Total Repurchase Wallet", total_repurchase])
    ws.append(["Total Flash Wallet", total_flash])

    # Rank Summary
    ws.append([])
    ws.append(["Rank Summary"])
    rank_titles = ["1st Star", "Double Star", "Triple Star"]
    for title in rank_titles:
        count = members.filter(current_rank=title).count()
        ws.append([title, count])

    # Chart: Rank Distribution (uses the last 3 rows just written)
    chart1 = BarChart()
    chart1.title = "Rank Distribution"
    chart1.x_axis.title = "Rank"
    chart1.y_axis.title = "Members"
    # Identify start row for these 3 entries
    rank_end = ws.max_row
    rank_start = rank_end - 2
    data = Reference(ws, min_col=2, min_row=rank_start, max_row=rank_end)
    cats = Reference(ws, min_col=1, min_row=rank_start, max_row=rank_end)
    chart1.add_data(data, titles_from_data=False)
    chart1.set_categories(cats)
    ws.add_chart(chart1, "E5")

    # Chart: BV vs Wallet Comparison
    chart2 = BarChart()
    chart2.type = "col"
    chart2.grouping = "stacked"
    chart2.title = "BV vs Wallet Comparison"
    # BV/Wallet rows are from line 2 to 7 (after "Dashboard Summary")
    data2 = Reference(ws, min_col=2, min_row=2, max_row=7)
    cats2 = Reference(ws, min_col=1, min_row=2, max_row=7)
    chart2.add_data(data2, titles_from_data=False)
    chart2.set_categories(cats2)
    ws.add_chart(chart2, "E20")

    # Optional: Rank Progression example (if you later add a monthly table)
    # Placeholders, adjust rows to your actual progression table
    chart3 = LineChart()
    chart3.title = "Rank Progression Trend"
    chart3.y_axis.title = "Members"
    chart3.x_axis.title = "Month"
    # Example rows for progression table (adjust as needed)
    # data3 = Reference(ws, min_col=2, min_row=15, max_row=20)
    # cats3 = Reference(ws, min_col=1, min_row=15, max_row=20)
    # chart3.add_data(data3, titles_from_data=False)
    # chart3.set_categories(cats3)
    # ws.add_chart(chart3, "M5")


# -------------------------
# HOME / STATIC PAGES
# -------------------------
def home(request):
    return render(request, "home.html")


def about(request):
    return render(request, "about.html", {
        "page_title": "About Us",
        "company": "Rocky Herbals",
        "description": "We are a herbal products company."
    })


def contact(request):
    return render(request, "contact.html", {
        "page_title": "Contact Us",
        "email": "info@rockyherbals.com",
        "phone": "8122105779",
        "address": "Nambiyur, Tamil Nadu, India"
    })


# -------------------------
# AUTH / MEMBER LOGIN / REGISTER
# -------------------------
def member_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("member_list")
        messages.error(request, "Invalid username or password")
    return render(request, "member_login.html")

# -------------------------
# ADMIN / DASHBOARD
# -------------------------
def admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user and user.is_staff:
            login(request, user)
            return redirect("admin_dashboard")
        messages.error(request, "Invalid admin credentials")
    return render(request, "admin_login.html")


@login_required
def admin_dashboard(request):
    total_members = Member.objects.count()
    paid = Payment.objects.filter(status="Paid").count()
    unpaid = total_members - paid
    income = Payment.objects.filter(status="Paid").aggregate(total=Sum("amount"))["total"] or 0

    return render(request, "admin_dashboard.html", {
        "company_name": "Rocky Herbals",
        "total_members": total_members,
        "paid": paid,
        "unpaid": unpaid,
        "income": income,
        "products_count": Product.objects.count(),
        "income_count": Income.objects.count(),
    })


# -------------------------
# MEMBER CRUD / LIST
# -------------------------
def member_list(request):
    members = Member.objects.all().order_by("id")
    return render(request, "member_list.html", {"members": members})

@login_required
def delete_member(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    parent = member.parent
    if parent:
        if parent.left_child_id == member.id:
            parent.left_child = None
        elif parent.right_child_id == member.id:
            parent.right_child = None
        parent.save()
    member.delete()
    messages.success(request, f"{member.name} deleted successfully!")
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


# -------------------------
# PRODUCT / CART / CHECKOUT (placeholders)
# -------------------------
def product_list(request):
    products = Product.objects.all().order_by("-id")
    return render(request, "products.html", {"products": products})


def add_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Product added!")
            return redirect("products")
    else:
        form = ProductForm()
    return render(request, "add_product.html", {"form": form})


def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated!")
            return redirect("products")
    else:
        form = ProductForm(instance=product)

    return render(request, "add_product.html", {"form": form, "edit": True})


def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    messages.success(request, "Product deleted successfully!")
    return redirect("products")


def cart_view(request):
    return render(request, "cart.html")


def add_to_cart(request, product_id):
    return redirect('cart')


def remove_from_cart(request, product_id):
    return redirect('cart')


def checkout(request):
    return HttpResponse("Checkout Page - To be implemented")


# -------------------------
# COMMISSIONS / INCOME helpers
# -------------------------
def credit_commission(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    messages.success(request, f"Commission credited for {member.name}")
    return redirect("member_list")
from .models import Payment, Commission, Member
from django.shortcuts import redirect, get_object_or_404

# =====================================================
# PAYMENT APPROVE & STOCK COMMISSION GENERATOR
# =====================================================
def approve_payment(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    member = payment.member

    # Check commission level
    if member.level == "district":
        percentage = 7
    elif member.level == "taluk":
        percentage = 5
    elif member.level == "pincode":
        percentage = 3
    else:
        percentage = 0   # No commission

    commission_amount = payment.amount * percentage / 100

    # Store commission only if level exists
    if percentage > 0:
        Commission.objects.create(
            member=member,
            payment=payment,
            commission_type=member.level,
            percentage=percentage,
            commission_amount=commission_amount
        )

    # Mark payment approved
    payment.status = "approved"
    payment.save()

    return redirect('payments_list')   # Change to your payment list url name



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

    safe_name = (member.name or "").replace("'", "\\'").replace('"', '\\"')
    safe_auto = str(member.member_id)

    node_html = (
        f"<li>"
        f"<div class='member-box' onclick=\"showMemberDetail({{id:'{member.member_id}', name:'{safe_name}', phone:'{(member.phone or '')}'}})\">"
        f"{safe_name} <br><small>ID: {safe_auto}</small>"
        f"</div>"
    )

    node_html += "<ul>"

    if left:
        node_html += build_tree_html(left)
    else:
        add_url = reverse('add_member_form') + f"?parent={member.member_id}&side=left"
        node_html += (
            "<li><div class='member-box text-muted'>➕ Left<br>"
            f"<a href='{add_url}'>Add</a></div></li>"
        )

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
    try:
        # First try business member_id
        member = Member.objects.get(member_id=member_id)
    except Member.DoesNotExist:
        try:
            # Fallback: try numeric PK
            member = Member.objects.get(id=int(member_id))
        except (Member.DoesNotExist, ValueError):
            return render(request, "tree_not_found.html", {"member_id": member_id})

    tree_html = "<ul class='tree-root'>" + build_tree_html(member) + "</ul>"
    bv = member.calculate_bv()
    return render(request, "tree_view.html", {
        "member": member,
        "tree_html": tree_html,
        "self_bv": bv["self_bv"],
        "left_bv": bv["left_bv"],
        "right_bv": bv["right_bv"],
        "total_bv": bv["total_bv"],
    })


def pyramid_view(request, member_id):
    root = get_object_or_404(Member, member_id=member_id)

    def build_pyramid(member):
        if not member:
            return ""
        left, right = _get_children(member)
        safe_name = (member.name or "").replace("'", "\\'").replace('"', '\\"')
        safe_auto = member.member_id
        node_html = "<li>"
        node_html += (
            f"<div class='member-box' "
            f"onclick=\"showMemberDetail({{id:'{member.member_id}', name:'{safe_name}', phone:'{getattr(member, 'phone', '')}'}})\">"
            f"{safe_name} <br><small>ID: {safe_auto}</small>"
            f"</div>"
        )
        node_html += "<ul>"
        if left:
            node_html += build_pyramid(left)
        else:
            add_url_left = reverse('add_member_form') + f"?parent={member.member_id}&side=left"
            node_html += "<li><div class='member-box text-muted'>➕ Left<br><a href='{add_url_left}'>Add</a></div></li>"
        if right:
            node_html += build_pyramid(right)
        else:
            add_url_right = reverse('add_member_form') + f"?parent={member.member_id}&side=right"
            node_html += "<li><div class='member-box text-muted'>➕ Right<br><a href='{add_url_right}'>Add</a></div></li>"
        node_html += "</ul></li>"
        return node_html

    tree_html = "<ul class='tree-root'>" + build_pyramid(root) + "</ul>"
    return render(request, "pyramid.html", {"tree_html": tree_html, "root_member": root})


# -------------------------
# member_tree wrappers
# -------------------------
def member_tree_root(request):
    root = get_object_or_404(Member, member_id="rocky001")
    return render(request, "member_tree_root.html", {"roots": [root]})


def member_tree(request, member_id):
    root = get_object_or_404(Member, member_id=member_id)
    tree_html = "<ul class='tree-root'>" + build_tree_html(root) + "</ul>"
    return render(request, "member_tree.html", {"tree_html": tree_html, "root_member": root})


def dynamic_tree(request, member_id):
    member = get_object_or_404(Member, member_id=member_id)
    if hasattr(member, "get_pyramid_tree"):
        tree_data = member.get_pyramid_tree()
        return render(request, "dynamic_tree.html", {"tree": tree_data, "root_member": member})
    tree_html = "<ul class='tree-root'>" + build_tree_html(member) + "</ul>"
    return render(request, "dynamic_tree.html", {"tree_html": tree_html, "root_member": member})

def place_member(request):
    # Order by business member_id instead of numeric id
    members = Member.objects.all().order_by("member_id")
    return render(request, "place_member.html", {"members": members})

def join(request):
    return render(request, "join.html", {"page_title": "Join Us"})

def shop_login(request):
    return render(request, "shop_login.html", {"page_title": "Shop Login"})

from django.http import JsonResponse
from .models import Member

def member_detail_json(request, member_id):
    try:
        member = Member.objects.get(id=member_id)
        # Self BV calculation
        bv_data = member.calculate_bv()

        # Last month BV (example: simple query from previous month)
        from django.utils import timezone
        from datetime import timedelta
        last_month_start = (timezone.now().replace(day=1) - timedelta(days=1)).replace(day=1)
        last_month_end = last_month_start.replace(day=28) + timedelta(days=4)  # last day of month
        last_month_end = last_month_end - timedelta(days=last_month_end.day)

        # Example: sum orders in last month
        last_month_orders = member.order_set.filter(
            status="Paid",
            created_at__date__gte=last_month_start,
            created_at__date__lte=last_month_end
        )
        last_month_bv = sum([o.product.bv_value * o.quantity for o in last_month_orders]) if last_month_orders else 0

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
    except Member.DoesNotExist:
        return JsonResponse({"error": "Member not found"}, status=404)


from django.shortcuts import render as _render, get_object_or_404 as _get
from .models import Member as _Member

def member_tree_modern(request, auto_id):
    root = _get(_Member, auto_id=auto_id)
    return _render(request, 'tree_modern.html', {'root': root})


def member_tree_modern_root(request):
    root = _Member.objects.filter(parent__isnull=True).order_by("id").first()
    if not root:
        return render(request, "tree_not_found.html", {"message": "No root member found."})
    return render(request, "tree_modern.html", {"root": root})


from django.shortcuts import render as __render, get_object_or_404 as __get, redirect as __redirect
from .models import Member as __Member

def edit_member(request, member_id):
    member = __get(__Member, id=member_id)
    if request.method == 'POST':
        member.name = request.POST.get('name')
        member.phone = request.POST.get('phone')
        member.aadhar = request.POST.get('aadhar')
        member.save()
        # after saving, redirect back to tree view
        return __redirect('tree_view', member_id=member.id)
    return __render(request, 'edit_member.html', {'member': member})


from django.shortcuts import render as ___render, get_object_or_404 as ___get, redirect as ___redirect
from .models import Member as ___Member

def edit_sponsor(request, member_id):
    member = ___get(___Member, id=member_id)
    if request.method == 'POST':
        sponsor_auto_id = request.POST.get('sponsor_auto_id')
        sponsor = ___Member.objects.filter(auto_id=sponsor_auto_id).first()
        if sponsor:
            member.parent = sponsor
            member.save()
            return ___redirect('tree_view', member_id=member.id)
    return ___render(request, 'edit_sponsor.html', {'member': member})


# ======================================================
# INCOME PAGE WITH FILTERS
# ======================================================
from django.db.models import Sum, F

def income_view(request):
    incomes = Income.objects.all()

    incomes = incomes.annotate(
        total_income = F('binary_income') + F('sponsor_income') + F('salary_income') + F('flash_out_bonus')
    )

    context = {
        "incomes": incomes,
        "total_income_all": incomes.aggregate(
            total=Sum(F('binary_income') + F('sponsor_income') + F('salary_income') + F('flash_out_bonus'))
        )['total'] or 0,
    }

    return render(request, "income_report.html", context)

# ======================================================
# EXPORT INCOME TO EXCEL (multi-sheet + charts)
# ======================================================
def export_income_excel(request):
    import openpyxl
    from openpyxl.chart import BarChart, Reference
    from django.http import HttpResponse

    members = Member.objects.all().order_by("id")

    # Create workbook
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # remove default sheet

    # Distinct groups
    districts = members.values_list("district", flat=True).distinct()
    for district in districts:
        taluks = members.filter(district=district).values_list("taluk", flat=True).distinct()
        for taluk in taluks:
            sides = members.filter(district=district, taluk=taluk).values_list("side", flat=True).distinct()
            for side in sides:
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

                    # Rewards, BV, Wallet
                    rewards_qs = RankReward.objects.filter(member=m) if RankReward else None
                    left_bv, right_bv = m.get_bv_counts()
                    matched_bv = min(left_bv, right_bv)

                    repurchase_wallet = getattr(m, "repurchase_wallet", 0)
                    flash_wallet = getattr(m, "flash_wallet", 0)

                    # Append rows
                    if rewards_qs.exists():
                        for r in rewards_qs:
                            ws.append([
                                m.auto_id, m.name,
                                joining, binary_income, flash_bonus,
                                sponsor_income, salary, stock_commission,
                                total_income_all,
                                getattr(r, "rank_title", None), getattr(r, "start_date", None), getattr(r, "monthly_income", None),
                                getattr(r, "duration_months", None), getattr(r, "months_paid", None), getattr(r, "active", None),
                                left_bv, right_bv, matched_bv,
                                repurchase_wallet, flash_wallet
                            ])
                    else:
                        ws.append([
                            m.auto_id, m.name,
                            joining, binary_income, flash_bonus,
                            sponsor_income, salary, stock_commission,
                            total_income_all,
                            None, None, None, None, None, None,
                            left_bv, right_bv, matched_bv,
                            repurchase_wallet, flash_wallet
                        ])

                # Totals summary
                ws.append([])
                ws.append(["Rank Summary"])
                rank_titles = ["1st Star", "Double Star", "Triple Star"]
                for title in rank_titles:
                    count = group_members.filter(current_rank=title).count()
                    ws.append([title, count])

                # BV summary
                ws.append([])
                bv_start_row = ws.max_row + 1
                ws.append(["BV Summary"])
                ws.append(["Total Left BV", sum(m.get_bv_counts()[0] for m in group_members)])
                ws.append(["Total Right BV", sum(m.get_bv_counts()[1] for m in group_members)])
                ws.append(["Total Matched BV", min(
                    sum(m.get_bv_counts()[0] for m in group_members),
                    sum(m.get_bv_counts()[1] for m in group_members)
                )])

                # Wallet summary
                ws.append([])
                wallet_start_row = ws.max_row + 1
                ws.append(["Wallet Summary"])
                ws.append(["Total Repurchase Wallet", sum(getattr(m, "repurchase_wallet", 0) for m in group_members)])
                ws.append(["Total Flash Wallet", sum(getattr(m, "flash_wallet", 0) for m in group_members)])

                # Charts
                chart = BarChart()
                chart.title = "Rank Distribution"
                chart.x_axis.title = "Rank"
                chart.y_axis.title = "Members"
                rank_end = bv_start_row - 2
                rank_start = rank_end - 2
                if rank_start >= 1:
                    data_ref = Reference(ws, min_col=2, min_row=rank_start, max_row=rank_end)
                    cat_ref = Reference(ws, min_col=1, min_row=rank_start, max_row=rank_end)
                    chart.add_data(data_ref, titles_from_data=False)
                    chart.set_categories(cat_ref)
                    ws.add_chart(chart, "M2")

                # BV + Wallet chart
                add_bv_wallet_chart(ws, bv_start_row + 1)

    # Top-level Dashboard sheet
    add_dashboard_sheet(wb, members)

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
from herbalapp.models import Member

def export_members_income(request):
    # Create workbook and sheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Members Income"

    # Header row
    headers = [
        'Member ID', 'Name', 'Joining Package',
        'Binary Income', 'Flash Bonus', 'Sponsor Income',
        'Repurchase Wallet', 'Rank Reward', 'Total Income'
    ]
    ws.append(headers)

    today = datetime.date.today()
    members = Member.objects.all()

    for member in members:
        # Daily cut-off logic
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

    # Prepare response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=members_income.xlsx'
    wb.save(response)
    return response
from django.shortcuts import render
from .models import Member


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

    # Prepare mail content
    body = f"Rocky Herbals Daily Income Report - {today}\n\n"
    for r in reports:
        body += f"{r.member.auto_id} - {r.member.name} : ₹{r.total_income}\n"

    email = EmailMessage(
        subject=f"Rocky Herbals Daily Income Report - {today}",
        body=body,
        from_email="noreply@rockyherbals.com",
        to=["rockysriherbals@gmail.com"],
    )
    email.send()


from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .models import Member

# Dashboard
def dashboard(request):
    member = Member.objects.get(id=request.user.member.id)

    # --- Wallet Values ---
    rep_wallet = member.repurchase_wallet or 0
    flash_wallet = member.flash_wallet or 0
    total_wallet = rep_wallet + flash_wallet
    # ----------------------

    return render(request, "dashboard.html", {
        "member": member,
        "rep_wallet": rep_wallet,
        "flash_wallet": flash_wallet,
        "total_wallet": total_wallet,
    })

# Members list
def member_list(request):
    members = Member.objects.all()
    return render(request, "member_list.html", {"members": members})

# Products page
def products(request):
    return render(request, "products.html")

# Income page
def income_page(request):
    return render(request, "income.html")
# ======================================
# IMPORTS
# ======================================
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from .models import Member


# ======================================
# BV DETAILS ENDPOINT
# ======================================
def member_bv(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    bv_data = member.calculate_bv()  # returns dict: self_bv, left_bv, right_bv, total_bv
    return JsonResponse(bv_data)


# ======================================
# MEMBER REGISTER (NORMAL REGISTER)
# ======================================
def member_register(request):
    if request.method == "POST":
        name = request.POST.get("name")
        mobile = request.POST.get("mobile")
        email = request.POST.get("email")
        auto_id = request.POST.get("auto_id")
        place = request.POST.get("place")
        district = request.POST.get("district")
        pincode = request.POST.get("pincode")
        aadhar = request.POST.get("aadhar")

        # Example actual DB save (uncomment)
        # Member.objects.create(
        #     name=name,
        #     mobile=mobile,
        #     email=email,
        #     auto_id=auto_id,
        #     place=place,
        #     district=district,
        #     pincode=pincode,
        #     aadhar_number=aadhar,
        # )

        messages.success(
            request,
            f"Member {name} added successfully! 📞 Mobile: {mobile}"
        )
        return redirect("member_list")

    return render(request, "member_register.html")


# ======================================
# ADD MEMBER UNDER PARENT (LEFT / RIGHT)
# ======================================
def add_member_under_parent(request, parent_id, position):
    parent = get_object_or_404(Member, id=parent_id)

    # Auto ID generate example
    auto_id = f"M{Member.objects.count() + 1:05d}"

    if request.method == "POST":
        name = request.POST.get("name")
        mobile = request.POST.get("phone")
        email = request.POST.get("email")
        auto_id = request.POST.get("auto_id")
        place = request.POST.get("place")
        district = request.POST.get("district")
        pincode = request.POST.get("pincode")
        aadhar = request.POST.get("aadhar")

        # Save in your DB (uncomment when ready)
        # Member.objects.create(
        #     name=name,
        #     mobile=mobile,
        #     email=email,
        #     parent=parent,
        #     position=position,
        #     auto_id=auto_id,
        #     place=place,
        #     district=district,
        #     pincode=pincode,
        #     aadhar_number=aadhar,
        # )

        messages.success(request, f"New member {name} added under {parent.name} on {position.upper()}.")
        return redirect("member_list")

    return render(request, "add_member.html", {
        "parent": parent,
        "position": position,
        "auto_id": auto_id,
    })

# ===================== IMPORTS =====================
from django.shortcuts import render, redirect
from .models import Member, Payment, Commission
from decimal import Decimal

# income imports
from herbalapp.utils.binary_income import process_member_binary_income
from herbalapp.utils.sponsor_income import give_sponsor_income     # <-- sponsor income engine


# ===============================================================
# ADD MEMBER VIEW  (auto ID, placement, sponsor, binary + sponsor pay)
# ===============================================================
def add_member_form(request):

    # Auto-generate rocky ID
    last = Member.objects.order_by('-id').first()
    if last:
        try:
            num = int(last.member_id.replace("rocky", ""))
        except ValueError:
            num = last.id
        new_member_id = f"rocky{num+1:03d}"
    else:
        new_member_id = "rocky001"

    parent_code = request.GET.get("parent")
    placement_member_id = ""

    parent = None
    if parent_code:
        # First try business member_id
        parent = Member.objects.filter(member_id=parent_code).first()
        if not parent:
            try:
                parent = Member.objects.filter(id=int(parent_code)).first()
            except ValueError:
                parent = None
        if parent:
            placement_member_id = parent.member_id

    # ===================== ON SUBMIT =====================
    if request.method == "POST":

        member_id = request.POST.get('member_id')
        placement_code = request.POST.get('placement_id')
        sponsor_code = request.POST.get('sponsor_id')

        placement = Member.objects.filter(member_id=placement_code).first()
        sponsor = Member.objects.filter(member_id=sponsor_code).first()

        if not placement:
            return render(request,"add_member.html",{
                "error":"❌ Placement ID not found",
                "member_id":new_member_id,
                "placement_id":placement_member_id
            })

        if not sponsor:
            return render(request,"add_member.html",{
                "error":"❌ Sponsor ID not found",
                "member_id":new_member_id,
                "placement_id":placement_member_id
            })

        # Auto Left → Right allocation
        if not placement.left_child:
            side = "left"
        elif not placement.right_child:
            side = "right"
        else:
            return render(request,"add_member.html",{
                "error":"❌ Both legs are filled!",
                "member_id":new_member_id,
                "placement_id":placement_member_id
            })

        # Create Member
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
            sponsor=sponsor
        )

        # Attach Child
        if side == "left":
            placement.left_child = new
        else:
            placement.right_child = new
        placement.save()

        # Update binary count
        if side == "left":
            placement.left_new_today += 1
        else:
            placement.right_new_today += 1
        placement.save()

        # Generate binary income
        process_member_binary_income(placement)

        # Generate sponsor income
        give_sponsor_income(new)

        return redirect("/tree/")

    return render(request,"add_member.html",{
        "member_id":new_member_id,
        "placement_member_id":placement_member_id
    })


from django.shortcuts import render
from herbalapp.models import Member, DailyIncomeReport

# ==========================================================
# INCOME REPORT VIEW (list all members + calculated incomes)
# ==========================================================
def income_report(request):
    name = request.GET.get('name', '')

    members = Member.objects.all()
    if name:
        members = members.filter(name__icontains=name)

    income_data = []
    for m in members:
        # MUST EXIST in Member model
        income = m.calculate_full_income()

        income_data.append({
            "member": m,
            "package": income.get('joining', 0),
            "binary": income.get('binary_income', 0),
            "sponsor": income.get('sponsor_income', 0),
            "flash": income.get('flash_bonus', 0),
            "salary": income.get('salary', 0),
            "stock": income.get('stock_commission', 0),   # future use
            "total": income.get('total_income_all', 0),
        })

    return render(request, "income_report.html", {"income_data": income_data})


# ==========================================================
# INCOME CHART VIEW (plot salary + total income growth)
# ==========================================================
def income_chart(request, member_id):
    reports = DailyIncomeReport.objects.filter(member_id=member_id).order_by('date')

    dates = [str(r.date) for r in reports]
    salary = [float(r.salary) for r in reports]
    total_income = [float(r.total_income) for r in reports]

    return render(request, "income_chart.html", {
        "dates": dates,
        "salary": salary,
        "total_income": total_income,
    })

