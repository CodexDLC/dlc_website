"""Use the existing green completion style consistently on the Chef overview."""

import copy
import json
import os
from datetime import datetime
from pathlib import Path

import sync_google_sheets as sync

book = sync.get_spreadsheet()
assert book.id == os.environ["GOOGLE_SHEET_ID"], "Unexpected spreadsheet target"
metadata = book.fetch_sheet_metadata(params={"includeGridData": "true", "ranges": "'Übersicht'!A1:J100"})
sheet = next(s for s in metadata["sheets"] if s["properties"]["title"] == "Übersicht")
grid = sheet["data"][0]["rowData"]
sites = []
for index, row in enumerate(grid):
    cells = row.get("values", [])
    if len(cells) > 4 and cells[4].get("formattedValue") == "Fertiggestellt":
        sites.append((index, cells[4]))
styles = {json.dumps(c.get("userEnteredFormat", {}), sort_keys=True): 0 for _, c in sites}
for _, c in sites:
    styles[json.dumps(c.get("userEnteredFormat", {}), sort_keys=True)] += 1
print(json.dumps({"rows": len(sites), "styles": styles}, ensure_ascii=False))
green = []
for _, cell in sites:
    fmt = cell.get("userEnteredFormat", {})
    text = fmt.get("textFormat", {})
    color = text.get("foregroundColorStyle", {}).get("rgbColor", text.get("foregroundColor", {}))
    if color.get("green", 0) > color.get("red", 0) + 0.15 and color.get("green", 0) > color.get("blue", 0):
        green.append(fmt)
assert green, "No existing green status style found"
template = copy.deepcopy(green[0])
out = Path("outputs/chef-completion-overview")
(out / f"status-style-before-{datetime.now():%Y%m%d-%H%M%S}.json").write_text(
    json.dumps(metadata, ensure_ascii=False), encoding="utf8"
)
gid = sheet["properties"]["sheetId"]
requests = []
for index, _ in sites:
    requests.append(
        {
            "repeatCell": {
                "range": {
                    "sheetId": gid,
                    "startRowIndex": index,
                    "endRowIndex": index + 1,
                    "startColumnIndex": 4,
                    "endColumnIndex": 5,
                },
                "cell": {"userEnteredFormat": template},
                "fields": "userEnteredFormat",
            }
        }
    )
book.batch_update({"requests": requests})
after = book.fetch_sheet_metadata(params={"includeGridData": "true", "ranges": "'Übersicht'!A1:J100"})
updated = next(s for s in after["sheets"] if s["properties"]["sheetId"] == gid)["data"][0]["rowData"]
for index, cell in sites:
    current = updated[index]["values"][4]
    assert current["userEnteredValue"] == cell["userEnteredValue"]
    assert current["userEnteredFormat"] == template
print(f"Verified uniform status formatting on {len(sites)} sites.")
