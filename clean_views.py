# herbalapp/clean_views.py
# =====================================
# Clean Product Views (MLM Safe)
# =====================================

from django.shortcuts import render, redirect
from .forms import ProductForm
from .models import Product


# -------------------------------------
# Upload Product
# -------------------------------------
def upload_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()   # ✅ save first → id created

            # Auto assign distributor_id if missing
            if not product.distributor_id:
                product.distributor_id = f"DIST-{product.id}"
                product.save(update_fields=["distributor_id"])

            return redirect("product_list")
    else:
        form = ProductForm()

    return render(request, "upload_product.html", {"form": form})


# -------------------------------------
# Product List
# -------------------------------------
def product_list(request):
    products = Product.objects.all().order_by("-created_at")
    return render(
        request,
        "product_list.html",
        {"products": products}
    )

