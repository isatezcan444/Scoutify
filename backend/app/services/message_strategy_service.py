"""
Category-Aware Message Strategy Engine.
Generates highly tailored, professional B2B outreach messages based on target category,
user offer, business goal, and lead context without fake personalization or risk leakage.
"""
import logging
from typing import Optional, Dict, Any, Tuple
from backend.app.schemas.smart_outreach import (
    BusinessGoal,
    MessageRecommendationRequest,
    MessageRecommendationResponse
)
from backend.app.data.turkey_locations import normalize_turkish

logger = logging.getLogger(__name__)


class MessageStrategyService:
    """
    Produces tailored outreach copy based on Category Context + Offer + Goal.
    """

    @classmethod
    def generate_recommendation(
        cls,
        lead_id: int,
        lead_name: str,
        target_category: str,
        offer_title: str,
        offer_description: Optional[str] = None,
        business_goal: BusinessGoal = BusinessGoal.DISCOVERY
    ) -> MessageRecommendationResponse:
        norm_cat = normalize_turkish(target_category.lower())
        norm_offer = normalize_turkish(offer_title.lower())

        has_valid_name = bool(lead_name and not lead_name.lower().startswith("lead #") and lead_name.strip() != "")
        clean_lead_name = lead_name.strip() if has_valid_name else ""
        greeting = f"Merhaba {clean_lead_name}," if clean_lead_name else "Merhaba,"
        alt_greeting = f"İyi günler {clean_lead_name}," if clean_lead_name else "İyi günler,"

        strategy_summary = ""
        recommended_message = ""
        alternative_message = ""

        # =========================================================================
        # 1. VIP TRANSFER / ULAŞIM KATEGORİ ÖZELİ
        # =========================================================================
        if any(w in norm_offer for w in ["transfer", "vito", "soforlu", "vip"]):
            if any(w in norm_cat for w in ["otel", "hotel", "konaklama", "resort"]):
                strategy_summary = "Otel misafirleri ve havalimanı transfer ihtiyaçlarına odaklı yaklaşım."
                if business_goal == BusinessGoal.DISCOVERY:
                    recommended_message = (
                        f"{greeting} otelinizde konaklayan misafirleriniz ve havalimanı VIP transfer "
                        f"operasyonları için dışarıdan profesyonel araç çözümü kullanıyor musunuz? "
                        f"Uygun olursanız VIP araç filomuz ve hizmet detaylarımız hakkında kısa bilgi paylaşabiliriz."
                    )
                    alternative_message = (
                        f"{alt_greeting} otel misafirlerinizin özel transfer ve havalimanı karşılama "
                        f"taleplerinde birlikte çalışabileceğimiz bir iş birliği modeli sunmak isteriz. Kısa bir bilgi iletebilir miyiz?"
                    )
                elif business_goal == BusinessGoal.INTRO:
                    recommended_message = (
                        f"{greeting} otel misafirlerinize yönelik VIP araç ve havalimanı karşılama "
                        f"hizmetlerimizi içeren kurumsal kataloğumuzu incelemek isterseniz kısa bir özet paylaşabiliriz."
                    )
                    alternative_message = (
                        f"{alt_greeting} oteliniz için hazırladığımız özel transfer çözümleri özetini iletmek isteriz."
                    )
                elif business_goal == BusinessGoal.OFFER:
                    recommended_message = (
                        f"{greeting} otelinizin transfer operasyonları için avantajlı kurumsal fiyat teklifimizi "
                        f"ve araç filomuzu paylaşmak isteriz. Uygun bir zamanınızda iletebilir miyiz?"
                    )
                    alternative_message = (
                        f"{alt_greeting} sezonluk otel transfer iş birliği teklifimizi incelemeniz için paylaşabiliriz."
                    )
                else:
                    recommended_message = (
                        f"{greeting} VIP transfer hizmetimizle ilgili detayları ve otelinize özel "
                        f"avantajlarımızı görüşmek üzere bu hafta kısa bir telefon görüşmesi organize edebilir miyiz?"
                    )
                    alternative_message = (
                        f"{alt_greeting} kurumsal transfer iş birliğimiz hakkında kısa bir değerlendirme görüşmesi planlayabilir miyiz?"
                    )

            elif any(w in norm_cat for w in ["kurumsal", "sirket", "holding", "plaza", "ofis"]):
                strategy_summary = "Üst düzey yönetici ve kurumsal heyet taşımacılığına odaklı yaklaşım."
                recommended_message = (
                    f"{greeting} şirketinizde üst düzey yöneticileriniz ve iş ortaklarınız için "
                    f"şehir içi / havalimanı VIP transfer süreçlerini siz mi koordine ediyorsunuz? "
                    f"Uygun olursa kurumsal araç çözümlerimiz hakkında kısa bir özet iletebiliriz."
                )
                alternative_message = (
                    f"{alt_greeting} kurumsal misafir ve yönetici transferleriniz için güvenli, "
                    f"konforlu VIP araç çözümlerimizi paylaşmak isteriz."
                )

            elif any(w in norm_cat for w in ["turizm", "acente", "seyahat"]):
                strategy_summary = "Tur ve acente transfer operasyonlarında iş birliği yaklaşımı."
                recommended_message = (
                    f"{greeting} acentenizin tur, karşılama ve özel transfer operasyonlarında "
                    f"VIP araç tedariği ihtiyacı oluyor mu? İş birliği imkanlarımız hakkında kısa bilgi paylaşmak isteriz."
                )
                alternative_message = (
                    f"{alt_greeting} acente transfer operasyonlarında birlikte çalışabileceğimiz kurumsal filo avantajlarımızı iletmek isteriz."
                )

        # =========================================================================
        # 2. YAZILIM / DİJİTAL ÇÖZÜMLER KATEGORİ ÖZELİ
        # =========================================================================
        elif any(w in norm_offer for w in ["yazilim", "dijital", "crm", "erp", "otomasyon", "saas", "web"]):
            if any(w in norm_cat for w in ["mimarlik", "muhendislik", "proje", "tasarim"]):
                strategy_summary = "Mimarlık ve proje süreçlerinde iş akışı ve dijitalleşme odaklı yaklaşım."
                if business_goal == BusinessGoal.DISCOVERY:
                    recommended_message = (
                        f"{greeting} mimarlık ve proje süreçlerinizde iş akışlarını ve müşteri takibini kolaylaştıran "
                        f"{offer_title} konusunda bir dış çözüm ortağı ihtiyacınız bulunuyor mu? "
                        f"Uygun olursanız kısa bilgi paylaşabiliriz."
                    )
                    alternative_message = (
                        f"{alt_greeting} mimarlık ofislerinin operasyonel verimliliğini artıran {offer_title} "
                        f"çözümümüz hakkında kısa bir özet iletmek isteriz."
                    )
                else:
                    recommended_message = (
                        f"{greeting} mimarlık ofisinize özel {offer_title} çözüm detaylarını ve sağlayacağı verimlilik "
                        f"avantajlarını paylaşmak isteriz. Uygun bir zamanınızda kısa bilgi iletebilir miyiz?"
                    )
                    alternative_message = (
                        f"{alt_greeting} ofisinizin iş süreçlerine yönelik hazırladığımız dijitalleşme özetini incelemeniz için sunabiliriz."
                    )

            elif any(w in norm_cat for w in ["guzellik", "estetik", "klinik", "kuafor"]):
                strategy_summary = "Danışan randevu yönetimi ve operasyonel dijitalleşme yaklaşımı."
                recommended_message = (
                    f"{greeting} merkezinizde danışan randevu takibi ve operasyonel süreçlerde {offer_title} "
                    f"konusunda bir çözüm ortağı arayışınız var mı? Uygun olursanız kısa bir özet paylaşabiliriz."
                )
                alternative_message = (
                    f"{alt_greeting} danışan memnuniyetini ve randevu devamlılığını artıran {offer_title} "
                    f"çözümümüzü incelemeniz için iletmek isteriz."
                )

            elif any(w in norm_cat for w in ["perakende", "ticaret", "e-ticaret", "magaza"]):
                strategy_summary = "Perakende/e-ticaret satış ve operasyon optimizasyonu yaklaşımı."
                recommended_message = (
                    f"{greeting} perakende ve ticari operasyonlarınızda sipariş ve süreç yönetimini hızlandıran "
                    f"{offer_title} konusunda dış tedarikçi ihtiyacınız bulunuyor mu? Uygun olursanız kısa bilgi aktarabiliriz."
                )
                alternative_message = (
                    f"{alt_greeting} satış ve operasyon verimliliğinizi artıracak {offer_title} "
                    f"hizmetimiz hakkında kısa bir özet paylaşabiliriz."
                )

        # =========================================================================
        # 3. DENTAL / DİŞ KLİNİĞİ ÖZELİ
        # =========================================================================
        elif any(w in norm_offer for w in ["dental", "dis", "implant", "ortodonti"]):
            strategy_summary = "Klinik tedarik sürecine ve hekim memnuniyetine odaklı yaklaşım."
            if business_goal == BusinessGoal.DISCOVERY:
                recommended_message = (
                    f"{greeting} kliniğinizde dental sarf ve implant ürünlerinin tedarik sürecini "
                    f"siz mi yönetiyorsunuz? Uygun olursa hekimlerimize özel ürün grubumuz ve güncel fiyat kataloğumuz "
                    f"hakkında kısa bilgi iletebiliriz."
                )
                alternative_message = (
                    f"{alt_greeting} kliniğinizin aylık dental sarf malzeme tedariğinde maliyet avantajı "
                    f"sağlayan ürün listemizi incelemeniz için paylaşabilir miyiz?"
                )
            elif business_goal == BusinessGoal.OFFER:
                recommended_message = (
                    f"{greeting} kliniğinize özel hazırladığımız avantajlı dental sarf malzeme "
                    f"teklifimizi ve ürün numune listemizi iletmek isteriz. Uygun bir zamanınızda inceleyebilir misiniz?"
                )
                alternative_message = (
                    f"{alt_greeting} kliniğiniz için özel fiyatlı dental ürün teklifimizi iletebiliriz."
                )

        # =========================================================================
        # 4. TEMİZLİK & HİJYEN KATEGORİ ÖZELİ
        # =========================================================================
        elif any(w in norm_offer for w in ["temizlik", "hijyen", "dezenfeksiyon", "tesis"]):
            if any(w in norm_cat for w in ["otel", "hotel", "resort"]):
                strategy_summary = "Otel oda hijyeni ve periyodik temizlik sarf/hizmet tedariği yaklaşımı."
                recommended_message = (
                    f"{greeting} otelinizde oda hijyeni ve periyodik derin temizlik süreçlerinde "
                    f"dış tedarikçi/hizmet ortağı ile çalışıyor musunuz? {offer_title} tarafında kurumsal çözümlerimizi paylaşmak isteriz."
                )
                alternative_message = (
                    f"{alt_greeting} otel misafirlerinizin hijyen standartlarını güvenceye alan profesyonel {offer_title} çözümlerimizi iletebiliriz."
                )
            elif any(w in norm_cat for w in ["okul", "kres", "kolej"]):
                strategy_summary = "Öğrenci hijyeni ve kurumsal temizlik standartları yaklaşımı."
                recommended_message = (
                    f"{greeting} kurumunuzda öğrenci sağlığı ve periyodik hijyen süreçleri için "
                    f"{offer_title} konusunda kurumsal hizmet detaylarımızı paylaşabilir miyiz?"
                )
                alternative_message = (
                    f"{alt_greeting} eğitim kurumlarına özel hijyen standartlarımız ve {offer_title} paketimiz hakkında bilgi sunmak isteriz."
                )

        # =========================================================================
        # 5. GENEL B2B STRATEJİ ŞABLONU (DİĞER TÜM SEKTÖRLER)
        # =========================================================================
        if not recommended_message:
            strategy_summary = f"{target_category} sektörü için {business_goal.value} stratejisi."

            if business_goal == BusinessGoal.DISCOVERY:
                recommended_message = (
                    f"{greeting} {target_category} alanındaki faaliyetlerinizde {offer_title} "
                    f"konusunda dış tedarikçi/çözüm ortağı ihtiyacınız bulunuyor mu? "
                    f"Uygun olursanız kısa bilgi paylaşabiliriz."
                )
                alternative_message = (
                    f"{alt_greeting} {offer_title} alanındaki kurumsal çözümlerimiz hakkında "
                    f"kısa bir özet iletmek isteriz."
                )
            elif business_goal == BusinessGoal.INTRO:
                recommended_message = (
                    f"{greeting} {offer_title} kapsamında işletmelere sunduğumuz çözümleri "
                    f"incelemek isterseniz kısa bir tanıtım dokümanı paylaşabiliriz."
                )
                alternative_message = (
                    f"{alt_greeting} işletmenizin faaliyet alanına yönelik {offer_title} tanıtım özetimizi paylaşabiliriz."
                )
            elif business_goal == BusinessGoal.OFFER:
                recommended_message = (
                    f"{greeting} {offer_title} hizmetimizle ilgili detayları ve işletmenize özel "
                    f"avantajlı teklifimizi iletmek isteriz. Uygun bir zamanınızda paylaşabilir miyiz?"
                )
                alternative_message = (
                    f"{alt_greeting} işletmeniz için hazırladığımız özel {offer_title} teklifini değerlendirmeniz için iletebiliriz."
                )
            elif business_goal == BusinessGoal.FOLLOW_UP:
                recommended_message = (
                    f"{greeting} {offer_title} konulu önceki bilgilendirmemizle ilgili kısa bir "
                    f"durum kontrolü yapmak istedim. Değerlendirme fırsatınız oldu mu?"
                )
                alternative_message = (
                    f"{alt_greeting} önceki mesajımız hakkında müsaitliğinizi kontrol etmek istedim."
                )
            elif business_goal == BusinessGoal.MEETING:
                recommended_message = (
                    f"{greeting} {offer_title} detaylarını netleştirmek ve işletmenize en uygun "
                    f"çözümü planlamak adına bu hafta kısa bir telefon görüşmesi organize edebilir miyiz?"
                )
                alternative_message = (
                    f"{alt_greeting} iş birliği imkanlarını değerlendirmek adına uygun olduğunuz bir gün 5 dakikalık bir görüşme ayarlayabilir miyiz?"
                )

        return MessageRecommendationResponse(
            lead_id=lead_id,
            lead_name=clean_lead_name if clean_lead_name else "İşletme",
            target_category=target_category,
            business_goal=business_goal,
            strategy_summary=strategy_summary,
            recommended_message=recommended_message,
            alternative_message=alternative_message
        )

    @classmethod
    def generate_campaign_message(
        cls,
        communication_goal: str,
        target_category: Optional[str] = None,
        offer_title: Optional[str] = None,
        key_benefit: Optional[str] = None,
        extra_information: Optional[str] = None,
        preferred_channel: Optional[str] = None,
        lead_need: Optional[str] = None,
        specific_question: Optional[str] = None,
        pricing_info: Optional[str] = None,
        meeting_purpose: Optional[str] = None,
        previous_topic: Optional[str] = None,
        language: str = "tr",
        variation_seed: Optional[int] = None
    ) -> Tuple[str, str]:
        """
        Generates a natural, highly tailored B2B outreach message for campaign creation.
        Returns: (generated_message, strategy_summary)
        """
        lang = language.lower() if language else "tr"
        goal = communication_goal.upper().strip()
        cat = target_category.strip() if target_category else ("{category}" if lang == "tr" else "{category}")
        variant_idx = (variation_seed or 0) % 2

        if lang == "en":
            greeting_a = "{Hello|Hi|Greetings} {name},"
            greeting_b = "{Dear|Hello} {name},"
            greeting = greeting_b if variant_idx == 1 else greeting_a

            if goal == "FIRST_CONTACT":
                summary = f"First contact introduction for {cat}"
                if offer_title:
                    intro_part = f"We would like to introduce ourselves and share how our {offer_title} solutions"
                    extra_part = f" {extra_information}." if extra_information else " If you are available, we would be pleased to share a brief overview."
                    msg = f"{greeting}\n\n{intro_part} support {cat} businesses.{extra_part}\n\nBest regards."
                else:
                    msg = f"{greeting}\n\nWe would like to introduce ourselves and briefly share details about our specialized solutions for {cat}. If you are available, we can provide a quick overview.\n\nBest regards."

            elif goal == "SERVICE_PROMOTION":
                summary = f"Product/Service promotion highlighting key benefits for {cat}"
                prod = offer_title or "our specialized solutions"
                ben = f" regarding {key_benefit}" if key_benefit else " and tailored operational advantages"
                extra_part = f" {extra_information}." if extra_information else " Please let us know if you would like us to send a brief overview."
                msg = f"{greeting}\n\nFor your {cat} operations, we provide {prod}{ben}.{extra_part}\n\nBest regards."

            elif goal == "DISCOVERY":
                summary = f"Needs discovery and open question approach for {cat}"
                prod = offer_title or "modern workflow solutions"
                need = lead_need or "an external solution partner or specialized workflow"
                quest = f" {specific_question}" if specific_question else " We would be glad to share quick information if you are available."
                msg = f"{greeting}\n\nRegarding {prod}, in your {cat} operations, do you currently experience a need for {need}?{quest}\n\nBest regards."

            elif goal == "OFFER":
                summary = f"Commercial offer and value proposition for {cat}"
                prod = offer_title or "our enterprise package"
                summ = f" featuring {key_benefit}" if key_benefit else ""
                ben = f" We provide {key_benefit}." if key_benefit else ""
                price = f" ({pricing_info})" if pricing_info else ""
                msg = f"{greeting}\n\nWe would like to present our tailored commercial offer for {prod}{price} designed for {cat} businesses{summ}.{ben} Can we share a quick overview when convenient?\n\nBest regards."

            elif goal == "MEETING":
                summary = f"Meeting/demo invitation for {cat}"
                prod = offer_title or "our solutions"
                purp = meeting_purpose or "explore potential cost advantages and workflow fit"
                chan = preferred_channel or "a brief 5-minute introductory call"
                msg = f"{greeting}\n\nCould we schedule {chan} this week to discuss how {prod} can benefit your {cat} operations regarding {purp}?\n\nBest regards."

            elif goal == "FOLLOW_UP":
                summary = f"Polite follow-up message for {cat}"
                prev = previous_topic or "our previous conversation"
                upd = key_benefit or "see if you had a chance to review the details"
                extra_part = f" {extra_information}." if extra_information else ""
                msg = f"{greeting}\n\nI just wanted to follow up on {prev} to {upd}.{extra_part} Please let us know if you have any questions.\n\nBest regards."

            else:
                summary = f"General B2B outreach for {cat}"
                msg = f"{greeting}\n\nWe would like to introduce ourselves and share details about our business solutions for {cat}. Please let us know if you are available for a quick overview.\n\nBest regards."

        else:
            # TURKISH
            greeting_a = "{Merhaba|İyi günler|Selamlar} {name},"
            greeting_b = "{Selamlar|Merhaba} {name},"
            greeting = greeting_b if variant_idx == 1 else greeting_a

            if goal == "FIRST_CONTACT":
                summary = f"{cat} sektörü için ilk temas ve tanışma stratejisi"
                if offer_title:
                    intro_part = f"Firmanızla tanışmak ve {cat} alanındaki faaliyetleriniz için sunduğumuz {offer_title} hakkında"
                    extra_part = f" {extra_information}." if extra_information else " Uygunsanız size kısaca bahsedebiliriz."
                    msg = f"{greeting}\n\n{intro_part} kısaca bilgi paylaşmak istedik.{extra_part}\n\nSaygılarımızla."
                else:
                    msg = f"{greeting}\n\nFirmanızla tanışmak ve {cat} alanındaki faaliyetlerinize yönelik sunduğumuz çözümler hakkında kısaca bilgi paylaşmak istedik. Uygunsanız size kısaca bahsedebiliriz.\n\nSaygılarımızla."

            elif goal == "SERVICE_PROMOTION":
                summary = f"{cat} sektörü için ürün/hizmet tanıtımı ve fayda odaklı yaklaşım"
                prod = offer_title or "kurumsal çözümlerimiz"
                ben = f" {key_benefit} avantajları" if key_benefit else " iş süreçlerinizi kolaylaştıran çözümler"
                extra_part = f" {extra_information}." if extra_information else " İncelemek isterseniz detaylı ürün ve hizmet bilgilerimizi iletebiliriz."
                msg = f"{greeting}\n\n{cat} faaliyetlerinizde {prod} konusunda{ben} sağlıyoruz.{extra_part}\n\nİyi çalışmalar."

            elif goal == "DISCOVERY":
                summary = f"{cat} sektörü için ihtiyaç keşfi ve soru odaklı strateji"
                prod = offer_title or "bu alandaki operasyonlarınız"
                need = lead_need or "dış çözüm ortağı ihtiyacınız veya kullandığınız mevcut bir sistem"
                quest = f" {specific_question}" if specific_question else " Uygun olursanız kısa bilgi paylaşabiliriz."
                msg = f"{greeting}\n\n{cat} sektöründeki operasyonlarınızda {prod} konusunda {need} bulunuyor mu?{quest}\n\nİyi çalışmalar."

            elif goal == "OFFER":
                summary = f"{cat} sektörü için ticari teklif ve fiyat/avantaj sunumu"
                prod = offer_title or "özel hizmet paketi"
                summ = f" ({key_benefit})" if key_benefit else ""
                price = f" Fiyat ve avantaj detayları: {pricing_info}." if pricing_info else ""
                msg = f"{greeting}\n\n{cat} işletmelerine özel hazırladığımız avantajlı {prod}{summ} teklifimizi değerlendirmeniz için iletmek isteriz.{price} Uygun bir zamanınızda kısa bilgi paylaşabilir miyiz?\n\nSaygılarımızla."

            elif goal == "MEETING":
                summary = f"{cat} sektörü için randevu ve kısa görüşme talebi"
                prod = offer_title or "çözümlerimiz"
                purp = meeting_purpose or "işletmenize sağlayacağı verimlilik avantajlarını değerlendirmek"
                chan = preferred_channel or "bu hafta 5 dakikalık kısa bir görüşme"
                msg = f"{greeting}\n\n{cat} alanındaki {prod} tarafında {purp} adına {chan} organize edebilir miyiz?\n\nİyi çalışmalar."

            elif goal == "FOLLOW_UP":
                summary = f"{cat} sektörü için takip ve durum kontrolü"
                prev = previous_topic or "önceki bilgilendirmemiz"
                upd = key_benefit or "Değerlendirme fırsatınız oldu mu?"
                extra_part = f" {extra_information}." if extra_information else ""
                msg = f"{greeting}\n\n{prev} ile ilgili kısa bir durum kontrolü yapmak istedim. {upd}{extra_part}\n\nİyi çalışmalar."

            else:
                summary = f"{cat} sektörü için genel B2B iletişim stratejisi"
                msg = f"{greeting}\n\n{cat} alanındaki faaliyetlerinize yönelik kurumsal çözümlerimiz hakkında kısa bilgi paylaşmak istedik. Uygunsanız size kısaca bahsedebiliriz.\n\nİyi çalışmalar."

        return msg, summary

