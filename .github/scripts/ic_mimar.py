#!/usr/bin/env python3
"""
☁️ CloudStream Latte Depo Yöneticisi
Özgün eklenti yönetim sistemi - Sinetech için özel olarak geliştirilmiştir
"""

import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import urllib.parse

# ⚙️ Yapılandırma
CONFIG = {
    "paths": {
        "plugins_json": "builds/plugins.json",
        "last_plugins": ".github/scripts/last_plugins.json",
        "readme": "README.md",
        "changelog": "CHANGELOG.md"
    },
    "repo": {
        "name": "Latte - Sinetech",
        "forum_url": "https://forum.sinetech.tr/konu/powerboard-film-ve-dizi-arsivine-ozel-cloudstream-deposu.3672/",
        "github_url": "https://github.com/GitLatte/latte-extensions",
        "support_keywords": ["Latte", "sinetech"]
    },
    "periods": {
        "recent_days": 3,
        "update_interval_hours": 3
    }
}

# 🌍 Dil ve Bayrak Eşleşmeleri
LANGUAGE_DATA = {
    "TR": {"flag": "🇹🇷", "name": "Türkçe", "emoji": "🥨"},
    "EN": {"flag": "🇺🇸", "name": "English", "emoji": "🍔"},
    "FR": {"flag": "🇫🇷", "name": "Français", "emoji": "🥖"},
    "ES": {"flag": "🇪🇸", "name": "Español", "emoji": "💃"},
    "DE": {"flag": "🇩🇪", "name": "Deutsch", "emoji": "🚗"},
    "AR": {"flag": "🇸🇦", "name": "العربية", "emoji": "🏺"},
    "RU": {"flag": "🇷🇺", "name": "Русский", "emoji": "🐻"},
    "JA": {"flag": "🇯🇵", "name": "日本語", "emoji": "🎌"},
    "KO": {"flag": "🇰🇷", "name": "한국어", "emoji": "🍜"},
    "IT": {"flag": "🇮🇹", "name": "Italiano", "emoji": "🍕"},
    "PT": {"flag": "🇵🇹", "name": "Português", "emoji": "⚽"},
    "PL": {"flag": "🇵🇱", "name": "Polski", "emoji": "🍖"},
    "NL": {"flag": "🇳🇱", "name": "Nederlands", "emoji": "🌷"},
    "HI": {"flag": "🇮🇳", "name": "हिन्दी", "emoji": "🕉️"},
    "ZH": {"flag": "🇨🇳", "name": "中文", "emoji": "🐉"}
}

# 🎨 Versiyon Renk Şeması
VERSION_COLORS = {
    "0.": "red",      # Beta/Test
    "1.": "green",    # Stable
    "2.": "blue",     # Major Update
    "3.": "purple",   # Rewrite
    "4.": "orange",   # Experimental
    "default": "gray"
}

# 👥 Katkıda Bulunanlar
CONTRIBUTORS = [
    {
        "name": "GitLatte", 
        "url": "https://github.com/GitLatte",
        "role": "Depo Geliştiricisi",
        "emoji": "☕"
    },
    {
        "name": "patr0nq", 
        "url": "https://github.com/patr0nq",
        "role": "Güncelleme ve Geliştirme Ortağı", 
        "emoji": "🔧"
    },
    {
        "name": "keyiflerolsun",
        "url": "https://github.com/keyiflerolsun", 
        "role": "Eklenti Kodları İlham Kaynağı",
        "emoji": "💡"
    },
    {
        "name": "feroxx",
        "url": "https://github.com/feroxx",
        "role": "YouTube Video Altyapısı Geliştiricisi",
        "emoji": "🎬"
    },
    {
        "name": "doGior",
        "url": "https://github.com/DoGior", 
        "role": "Eklenti Kodları İlham Kaynağı",
        "emoji": "👨‍💻"
    },
    {
        "name": "powerboard",
        "url": "https://forum.sinetech.tr/uye/powerboard.3822/",
        "role": "PowerDizi-PowerSinema Liste Sahibi",
        "emoji": "📺"
    },
    {
        "name": "tıngırmıngır", 
        "url": "https://forum.sinetech.tr/uye/tingirmingir.137/",
        "role": "TMDB ve Tv Bahçesi İlham Kaynağı",
        "emoji": "🌿"
    },
    {
        "name": "mooncrown",
        "url": "https://forum.sinetech.tr/uye/mooncrown.10472/",
        "role": "\"İzlemeye Devam Et\" Özelliği Fikri",
        "emoji": "👑"
    },
    {
        "name": "nedirne",
        "url": "https://forum.sinetech.tr/uye/nedirne.13409/", 
        "role": "TMDB Entegrasyonu Fikri",
        "emoji": "🎯"
    },
    {
        "name": "Memetcandal",
        "url": "https://forum.sinetech.tr/uye/memetcandal.306/",
        "role": "Aniworld Eklenti Adaptasyonu", 
        "emoji": "🌍"
    },
    {
        "name": "fsozkan", 
        "url": "https://forum.sinetech.tr/uye/fsozkan.14502/",
        "role": "KickTR Eklenti Çıkış Sebebi",
        "emoji": "⚽"
    }
]

