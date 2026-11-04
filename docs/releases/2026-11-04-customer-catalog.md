# Kundenpositionen und Abnahme

Die Kundenabnahme verwendet die 21 Positionsnummern des Leistungsaufmaßes mit Mengen einschließlich Null. Preise und interne Arbeitszeiten bleiben ausgeblendet. „Alles OK“ wählt alle Positionen aus; das Speichern erfolgt weiterhin ausdrücklich. Nur abgeschlossene Standorte können zur Abnahme vorgelegt werden. Frühere Entscheidungen bleiben erhalten.

Interne Abrechnungen ordnen physische Arbeiten den Kundenpositionen zu. NH-Montage und Anschluss sind getrennte Einheiten. Ein zusätzliches Kabel zur Verlängerung einer Bestandsleitung wird ausdrücklich als zusätzlicher, zur Bestätigung vorgelegter Umfang bezeichnet. Mehrere Liefertage am selben Standort vervielfachen die Lieferpauschale nicht. Ungeklärte Mengen bleiben manuell; Tagesberichte und tatsächlich erfasste Stunden werden nicht umgeschrieben.

## Prüfung und Einführung

Das Release wird aus einem isolierten Git-Stand geprüft und gebaut. Die bereits produktiven E-Mail-Zugänge und die tägliche Zusammenfassung sind enthalten. Unabhängige, nicht fertiggestellte Änderungen an Rechnungsimport und Google-Berichten gehören nicht zu diesem Release.

Vor den additiven Migrationen werden Web und Foto-Worker kurz angehalten und eine PostgreSQL-Sicherung geprüft. Der neue boolesche Zeitnachweis-Marker erhält auch einen Datenbankstandard, damit der vorherige Code bei einem Rückwechsel weiter schreiben kann. Der Rückwechsel verwendet vorherige Runtime-Images und statische Dateien; die neuen Tabellen werden nicht durch Rückwärtsmigration gelöscht.

Offene, bisher noch nicht entschiedene Prüfungen werden ausdrücklich mit dem neuen Katalog erneut vorgelegt. Bereits getroffene Kundenentscheidungen und historische Berichtsversionen bleiben unverändert. E-Mail-Versand ist kein Bestandteil des manuellen Release-Schritts.
