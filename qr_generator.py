import qrcode

# Create QR code instance
qr = qrcode.QRCode(version=1, box_size=10, border=5)

# Add data (your website URL)
qr.add_data('http://127.0.0.1:5000')
qr.make(fit=True)

# Create image
img = qr.make_image(fill_color="black", back_color="white")

# Save the image
img.save("website_qrcode.png")
print("QR code generated successfully!")