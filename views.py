from django.shortcuts import render, redirect
from .forms import ProductForm
from .models import Product

# -----------------------------------------
# Upload Product (MLM features applicable)
# -----------------------------------------
def upload_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)

            # MLM Auto Distributor ID assign if empty
            if not product.distributor_id:
                product.save()  # save first to get ID
                product.distributor_id = f"DIST-{product.id}"
                product.save()

            return redirect('product_list')
    else:
        form = ProductForm()

    return render(request, 'upload_product.html', {'form': form})


# -----------------------------------------
# Product List View (MLM future expansion)
# -----------------------------------------
def product_list(request):
    products = Product.objects.all().order_by('-created_at')
    return render(request, 'product_list.html', {
        'products': products,
    })

