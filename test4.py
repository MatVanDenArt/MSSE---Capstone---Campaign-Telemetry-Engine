from app.services.analytics import get_asset_impact_matrix
import pprint

assets = get_asset_impact_matrix("CMP_LIVE_DECARBONIZATION_25_26", 90)
for a in assets:
    if "Report 4" in a.get("formatted_name", "") or "Promo 4" in a.get("formatted_name", ""):
        pprint.pprint(a)
