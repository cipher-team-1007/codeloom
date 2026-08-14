export type SourceMappingStatus = 'MATCHED' | 'AMBIGUOUS' | 'NOT_FOUND';

export interface SourceLocation {
  line: number;
  column: number;
}

export interface SourceRange {
  start: SourceLocation;
}

export interface SourceCandidate {
  file: string;
  component: string;
  element: string;
  sourceRange: SourceRange;
  score: number;
  signals: string[];
}

export interface ParserMetadata {
  filesScanned: number;
  elementsIndexed: number;
}

export interface SourceMappingResult {
  status: SourceMappingStatus;
  findingId?: string;
  candidates: SourceCandidate[];
  parserMetadata?: ParserMetadata;
}

