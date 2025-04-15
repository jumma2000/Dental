from PIL import Image, ImageDraw, ImageFont
import os

# إنشاء صورة جديدة بخلفية شفافة
img = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# رسم دائرة زرقاء
draw.ellipse((0, 0, 64, 64), fill=(13, 110, 253, 255))

# إضافة حرف "ا" باللون الأبيض
try:
    # محاولة تحميل خط عربي إذا كان متوفرًا
    font = ImageFont.truetype("arial.ttf", 40)
except IOError:
    # استخدام الخط الافتراضي إذا لم يكن الخط العربي متوفرًا
    font = ImageFont.load_default()

# رسم الحرف في وسط الدائرة
draw.text((32, 32), "ا", fill=(255, 255, 255, 255), font=font, anchor="mm")

# حفظ الصورة كملف PNG أولاً
png_path = os.path.join("static", "favicon.png")
img.save(png_path)

# تحويل الصورة إلى أيقونة
ico_path = os.path.join("static", "favicon.ico")
img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (64, 64)])

print(f"تم إنشاء ملف الأيقونة بنجاح في: {ico_path}")
