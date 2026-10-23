<p align="center">
  <a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a> · <b>Türkçe</b> · <a href="README.ar.md">العربية</a>
</p>
<p align="center">Video eğitimleri: <a href="https://www.youtube.com/@pwfauth">youtube.com/@pwfauth</a></p>

# python-cli-license-starter

Bir Python komut satırı aracını lisans anahtarlarıyla satmak için küçük bir şablon. Depoyu klonlayın, `mytool` adını değiştirin ve kendi komutlarınızı `commands.py` dosyasına ekleyin

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2ea44f)](LICENSE)

<p align="center">
  <img src="docs/terminal.png" alt="Windows Terminal'de mytool status ve iki çalıştırma; ikincisi panelden gelen bir mesajı gösteriyor" width="820">
</p>

Lisanslama, ücretsiz olan [PWF Auth](https://pwfauth.com) üzerinde çalışır. Uygulama gizli anahtarı (app secret) ve lisans anahtarları için orada bir hesap açmanız gerekiyor

Her adımı gerçek kayıtla gösteren 3 dakikalık bir video var; `git clone` komutundan, exe çalışırken anahtarın yasaklanmasına kadar: [youtu.be/2tYxlYZwNnc](https://youtu.be/2tYxlYZwNnc)

## Deneyin

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

Gizli anahtar, paneldeki Applications sayfasında uygulamanızın kartında bulunur. Lisans anahtarları Licences sayfasında oluşturulur

<p align="center">
  <img src="docs/activate.png" alt="mytool activate anahtarı bu bilgisayara bağlar ve lisans bilgilerini gösterir" width="820">
</p>

## Neler var

- `mytool activate` anahtarı bu bilgisayara bağlar ve işletim sisteminin kimlik bilgisi deposunda saklar (Windows'ta Credential Manager, macOS'ta Keychain, Linux'ta Secret Service)
- `mytool trial` ücretsiz denemeyi başlatır, her bilgisayarda yalnızca bir kez
- `mytool status` lisansı bir cihaz hakkı harcamadan gösterir. Bir betiğin ihtiyacı olduğunda `--json` ekleyin
- `mytool update` yeni bir sürüm yayımladığınızda kullanıcılara değişiklik notlarıyla birlikte haber verir
- `mytool deactivate` anahtarı bu bilgisayardan siler
- `mytool run` aracın ücretli kısmıdır. Yerine kendi kodunuzu koyun

Bir anahtar başka bir bilgisayarda kullanılıyorsa `activate` onu bu bilgisayara taşımayı önerir. Müşterilerin bunu kendilerinin yapıp yapamayacağını ve ne sıklıkla yapabileceğini panelden siz belirlersiniz

## Çalışırken uzaktan durdurma

<p align="center">
  <img src="docs/kill-switch.gif" alt="Anahtar panelde yasaklanıyor ve çalışan exe duruyor" width="820">
</p>

Ücretli komutlar `get_licensing().session()` içinde çalışır. Blok çalıştığı sürece arka planda bir heartbeat anahtarı kontrol eder. Anahtarı panelden yasaklayın, duraklatın ya da silin; komut bir sonraki heartbeat'te 3 çıkış koduyla durur

Nasıl durur: heartbeat iş parçacığı `_thread.interrupt_main()` çağırır, oturum da ortaya çıkan `KeyboardInterrupt` hatasını `SessionEnded` hatasına çevirir. Bir C çağrısında takılı kalan kod kesilemez, bu yüzden süreç 10 saniye sonra her durumda kapanır

## Kendi komutunuzu eklemek

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

Lisans sunucusuyla konuşan tek dosya `licensing.py`; bu yüzden kodun geri kalanı anahtarların nereden geldiğiyle ilgilenmez

## Durum ve güncellemeler

<p align="center">
  <img src="docs/dashboard-text.png" alt="PWF Auth panelinde Texts & slides altındaki motd metni" width="820">
</p>

Paneldeki Updates sayfasından bir sürüm yayımlayın, `mytool update` onu gösterir. Texts & slides altındaki metinler de araçta görünür: örnek, her çalıştırmanın başında `motd` adlı metni yazdırır; böylece yeni bir sürüm çıkarmadan kullanıcılarınıza bir şey söyleyebilirsiniz

## Tek bir çalıştırılabilir dosya oluşturmak

```bash
pip install -e ".[build]"
PWFAUTH_SECRET=your-app-secret python scripts/build.py
```

Bu komut Windows'ta `dist/mytool.exe`, diğer sistemlerde `dist/mytool` oluşturur. Gizli anahtar yalnızca bu derlemeye gömülür. `build/`, `dist/` ve `src/mytool/_build_secret.py` gizli anahtarı içerdiği için `.gitignore` dosyasında yer alır

Müşterinin bilgisayarına giden her program değiştirilebilir. Sunucu her yanıtı imzalar, bu yüzden sahte bir sunucu aracın kilidini açamaz; ama gerçekten değerli bir şeyiniz varsa onu kendi sunucunuzda tutun ve lisansı orada kontrol edin

## Ayarlar

| Değişken | Ne işe yarar |
|---|---|
| `PWFAUTH_SECRET` | Uygulamanızın gizli anahtarı (yayın derlemesinde gömülüdür) |
| `MYTOOL_LICENSE_KEY` | CI veya sunucu için bir anahtar; yalnızca o çalıştırmada kullanılır, kaydedilmez |
| `MYTOOL_STORE` | `keyring` (varsayılan) veya `file` |
| `MYTOOL_HOME` | Dosya deposunun anahtarı sakladığı klasör |

Kimlik bilgisi deposu olmayan makineler (ekransız bir sunucu ya da konteyner gibi) yalnızca geçerli kullanıcının okuyabildiği bir dosya kullanır

Çıkış kodları: `0` sorun yok, `1` kurulum veya ağ sorunu, `2` lisans yok ya da sunucu reddetti, `3` lisans çalışma sırasında sona erdi, `130` Ctrl+C

## Testler

```bash
pytest
```

Testler `tests/conftest.py` içindeki sahte bir istemciyle çalışır; ağ bağlantısı ya da hesap gerekmez

## Lisans

MIT, ayrıntılar için [LICENSE](LICENSE)
