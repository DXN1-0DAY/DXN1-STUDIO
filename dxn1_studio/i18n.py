"""DXN1 STUDIO — internationalization (DS2 v2.1).

A tiny, honest i18n layer: string keys resolved from the active
language pack (English is the source of truth and always complete),
with graceful fallback to English for any missing key. Eight packs
ship built-in — English, Spanish, French, German, Portuguese, Chinese,
Hindi, Japanese — stored as JSON so a community pack is just a file in
``~/.dxn1-studio/lang/<code>.json``.

The API is deliberately boring:

    from .i18n import tr
    tr("menu.settings")           # → "Ajustes" with es active

`tr` never raises, never returns empty, and logs nothing — it is meant
to be sprinkled liberally.
"""

import json
import os

from . import APP_VERSION

LANG_DIR = os.path.join(os.path.expanduser("~"), ".dxn1-studio", "lang")

# ---------------------------------------------------------------- keys
# English source of truth. Keys are dotted: area.name

EN = {
    "app.tagline": "The clean, modern IDE. Built for flow.",
    "menu.file": "File",
    "menu.edit": "Edit",
    "menu.view": "View",
    "menu.tools": "Tools",
    "menu.help": "Help",
    "menu.settings": "Settings…",
    "menu.hub": "Project Hub…",
    "menu.new_file": "New File",
    "menu.open_file": "Open File…",
    "menu.save": "Save",
    "menu.save_as": "Save As…",
    "menu.run": "Run",
    "menu.stop": "Stop",
    "menu.find": "Find",
    "menu.replace": "Replace",
    "menu.quick_open": "Quick Open…",
    "menu.cheatsheet": "DS2 Cheat Sheet…",
    "menu.about": "About DXN1 STUDIO",
    "menu.updates": "Check for Updates…",
    "menu.tour": "Replay Welcome & Tour",
    "panel.explorer": "Explorer",
    "panel.search": "Search",
    "panel.git": "Source Control",
    "panel.packages": "Packages",
    "panel.agents": "DXN1 Agents",
    "git.commit": "Commit",
    "git.stage_all": "Stage all",
    "git.graph": "Graph",
    "git.branches": "Branches",
    "git.ai_msg": "AI msg",
    "git.message_placeholder": "Message (Ctrl+Enter to commit)",
    "hub.title": "Project Hub",
    "hub.welcome": "Welcome back, {name}. Where to?",
    "hub.new": "START SOMETHING NEW",
    "hub.recents": "RECENT WORKSPACES",
    "hub.open_folder": "Open existing folder",
    "hub.clone": "Clone from GitHub",
    "hub.explore": "Just explore the studio",
    "hub.pinned": "pinned",
    "hub.filter": "type to filter",
    "agents.title": "DXN1 Agents",
    "agents.brain": "Brain",
    "agents.stop": "Stop",
    "usage.title": "Token Usage",
    "usage.today": "TODAY",
    "usage.week": "LAST 7 DAYS",
    "usage.total": "ALL TIME",
    "usage.calls": "COMPLETIONS",
    "memory.title": "Agent Memory",
    "memory.remember": "Remember",
    "themes.title": "Theme Gallery",
    "themes.apply": "Apply",
    "markprev.copy_html": "Copy HTML",
    "markprev.export_html": "Export HTML…",
    "chart.copy_stats": "copy stats",
    "unit.copy_result": "copy result",
    "textcase.click_copy": "click any row to copy",
    "charmap.click_copy": "click a character to copy",
    "common.cancel": "Cancel",
    "common.close": "Close",
    "common.delete": "Delete",
    "common.rename": "Rename",
    "common.checkout": "Checkout",
    "common.copy": "Copy",
    "common.refresh": "Refresh",
    "common.export": "Export…",
    "common.import": "Import…",
}