class TurkishDateTime:
    """Türkçe tarih-saat işlemleri"""
    
    MONTHS = {
        'January': 'Ocak', 'February': 'Şubat', 'March': 'Mart',
        'April': 'Nisan', 'May': 'Mayıs', 'June': 'Haziran',
        'July': 'Temmuz', 'August': 'Ağustos', 'September': 'Eylül', 
        'October': 'Ekim', 'November': 'Kasım', 'December': 'Aralık'
    }
    
    DAYS = {
        'Monday': 'Pazartesi', 'Tuesday': 'Salı', 'Wednesday': 'Çarşamba',
        'Thursday': 'Perşembe', 'Friday': 'Cuma', 
        'Saturday': 'Cumartesi', 'Sunday': 'Pazar'
    }
    
    @classmethod
    def now_tr(cls) -> str:
        """Şu anki zamanı Türkçe olarak formatla"""
        now = datetime.now(timezone.utc) + timedelta(hours=3)  # UTC+3
        month_en = now.strftime('%B')
        day_en = now.strftime('%A')
        
        month_tr = cls.MONTHS.get(month_en, month_en)
        day_tr = cls.DAYS.get(day_en, day_en)
        
        return now.strftime(f'%d {month_tr} %Y {day_tr} - %H:%M:%S')

class PluginManager:
    """Eklenti yönetim sınıfı"""
    
    def __init__(self):
        self.plugins = []
        self.last_plugins = []
        
    def load_plugins(self, path: str) -> Optional[List[Dict]]:
        """JSON dosyasından eklentileri yükle"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"❌ {path} yüklenemedi: {e}")
            return None
    
    def save_plugins(self, plugins: List[Dict], path: str):
        """Eklentileri JSON dosyasına kaydet"""
        Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(plugins, f, ensure_ascii=False, indent=2)
    
    def analyze_changes(self) -> Dict:
        """Eklenti değişikliklerini analiz et"""
        current_dict = {p["internalName"]: p for p in self.plugins}
        last_dict = {p["internalName"]: p for p in self.last_plugins}
        
        changes = {
            "new": [],
            "updated": [], 
            "removed": [],
            "recent": []
        }
        
        # Yeni ve güncellenen eklentiler
        for name, plugin in current_dict.items():
            if name not in last_dict:
                changes["new"].append(plugin)
            elif plugin != last_dict[name]:
                changes["updated"].append(plugin)
        
        # Kaldırılan eklentiler
        for name in last_dict:
            if name not in current_dict:
                changes["removed"].append(last_dict[name])
        
        # Son 3 gündeki değişiklikler
        three_days_ago = datetime.now(timezone.utc) - timedelta(
            days=CONFIG["periods"]["recent_days"]
        )
        
        for plugin in self.plugins:
            last_updated = plugin.get("lastUpdated", "")
            if last_updated:
                try:
                    last_updated_dt = datetime.fromisoformat(
                        last_updated.replace('Z', '+00:00')
                    )
                    if last_updated_dt >= three_days_ago:
                        changes["recent"].append(plugin)
                except ValueError:
                    continue
        
        return changes

class BadgeGenerator:
    """Badge (rozet) oluşturucu"""
    
    @staticmethod
    def version(version: str) -> str:
        """Versiyon badge'i oluştur"""
        if version == "N/A":
            return "![](https://img.shields.io/badge/version-N/A-lightgray)"
        
        version_str = str(version)
        color = VERSION_COLORS["default"]
        
        for prefix, badge_color in VERSION_COLORS.items():
            if prefix != "default" and version_str.startswith(prefix):
                color = badge_color
                break
        
        return f"![](https://img.shields.io/badge/v{version_str}-{color})"
    
    @staticmethod
    def status(status: int) -> str:
        """Durum badge'i oluştur"""
        status_data = {
            1: ("✅", "Çalışıyor", "green"),
            0: ("🛠️", "Bakım Gerekli", "orange"),
            -1: ("❌", "Bozuk", "red")
        }
        
        emoji, text, color = status_data.get(status, ("❓", "Bilinmiyor", "gray"))
        return f"![](https://img.shields.io/badge/{emoji}-{text}-{color})"
    
    @staticmethod
    def language(lang_code: str) -> str:
        """Dil badge'i oluştur"""
        lang_data = LANGUAGE_DATA.get(lang_code.upper(), {})
        flag = lang_data.get("flag", "🏳️")
        name = lang_data.get("name", "Bilinmiyor")
        
        return f"![](https://img.shields.io/badge/{flag}-{urllib.parse.quote(name)}-blue)"

