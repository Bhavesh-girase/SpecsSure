import os
import json
import glob
import asyncio
import logging
from sqlalchemy import select
from app.db.session import async_session_maker
from app.models.product_ontology import ProductCategory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_ontology")

async def seed_product_ontology():
    ontology_dir = os.path.join(os.path.dirname(__file__), "..", "data", "product_ontology")
    json_files = glob.glob(os.path.join(ontology_dir, "*.json"))

    if not json_files:
        logger.warning(f"No JSON ontology files found in {ontology_dir}")
        return

    async with async_session_maker() as session:
        for fpath in json_files:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                cat_name = data.get("category_name")
                if not cat_name:
                    continue

                # Check if exists
                stmt = select(ProductCategory).where(ProductCategory.category_name == cat_name)
                res = await session.execute(stmt)
                existing = res.scalars().first()

                if existing:
                    existing.bis_division = data.get("bis_division")
                    existing.bis_section_committee = data.get("bis_section_committee")
                    existing.primary_standard_is = data.get("primary_standard_is")
                    existing.parameter_template = data.get("parameter_template", {})
                    existing.keywords = data.get("keywords")
                    logger.info(f"Updated product ontology category: {cat_name}")
                else:
                    new_cat = ProductCategory(
                        category_name=cat_name,
                        bis_division=data.get("bis_division"),
                        bis_section_committee=data.get("bis_section_committee"),
                        primary_standard_is=data.get("primary_standard_is"),
                        parameter_template=data.get("parameter_template", {}),
                        keywords=data.get("keywords")
                    )
                    session.add(new_cat)
                    logger.info(f"Inserted product ontology category: {cat_name}")

                await session.commit()
            except Exception as e:
                logger.error(f"Error seeding ontology from {fpath}: {e}")
                await session.rollback()

if __name__ == "__main__":
    asyncio.run(seed_product_ontology())
