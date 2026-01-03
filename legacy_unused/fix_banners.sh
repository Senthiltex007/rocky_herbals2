#!/bin/bash
# Rocky Herbals banner auto-replace script

# Root templates folder
TEMPLATE_DIR="herbalapp/templates"

# Replace old banner references with new unique names
grep -rl "{% static 'images/banner.jpg' %}" $TEMPLATE_DIR | xargs sed -i "s|{% static 'images/banner.jpg' %}|{% static 'images/banner_main.jpg' %}|g"
grep -rl "{% static 'images/banner1.jpg' %}" $TEMPLATE_DIR | xargs sed -i "s|{% static 'images/banner1.jpg' %}|{% static 'images/banner_home.jpg' %}|g"
grep -rl "{% static 'images/banner2.jpg' %}" $TEMPLATE_DIR | xargs sed -i "s|{% static 'images/banner2.jpg' %}|{% static 'images/banner_shop.jpg' %}|g"
grep -rl "{% static 'images/banner3.jpg' %}" $TEMPLATE_DIR | xargs sed -i "s|{% static 'images/banner3.jpg' %}|{% static 'images/banner_contact.jpg' %}|g"

echo "✅ Banner references updated successfully!"

