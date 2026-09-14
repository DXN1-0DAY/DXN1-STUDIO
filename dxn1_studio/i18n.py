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
    "common.copy_output": "Copy output",
    "common.copy_matches": "Copy matches",
    "devtools.preview": "Preview",
    "devtools.count": "Count",
    "math.copy_result": "copy result",
    "math.click_copy": "click a history row to copy",
    "hex.copy_dump": "copy hexdump",
    "hex.rows_label": "hexdump — 16 bytes per row",
    "diff.copy_diff": "copy diff",
    "diff.paste_hint": "paste old and new text above",
    "xml.copy_out": "copy",
    "contrast.copy_report": "copy report",
    "cvdlab.severity": "severity",
    "cvdlab.copy_hex": "copy simulated hex",
    "session.saved": "Saved sessions",
    "session.restore": "Restore selected",
    "session.clear": "Clear selected",
    "session.empty": "no saved sessions yet — they appear when you close the studio with files open",
    "cheatsheet.save_html": "save HTML…",
    "cheatsheet.open_browser": "open in browser",
    "cheatsheet.copy_html": "copy HTML",
    "cheatsheet.save_hint": "preview below — save a print-ready HTML copy",
    "contrast.audit_hint": "pick a theme — every text pair gets a WCAG grade",
    "xml.paste_hint": "paste some XML first",
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
        "common.copy_output": "Copiar salida",
        "common.copy_matches": "Copiar coincidencias",
        "devtools.preview": "Vista previa",
        "devtools.count": "Contar",
        "math.copy_result": "copiar resultado",
        "math.click_copy": "clic en una fila del historial para copiar",
        "hex.copy_dump": "copiar hexdump",
        "hex.rows_label": "hexdump — 16 bytes por fila",
        "diff.copy_diff": "copiar diff",
        "diff.paste_hint": "pega el texto viejo y el nuevo arriba",
        "session.saved": "Sesiones guardadas",
        "session.restore": "Restaurar selección",
        "session.clear": "Borrar selección",
        "session.empty": "aún no hay sesiones guardadas — aparecen al cerrar el estudio con archivos abiertos",
        "xml.copy_out": "copiar",
        "contrast.copy_report": "copiar informe",
        "cvdlab.severity": "gravedad",
        "cvdlab.copy_hex": "copiar hex simulado",
        "cheatsheet.save_html": "guardar HTML…",
        "cheatsheet.open_browser": "abrir en el navegador",
        "cheatsheet.copy_html": "copiar HTML",
        "cheatsheet.save_hint": "vista previa abajo — guarda una copia HTML lista para imprimir",
        "contrast.audit_hint": "elige un tema — cada par de textos recibe una calificación WCAG",
        "xml.paste_hint": "pega algo de XML primero",
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
        "common.copy_output": "Copier la sortie",
        "common.copy_matches": "Copier les correspondances",
        "devtools.preview": "Aperçu",
        "devtools.count": "Compter",
        "math.copy_result": "copier le résultat",
        "math.click_copy": "cliquez une ligne d'historique pour copier",
        "session.saved": "Sessions enregistrées",
        "session.restore": "Restaurer la sélection",
        "session.clear": "Effacer la sélection",
        "session.empty": "aucune session enregistrée — elles apparaissent en fermant le studio avec des fichiers ouverts",
        "hex.copy_dump": "copier l'hexdump",
        "hex.rows_label": "hexdump — 16 octets par ligne",
        "diff.copy_diff": "copier le diff",
        "diff.paste_hint": "collez l'ancien et le nouveau texte ci-dessus",
        "xml.copy_out": "copier",
        "contrast.copy_report": "copier le rapport",
        "cvdlab.severity": "sévérité",
        "cvdlab.copy_hex": "copier l'hex simulé",
        "cheatsheet.save_html": "enregistrer le HTML…",
        "cheatsheet.open_browser": "ouvrir dans le navigateur",
        "cheatsheet.copy_html": "copier le HTML",
        "cheatsheet.save_hint": "aperçu ci-dessous — enregistrez une copie HTML prête à imprimer",
        "contrast.audit_hint": "choisissez un thème — chaque paire reçoit une note WCAG",
        "xml.paste_hint": "collez du XML d'abord",
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
        "common.copy_output": "Ausgabe kopieren",
        "common.copy_matches": "Treffer kopieren",
        "session.saved": "Gespeicherte Sitzungen",
        "session.restore": "Auswahl wiederherstellen",
        "session.clear": "Auswahl löschen",
        "session.empty": "noch keine Sitzungen gespeichert — sie entstehen beim Schließen des Studios mit offenen Dateien",
        "devtools.preview": "Vorschau",
        "devtools.count": "Zählen",
        "math.copy_result": "Ergebnis kopieren",
        "math.click_copy": "Klicke eine Verlaufszeile zum Kopieren",
        "hex.copy_dump": "Hexdump kopieren",
        "hex.rows_label": "Hexdump — 16 Bytes pro Zeile",
        "diff.copy_diff": "Diff kopieren",
        "diff.paste_hint": "Füge oben alten und neuen Text ein",
        "xml.copy_out": "kopieren",
        "contrast.copy_report": "Bericht kopieren",
        "cvdlab.severity": "Ausprägung",
        "cvdlab.copy_hex": "simulierten Hex kopieren",
        "cheatsheet.save_html": "HTML speichern…",
        "cheatsheet.open_browser": "im Browser öffnen",
        "cheatsheet.copy_html": "HTML kopieren",
        "cheatsheet.save_hint": "Vorschau unten — druckfertige HTML-Kopie speichern",
        "contrast.audit_hint": "Thema wählen — jedes Textpaar bekommt eine WCAG-Note",
        "xml.paste_hint": "füge zuerst XML ein",
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
        "session.saved": "Sessões salvas",
        "session.restore": "Restaurar seleção",
        "session.clear": "Limpar seleção",
        "session.empty": "ainda não há sessões salvas — elas aparecem ao fechar o studio com arquivos abertos",
        "textcase.click_copy": "clique numa linha para copiar",
        "charmap.click_copy": "clique num caractere para copiar",
        "common.copy_output": "Copiar saída",
        "common.copy_matches": "Copiar correspondências",
        "devtools.preview": "Pré-visualizar",
        "devtools.count": "Contar",
        "math.copy_result": "copiar resultado",
        "math.click_copy": "clique numa linha do histórico para copiar",
        "hex.copy_dump": "copiar hexdump",
        "hex.rows_label": "hexdump — 16 bytes por linha",
        "diff.copy_diff": "copiar diff",
        "diff.paste_hint": "cole o texto antigo e o novo acima",
        "xml.copy_out": "copiar",
        "contrast.copy_report": "copiar relatório",
        "cvdlab.severity": "gravidade",
        "cvdlab.copy_hex": "copiar hex simulado",
        "cheatsheet.save_html": "salvar HTML…",
        "cheatsheet.open_browser": "abrir no navegador",
        "cheatsheet.copy_html": "copiar HTML",
        "cheatsheet.save_hint": "prévia abaixo — salve uma cópia HTML pronta para imprimir",
        "contrast.audit_hint": "escolha um tema — cada par de textos recebe uma nota WCAG",
        "xml.paste_hint": "cole algum XML primeiro",
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
        "session.saved": "已保存的会话",
        "session.restore": "恢复所选会话",
        "session.clear": "清除所选会话",
        "session.empty": "还没有已保存的会话——在打开文件的情况下关闭工作室时生成",
        "markprev.copy_html": "复制 HTML",
        "markprev.export_html": "导出 HTML…",
        "chart.copy_stats": "复制统计",
        "unit.copy_result": "复制结果",
        "textcase.click_copy": "点击任意行复制",
        "charmap.click_copy": "点击字符即可复制",
        "common.copy_output": "复制输出",
        "common.copy_matches": "复制匹配项",
        "devtools.preview": "预览",
        "devtools.count": "统计",
        "math.copy_result": "复制结果",
        "math.click_copy": "点击历史行即可复制",
        "hex.copy_dump": "复制十六进制转储",
        "hex.rows_label": "十六进制转储 — 每行 16 字节",
        "diff.copy_diff": "复制差异",
        "diff.paste_hint": "在上方粘贴新旧文本",
        "xml.copy_out": "复制",
        "contrast.copy_report": "复制报告",
        "cvdlab.severity": "严重程度",
        "cvdlab.copy_hex": "复制模拟后的色值",
        "cheatsheet.save_html": "保存 HTML…",
        "cheatsheet.open_browser": "在浏览器中打开",
        "cheatsheet.copy_html": "复制 HTML",
        "cheatsheet.save_hint": "下方为预览——保存即可打印的 HTML 副本",
        "contrast.audit_hint": "选择主题——每对文本都会获得 WCAG 等级",
        "xml.paste_hint": "先粘贴一些 XML",
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
        "session.saved": "सहेजे गए सेशन",
        "session.restore": "चयन पुनर्स्थापित करें",
        "session.clear": "चयन साफ़ करें",
        "session.empty": "अभी कोई सहेजा गया सेशन नहीं — फ़ाइलें खोलकर स्टूडियो बंद करने पर बनते हैं",
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
        "common.copy_output": "आउटपुट कॉपी करें",
        "common.copy_matches": "मिलान कॉपी करें",
        "devtools.preview": "पूर्वावलोकन",
        "devtools.count": "गिनती",
        "math.copy_result": "परिणाम कॉपी करें",
        "math.click_copy": "कॉपी करने के लिए इतिहास पंक्ति पर क्लिक करें",
        "hex.copy_dump": "हेक्सडम्प कॉपी करें",
        "hex.rows_label": "हेक्सडम्प — प्रति पंक्ति 16 बाइट",
        "diff.copy_diff": "डिफ़ कॉपी करें",
        "diff.paste_hint": "ऊपर पुराना और नया टेक्स्ट पेस्ट करें",
        "xml.copy_out": "कॉपी करें",
        "contrast.copy_report": "रिपोर्ट कॉपी करें",
        "cvdlab.severity": "गंभीरता",
        "cvdlab.copy_hex": "सिम्युलेटेड हेक्स कॉपी करें",
        "cheatsheet.save_html": "HTML सेव करें…",
        "cheatsheet.open_browser": "ब्राउज़र में खोलें",
        "cheatsheet.copy_html": "HTML कॉपी करें",
        "cheatsheet.save_hint": "नीचे प्रीव्यू — प्रिंट-रेडी HTML कॉपी सेव करें",
        "contrast.audit_hint": "थीम चुनें — हर टेक्स्ट जोड़ी को WCAG ग्रेड मिलता है",
        "xml.paste_hint": "पहले कुछ XML पेस्ट करें",
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
        "session.saved": "保存されたセッション",
        "session.restore": "選択を復元",
        "session.clear": "選択を消去",
        "session.empty": "保存されたセッションはまだありません — ファイルを開いたままスタジオを終了すると作成されます",
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
        "common.copy_output": "出力をコピー",
        "common.copy_matches": "一致をコピー",
        "devtools.preview": "プレビュー",
        "devtools.count": "カウント",
        "math.copy_result": "結果をコピー",
        "math.click_copy": "履歴行をクリックでコピー",
        "hex.copy_dump": "HEXダンプをコピー",
        "hex.rows_label": "HEXダンプ — 1行16バイト",
        "diff.copy_diff": "差分をコピー",
        "diff.paste_hint": "上に新旧のテキストを貼り付け",
        "xml.copy_out": "コピー",
        "contrast.copy_report": "レポートをコピー",
        "cvdlab.severity": "強さ",
        "cvdlab.copy_hex": "シミュレート色をコピー",
        "cheatsheet.save_html": "HTMLを保存…",
        "cheatsheet.open_browser": "ブラウザで開く",
        "cheatsheet.copy_html": "HTMLをコピー",
        "cheatsheet.save_hint": "下にプレビュー — 印刷用HTMLコピーを保存できます",
        "contrast.audit_hint": "テーマを選択 — 各テキストペアに WCAG グレードが付きます",
        "xml.paste_hint": "まずXMLを貼り付け",
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


