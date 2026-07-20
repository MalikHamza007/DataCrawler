from app.collectors.google_places.query_generator import generate_project_queries
from app.schemas.map_config import ProjectSearchConfig


def config(types: list[str]) -> ProjectSearchConfig:
    return ProjectSearchConfig(search_mode="zone", zone_id="gulberg", radius_meters=5000, project_types=types)


def test_project_queries_are_deterministic_and_include_lahore_zone() -> None:
    first = generate_project_queries(config(["apartments", "commercial", "mixed_use"]), max_queries=10)
    second = generate_project_queries(config(["apartments", "commercial", "mixed_use"]), max_queries=10)
    assert first == second
    assert first[:3] == [
        ("apartment project in Gulberg Lahore", "apartments"),
        ("commercial project in Gulberg Lahore", "commercial"),
        ("mixed use project in Gulberg Lahore", "mixed_use"),
    ]
    assert all("Lahore" in query for query, _ in first)
    assert all("Gulberg" in query for query, _ in first)


def test_queries_exist_for_core_project_types_and_limit_is_respected() -> None:
    queries = generate_project_queries(
        config(["housing_society", "shopping_mall", "business_center", "villas", "plot_development", "project_sales_office", "other"]),
        max_queries=5,
    )
    assert len(queries) == 5
    assert len({query for query, _ in queries}) == len(queries)
    assert any("housing society" in query for query, _ in queries)


def test_arbitrary_user_query_text_is_not_part_of_schema() -> None:
    fields = ProjectSearchConfig.model_fields
    assert "query" not in fields
    assert "textQuery" not in fields
