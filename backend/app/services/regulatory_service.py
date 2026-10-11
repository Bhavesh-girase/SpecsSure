import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.models.regulation import Regulation
from app.models.certification import CertificationRecord
from app.schemas.analysis import CertificationInfo

logger = logging.getLogger(__name__)

class RegulatoryService:
    @staticmethod
    async def check_certification_requirements(
        is_numbers: List[str], 
        product_description: Optional[str], 
        db: AsyncSession
    ) -> List[CertificationInfo]:
        """
        Queries Regulation and Certification tables for compulsory certification mandates (QCO/CRS/ISI).
        Returns a list of CertificationInfo objects for each evaluated standard.
        """
        if not is_numbers:
            return []

        # Load all regulations
        stmt = select(Regulation)
        res = await db.execute(stmt)
        regulations = res.scalars().all()
        
        cert_info_list: List[CertificationInfo] = []
        
        for is_num in is_numbers:
            clean_is = is_num.split(":")[0].strip() # e.g. "IS 269" from "IS 269:2015"
            matched_reg = None
            
            for reg in regulations:
                if reg.standard_ids and any(clean_is.lower() in str(s).lower() for s in reg.standard_ids):
                    matched_reg = reg
                    break
                # Also check product scope match if text matches
                elif reg.product_scope and product_description and (reg.product_scope.lower() in product_description.lower() or product_description.lower() in reg.product_scope.lower()):
                    matched_reg = reg
                    break

            if matched_reg:
                cert_info_list.append(CertificationInfo(
                    is_number=is_num,
                    standard_title=matched_reg.title,
                    is_mandatory=matched_reg.is_mandatory or "yes",
                    scheme=matched_reg.regulation_type or "BIS ISI Mark",
                    qco_reference=matched_reg.notification_number or matched_reg.title,
                    issuing_authority=matched_reg.issuing_authority or "Government of India / BIS",
                    effective_from=matched_reg.effective_from.strftime("%Y-%m-%d") if matched_reg.effective_from else None,
                    verification_state="verified_regulation",
                    note=f"Compulsory certification mandated under {matched_reg.title}. All bidders must possess a valid BIS license."
                ))
            else:
                # Default non-mandatory or voluntary standard note
                cert_info_list.append(CertificationInfo(
                    is_number=is_num,
                    standard_title="Indian Standard",
                    is_mandatory="no",
                    scheme="Voluntary / Standard BIS Certification Scheme",
                    qco_reference=None,
                    issuing_authority="Bureau of Indian Standards",
                    effective_from=None,
                    verification_state="not_found",
                    note="No mandatory Quality Control Order (QCO) identified for this specific standard in the current registry. Verification on the BIS CARE portal is recommended for latest gazette notifications."
                ))
                
        return cert_info_list

regulatory_service = RegulatoryService()
