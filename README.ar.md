<p align="center">
  <a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a> · <a href="README.tr.md">Türkçe</a> · <b>العربية</b>
</p>

# python-cli-license-starter

قالب صغير لبيع أداة سطر أوامر مكتوبة بلغة Python باستخدام مفاتيح الترخيص. انسخ المستودع، وغيّر اسم `mytool`، وضع أوامرك في الملف `commands.py`

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2ea44f)](LICENSE)

<p align="center">
  <img src="docs/terminal.png" alt="الأمر mytool status وتشغيلان للأداة في Windows Terminal، ويعرض التشغيل الثاني رسالة من لوحة التحكم" width="820">
</p>

يعتمد الترخيص على [PWF Auth](https://pwfauth.com)، وهو مجاني. ستحتاج إلى حساب فيه للحصول على سر التطبيق ومفاتيح الترخيص

يوجد فيديو مدته 3 دقائق يعرض كل الخطوات بتسجيل حقيقي، من `git clone` حتى حظر المفتاح أثناء تشغيل ملف exe: [youtu.be/2tYxlYZwNnc](https://youtu.be/2tYxlYZwNnc)

## جرّبه

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

تجد سر التطبيق في بطاقة تطبيقك ضمن صفحة Applications في لوحة التحكم، وتُنشأ المفاتيح من صفحة Licences

<p align="center">
  <img src="docs/activate.png" alt="الأمر mytool activate يربط المفتاح بالجهاز ويعرض بيانات الترخيص" width="820">
</p>

## محتويات القالب

- يربط `mytool activate` المفتاح بهذا الجهاز ويحفظه في مخزن بيانات الاعتماد في نظام التشغيل (Credential Manager في Windows، وKeychain في macOS، وSecret Service في Linux)
- يمنح `mytool trial` النسخة التجريبية المجانية، مرة واحدة لكل جهاز
- يعرض `mytool status` حالة الترخيص دون أن يستهلك أحد الأجهزة المسموح بها. أضف `--json` عندما يحتاج سكربت إلى النتيجة
- يُعلم `mytool update` المستخدمين عند نشر إصدار جديد، مع قائمة التغييرات
- يحذف `mytool deactivate` المفتاح من هذا الجهاز
- يمثّل `mytool run` الجزء المدفوع من الأداة. ضع عملك مكانه

إذا كان المفتاح مستخدماً على جهاز آخر، يعرض `activate` نقله إلى هذا الجهاز. وتحدد من لوحة التحكم ما إذا كان العملاء يستطيعون ذلك وكم مرة

## الإيقاف عن بُعد أثناء التشغيل

<p align="center">
  <img src="docs/kill-switch.gif" alt="حظر المفتاح من لوحة التحكم يوقف ملف exe العامل" width="820">
</p>

تعمل الأوامر المدفوعة داخل `get_licensing().session()`. وطوال تنفيذ هذه الكتلة، يتحقق نبض دوري (heartbeat) من المفتاح في الخلفية. احظر المفتاح أو أوقفه مؤقتاً أو احذفه من لوحة التحكم، فيتوقف الأمر عند النبضة التالية برمز الخروج 3

آلية التوقف: يستدعي خيط النبض الدالة `_thread.interrupt_main()`، فتحوّل الجلسة الاستثناء `KeyboardInterrupt` الناتج إلى `SessionEnded`. ولا يمكن مقاطعة شيفرة عالقة داخل استدعاء بلغة C، لذلك تنتهي العملية بعد 10 ثوانٍ في كل الأحوال

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

الملف `licensing.py` هو الوحيد الذي يتواصل مع خادم الترخيص، لذلك لا تهتم بقية الشيفرة بمصدر المفاتيح

## الحالة والتحديثات

<p align="center">
  <img src="docs/dashboard-text.png" alt="النص motd في صفحة Texts & slides في لوحة تحكم PWF Auth" width="820">
</p>

انشر إصداراً من صفحة Updates في لوحة التحكم ليعرضه `mytool update`. وتظهر النصوص التي تضيفها في صفحة Texts & slides داخل الأداة أيضاً: يطبع المثال نصاً اسمه `motd` في بداية كل تشغيل، فتستطيع إبلاغ المستخدمين بما تريد دون إصدار نسخة جديدة

## إنشاء ملف تنفيذي واحد

```bash
pip install -e ".[build]"
PWFAUTH_SECRET=your-app-secret python scripts/build.py
```

ينتج ذلك `dist/mytool.exe` في Windows و`dist/mytool` في الأنظمة الأخرى. ويُضمَّن السر في هذا البناء فقط. يحتوي المجلدان `build/` و`dist/` والملف `src/mytool/_build_secret.py` على السر، لذلك أُضيفت إلى `.gitignore`

يمكن تعديل أي برنامج يصل إلى جهاز العميل. يوقّع الخادم كل رد، فلا يستطيع خادم مزيّف فتح الأداة، لكن إن كان لديك شيء ثمين فعلاً فاحتفظ به على خادمك وتحقق من الترخيص هناك

## الإعدادات

| المتغير | الغرض منه |
|---|---|
| `PWFAUTH_SECRET` | سر تطبيقك (يكون مضمّناً في النسخة المبنية للإصدار) |
| `MYTOOL_LICENSE_KEY` | مفتاح لبيئة CI أو لخادم، يُستخدم في ذلك التشغيل فقط ولا يُحفظ |
| `MYTOOL_STORE` | `keyring` (الافتراضي) أو `file` |
| `MYTOOL_HOME` | المجلد الذي يحفظ فيه مخزن الملفات المفتاح |

الأجهزة التي لا تملك مخزناً لبيانات الاعتماد، مثل الخوادم دون واجهة رسومية أو الحاويات، تحفظ المفتاح في ملف لا يقرؤه إلا المستخدم الحالي

رموز الخروج: `0` نجاح، و`1` مشكلة في الإعداد أو الشبكة، و`2` لا يوجد ترخيص أو رفضه الخادم، و`3` انتهى الترخيص أثناء التشغيل، و`130` الضغط على Ctrl+C

## الاختبارات

```bash
pytest
```

تعمل الاختبارات على عميل وهمي في `tests/conftest.py`، ولا تحتاج إلى شبكة أو حساب

## الرخصة

MIT، راجع الملف [LICENSE](LICENSE)
