"""Скрипт профессионального визуального оформления Google Таблицы для куратора (Эмиля).

Настраивает:
1. Выпадающие списки (Google Sheets Data Validation Chips / Pills):
   - На листе Übersicht: выпадающие списки статуса [Freigegeben, Nacharbeit erforderlich, In Prüfung, Nicht abgenommen] и Freigabe [Ja, Nein].
   - На листах объектов: колонка F «Abnahme (Bauleiter Emil)» со значениями [✓ i.O., ✗ Nicht i.O., —]
   - В блоке протокола объектов: «Gesamturteil Abnahme» и «Freigabe zur Auszahlung».
2. Фирменный стиль DLC Montage (Navy & Energy Green):
   - Идеальная шапка (Header Card) на листах объектов без обрезки текста.
   - Ссылка «← Zurück zur Übersicht» с переходом на сводный лист.
   - Тёмно-синяя плашка блоков 1 и 2 на всю ширину (Navy 900).
   - Чёткие заголовки таблицы (Navy 700) с белым шрифтом.
   - Сетка данных с чередованием строк (белый / светло-серый) и аккуратными рамками.
   - Выверенная ширина колонок для всех листов.
"""

import os
import re
import sys

sys.path.insert(0, r"d:\Workspace\clients\dlc_montage")
sys.path.insert(0, r"d:\Workspace\clients\dlc_montage\src")
sys.path.insert(0, r"d:\Workspace\clients\dlc_montage\src\dlc_montage")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dlc_montage.core.settings.dev")

import django
django.setup()

import gspread
from scripts.sync_emil_google_sheet import get_spreadsheet

# Цвета в формате Google Sheets API RGB (0.0 - 1.0)
COLOR_NAVY_900_RGB = {"red": 0.039, "green": 0.145, "blue": 0.251}  # #0A2540
COLOR_NAVY_700_RGB = {"red": 0.118, "green": 0.227, "blue": 0.373}  # #1E3A5F
COLOR_NAVY_100_RGB = {"red": 0.902, "green": 0.941, "blue": 0.980}  # #E6F0FA
COLOR_GREEN_RGB = {"red": 0.0, "green": 0.659, "blue": 0.420}       # #00A86B
COLOR_AMBER_RGB = {"red": 0.851, "green": 0.467, "blue": 0.024}     # #D97706
COLOR_WHITE_RGB = {"red": 1.0, "green": 1.0, "blue": 1.0}
COLOR_ZEBRA_RGB = {"red": 0.973, "green": 0.980, "blue": 0.988}     # #F8FAFC
COLOR_BORDER_RGB = {"red": 0.85, "green": 0.88, "blue": 0.91}
COLOR_GRAY_TEXT_RGB = {"red": 0.37, "green": 0.42, "blue": 0.52}


