#!/bin/bash
# Rocky Herbals favicon conversion script

# Input PNG logo
INPUT="herbalapp/static/images/rocky_logo.png"

# Output ICO file
OUTPUT="herbalapp/static/images/favicon.ico"

# Convert PNG to ICO using ImageMagick
convert $INPUT -resize 64x64 $OUTPUT

echo "✅ Favicon created: $OUTPUT"