# The eight packs — translations for the most visible surfaces. Missing
# keys fall back to English at lookup time; packs are intentionally
# partial and honest about it.
PACKS = {
    "es": {  # Spanish
        "app.tagline": "El IDE limpio y moderno. Hecho para fluir.",
        "menu.file": "Archivo", "menu.edit": "Editar", "menu.view": "Ver",
        "menu.tools": "Herramientas", "menu.help": "Ayuda",
        "menu.settings": "Ajustes…", "menu.hub": "Hub de proyectos…",
        "menu.new_file": "Nuevo archivo", "menu.open_file": "Abrir archivo…",
        "menu.save": "Guardar", "menu.save_as": "Guardar como…",
        "menu.run": "Ejecutar", "menu.stop": "Detener",
        "menu.find": "Buscar", "menu.replace": "Reemplazar",
        "menu.quick_open": "Apertura rápida…",
        "menu.cheatsheet": "Chuleta de DS2…",
        "menu.about": "Acerca de DXN1 STUDIO",
        "menu.updates": "Buscar actualizaciones…",
        "menu.tour": "Repetir bienvenida y tour",
        "panel.explorer": "Explorador", "panel.search": "Buscar",
        "panel.git": "Control de código", "panel.packages": "Paquetes",
        "panel.agents": "Agentes DXN1",
        "git.commit": "Confirmar", "git.stage_all": "Preparar todo",
        "git.graph": "Grafo", "git.branches": "Ramas",
        "git.ai_msg": "Mensaje IA",
        "git.message_placeholder": "Mensaje (Ctrl+Enter para confirmar)",
        "hub.title": "Hub de proyectos",
        "hub.welcome": "Bienvenido de nuevo, {name}. ¿Adónde?",
        "hub.new": "EMPIEZA ALGO NUEVO",
        "hub.recents": "ESPACIOS RECIENTES",
        "hub.open_folder": "Abrir carpeta existente",
        "hub.clone": "Clonar desde GitHub",
        "hub.explore": "Solo explorar el estudio",
        "hub.pinned": "fijado", "hub.filter": "escribe para filtrar",
        "agents.title": "Agentes DXN1", "agents.brain": "Cerebro",
        "agents.stop": "Detener",
        "usage.title": "Uso de tokens",
        "usage.today": "HOY", "usage.week": "ÚLTIMOS 7 DÍAS",
        "usage.total": "TOTAL", "usage.calls": "GENERACIONES",
        "memory.title": "Memoria del agente",
        "memory.remember": "Recordar",
        "themes.title": "Galería de temas", "themes.apply": "Aplicar",
        "common.cancel": "Cancelar", "common.close": "Cerrar",
        "common.delete": "Eliminar", "common.rename": "Renombrar",
        "common.checkout": "Cambiar a", "common.copy": "Copiar",
        "common.refresh": "Actualizar", "common.export": "Exportar…",
        "common.import": "Importar…",
        "markprev.copy_html": "Copiar HTML",
        "markprev.export_html": "Exportar HTML…",
        "chart.copy_stats": "copiar estadísticas",
        "unit.copy_result": "copiar resultado",
        "textcase.click_copy": "haz clic en cualquier fila para copiar",
        "charmap.click_copy": "clic en un carácter para copiar",
    },
    "fr": {  # French
        "app.tagline": "L'IDE propre et moderne. Conçu pour le flow.",
        "menu.file": "Fichier", "menu.edit": "Édition", "menu.view": "Vue",
        "menu.tools": "Outils", "menu.help": "Aide",
        "menu.settings": "Paramètres…", "menu.hub": "Hub de projets…",
        "menu.new_file": "Nouveau fichier",
        "menu.open_file": "Ouvrir un fichier…",
        "menu.save": "Enregistrer", "menu.save_as": "Enregistrer sous…",
        "menu.run": "Exécuter", "menu.stop": "Arrêter",
        "menu.find": "Rechercher", "menu.replace": "Remplacer",
        "menu.quick_open": "Ouverture rapide…",
        "menu.cheatsheet": "Aide-mémoire DS2…",
        "menu.about": "À propos de DXN1 STUDIO",
        "menu.updates": "Rechercher les mises à jour…",
        "menu.tour": "Revoir l'accueil et la visite",
        "panel.explorer": "Explorateur", "panel.search": "Recherche",
        "panel.git": "Contrôle de version", "panel.packages": "Paquets",
        "panel.agents": "Agents DXN1",
        "git.commit": "Valider", "git.stage_all": "Tout indexer",
        "git.graph": "Graphe", "git.branches": "Branches",
        "git.ai_msg": "Message IA",
        "hub.welcome": "Bon retour, {name}. On fait quoi ?",
        "hub.new": "COMMENCER QUELQUE CHOSE",
        "hub.recents": "ESPACES RÉCENTS",
        "hub.open_folder": "Ouvrir un dossier existant",
        "hub.clone": "Cloner depuis GitHub",
        "hub.explore": "Explorer le studio",
        "usage.title": "Utilisation des tokens",
        "usage.today": "AUJOURD'HUI", "usage.week": "7 DERNIERS JOURS",
        "usage.total": "TOTAL", "usage.calls": "GÉNÉRATIONS",
        "memory.title": "Mémoire de l'agent",
        "memory.remember": "Retenir",
        "themes.title": "Galerie de thèmes", "themes.apply": "Appliquer",
        "common.cancel": "Annuler", "common.close": "Fermer",
        "common.delete": "Supprimer", "common.rename": "Renommer",
        "common.copy": "Copier", "common.refresh": "Rafraîchir",
        "markprev.copy_html": "Copier le HTML",
        "markprev.export_html": "Exporter le HTML…",
        "chart.copy_stats": "copier les stats",
        "unit.copy_result": "copier le résultat",
        "textcase.click_copy": "cliquez sur une ligne pour copier",
        "charmap.click_copy": "cliquez un caractère pour copier",
    },
    "de": {  # German
        "app.tagline": "Die moderne, aufgeräumte IDE. Für echten Flow.",
        "menu.file": "Datei", "menu.edit": "Bearbeiten", "menu.view": "Ansicht",
        "menu.tools": "Werkzeuge", "menu.help": "Hilfe",
        "menu.settings": "Einstellungen…", "menu.hub": "Projekt-Hub…",
        "menu.new_file": "Neue Datei", "menu.open_file": "Datei öffnen…",
        "menu.save": "Speichern", "menu.save_as": "Speichern unter…",
        "menu.run": "Ausführen", "menu.stop": "Stopp",
        "menu.find": "Suchen", "menu.replace": "Ersetzen",
        "menu.quick_open": "Schnellöffnen…",
        "menu.cheatsheet": "DS2-Spickzettel…",
        "menu.about": "Über DXN1 STUDIO",
        "menu.updates": "Nach Updates suchen…",
        "menu.tour": "Willkommen & Tour wiederholen",
        "panel.explorer": "Explorer", "panel.search": "Suche",
        "panel.git": "Quellcodeverwaltung", "panel.packages": "Pakete",
        "panel.agents": "DXN1 Agents",
        "git.commit": "Committen", "git.stage_all": "Alle stagen",
        "git.graph": "Graph", "git.branches": "Branches",
        "git.ai_msg": "KI-Msg",
        "hub.welcome": "Willkommen zurück, {name}. Wohin?",
        "hub.new": "ETWAS NEUES STARTEN",
        "hub.recents": "AKTUELLE ARBEITSBEREICHE",
        "hub.open_folder": "Bestehenden Ordner öffnen",
        "hub.clone": "Von GitHub klonen",
        "hub.explore": "Studio erkunden",
        "usage.title": "Token-Nutzung",
        "usage.today": "HEUTE", "usage.week": "LETZTE 7 TAGE",
        "usage.total": "GESAMT", "usage.calls": "GENERIERUNGEN",
        "memory.title": "Agenten-Gedächtnis",
        "memory.remember": "Merken",
        "themes.title": "Theme-Galerie", "themes.apply": "Anwenden",
        "common.cancel": "Abbrechen", "common.close": "Schließen",
        "common.delete": "Löschen", "common.rename": "Umbenennen",
        "common.copy": "Kopieren", "common.refresh": "Aktualisieren",
        "markprev.copy_html": "HTML kopieren",
        "markprev.export_html": "HTML exportieren…",
        "chart.copy_stats": "Statistiken kopieren",
        "unit.copy_result": "Ergebnis kopieren",
        "textcase.click_copy": "Zeile anklicken zum Kopieren",
        "charmap.click_copy": "Zeichen anklicken zum Kopieren",
    },
    "pt": {  # Portuguese
        "app.tagline": "A IDE limpa e moderna. Feita para o fluxo.",
        "menu.file": "Arquivo", "menu.edit": "Editar", "menu.view": "Ver",
        "menu.tools": "Ferramentas", "menu.help": "Ajuda",
        "menu.settings": "Configurações…", "menu.hub": "Hub de projetos…",
        "menu.new_file": "Novo arquivo", "menu.open_file": "Abrir arquivo…",
        "menu.save": "Salvar", "menu.save_as": "Salvar como…",
        "menu.run": "Executar", "menu.stop": "Parar",
        "menu.find": "Localizar", "menu.replace": "Substituir",
        "hub.welcome": "Bem-vindo de volta, {name}. Vamos onde?",
        "hub.new": "COMECE ALGO NOVO",
        "hub.recents": "ESPAÇOS RECENTES",
        "usage.title": "Uso de tokens",
        "usage.today": "HOJE", "usage.week": "ÚLTIMOS 7 DIAS",
        "memory.title": "Memória do agente",
        "themes.apply": "Aplicar",
        "common.cancel": "Cancelar", "common.close": "Fechar",
        "common.delete": "Excluir", "common.copy": "Copiar",
        "markprev.copy_html": "Copiar HTML",
        "markprev.export_html": "Exportar HTML…",
        "chart.copy_stats": "copiar estatísticas",
        "unit.copy_result": "copiar resultado",
        "textcase.click_copy": "clique numa linha para copiar",
        "charmap.click_copy": "clique num caractere para copiar",
    },
    "zh": {  # Chinese (Simplified)
        "app.tagline": "干净现代的 IDE，为心流而生。",
        "menu.file": "文件", "menu.edit": "编辑", "menu.view": "查看",
        "menu.tools": "工具", "menu.help": "帮助",
        "menu.settings": "设置…", "menu.hub": "项目中心…",
        "menu.new_file": "新建文件", "menu.open_file": "打开文件…",
        "menu.save": "保存", "menu.save_as": "另存为…",
        "menu.run": "运行", "menu.stop": "停止",
        "menu.find": "查找", "menu.replace": "替换",
        "menu.quick_open": "快速打开…",
        "menu.cheatsheet": "DS2 速查表…",
        "menu.about": "关于 DXN1 STUDIO",
        "menu.updates": "检查更新…",
        "menu.tour": "重播欢迎与引导",
        "panel.explorer": "资源管理器", "panel.search": "搜索",
        "panel.git": "源代码管理", "panel.packages": "包管理",
        "panel.agents": "DXN1 智能体",
        "git.commit": "提交", "git.stage_all": "暂存全部",
        "git.graph": "提交图", "git.branches": "分支",
        "git.ai_msg": "AI 信息",
        "hub.welcome": "欢迎回来，{name}。要去哪里？",
        "hub.new": "开始新项目",
        "hub.recents": "最近的工作区",
        "hub.open_folder": "打开现有文件夹",
        "hub.clone": "从 GitHub 克隆",
        "hub.explore": "随便逛逛",
        "usage.title": "Token 用量",
        "usage.today": "今天", "usage.week": "过去 7 天",
        "usage.total": "总计", "usage.calls": "生成次数",
        "memory.title": "智能体记忆",
        "memory.remember": "记住",
        "themes.title": "主题画廊", "themes.apply": "应用",
        "common.cancel": "取消", "common.close": "关闭",
        "common.delete": "删除", "common.rename": "重命名",
        "common.copy": "复制", "common.refresh": "刷新",
        "markprev.copy_html": "复制 HTML",
        "markprev.export_html": "导出 HTML…",
        "chart.copy_stats": "复制统计",
        "unit.copy_result": "复制结果",
        "textcase.click_copy": "点击任意行复制",
        "charmap.click_copy": "点击字符即可复制",
    },
    "hi": {  # Hindi
        "app.tagline": "साफ़, आधुनिक IDE। फ़्लो के लिए बना।",
        "menu.file": "फ़ाइल", "menu.edit": "संपादन", "menu.view": "दृश्य",
        "menu.tools": "उपकरण", "menu.help": "सहायता",
        "menu.settings": "सेटिंग्स…", "menu.hub": "प्रोजेक्ट हब…",
        "menu.new_file": "नई फ़ाइल", "menu.open_file": "फ़ाइल खोलें…",
        "menu.save": "सहेजें", "menu.save_as": "इस रूप में सहेजें…",
        "menu.run": "चलाएँ", "menu.stop": "रोकें",
        "menu.find": "खोजें", "menu.replace": "बदलें",
        "panel.explorer": "एक्सप्लोरर", "panel.search": "खोज",
        "panel.git": "सोर्स कंट्रोल", "panel.packages": "पैकेज",
        "panel.agents": "DXN1 एजेंट",
        "git.commit": "कमिट", "git.branches": "ब्रांच",
        "hub.welcome": "वापसी के लिए स्वागत, {name}। कहाँ चलें?",
        "usage.today": "आज", "memory.remember": "याद रखें",
        "themes.apply": "लागू करें",
        "common.cancel": "रद्द करें", "common.close": "बंद करें",
        "common.copy": "कॉपी",
        "markprev.copy_html": "HTML कॉपी करें",
        "markprev.export_html": "HTML निर्यात करें…",
        "chart.copy_stats": "आंकड़े कॉपी करें",
        "unit.copy_result": "परिणाम कॉपी करें",
        "textcase.click_copy": "कॉपी करने के लिए कोई पंक्ति क्लिक करें",
        "charmap.click_copy": "कॉपी करने के लिए कोई वर्ण क्लिक करें",
    },
    "ja": {  # Japanese
        "app.tagline": "クリーンでモダンな IDE。フローのために。",
        "menu.file": "ファイル", "menu.edit": "編集", "menu.view": "表示",
        "menu.tools": "ツール", "menu.help": "ヘルプ",
        "menu.settings": "設定…", "menu.hub": "プロジェクトハブ…",
        "menu.new_file": "新規ファイル", "menu.open_file": "ファイルを開く…",
        "menu.save": "保存", "menu.save_as": "名前を付けて保存…",
        "menu.run": "実行", "menu.stop": "停止",
        "menu.find": "検索", "menu.replace": "置換",
        "panel.explorer": "エクスプローラー", "panel.search": "検索",
        "panel.git": "ソース管理", "panel.packages": "パッケージ",
        "panel.agents": "DXN1 エージェント",
        "git.commit": "コミット", "git.branches": "ブランチ",
        "hub.welcome": "おかえりなさい、{name}。どこへ？",
        "usage.today": "今日", "memory.remember": "記憶する",
        "themes.apply": "適用",
        "common.cancel": "キャンセル", "common.close": "閉じる",
        "common.copy": "コピー",
        "markprev.copy_html": "HTMLをコピー",
        "markprev.export_html": "HTMLをエクスポート…",
        "chart.copy_stats": "統計をコピー",
        "unit.copy_result": "結果をコピー",
        "textcase.click_copy": "行をクリックしてコピー",
        "charmap.click_copy": "文字をクリックでコピー",
    },
}

