
from pydantic import BaseModel, Field, AliasChoices, ConfigDict, field_validator
from typing import List, Literal


class TestCase(BaseModel):

    model_config = ConfigDict(populate_by_name=True)

    test_id: str = Field(
        validation_alias=AliasChoices("test_id", "test_case_id")
    )

    scenario: str = Field(
        validation_alias=AliasChoices("scenario", "title")
    )

    objective: str = Field(
        default="Validate the functionality described in the scenario."
    )

    test_type: Literal[
        "Positive",
        "Negative",
        "Boundary",
        "Security"
    ]

    preconditions: str
    test_steps: List[str]
    test_data: str
    expected_result: str

    priority: Literal["High", "Medium", "Low"]


class TestSuite(BaseModel):

    test_cases: List[TestCase]

    ambiguities: List[str] = Field(default_factory=list)

    @field_validator("ambiguities", mode="before")
    @classmethod
    def normalize_ambiguities(cls, value):

        if value is None:
            return []

        if isinstance(value, str):
            return [value]

        if isinstance(value, list):
            normalized = []

            for item in value:

                if isinstance(item, dict):
                    issue = item.get("issue", "Requirement ambiguity")
                    description = item.get("description", "")

                    normalized.append(
                        f"{issue}: {description}"
                    )

                else:
                    normalized.append(str(item))

            return normalized

        return [str(value)]
