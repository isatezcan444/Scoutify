import re
import random
from typing import Dict, Any, List, Set

class SpintaxService:
    """
    Advanced Spintax Engine supporting nested variations and dynamic variable injection.
    Example Spintax: "{Merhaba|Selamlar|İyi günler} {name} Yetkilisi, {city} bölgesindeki {category}..."
    """

    SPINTAX_REGEX = re.compile(r'\{([^{}]+)\}')
    VARIABLE_REGEX = re.compile(r'\{([a-zA-Z0-9_]+)\}')

    @classmethod
    def spin(cls, text: str) -> str:
        """
        Recursively resolves all spintax {option1|option2|...} patterns.
        """
        if not text:
            return ""
        
        while True:
            match = cls.SPINTAX_REGEX.search(text)
            if not match:
                break
            
            # Check if this is a spintax with pipe or a simple variable placeholder
            content = match.group(1)
            if '|' in content:
                choices = content.split('|')
                chosen = random.choice(choices)
                text = text[:match.start()] + chosen + text[match.end():]
            else:
                # Temporary token protection for single variable placeholders like {name}
                # so inner spintax doesn't break them
                token = f"__VAR_TOKEN_{match.start()}_{match.end()}__"
                text = text[:match.start()] + token + text[match.end():]
                # Re-spin the rest, then we will restore variables later
                sub_res = cls.spin(text)
                return sub_res.replace(token, f"{{{content}}}")

        return text

    @classmethod
    def render_template(cls, template: str, lead_data: Dict[str, Any]) -> str:
        """
        Resolves Spintax first, then substitutes dynamic lead variables:
        {name}, {category}, {city}, {district}, {address}, {rating}, {website}, {phone}
        """
        # Step 1: Spin variations
        spun_text = cls.spin(template)

        # Step 2: Inject Lead Variables
        variables = {
            "name": lead_data.get("name") or "Yetkili",
            "category": lead_data.get("category") or "İşletme",
            "city": lead_data.get("city") or "bölgeniz",
            "district": lead_data.get("district") or "",
            "address": lead_data.get("address") or "",
            "rating": str(lead_data.get("rating") or ""),
            "website": lead_data.get("website") or "",
            "phone": lead_data.get("phone") or "",
        }

        for var_name, var_value in variables.items():
            spun_text = spun_text.replace(f"{{{var_name}}}", str(var_value))

        # Clean multiple spaces and normalize line breaks
        cleaned_text = re.sub(r'[ \t]+', ' ', spun_text)
        return cleaned_text.strip()

    @classmethod
    def calculate_permutations(cls, template: str) -> int:
        """
        Calculates total unique message combinations possible from a spintax template.
        """
        total = 1
        matches = cls.SPINTAX_REGEX.findall(template)
        for match in matches:
            if '|' in match:
                choices = match.split('|')
                total *= len(choices)
        return total

    @classmethod
    def generate_preview_samples(cls, template: str, count: int = 5, sample_lead: Dict[str, Any] = None) -> List[str]:
        """
        Generates distinct preview samples for the user in the UI.
        """
        if not sample_lead:
            sample_lead = {
                "name": "Örnek Diş Kliniği",
                "category": "Diş Kliniği",
                "city": "İstanbul",
                "district": "Ümraniye",
                "rating": "4.8",
                "website": "www.ornekdis.com",
                "phone": "+905321234567"
            }
            
        samples: Set[str] = set()
        for _ in range(count * 3): # try up to 3x to find unique variations
            rendered = cls.render_template(template, sample_lead)
            samples.add(rendered)
            if len(samples) >= count:
                break
                
        return list(samples)