class MarkdownGenerator:
    """Markdown içerik üretici"""
    
    def __init__(self, plugin_manager: PluginManager):
        self.pm = plugin_manager
        self.badge = BadgeGenerator()
    
    def generate_header(self) -> str:
        """Başlık bölümünü oluştur"""
        return f"""# ☁️ {CONFIG['repo']['name']} CloudStream Depo

![Depo Durumu](https://img.shields.io/badge/STATUS-AKTİF-brightgreen)
![Eklenti Sayısı](https://img.shields.io/badge/eklentiler-{len(self.pm.plugins)}-orange)
![Son Güncelleme](https://img.shields.io/badge/son_güncelleme-{urllib.parse.quote(TurkishDateTime.now_tr().split(' - ')[0])}-lightgray)

**📍 Son Güncelleme:** {TurkishDateTime.now_tr()}

> 🎯 Bu depo, {CONFIG['repo']['name']} tarafından geliştirilen tüm CloudStream eklentilerini ve en son güncellemeleri içerir.

---
"""
    
    def generate_changelog_section(self, changes: Dict) -> str:
        """Değişiklik günlüğü bölümünü oluştur"""
        sections = []
        
        # Son değişiklikler
        if changes["recent"]:
            sections.append("## 🚀 Son Güncellemeler\n")
            for plugin in changes["recent"][:5]:  # Son 5 taneyi göster
                lang_data = LANGUAGE_DATA.get(plugin.get("language", "N/A").upper(), {})
                sections.append(
                    f"- **{plugin['name']}** {self.badge.version(plugin['version'])} "
                    f"{lang_data.get('emoji', '📦')} {lang_data.get('flag', '🏳️')}"
                )
            sections.append("")
        
        # Detaylı değişiklikler
        if any(len(changes[key]) > 0 for key in ["new", "updated", "removed"]):
            sections.append("## 📊 Detaylı Değişiklik Analizi\n")
            
            if changes["new"]:
                sections.append("### 🆕 Yeni Eklentiler\n")
                for plugin in changes["new"]:
                    sections.append(f"- **{plugin['name']}** v{plugin['version']}")
                sections.append("")
            
            if changes["updated"]:
                sections.append("### 🔄 Güncellenen Eklentiler\n")
                for plugin in changes["updated"]:
                    sections.append(f"- **{plugin['name']}** v{plugin['version']}")
                sections.append("")
            
            if changes["removed"]:
                sections.append("### 🗑️ Kaldırılan Eklentiler\n")
                for plugin in changes["removed"]:
                    sections.append(f"- ~~{plugin['name']}~~ v{plugin['version']}")
                sections.append("")
        else:
            sections.extend([
                "## 📊 Değişiklik Analizi\n",
                "ℹ️ Son güncellemede herhangi bir değişiklik tespit edilmedi.\n"
            ])
        
        return "\n".join(sections)
    
    def generate_plugins_table(self) -> str:
        """Eklenti tablosunu oluştur"""
        if not self.pm.plugins:
            return "## 📦 Eklentiler\n\n⚠️ Henüz hiç eklenti bulunmuyor.\n"
        
        table = [
            "## 📦 Tüm Eklentiler\n",
            "| Durum | Görsel | Eklenti Adı | Versiyon | Dil | Geliştirici | Açıklama |",
            "|:-----:|:------:|:------------|:--------:|:---:|:-----------:|:--------:|"
        ]
        
        for plugin in sorted(self.pm.plugins, key=lambda x: x["name"].lower()):
            # Durum
            status_badge = self.badge.status(plugin.get("status", 1))
            
            # Görsel
            icon_url = plugin.get("iconUrl", "")
            icon_markdown = f"<img src='{icon_url}' width='32' height='32'>" if icon_url else "📁"
            
            # Eklenti adı (özel durumlar için emoji)
            name = plugin["name"]
            if plugin.get("isNsfw"):
                name = f"🔞 {name}"
            if plugin.get("requiredResources"):
                name = f"🎨 {name}"
            
            # Versiyon
            version_badge = self.badge.version(plugin.get("version", "N/A"))
            
            # Dil
            lang_code = plugin.get("language", "N/A").upper()
            lang_badge = self.badge.language(lang_code)
            
            # Geliştirici
            authors = "<br>".join(plugin.get("authors", ["Bilinmiyor"]))
            
            # Açıklama
            description = plugin.get("description", "Açıklama eklenmemiş.")
            description = re.sub(r'[\\|`]', '', description)  # Güvenlik temizliği
            description = description.replace('\n', '<br>')[:100] + "..." if len(description) > 100 else description
            
            table.append(
                f"| {status_badge} | {icon_markdown} | {name} | {version_badge} | "
                f"{lang_badge} | {authors} | {description} |"
            )
        
        return "\n".join(table)
    
    def generate_statistics(self) -> str:
        """İstatistik bölümünü oluştur"""
        stats = {
            "toplam": len(self.pm.plugins),
            "calisiyor": sum(1 for p in self.pm.plugins if p.get("status", 1) == 1),
            "bakim": sum(1 for p in self.pm.plugins if p.get("status", 1) == 0),
            "bozuk": sum(1 for p in self.pm.plugins if p.get("status", 1) == -1),
            "diller": {},
            "versiyonlar": {}
        }
        
        # Dil istatistikleri
        for plugin in self.pm.plugins:
            lang = plugin.get("language", "N/A").upper()
            stats["diller"][lang] = stats["diller"].get(lang, 0) + 1
            
            version = str(plugin.get("version", "N/A"))
            major_version = version.split('.')[0] if '.' in version else version
            stats["versiyonlar"][major_version] = stats["versiyonlar"].get(major_version, 0) + 1
        
        # En popüler dil
        top_lang = max(stats["dillers"].items(), key=lambda x: x[1]) if stats["dillers"] else ("N/A", 0)
        top_lang_data = LANGUAGE_DATA.get(top_lang[0], {})
        
        return f"""
## 📊 Depo İstatistikleri

| Metrik | Değer |
|:------:|:-----:|
| 📦 Toplam Eklenti | **{stats['toplam']}** |
| ✅ Çalışıyor | {stats['calisiyor']} |
| 🛠️ Bakım Gerekli | {stats['bakim']} |
| ❌ Bozuk | {stats['bozuk']} |
| 🌍 Toplam Dil | {len(stats['dillers'])} |
| 🏆 En Popüler Dil | {top_lang_data.get('flag', '🏳️')} {top_lang_data.get('name', 'N/A')} ({top_lang[1]}) |
| 🔢 Farklı Major Versiyon | {len(stats['versiyonlar'])} |

"""
    
    def generate_contributors(self) -> str:
        """Katkıda bulunanlar bölümünü oluştur"""
        contributors_text = ["## 🤝 Ekibimiz\n", "| Üye | Rol | Katkıları |", "|:----|:----|:----------|"]
        
        for contributor in CONTRIBUTORS:
            profile_link = f"[{contributor['emoji']} {contributor['name']}]({contributor['url']})"
            contributors_text.append(
                f"| {profile_link} | {contributor['role']} | {self._generate_contributor_badges(contributor)} |"
            )
        
        return "\n".join(contributors_text)
    
    def _generate_contributor_badges(self, contributor: Dict) -> str:
        """Katkıda bulunan için badge'ler oluştur"""
        badges = []
        name_lower = contributor['name'].lower()
        
        if 'latte' in name_lower or 'gitlatte' in name_lower:
            badges.append("![](![Depo Sahibi](https://img.shields.io/badge/☕-Depo_Sahibi-brown)")
        if 'patr0nq' in name_lower:
            badges.append("![](https://img.shields.io/badge/🔧-Geliştirici-orange)")
        if 'forum' in contributor['url']:
            badges.append("![](https://img.shields.io/badge/💡-Fikir_Lideri-yellow)")
        
        return " ".join(badges) if badges else "![](https://img.shields.io/badge/🌟-Katkıda_Bulunan-purple)"
    
    def generate_footer(self) -> str:
        """Alt bilgi bölümünü oluştur"""
        support_keywords = " / ".join(f"**`{kw}`**" for kw in CONFIG["repo"]["support_keywords"])
        
        return f"""
---

## 💬 Destek ve İletişim

📣 **Forum:** [{CONFIG['repo']['name']} Topluluğu]({CONFIG['repo']['forum_url']})  
🐛 **Hata Bildirimi:** [GitHub Issues]({CONFIG['repo']['github_url']}/issues)  
💡 **Öneriler:** [Forum Sayfası]({CONFIG['repo']['forum_url']})

## 🚀 Hızlı Başlangıç

1. **CloudStream uygulamasını açın**
2. **Ayarlar → Depo Ekle'ye gidin**
3. **URL kısmına şunlardan birini yazın:** {support_keywords}
4. **Depo otomatik olarak eklenecektir**

---

<div align="center">

### ⚠️ Önemli Notlar

• Eklentiler düzenli olarak güncellenmektedir  
• Sorun yaşarsanız önce depoyu yenileyin  
• NSFW (18+) içerikler için yaş sınırına dikkat edin  
• Tüm içerikler üçüncü parti kaynaklardan sağlanmaktadır

**✨ {CONFIG['repo']['name']} - Kaliteli streaming deneyimi için 🎬**

</div>
"""

