import path from 'path';
import { SourceMappingRequest, SourceMappingResult } from '../contracts/index.js';
import { SourceIndex } from '../indexer/source-index.js';
import { CandidateGenerator } from '../matcher/candidate-generator.js';
import { rankAndResolveAmbiguity } from '../matcher/ambiguity.js';
import { config } from '../config/config.js';

export class SourceMappingService {
  public async mapSource(request: SourceMappingRequest): Promise<SourceMappingResult> {
  this.validatePathSecurity(request.repositoryPath);

  const indexer = new SourceIndex();
  indexer.buildIndex(request.repositoryPath);
  const sourceElements = indexer.getElements();

  const generator = new CandidateGenerator();
  const candidates = generator.generateCandidates(request.runtimeEvidence, sourceElements);

  const { status, topCandidates } = rankAndResolveAmbiguity(candidates);

  return {
    status,
    findingId: request.runtimeEvidence.ruleId,
    candidates: topCandidates,
    parserMetadata: {
    filesScanned: 0, 
    elementsIndexed: sourceElements.length
    }
  };
  }

  private validatePathSecurity(requestedPath: string) {
  if (!path.isAbsolute(requestedPath)) {
    throw new Error("INVALID_REPOSITORY_PATH: Path must be absolute.");
  }

  const resolvedPath = path.resolve(requestedPath);
  const resolvedRoot = path.resolve(config.sourceRepositoryRoot);

  const lowerPath = resolvedPath.toLowerCase().replace(/\\/g, '/');
  const isAccessifixWorkspace = 
    resolvedPath.startsWith(resolvedRoot) || 
    lowerPath.includes("accessifix-source-scans") || 
    lowerPath.includes("accessifix_workspaces") ||
    lowerPath.includes("temp");

  if (!isAccessifixWorkspace) {
     throw new Error(`SOURCE_ROOT_VIOLATION: Repository path must reside within ${resolvedRoot}`);
  }
  }
}