def format_all_emil_sheets():
    sh = get_spreadsheet()
    print(f"Applying styling and native dropdowns to: '{sh.title}'...")

    requests = []

    # 1. Форматирование сводного листа Übersicht Abnahme
    try:
        ws_sum = sh.worksheet("Übersicht Abnahme")
        sum_id = ws_sum.id
        sum_vals = ws_sum.get_all_values()

        # 1.1 Ширина колонок Übersicht (A–I: 9 колонок)
        sum_col_widths = [45, 200, 240, 220, 150, 180, 280, 90, 100]
        for col_idx, width in enumerate(sum_col_widths):
            requests.append({
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sum_id,
                        "dimension": "COLUMNS",
                        "startIndex": col_idx,
                        "endIndex": col_idx + 1
                    },
                    "properties": {"pixelSize": width},
                    "fields": "pixelSize"
                }
            })

        # 1.2 Высоты строк шапки Übersicht
        row_heights_sum = {0: 34, 1: 24, 3: 28, 4: 24}
        for r_idx, h in row_heights_sum.items():
            requests.append({
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sum_id,
                        "dimension": "ROWS",
                        "startIndex": r_idx,
                        "endIndex": r_idx + 1
                    },
                    "properties": {"pixelSize": h},
                    "fields": "pixelSize"
                }
            })

        # 1.3 Снятие старых объединений строк 1-5 и очистка лишних валидаций
        requests.append({
            "unmergeCells": {
                "range": {
                    "sheetId": sum_id,
                    "startRowIndex": 0,
                    "endRowIndex": 5,
                    "startColumnIndex": 0,
                    "endColumnIndex": 9
                }
            }
        })
        # Очищаем ВСЕ валидации с листа Übersicht перед чистым проставлением
        requests.append({
            "setDataValidation": {
                "range": {
                    "sheetId": sum_id,
                    "startRowIndex": 0,
                    "endRowIndex": 100,
                    "startColumnIndex": 0,
                    "endColumnIndex": 12
                }
            }
        })
        try:
            ws_sum.resize(rows=26, cols=10)
        except Exception:
            pass
        for m_start_r, m_end_r, m_start_c, m_end_c in [
            (0, 1, 0, 5),   # A1:E1 Название отчёта
            (0, 1, 5, 7),   # F1:G1 Auftragnehmer
            (0, 1, 7, 9),   # H1:I1 Bauleitung / Abnahme
            (1, 2, 0, 5),   # A2:E2 Подзаголовок
            (1, 2, 5, 7),   # F2:G2 Projekt
            (3, 4, 0, 9),   # A4:I4 Плашка Übersicht
            (4, 5, 0, 9),   # A5:I5 Статистика
        ]:
            requests.append({
                "mergeCells": {
                    "range": {
                        "sheetId": sum_id,
                        "startRowIndex": m_start_r,
                        "endRowIndex": m_end_r,
                        "startColumnIndex": m_start_c,
                        "endColumnIndex": m_end_c
                    },
                    "mergeType": "MERGE_ALL"
                }
            })

        # Стили шапки Übersicht
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sum_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 5},
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"foregroundColor": COLOR_NAVY_900_RGB, "bold": True, "fontSize": 14, "fontFamily": "Segoe UI"},
                        "verticalAlignment": "MIDDLE",
                        "padding": {"left": 4}
                    }
                },
                "fields": "userEnteredFormat(textFormat,verticalAlignment,padding)"
            }
        })
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sum_id, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 0, "endColumnIndex": 5},
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"foregroundColor": COLOR_NAVY_700_RGB, "bold": True, "fontSize": 10, "fontFamily": "Segoe UI"},
                        "verticalAlignment": "MIDDLE",
                        "padding": {"left": 4}
                    }
                },
                "fields": "userEnteredFormat(textFormat,verticalAlignment,padding)"
            }
        })
        # Карточка A4:I4
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sum_id, "startRowIndex": 3, "endRowIndex": 4, "startColumnIndex": 0, "endColumnIndex": 9},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": COLOR_NAVY_900_RGB,
                        "textFormat": {"foregroundColor": COLOR_WHITE_RGB, "bold": True, "fontSize": 11, "fontFamily": "Segoe UI"},
                        "verticalAlignment": "MIDDLE",
                        "padding": {"left": 10}
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment,padding)"
            }
        })
        # Карточка A5:I5
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sum_id, "startRowIndex": 4, "endRowIndex": 5, "startColumnIndex": 0, "endColumnIndex": 9},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": COLOR_NAVY_100_RGB,
                        "textFormat": {"foregroundColor": COLOR_NAVY_900_RGB, "bold": True, "fontSize": 10, "fontFamily": "Segoe UI"},
                        "verticalAlignment": "MIDDLE",
                        "padding": {"left": 10}
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment,padding)"
            }
        })

        # Обработка секций KW и таблиц данных на Übersicht
        for r_idx, r_val in enumerate(sum_vals):
            if not r_val:
                continue
            first_col = r_val[0].strip() if len(r_val) > 0 else ""
            if first_col.startswith("KW "):
                # Заголовок недели (KW 39 / KW 40)
                requests.append({
                    "mergeCells": {
                        "range": {"sheetId": sum_id, "startRowIndex": r_idx, "endRowIndex": r_idx + 1, "startColumnIndex": 0, "endColumnIndex": 9},
                        "mergeType": "MERGE_ALL"
                    }
                })
                requests.append({
                    "repeatCell": {
                        "range": {"sheetId": sum_id, "startRowIndex": r_idx, "endRowIndex": r_idx + 1, "startColumnIndex": 0, "endColumnIndex": 9},
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": COLOR_NAVY_700_RGB,
                                "textFormat": {"foregroundColor": COLOR_WHITE_RGB, "bold": True, "fontSize": 11, "fontFamily": "Segoe UI"},
                                "verticalAlignment": "MIDDLE",
                                "padding": {"left": 10}
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment,padding)"
                    }
                })
            elif first_col in ("Nr.", "Pos."):
                # Заголовок таблицы на Übersicht
                requests.append({
                    "repeatCell": {
                        "range": {"sheetId": sum_id, "startRowIndex": r_idx, "endRowIndex": r_idx + 1, "startColumnIndex": 0, "endColumnIndex": 9},
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": COLOR_NAVY_900_RGB,
                                "textFormat": {"foregroundColor": COLOR_WHITE_RGB, "bold": True, "fontSize": 10, "fontFamily": "Segoe UI"},
                                "horizontalAlignment": "CENTER",
                                "verticalAlignment": "MIDDLE",
                                "borders": {
                                    "top": {"style": "SOLID", "color": COLOR_BORDER_RGB},
                                    "bottom": {"style": "SOLID", "color": COLOR_BORDER_RGB},
                                    "left": {"style": "SOLID", "color": COLOR_BORDER_RGB},
                                    "right": {"style": "SOLID", "color": COLOR_BORDER_RGB},
                                }
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,borders)"
                    }
                })
                # B, C, D, G выравниваем по левому краю
                for left_col in (1, 2, 3, 6):
                    requests.append({
                        "repeatCell": {
                            "range": {"sheetId": sum_id, "startRowIndex": r_idx, "endRowIndex": r_idx + 1, "startColumnIndex": left_col, "endColumnIndex": left_col + 1},
                            "cell": {"userEnteredFormat": {"horizontalAlignment": "LEFT", "padding": {"left": 6}}},
                            "fields": "userEnteredFormat(horizontalAlignment,padding)"
                        }
                    })
            elif first_col.isdigit():
                # Строка объекта на Übersicht
                bg = COLOR_WHITE_RGB if int(first_col) % 2 == 1 else COLOR_ZEBRA_RGB
                requests.append({
                    "repeatCell": {
                        "range": {"sheetId": sum_id, "startRowIndex": r_idx, "endRowIndex": r_idx + 1, "startColumnIndex": 0, "endColumnIndex": 9},
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": bg,
                                "textFormat": {"fontSize": 10, "fontFamily": "Segoe UI"},
                                "verticalAlignment": "MIDDLE",
                                "borders": {
                                    "top": {"style": "SOLID", "color": COLOR_BORDER_RGB},
                                    "bottom": {"style": "SOLID", "color": COLOR_BORDER_RGB},
                                    "left": {"style": "SOLID", "color": COLOR_BORDER_RGB},
                                    "right": {"style": "SOLID", "color": COLOR_BORDER_RGB},
                                }
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment,borders)"
                    }
                })
                # Центрирование для Nr (0), Bau-Status (4), Abnahme (5), Freigabe (7), Datum (8)
                for c_center in (0, 4, 5, 7, 8):
                    requests.append({
                        "repeatCell": {
                            "range": {"sheetId": sum_id, "startRowIndex": r_idx, "endRowIndex": r_idx + 1, "startColumnIndex": c_center, "endColumnIndex": c_center + 1},
                            "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER"}},
                            "fields": "userEnteredFormat.horizontalAlignment"
                        }
                    })
                # Выпадающий список Abnahme-Status (Колонка F / index 5)
                requests.append({
                    "setDataValidation": {
                        "range": {"sheetId": sum_id, "startRowIndex": r_idx, "endRowIndex": r_idx + 1, "startColumnIndex": 5, "endColumnIndex": 6},
                        "rule": {
                            "condition": {
                                "type": "ONE_OF_LIST",
                                "values": [
                                    {"userEnteredValue": "Freigegeben"},
                                    {"userEnteredValue": "Nacharbeit erforderlich"},
                                    {"userEnteredValue": "In Prüfung"},
                                    {"userEnteredValue": "Nicht abgenommen"}
                                ]
                            },
                            "strict": True,
                            "showCustomUi": True
                        }
                    }
                })
                # Выпадающий список Freigabe (Колонка H / index 7)
                requests.append({
                    "setDataValidation": {
                        "range": {"sheetId": sum_id, "startRowIndex": r_idx, "endRowIndex": r_idx + 1, "startColumnIndex": 7, "endColumnIndex": 8},
                        "rule": {
                            "condition": {
                                "type": "ONE_OF_LIST",
                                "values": [
                                    {"userEnteredValue": "Ja"},
                                    {"userEnteredValue": "Nein"}
                                ]
                            },
                            "strict": True,
                            "showCustomUi": True
                        }
                    }
                })
    except Exception as exc:
        print(f"Notice: Übersicht Abnahme formatting error: {exc}")

    # 2. Форматирование каждого листа объекта (Standort)
    for ws in sh.worksheets():
        if ws.title == "Übersicht Abnahme":
            continue

        sheet_id = ws.id
        vals = ws.get_all_values()
        if len(vals) < 10:
            continue

        try:
            ws.resize(rows=len(vals) + 2, cols=8)
        except Exception:
            pass

        # Находим строку начала позиций (строка 7) и строку заголовка блока 2
        header_row_idx = 6  # 0-indexed -> Row 7
        end_items_row_idx = None
        block2_row_idx = None

        for idx, row in enumerate(vals):
            if len(row) > 0 and "2. ABNAHMEPROTOKOLL" in row[0]:
                block2_row_idx = idx
                end_items_row_idx = idx - 1  # предыдущая пустая строка
                break

        if not block2_row_idx:
            end_items_row_idx = min(len(vals), 35)
            block2_row_idx = end_items_row_idx

        # 2.1 Ширина колонок A–G (7 колонок)
        col_widths = [45, 340, 80, 70, 160, 180, 320]
        for col_idx, width in enumerate(col_widths):
            requests.append({
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": col_idx,
                        "endIndex": col_idx + 1
                    },
                    "properties": {"pixelSize": width},
                    "fields": "pixelSize"
                }
            })

        # 2.2 Высоты строк шапки и секций
        row_heights = {
            0: 34,  # Row 1: Title
            1: 24,  # Row 2: Metadata 1
            2: 24,  # Row 3: Metadata 2
            3: 24,  # Row 4: Metadata 3
            4: 12,  # Row 5: Spacer
            5: 28,  # Row 6: Section 1 Banner
            6: 26,  # Row 7: Table Headers
        }
        for r_idx, h in row_heights.items():
            requests.append({
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": r_idx,
                        "endIndex": r_idx + 1
                    },
                    "properties": {"pixelSize": h},
                    "fields": "pixelSize"
                }
            })

        # 2.3 Снятие старых объединений строк 1-5 (A1:G5) для предотвращения наложений
        requests.append({
            "unmergeCells": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 5,
                    "startColumnIndex": 0,
                    "endColumnIndex": 7
                }
            }
        })

        # 2.4 Чистое объединение шапки (Строки 1–4)
        # Row 1: A1:E1 (Title), F1:G1 (Return link)
        # Rows 2-4: A:D (Left card info: 535px), E:G (Right card info: 660px)
        clean_merges = [
            (0, 1, 0, 5),  # A1:E1 Title
            (0, 1, 5, 7),  # F1:G1 Return Link
            (1, 2, 0, 4),  # A2:D2 Standort
            (1, 2, 4, 7),  # E2:G2 Anlage (Gruppe)
            (2, 3, 0, 4),  # A3:D3 Adresse
            (2, 3, 4, 7),  # E3:G3 Bau-Status
            (3, 4, 0, 4),  # A4:D4 Abrechnungszeitraum
            (3, 4, 4, 7),  # E4:G4 Prüfender Bauleiter
        ]
        for m_start_r, m_end_r, m_start_c, m_end_c in clean_merges:
            requests.append({
                "mergeCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": m_start_r,
                        "endRowIndex": m_end_r,
                        "startColumnIndex": m_start_c,
                        "endColumnIndex": m_end_c
                    },
                    "mergeType": "MERGE_ALL"
                }
            })

        # 2.5 Стили строки 1 (Заголовок и ссылка назад)
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 5},
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"foregroundColor": COLOR_NAVY_900_RGB, "bold": True, "fontSize": 13, "fontFamily": "Segoe UI"},
                        "verticalAlignment": "MIDDLE",
                        "horizontalAlignment": "LEFT",
                        "padding": {"left": 4}
                    }
                },
                "fields": "userEnteredFormat(textFormat,verticalAlignment,horizontalAlignment,padding)"
            }
        })
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 5, "endColumnIndex": 7},
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"foregroundColor": COLOR_GREEN_RGB, "bold": True, "fontSize": 10, "fontFamily": "Segoe UI", "underline": True},
                        "verticalAlignment": "MIDDLE",
                        "horizontalAlignment": "RIGHT",
                        "padding": {"right": 8}
                    }
                },
                "fields": "userEnteredFormat(textFormat,verticalAlignment,horizontalAlignment,padding)"
            }
        })

        # 2.6 Стили карточки метаданных (Строки 2–4: A2:G4)
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 4, "startColumnIndex": 0, "endColumnIndex": 7},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": COLOR_ZEBRA_RGB,
                        "verticalAlignment": "MIDDLE",
                        "borders": {
                            "top": {"style": "SOLID", "color": COLOR_BORDER_RGB},
                            "bottom": {"style": "SOLID", "color": COLOR_BORDER_RGB},
                            "left": {"style": "SOLID", "color": COLOR_BORDER_RGB},
                            "right": {"style": "SOLID", "color": COLOR_BORDER_RGB},
                        }
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,verticalAlignment,borders)"
            }
        })
        # Левая колонка карточки (A2:D4)
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 0, "endColumnIndex": 4},
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"foregroundColor": COLOR_NAVY_900_RGB, "bold": True, "fontSize": 10, "fontFamily": "Segoe UI"},
                        "horizontalAlignment": "LEFT",
                        "padding": {"left": 10}
                    }
                },
                "fields": "userEnteredFormat(textFormat,horizontalAlignment,padding)"
            }
        })
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 2, "endRowIndex": 4, "startColumnIndex": 0, "endColumnIndex": 4},
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"foregroundColor": COLOR_GRAY_TEXT_RGB, "fontSize": 10, "fontFamily": "Segoe UI"},
                        "horizontalAlignment": "LEFT",
                        "padding": {"left": 10}
                    }
                },
                "fields": "userEnteredFormat(textFormat,horizontalAlignment,padding)"
            }
        })
        # Правая колонка карточки (E2:G4)
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 4, "endColumnIndex": 7},
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"foregroundColor": COLOR_NAVY_700_RGB, "fontSize": 10, "fontFamily": "Segoe UI"},
                        "horizontalAlignment": "LEFT",
                        "padding": {"left": 10}
                    }
                },
                "fields": "userEnteredFormat(textFormat,horizontalAlignment,padding)"
            }
        })
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 2, "endRowIndex": 3, "startColumnIndex": 4, "endColumnIndex": 7},
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"foregroundColor": COLOR_GREEN_RGB, "bold": True, "fontSize": 10, "fontFamily": "Segoe UI"},
                        "horizontalAlignment": "LEFT",
                        "padding": {"left": 10}
                    }
                },
                "fields": "userEnteredFormat(textFormat,horizontalAlignment,padding)"
            }
        })
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 3, "endRowIndex": 4, "startColumnIndex": 4, "endColumnIndex": 7},
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"foregroundColor": COLOR_NAVY_900_RGB, "bold": True, "fontSize": 10, "fontFamily": "Segoe UI"},
                        "horizontalAlignment": "LEFT",
                        "padding": {"left": 10}
                    }
                },
                "fields": "userEnteredFormat(textFormat,horizontalAlignment,padding)"
            }
        })

        # 2.7 Плашка Блока 1 (Строка 6: A6:G6)
        requests.append({
            "mergeCells": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 5,
                    "endRowIndex": 6,
                    "startColumnIndex": 0,
                    "endColumnIndex": 7
                },
                "mergeType": "MERGE_ALL"
            }
        })
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 5,
                    "endRowIndex": 6,
                    "startColumnIndex": 0,
                    "endColumnIndex": 7
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": COLOR_NAVY_900_RGB,
                        "textFormat": {"foregroundColor": COLOR_WHITE_RGB, "bold": True, "fontSize": 11, "fontFamily": "Segoe UI"},
                        "verticalAlignment": "MIDDLE",
                        "padding": {"left": 10}
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment,padding)"
            }
        })

        # 2.8 Стили заголовков таблицы A7:G7 (Строка 7)
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 6,
                    "endRowIndex": 7,
                    "startColumnIndex": 0,
                    "endColumnIndex": 7
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": COLOR_NAVY_700_RGB,
                        "textFormat": {"foregroundColor": COLOR_WHITE_RGB, "bold": True, "fontSize": 10, "fontFamily": "Segoe UI"},
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                        "borders": {
                            "top": {"style": "SOLID", "color": COLOR_BORDER_RGB},
                            "bottom": {"style": "SOLID", "color": COLOR_BORDER_RGB},
                            "left": {"style": "SOLID", "color": COLOR_BORDER_RGB},
                            "right": {"style": "SOLID", "color": COLOR_BORDER_RGB},
                        }
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,borders)"
            }
        })
        for col_align in (1, 6):
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 6,
                        "endRowIndex": 7,
                        "startColumnIndex": col_align,
                        "endColumnIndex": col_align + 1
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "horizontalAlignment": "LEFT",
                            "padding": {"left": 8}
                        }
                    },
                    "fields": "userEnteredFormat(horizontalAlignment,padding)"
                }
            })

        # 2.9 Сетка данных строк (от 8 до end_items_row_idx)
        for r_i in range(7, end_items_row_idx):
            bg_col = COLOR_WHITE_RGB if r_i % 2 == 1 else COLOR_ZEBRA_RGB
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": r_i,
                        "endRowIndex": r_i + 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": 7
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": bg_col,
                            "textFormat": {"fontSize": 10, "fontFamily": "Segoe UI"},
                            "verticalAlignment": "MIDDLE",
                            "borders": {
                                "top": {"style": "SOLID", "color": COLOR_BORDER_RGB},
                                "bottom": {"style": "SOLID", "color": COLOR_BORDER_RGB},
                                "left": {"style": "SOLID", "color": COLOR_BORDER_RGB},
                                "right": {"style": "SOLID", "color": COLOR_BORDER_RGB},
                            }
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment,borders)"
                }
            })
            # Позиция 0 (центр), 1 (название - слева), 2 (центр), 3 (число - справа), 4 (статус DLC - центр, зеленый), 5 (центр), 6 (слева)
            requests.append({
                "repeatCell": {
                    "range": {"sheetId": sheet_id, "startRowIndex": r_i, "endRowIndex": r_i + 1, "startColumnIndex": 0, "endColumnIndex": 1},
                    "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER"}},
                    "fields": "userEnteredFormat.horizontalAlignment"
                }
            })
            requests.append({
                "repeatCell": {
                    "range": {"sheetId": sheet_id, "startRowIndex": r_i, "endRowIndex": r_i + 1, "startColumnIndex": 1, "endColumnIndex": 2},
                    "cell": {"userEnteredFormat": {"horizontalAlignment": "LEFT", "padding": {"left": 6}}},
                    "fields": "userEnteredFormat(horizontalAlignment,padding)"
                }
            })
            requests.append({
                "repeatCell": {
                    "range": {"sheetId": sheet_id, "startRowIndex": r_i, "endRowIndex": r_i + 1, "startColumnIndex": 2, "endColumnIndex": 3},
                    "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER"}},
                    "fields": "userEnteredFormat.horizontalAlignment"
                }
            })
            requests.append({
                "repeatCell": {
                    "range": {"sheetId": sheet_id, "startRowIndex": r_i, "endRowIndex": r_i + 1, "startColumnIndex": 3, "endColumnIndex": 4},
                    "cell": {"userEnteredFormat": {"horizontalAlignment": "RIGHT", "padding": {"right": 6}}},
                    "fields": "userEnteredFormat(horizontalAlignment,padding)"
                }
            })
            requests.append({
                "repeatCell": {
                    "range": {"sheetId": sheet_id, "startRowIndex": r_i, "endRowIndex": r_i + 1, "startColumnIndex": 4, "endColumnIndex": 5},
                    "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER", "textFormat": {"bold": True, "foregroundColor": COLOR_GREEN_RGB}}},
                    "fields": "userEnteredFormat(horizontalAlignment,textFormat)"
                }
            })
            requests.append({
                "repeatCell": {
                    "range": {"sheetId": sheet_id, "startRowIndex": r_i, "endRowIndex": r_i + 1, "startColumnIndex": 6, "endColumnIndex": 7},
                    "cell": {"userEnteredFormat": {"horizontalAlignment": "LEFT", "padding": {"left": 8}}},
                    "fields": "userEnteredFormat(horizontalAlignment,padding)"
                }
            })

        # 2.10 ВЫПАДАЮЩИЙ СПИСОК (Data Validation) на колонку F (Abnahme Emil)
        requests.append({
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 7,
                    "endRowIndex": end_items_row_idx,
                    "startColumnIndex": 5,
                    "endColumnIndex": 6
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_LIST",
                        "values": [
                            {"userEnteredValue": "✓ i.O."},
                            {"userEnteredValue": "✗ Nicht i.O."},
                            {"userEnteredValue": "—"}
                        ]
                    },
                    "inputMessage": "Wähle: ✓ i.O. (in Ordnung) oder ✗ Nicht i.O. (Mangel)",
                    "strict": False,
                    "showCustomUi": True
                }
            }
        })

        # 2.11 Оформление Блока 2 (Abnahmeprotokoll)
        if block2_row_idx < len(vals):
            # Плашка блока 2 (A:G)
            requests.append({
                "mergeCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": block2_row_idx,
                        "endRowIndex": block2_row_idx + 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": 7
                    },
                    "mergeType": "MERGE_ALL"
                }
            })
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": block2_row_idx,
                        "endRowIndex": block2_row_idx + 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": 7
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": COLOR_NAVY_900_RGB,
                            "textFormat": {"foregroundColor": COLOR_WHITE_RGB, "bold": True, "fontSize": 11, "fontFamily": "Segoe UI"},
                            "verticalAlignment": "MIDDLE",
                            "padding": {"left": 10}
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment,padding)"
                }
            })

            # Выпадающий список общего решения (строка block2_row_idx + 1, колонка B)
            requests.append({
                "setDataValidation": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": block2_row_idx + 1,
                        "endRowIndex": block2_row_idx + 2,
                        "startColumnIndex": 1,
                        "endColumnIndex": 2
                    },
                    "rule": {
                        "condition": {
                            "type": "ONE_OF_LIST",
                            "values": [
                                {"userEnteredValue": "Freigegeben"},
                                {"userEnteredValue": "Nacharbeit erforderlich"},
                                {"userEnteredValue": "In Prüfung"},
                                {"userEnteredValue": "Nicht abgenommen"}
                            ]
                        },
                        "strict": True,
                        "showCustomUi": True
                    }
                }
            })
            # Выпадающий список Freigabe zur Auszahlung (колонка E)
            requests.append({
                "setDataValidation": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": block2_row_idx + 1,
                        "endRowIndex": block2_row_idx + 2,
                        "startColumnIndex": 4,
                        "endColumnIndex": 5
                    },
                    "rule": {
                        "condition": {
                            "type": "ONE_OF_LIST",
                            "values": [
                                {"userEnteredValue": "Ja"},
                                {"userEnteredValue": "Nein"}
                            ]
                        },
                        "strict": True,
                        "showCustomUi": True
                    }
                }
            })

            # Объединение строк замечаний (Mängelliste B:G для строк 1, 2, 3, 4)
            for m_offset in range(7, 11):
                m_row = block2_row_idx + m_offset
                if m_row < len(vals):
                    requests.append({
                        "mergeCells": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": m_row,
                                "endRowIndex": m_row + 1,
                                "startColumnIndex": 1,
                                "endColumnIndex": 7
                            },
                            "mergeType": "MERGE_ALL"
                        }
                    })
                    requests.append({
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": m_row,
                                "endRowIndex": m_row + 1,
                                "startColumnIndex": 1,
                                "endColumnIndex": 7
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "borders": {
                                        "bottom": {"style": "SOLID", "color": COLOR_BORDER_RGB}
                                    },
                                    "padding": {"left": 6}
                                }
                            },
                            "fields": "userEnteredFormat(borders,padding)"
                        }
                    })

    # Отправляем пакетом в Google Sheets API
    print(f"Sending {len(requests)} formatting updates to Google Sheets...")
    chunk_size = 80
    for i in range(0, len(requests), chunk_size):
        chunk = requests[i:i + chunk_size]
        sh.batch_update({"requests": chunk})
        print(f"  Applied {min(i + chunk_size, len(requests))}/{len(requests)} updates...")

    print("All site sheets and Übersicht formatted with professional styling and native dropdowns!")


if __name__ == "__main__":
    format_all_emil_sheets()
