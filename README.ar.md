<p align="center">
  <a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a> · <a href="README.tr.md">Türkçe</a> · <b>العربية</b>
</p>

# python-cli-license-starter

قالب جاهز يساعدك على بيع أداة سطر أوامر مكتوبة بلغة Python بمفاتيح ترخيص. استنسخ المستودع، وغيّر الاسم `mytool` إلى اسم أداتك، ثم أضف أوامرك في الملف `commands.py`

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2ea44f)](LICENSE)

<p align="center">
  <img src="docs/terminal.png" alt="الأمر mytool status وتشغيلان للأداة في Windows Terminal، وفي التشغيل الثاني رسالة من لوحة التحكم" width="820">
</p>

يعتمد نظام الترخيص على [PWF Auth](https://pwfauth.com)، وهي خدمة مجانية. ستحتاج إلى حساب فيها لتحصل على سر التطبيق (app secret) وعلى مفاتيح الترخيص

شاهد فيديو مدته 3 دقائق يعرض الخطوات كلها بتسجيل حقيقي، من `git clone` حتى حظر المفتاح والملف التنفيذي قيد التشغيل: [youtu.be/2tYxlYZwNnc](https://youtu.be/2tYxlYZwNnc)

## البدء السريع

```bash
git clone https://github.com/pwfauth/python-cli-license-starter.git
cd python-cli-license-starter
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
export PWFAUTH_SECRET=your-app-secret  # PowerShell: $env:PWFAUTH_SECRET = "your-app-secret"
mytool activate YOUR-LICENSE-KEY
mytool run
```

ستجد سر التطبيق في بطاقة تطبيقك بصفحة Applications في لوحة التحكم، وتُنشئ مفاتيح الترخيص من صفحة Licences

<p align="center">
  <img src="docs/activate.png" alt="الأمر mytool activate يربط مفتاح الترخيص بالجهاز ويعرض بياناته" width="820">
</p>

## ما الذي يتضمنه القالب

- الأمر `mytool activate` يربط مفتاح الترخيص بهذا الجهاز ويحفظه في مخزن بيانات الاعتماد بنظام التشغيل (إدارة بيانات الاعتماد في Windows، وسلسلة المفاتيح Keychain في macOS، وSecret Service في Linux)
- الأمر `mytool trial` يمنح نسخة تجريبية مجانية، مرة واحدة لكل جهاز
- الأمر `mytool status` يعرض حالة الترخيص دون أن يُحتسب جهازاً إضافياً. أضف الخيار `--json` إذا كنت ستقرأ النتيجة من برنامج نصي
- الأمر `mytool update` يُعلم المستخدمين بالإصدار الجديد عند نشره، مع قائمة التغييرات
- الأمر `mytool deactivate` يحذف مفتاح الترخيص من هذا الجهاز
- الأمر `mytool run` هو الجزء المدفوع من الأداة، وفيه تضع عملك

إذا كان المفتاح مستخدماً على جهاز آخر، يعرض عليك `activate` نقله إلى هذا الجهاز. ومن لوحة التحكم تحدد هل يمكن للعملاء نقل الترخيص بأنفسهم، وكم مرة

## الإيقاف عن بُعد أثناء التشغيل

<p align="center">
  <img src="docs/kill-switch.gif" alt="حظر المفتاح من لوحة التحكم يوقف الملف التنفيذي أثناء تشغيله" width="820">
</p>

تعمل الأوامر المدفوعة داخل `get_licensing().session()`. وطوال تنفيذ هذه الكتلة يتحقق البرنامج من المفتاح في الخلفية على فترات منتظمة (heartbeat). احظر المفتاح أو أوقفه مؤقتاً أو احذفه من لوحة التحكم، فيتوقف الأمر عند التحقق التالي برمز الخروج 3

كيف يتوقف: يستدعي مؤشر ترابط التحقق الدالة `_thread.interrupt_main()`، فتحوّل الجلسة الاستثناء `KeyboardInterrupt` إلى `SessionEnded`. أما الشيفرة العالقة داخل استدعاء بلغة C فلا يمكن مقاطعتها، لذلك تنتهي العملية تلقائياً بعد 10 ثوانٍ

## إضافة أوامرك

```python
from .cli import app, friendly, get_licensing

@app.command()
@friendly
def convert(path: str) -> None:
    """Convert a folder (paid)"""
    with get_licensing().session() as session:
        for item in load(path):
            process(item)
            session.ensure_active()   # optional, stops between items once the key is revoked
```

الملف `licensing.py` هو الوحيد الذي يتصل بخادم الترخيص، فلا تحتاج بقية الشيفرة إلى معرفة مصدر المفاتيح

## الحالة والتحديثات

<p align="center">
  <img src="docs/dashboard-text.png" alt="النص motd في صفحة Texts & slides بلوحة تحكم PWF Auth" width="820">
</p>

انشر إصداراً من صفحة Updates في لوحة التحكم، وسيعرضه `mytool update` للمستخدمين. وتظهر في الأداة أيضاً النصوص التي تضيفها في صفحة Texts & slides: يعرض المثال نصاً باسم `motd` في بداية كل تشغيل، فتستطيع إبلاغ المستخدمين بما تريد دون إصدار نسخة جديدة

## إنشاء ملف تنفيذي واحد

```bash
pip install -e ".[build]"
PWFAUTH_SECRET=your-app-secret python scripts/build.py
```

ستحصل على الملف `dist/mytool.exe` في Windows، وعلى `dist/mytool` في الأنظمة الأخرى. ويُضمَّن السر في هذه النسخة فقط. يحتوي المجلدان `build/` و`dist/` والملف `src/mytool/_build_secret.py` على السر، ولهذا أُضيفت جميعها إلى `.gitignore`

أي برنامج يصل إلى جهاز العميل يمكن تعديله. صحيح أن الخادم يوقّع كل رد فلا يستطيع خادم مزيّف فتح الأداة، لكن إن كان لديك شيء ثمين فعلاً فاحتفظ به على خادمك وتحقق من الترخيص هناك

## الإعدادات

| متغير البيئة | وظيفته |
|---|---|
| `PWFAUTH_SECRET` | سر تطبيقك (يكون مضمّناً في النسخة المبنية للنشر) |
| `MYTOOL_LICENSE_KEY` | مفتاح ترخيص لبيئة CI أو لخادم، يُستخدم في ذلك التشغيل فقط ولا يُحفظ |
| `MYTOOL_STORE` | `keyring` (الافتراضي) أو `file` |
| `MYTOOL_HOME` | المجلد الذي يُحفظ فيه المفتاح عند استخدام الخيار `file` |

إذا لم يتوفر مخزن لبيانات الاعتماد، كما في خادم بلا واجهة رسومية أو في حاوية، يُحفظ المفتاح في ملف لا يستطيع قراءته إلا المستخدم الحالي

رموز الخروج: `0` نجاح، و`1` مشكلة في الإعداد أو الاتصال، و`2` لا يوجد ترخيص أو رفضه الخادم، و`3` انتهى الترخيص أثناء التشغيل، و`130` أُوقف البرنامج بالضغط على Ctrl+C

## الاختبارات

```bash
pytest
```

تعمل الاختبارات على عميل تجريبي في `tests/conftest.py`، فلا تحتاج إلى اتصال بالإنترنت ولا إلى حساب

## الرخصة

مرخّص بموجب MIT، راجع الملف [LICENSE](LICENSE)
