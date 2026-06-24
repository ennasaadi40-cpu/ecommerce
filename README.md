# RepairoX — Mobile Parts Store (Django)

متجر إلكتروني لقطع غيار الموبايلات مبني بـ **Python / Django**.

المتجر **يبدأ فاضي تماماً — بدون أي معلومات وهمية**. كل إشي حقيقي
(اسم المتجر، التلفون، الدوام، النصوص، البراندات، المنتجات، الأسعار) بتدخله
إنت من لوحة التحكم (admin).

يدعم: تصنيف المنتجات حسب البراند والموديل (mega menu)، صفحة كولكشن مع فلترة،
صفحة منتج، سلّة شراء (session cart)، وعملية checkout بتنشئ طلب (Order)،
بالإضافة للوحة admin كاملة لإدارة كل إشي.

---

## التشغيل (Setup)

```bash
# 1) بيئة افتراضية (اختياري)
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# 2) المكتبات
pip install -r requirements.txt

# 3) قاعدة البيانات
python manage.py migrate

# 4) مستخدم admin
python manage.py createsuperuser

# 5) شغّل
python manage.py runserver
```

افتح: <http://127.0.0.1:8000/>  •  لوحة التحكم: <http://127.0.0.1:8000/admin/>

> ملاحظة Python 3.14: إذا فشل تثبيت Pillow، خلّي السطر بملف
> `requirements.txt` هيك: `Pillow>=12.0.0` وأعد `pip install -r requirements.txt`.

---

## أول خطوات بعد التشغيل (من لوحة التحكم)

1. **Site configuration** — عبّي معلومات متجرك الحقيقية: الاسم، التلفون،
   الدوام، شريط العروض، نص "About"، الإيميل، العنوان. أي حقل بتتركه فاضي
   بيختفي من الموقع تلقائياً (ما في إشي مفبرك).
2. **Brands** — ضيف البراندات يلي بتتعامل فيها.
3. **Collections** — ضيف الموديلات/التصنيفات تحت كل براند.
4. **Products** — ضيف منتجاتك الحقيقية بأسعارها وصورها ومخزونها.

### اختصار للتصنيفات (اختياري)

إذا بدك توفّر وقت، في أمر بيعمل **شجرة التصنيفات بس** (أسماء أجهزة حقيقية،
**بدون أي منتجات أو أسعار**):

```bash
python manage.py seed
```

بعدها بتضيف منتجاتك الحقيقية تحت التصنيفات يلي فعلاً عندك بضاعة فيها.
لإلغاء الشجرة: `python manage.py seed --flush`. أو تجاهل الأمر كلياً
واعمل تصنيفاتك بإيدك من الـ admin.

---

## بنية المشروع

```
repairox/
├── manage.py
├── requirements.txt
├── qcp_store/              # إعدادات المشروع
│   ├── settings.py
│   └── urls.py
├── store/
│   ├── models.py           # Brand, Collection, Product, Order, OrderItem, SiteConfig
│   ├── views.py
│   ├── cart.py             # سلّة شراء (session-based)
│   ├── context_processors.py
│   ├── admin.py
│   ├── urls.py
│   └── management/commands/seed.py   # شجرة تصنيفات اختيارية (بدون منتجات)
├── templates/
│   ├── base.html
│   └── store/             # home, brand, collection, product, cart, checkout...
└── static/css/style.css   # كل الألوان كـ CSS variables بأول الملف
```

---

## نماذج البيانات (Models)

- **SiteConfig** — معلومات المتجر الحقيقية، سجل واحد بتعدّله من الـ admin.
- **Brand** — البراند (تضيفه إنت).
- **Collection** — تصنيف هرمي (Series → Model) عبر `parent` ذاتي المرجع.
- **Product** — المنتج بسعر، مخزون، صورة، SKU (تضيفه إنت).
- **Order / OrderItem** — الطلب وعناصره بعد الـ checkout.

---

## أفكار للتوسعة

- بوابة دفع حقيقية (Stripe / PayPal).
- حسابات وتسجيل دخول للزبائن.
- بحث وفلترة متقدمة.
- REST API بـ Django REST Framework لربط تطبيق Flutter.

---

## إشعارات الطلبات بالإيميل

لما أي زبون يعمل order، بيوصل إيميل تلقائي لصاحب المتجر بكل تفاصيل الطلب
(اسم الزبون، تلفونه، عنوانه، المنتجات، والمجموع).

### 1) حدّد لمين يوصل الإيميل
من لوحة التحكم → **Site configuration** → عبّي حقل **notify_email**
بإيميل صاحب المتجر (إذا تركته فاضي، بيستخدم حقل **email** العادي).

### 2) وضع التجربة (افتراضي — بدون أي إعداد)
الافتراضي بطبع الإيميل بالـ **terminal** يلي شغّال فيه السيرفر، فتقدر تتأكد
إنه الإشعار اشتغل بدون ما تربط إيميل حقيقي. اعمل order تجريبي وراقب نافذة
`runserver` — رح تشوف نص الإيميل كامل.

### 3) إرسال إيميل حقيقي عبر Gmail
أ. فعّل **2-Step Verification** على حساب Gmail تبعك.
ب. أنشئ **App Password** من إعدادات أمان Google (16 خانة) — مش كلمة سر حسابك العادية.
ج. شغّل السيرفر بهاي المتغيّرات (PowerShell):

```powershell
$env:EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend"
$env:EMAIL_HOST_USER="youremail@gmail.com"
$env:EMAIL_HOST_PASSWORD="ضع_App_Password_هنا"
$env:DEFAULT_FROM_EMAIL="youremail@gmail.com"
python manage.py runserver
```

> ملاحظة: متغيّرات الـ `$env:` بتضل فعّالة لنفس نافذة PowerShell بس. للتثبيت
> الدائم استخدم ملف `.env` أو إعدادات النظام، أو خدمة استضافة بتدعم
> environment variables.

أي مزوّد SMTP تاني (Outlook، مزوّد الاستضافة...) بيشتغل بنفس الطريقة —
بس غيّر `EMAIL_HOST` و `EMAIL_PORT` حسب المزوّد.
