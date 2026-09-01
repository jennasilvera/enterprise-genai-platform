from pathlib import Path

from enterprise_genai.data.universe import build_universe

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPOSITORY_ROOT / "data" / "raw" / "structured" / "northstar_v1_universe.json"


def main() -> None:
    universe = build_universe()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    serialized = universe.model_dump_json(indent=2) + "\n"
    OUTPUT_PATH.write_text(serialized, encoding="utf-8")

    print(f"dataset_version: {universe.metadata.dataset_version}")
    print(f"companies: {len(universe.companies)}")
    print(f"customers: {len(universe.customers)}")
    print(f"suppliers: {len(universe.suppliers)}")
    print(f"company_customer_relationships: {len(universe.company_customers)}")
    print(f"company_supplier_relationships: {len(universe.company_suppliers)}")
    print(f"geographic_exposures: {len(universe.geographic_exposures)}")
    print(f"risks: {len(universe.risks)}")
    print(f"transactions: {len(universe.transactions)}")
    print(f"wrote: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
