from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator

Mode = Literal["business", "awareness", "audit", "deals"]
Language = Literal["hindi", "marathi", "tamil", "telugu", "bengali", "kannada", "english"]
DOCUMENT_TYPES = {"business": "Business Requirements Document", "awareness": "Public Advisory / Circular", "audit": "Field Inspection Report", "deals": "Commercial Purchase Agreement"}

class Rule(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=500)
    condition: str = Field(min_length=1, max_length=3000)
    action: str = Field(min_length=1, max_length=3000)
    exception: str | None = None
    confidence: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    type: str = "requirement"
    source_quote: str = ""
    numbers: list[dict] = Field(default_factory=list, max_length=50)
    speaker: str | None = Field(default=None, max_length=100)
    evidence_id: str | None = None
    start: float | None = Field(default=None, ge=0)
    end: float | None = Field(default=None, ge=0)
    approved_at: str | None = None
    approved_by: str | None = None

    @model_validator(mode="after")
    def valid_range(self):
        if (self.start is None) != (self.end is None):
            raise ValueError("Clip start and end must be supplied together")
        if self.start is not None and (self.end <= self.start or not self.evidence_id):
            raise ValueError("A clip needs evidence and an increasing time range")
        return self

class Answer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    key: str = Field(min_length=1, max_length=40)
    answer: str = Field(min_length=1, max_length=5000)
    question: str = Field(default="", max_length=1000)
    speaker: str | None = Field(default=None, max_length=100)

class CompileIn(BaseModel):
    rules: list[Rule] = Field(default_factory=list, max_length=100)
    domain: str = Field(default="", max_length=500)
    mode: Mode = "business"
    metadata: dict[str, str] = Field(default_factory=dict)
    demo: bool = False
    transcript: str = Field(default="", max_length=100000)
    answers: list[Answer] = Field(default_factory=list, max_length=50)
    # AI-drafted sections (re-verified against the transcript before use) and coverage/conflict results.
    sections: dict[str, list[dict]] | None = None
    acceptance: list[dict] = Field(default_factory=list, max_length=300)
    coverage: list[dict] = Field(default_factory=list, max_length=50)
    conflicts: list[dict] = Field(default_factory=list, max_length=50)
    # Language of the generated app's interface, and optional Sarvam translations of BRD lines (for bilingual exports).
    app_language: Language = "english"
    translations: dict[str, str] = Field(default_factory=dict, max_length=600)
