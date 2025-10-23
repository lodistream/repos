import json
import os
from datetime import datetime, timezone, timedelta

PLUGINS_JSON_PATH = "builds/plugins.json"
LAST_PLUGINS_JSON_PATH = ".github/scripts/last_plugins.json"
README_PATH = "README.md"

LANGUAGE_FLAGS = {
    "EN": "🇺🇸",  # İngilizce için ABD bayrağı
    "TR": "🇹🇷",  # Türkçe için Türkiye bayrağı
    "FR": "🇫🇷",
    "ES": "🇪🇸",
    "DE": "🇩🇪",  # Almanca için Almanya bayrağı
}

# Tarih formatı için Türkçe çeviriler
MONTHS_TR = {
    'January': 'Ocak', 'February': 'Şubat', 'March': 'Mart',
    'April': 'Nisan', 'May': 'Mayıs', 'June': 'Haziran',
    'July': 'Temmuz', 'August': 'Ağustos', 'September': 'Eylül',
    'October': 'Ekim', 'November': 'Kasım', 'December': 'Aralık'
}

DAYS_TR = {
    'Monday': 'Pazartesi', 'Tuesday': 'Salı', 'Wednesday': 'Çarşamba',
    'Thursday': 'Perşembe', 'Friday': 'Cuma', 'Saturday': 'Cumartesi',
    'Sunday': 'Pazar'
}

def load_plugins(path):
    """JSON dosyasından eklenti verilerini yükler"""
    if not os.path.exists(path):
        print(f"Uyarı: {path} dosyası bulunamadı.")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"\nHATA: {path} dosyası okunamadı!")
        print(f"Detay: {e}")
        return None

