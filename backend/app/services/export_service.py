import io
from typing import List, Dict, Any

# NOTE: pandas (+openpyxl) is imported lazily inside the methods below: it
# costs seconds at startup and is only needed for explicit CSV/Excel exports.


class ExportService:
    @staticmethod
    def leads_to_dataframe(leads: List[Dict[str, Any]]) -> "pd.DataFrame":
        formatted = []
        for l in leads:
            formatted.append({
                "ID": l.get("id"),
                "İşletme Adı": l.get("name"),
                "Kategori": l.get("category"),
                "Telefon (E.164)": l.get("phone_e164"),
                "Telefon (Ham)": l.get("phone"),
                "Mobil Mi": "Evet" if l.get("is_mobile") else "Hayır",
                "WhatsApp Uygun": "Evet" if l.get("is_whatsapp_eligible") else "Hayır",
                "Şehir": l.get("city"),
                "İlçe": l.get("district"),
                "Adres": l.get("address"),
                "Puan": l.get("rating"),
                "Yorum Sayısı": l.get("reviews_count"),
                "Web Sitesi": l.get("website"),
                "Arama Kelimesi": l.get("search_keyword"),
                "Durum": l.get("status"),
                "Kayıt Tarihi": str(l.get("created_at")),
            })
        import pandas as pd

        return pd.DataFrame(formatted)

    @classmethod
    def export_csv(cls, leads: List[Dict[str, Any]]) -> bytes:
        df = cls.leads_to_dataframe(leads)
        output = io.StringIO()
        df.to_csv(output, index=False, encoding="utf-8-sig")
        return output.getvalue().encode("utf-8-sig")

    @classmethod
    def export_excel(cls, leads: List[Dict[str, Any]]) -> bytes:
        import pandas as pd

        df = cls.leads_to_dataframe(leads)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Leads")
        output.seek(0)
        return output.getvalue()