def main():
    """Ana yürütme fonksiyonu"""
    print("🚀 CloudStream Latte Depo Yöneticisi Başlatılıyor...\n")
    
    # Yönetici sınıflarını başlat
    pm = PluginManager()
    pm.plugins = pm.load_plugins(CONFIG["paths"]["plugins_json"])
    
    if not pm.plugins:
        print("❌ Eklentiler yüklenemedi, işlem durduruldu.")
        return
    
    print(f"✅ {len(pm.plugins)} eklenti başarıyla yüklendi.")
    
    # Önceki eklentileri yükle
    pm.last_plugins = pm.load_plugins(CONFIG["paths"]["last_plugins"]) or []
    
    # Değişiklik analizi
    changes = pm.analyze_changes()
    print("📊 Değişiklik analizi tamamlandı:")
    print(f"   🆕 Yeni: {len(changes['new'])}")
    print(f"   🔄 Güncellenen: {len(changes['updated'])}") 
    print(f"   🗑️ Kaldırılan: {len(changes['removed'])}")
    print(f"   🚀 Son 3 gün: {len(changes['recent'])}")
    
    # Markdown oluştur
    md = MarkdownGenerator(pm)
    
    readme_content = [
        md.generate_header(),
        md.generate_changelog_section(changes),
        md.generate_statistics(),
        md.generate_plugins_table(),
        md.generate_contributors(),
        md.generate_footer()
    ]
    
    # README'yi kaydet
    try:
        with open(CONFIG["paths"]["readme"], 'w', encoding='utf-8') as f:
            f.write('\n'.join(readme_content))
        print(f"✅ README.md başarıyla oluşturuldu ({len(readme_content)} satır)")
    except Exception as e:
        print(f"❌ README yazılırken hata: {e}")
        return
    
    # Değişiklik günlüğünü kaydet (ayrı dosya)
    if any(len(changes[key]) > 0 for key in ["new", "updated", "removed"]):
        try:
            with open(CONFIG["paths"]["changelog"], 'a', encoding='utf-8') as f:
                f.write(f"\n## 📅 {TurkishDateTime.now_tr()}\n")
                if changes["new"]:
                    f.write("\n### 🆕 Yeni Eklentiler\n")
                    for plugin in changes["new"]:
                        f.write(f"- {plugin['name']} v{plugin['version']}\n")
                if changes["updated"]:
                    f.write("\n### 🔄 Güncellenen Eklentiler\n")
                    for plugin in changes["updated"]:
                        f.write(f"- {plugin['name']} v{plugin['version']}\n")
            print("✅ CHANGELOG.md güncellendi")
        except Exception as e:
            print(f"⚠️ CHANGELOG yazılırken hata: {e}")
    
    # Son durumu kaydet
    pm.save_plugins(pm.plugins, CONFIG["paths"]["last_plugins"])
    print("✅ Son eklenti durumu kaydedildi")
    
    print(f"\n🎉 {CONFIG['repo']['name']} depo güncellemesi başarıyla tamamlandı!")
    print(f"📍 Son güncelleme: {TurkishDateTime.now_tr()}")

if __name__ == "__main__":
    main()
