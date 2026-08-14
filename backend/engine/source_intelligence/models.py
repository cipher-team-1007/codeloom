from typing import List, Optional
from pydantic import BaseModel, Field


class RuntimeEvidence(BaseModel):
    ruleId: str
    targetSelector: str
    htmlSnippet: str


class SourceMappingRequest(BaseModel):
    repositoryPath: str
    commitSha: str
    runtimeEvidence: RuntimeEvidence


class SourceLocation(BaseModel):
    line: int
    column: int


class SourceRange(BaseModel):
    start: SourceLocation


class SourceCandidate(BaseModel):
    file: str
    component: str
    element: str
    sourceRange: SourceRange
    score: int
    signals: List[str] = Field(default_factory=list)


class ParserMetadata(BaseModel):
    filesScanned: int
    elementsIndexed: int


class SourceMappingResult(BaseModel):
    status: str  # 'MATCHED' | 'AMBIGUOUS' | 'NOT_FOUND'
    findingId: Optional[str] = None
    candidates: List[SourceCandidate] = Field(default_factory=list)
    parserMetadata: Optional[ParserMetadata] = None
