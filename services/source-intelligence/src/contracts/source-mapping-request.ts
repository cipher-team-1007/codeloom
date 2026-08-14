export interface RuntimeEvidence {
  ruleId: string;
  targetSelector: string;
  htmlSnippet: string;
}

export interface SourceMappingRequest {
  repositoryPath: string;
  commitSha: string;
  runtimeEvidence: RuntimeEvidence;
}

