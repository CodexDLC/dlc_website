import os, sys
sys.path.insert(0, os.path.abspath("src/dlc_montage"))
os.environ["DJANGO_SETTINGS_MODULE"] = "core.settings.dev"
import django
django.setup()
from features.mbg_reports.selectors import site_position_summary_map

for site_id in [27, 14]:
    print(f"\n================ SITE {site_id} ================")
    summary = site_position_summary_map([site_id])[site_id]
    for r in summary[:12]:
        print(f"  {r.get('title', r.get('description')):<50} | qty: {r.get('quantity')} | price: {r.get('unit_price')} | amount: {r.get('amount')}")