LANG_NAMES = {
    "en": "English", "es": "Español", "fr": "Français", "de": "Deutsch",
    "pt": "Português", "zh": "简体中文", "hi": "हिन्दी", "ja": "日本語",
}

_active = {"lang": "en", "pack": {}}


def available():
    """Codes of built-in packs + any user packs found on disk."""
    codes = set(PACKS) | {"en"}
    try:
        if os.path.isdir(LANG_DIR):
            for name in os.listdir(LANG_DIR):
                if name.endswith(".json"):
                    codes.add(name[:-5])
    except OSError:
        pass
    return sorted(codes)


def set_language(code):
    """Activate a language. User packs on disk override built-ins."""
    code = (code or "en").lower()
    pack = dict(EN)
    if code != "en":
        if code in PACKS:
            pack.update(PACKS[code])
        user_path = os.path.join(LANG_DIR, f"{code}.json")
        try:
            if os.path.exists(user_path):
                with open(user_path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    pack.update({k: str(v) for k, v in data.items()
                                 if isinstance(v, str)})
        except (OSError, json.JSONDecodeError):
            pass
    _active["lang"] = code
    _active["pack"] = pack


def tr(key, **kwargs):
    """Translate a key with {placeholders}. Never raises."""
    text = _active["pack"].get(key) or EN.get(key)
    if text is None:
        return key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


def current():
    return _active["lang"]


def export_template(dest, code="en"):
    """Write a translation template (or a pack) as JSON for sharing."""
    data = dict(EN) if code == "en" else {**EN, **PACKS.get(code, {})}
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    return len(data)


# boot: honour the default config key if the studio stored a preference
def boot_from_config(config):
    try:
        set_language(config.get("language", "en"))
    except Exception:
        set_language("en")
