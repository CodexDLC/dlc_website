"""Тексты публичной обложки: меняйте значения в разделах ru и de.

Названия ключей сохраняйте: по ним Django Templates подставляют текст.
HTML сюда добавлять не нужно. Телефон и почта берутся из настроек компании.
После изменения файла работающий сервер нужно перезапустить; runserver обновляется сам.
"""

COMPANY_NAME = "DLC Montage"

PUBLIC_COPY = {
    "ru": {
        "navigation_label": "Навигация",
        "portal_label": "Кабинет",
        "direction_label": "AC / DC",
        "page_title": "Монтаж солнечных систем",
        "hero_title": "Реализуем солнечные проекты вместе.",
        "hero_description": "Монтаж солнечных систем и координация работ AC и DC на вашем объекте.",
        "hero_action": "Обсудить проект",
        "work_kicker": "Что мы делаем",
        "work_title": "Монтаж. Координация. Сотрудничество.",
        "work_items": [
            {"title": "Монтаж солнечных систем", "description": "Монтажные работы для проектов солнечной энергетики."},
            {"title": "AC / DC", "description": "Координация работ AC и DC на объекте."},
            {"title": "Организация работ", "description": "Чёткие договорённости между участниками работ."},
        ],
        "contact_label": "Контакты",
        "contact_title": "Ваш проект начинается с разговора.",
        "contact_description": "Обсудим ваш проект и следующие шаги.",
        "email_action": "Написать письмо",
        "phone_action": "Позвонить",
        "contact_empty": "Контактные данные будут добавлены.",
    },
    "de": {
        "navigation_label": "Navigation",
        "portal_label": "Kundenportal",
        "direction_label": "AC / DC",
        "page_title": "PV-Montage",
        "hero_title": "Gemeinsam Solarprojekte umsetzen.",
        "hero_description": "PV-Montage und Koordination der AC- und DC-Arbeiten auf Ihrer Baustelle.",
        "hero_action": "Projekt besprechen",
        "work_kicker": "Was wir machen",
        "work_title": "Montage. Abstimmung. Zusammenarbeit.",
        "work_items": [
            {"title": "PV-Montage", "description": "Montagearbeiten für Photovoltaikprojekte."},
            {"title": "AC / DC", "description": "Abstimmung der AC- und DC-Arbeiten vor Ort."},
            {
                "title": "Baustellenkoordination",
                "description": "Klare Absprachen mit den Beteiligten auf der Baustelle.",
            },
        ],
        "contact_label": "Kontakt",
        "contact_title": "Ihr Projekt beginnt mit einem Gespräch.",
        "contact_description": "Sprechen wir über Ihr Vorhaben und die nächsten Schritte.",
        "email_action": "E-Mail schreiben",
        "phone_action": "Jetzt anrufen",
        "contact_empty": "Die Kontaktdaten werden ergänzt.",
    },
}