def pack_stats():
    """DS2 v2.54 — every language pack answers for itself: how much of
    the English source it covers, how many keys it is missing, how
    many it carries that the source no longer names (stale), and
    whether its strings are highlight-safe — ``str.lower()`` keeping
    every string the same length, which is exactly what fuzzy-match
    positions (and the palette's highlight runs) silently assume. One
    exotic character ('İ' lowercases to two code points) would shift
    every highlight after it.

    Built-ins come first (``en`` then sorted codes), then any user
    pack on disk. Never raises: a pack that cannot be read reports
    itself as unreadable instead of disappearing."""
    total = len(EN)
    en_keys = set(EN)
    out = []

    def _entry(code, mapping, user=False, error=None):
        mapping = mapping or {}
        covered = len(en_keys & set(mapping))
        missing = total - covered
        stale = len([k for k in mapping if k not in en_keys])
        risk = sorted(k for k, v in mapping.items()
                      if isinstance(v, str) and len(v)
                      and len(v.lower()) != len(v))
        pct = int(round(covered * 100.0 / total)) if total else 100
        return {"code": code, "name": LANG_NAMES.get(code, code),
                "user": user, "error": error,
                "covered": covered, "total": total, "pct": pct,
                "missing": missing, "stale": stale,
                "index_safe": not risk, "risk_keys": risk[:5]}

    out.append(_entry("en", EN))
    for code in sorted(PACKS):
        if code == "en":
            continue
        out.append(_entry(code, PACKS[code]))
    try:
        if os.path.isdir(LANG_DIR):
            for name in sorted(os.listdir(LANG_DIR)):
                if not name.endswith(".json"):
                    continue
                code = name[:-5]
                try:
                    with open(os.path.join(LANG_DIR, name), "r",
                              encoding="utf-8") as fh:
                        loaded = json.load(fh)
                    data = {k: v for k, v in loaded.items()
                            if isinstance(k, str)
                            and isinstance(v, str)} \
                        if isinstance(loaded, dict) else {}
                    out.append(_entry(code, data, user=True))
                except (OSError, json.JSONDecodeError,
                        AttributeError) as exc:
                    out.append(_entry(code, {}, user=True,
                                      error=str(exc)))
    except OSError:
        pass
    return out


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