def save_last_plugins(plugins):
    """Mevcut eklentileri sonraki karşılaştırma için kaydeder"""
    os.makedirs(os.path.dirname(LAST_PLUGINS_JSON_PATH), exist_ok=True)
    try:
        with open(LAST_PLUGINS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(plugins, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"HATA: last_plugins.json kaydedilemedi: {e}")

def get_turkish_datetime():
    """Türkçe tarih ve saat bilgisini döndürür"""
    now = datetime.now(timezone.utc) + timedelta(hours=3)
    
    english_month = now.strftime('%B')
    english_day = now.strftime('%A')
    
    turkish_month = MONTHS_TR.get(english_month, english_month)
    turkish_day = DAYS_TR.get(english_day, english_day)
    
    formatted_date = now.strftime(f'%d {turkish_month} %Y {turkish_day} - %H:%M:%S')
    return formatted_date

def generate_version_badge(version):
    """Versiyona göre badge oluşturur"""
    if version == "N/A":
        return "![](https://img.shields.io/badge/version-N/A-lightgray)"
    
    version_str = str(version)
    if version_str.startswith("1."):
        color = "green"
    elif version_str.startswith("2."):
        color = "blue"
    elif version_str.startswith("0."):
        color = "orange"
    else:
        color = "red"
    
    return f"![](https://img.shields.io/badge/version-{version_str}-{color})"

def find_changes(current, last):
    """Son 3 gündeki değişiklikleri bulur"""
    if not last:
        return []
    
    last_dict = {p["internalName"]: p for p in last}
    changes = []
    three_days_ago = datetime.now(timezone.utc) - timedelta(days=3)

    for plugin in current:
        name = plugin["internalName"]
        last_plugin = last_dict.get(name, {})
        last_updated = last_plugin.get("lastUpdated", "")
        
        try:
            last_updated_dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00')) if last_updated else None
        except ValueError:
            last_updated_dt = None

        is_new = name not in last_dict
        is_recently_updated = last_updated_dt and last_updated_dt >= three_days_ago
        
        if is_new:
            changes.append(("🆕 Yeni Eklenti", plugin))
        elif is_recently_updated:
            changes.append(("🔄 Güncellenmiş Eklenti", plugin))
    
    return changes

def generate_changelog(changes):
    """Değişiklik günlüğü oluşturur"""
    if not changes:
        return "### ℹ️ Son 3 gün içinde herhangi bir değişiklik bulunamadı.\n"
    
    lines = ["### 📋 Son 3 Gün İçindeki Değişiklikler\n"]
    for change_type, plugin in changes:
        lang = plugin.get('language', 'N/A').upper()
        lang_flag = LANGUAGE_FLAGS.get(lang, '🏳️')
        lines.append(f"- **{plugin['name']}** v{plugin['version']} {lang_flag} - {change_type}")
    lines.append("")
    return "\n".join(lines)

def generate_table(plugins):
    """Eklenti tablosu oluşturur"""
    if not plugins:
        return "### ⚠️ Henüz hiç eklenti bulunmuyor.\n"
    
    lines = [
        "## 📦 Tüm Eklentiler\n",
        "| Görsel | Eklenti Adı | Versiyon | Dil | Geliştirici | Açıklama |",
        "|:------:|:------------|:--------:|:---:|:-----------:|:--------:|"
    ]
    
    for plugin in sorted(plugins, key=lambda x: x["name"].lower()):
        # Görsel URL'si
        icon_url = plugin.get("iconUrl", "")
        icon_markdown = f"![]({icon_url})" if icon_url else "📁"
        
        # Eklenti adı
        name = plugin.get("name", "Bilinmiyor")
        if plugin.get("status") == 0:
            name += " 🚧"  # Bakım gerekiyor
        
        # Versiyon badge
        version = plugin.get("version", "N/A")
        version_badge = generate_version_badge(version)
        
        # Dil bayrağı
        language = plugin.get("language", "N/A").upper()
        flag = LANGUAGE_FLAGS.get(language, "🏳️")
        
        # Geliştirici(ler)
        authors = ", ".join(plugin.get("authors", ["Bilinmiyor"]))
        
        # Açıklama (tablo formatını bozabilecek karakterleri temizle)
        description = plugin.get("description", "Açıklama eklenmemiş.")
        description = description.replace('|', '∣').replace('\n', ' ').replace('\r', '').strip()
        
        lines.append(f"| {icon_markdown} | {name} | {version_badge} | {flag} | {authors} | {description} |")
    
    lines.append("")
    return "\n".join(lines)

def generate_contributors_section():
    """Katkıda bulunanlar bölümünü oluşturur"""
    return """
## 🤝 Katkıda Bulunanlar

| Geliştirici | Rol |
|-------------|-----|
| [GitLatte](https://github.com/GitLatte) | Depo Geliştiricisi |
"""

def main():
    """Ana işlem fonksiyonu"""
    print("🔄 README.md güncelleme işlemi başlatılıyor...")
    
    # Eklentileri yükle
    plugins = load_plugins(PLUGINS_JSON_PATH)
    if plugins is None:
        print("❌ İşlem durdu: plugins.json dosyası düzgün değil veya eksik.")
        return

    # Önceki eklentileri yükle ve değişiklikleri bul
    last_plugins = load_plugins(LAST_PLUGINS_JSON_PATH) or []
    changes = find_changes(plugins, last_plugins)
    
    # README içeriğini oluştur
    readme_content = [
        "# ☁️ Latte - Sinetech CloudStream Eklenti Listesi ve Değişiklik Günlüğü",
        "",
        f"**Son Güncelleme:** {get_turkish_datetime()}",
        "",
        "Bu depo tüm Latte - Sinetech eklentilerini ve en son güncellemeleri içerir.",
        "",
        generate_changelog(changes),
        "---",
        generate_table(plugins),
        "---",
        generate_contributors_section(),
        "📬 **Destek İletişim:** [Latte Forum](https://forum.sinetech.tr/konu/powerboard-film-ve-dizi-arsivine-ozel-cloudstream-deposu.3672/)",
        "",
        "---",
        "## 🔔 Önemli Notlar",
        "- Repoyu eklemek için Cloudstream içerisindeki Depo Ekle alanında Depo URL kısmına **\"Latte\"** veya **\"sinetech\"** yazmanız yeterlidir.",
        "- Eklentiler düzenli olarak güncellenmektedir.",
        "- Sorun bildirimleri için forum sayfasını kullanabilirsiniz.",
        ""
    ]

    # README dosyasını yaz
    try:
        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(readme_content))
        print("✅ README.md başarıyla güncellendi!")
        
        # Mevcut eklentileri kaydet
        save_last_plugins(plugins)
        print("✅ Son eklenti durumu kaydedildi!")
        
    except IOError as e:
        print(f"❌ README.md yazılırken hata oluştu: {e}")

if __name__ == "__main__":
    main()
