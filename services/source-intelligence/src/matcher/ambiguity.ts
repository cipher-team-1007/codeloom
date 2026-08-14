import { SourceCandidate, SourceMappingStatus } from '../contracts/index.js';

export function rankAndResolveAmbiguity(candidates: SourceCandidate[]): { status: SourceMappingStatus, topCandidates: SourceCandidate[] } {
  const validCandidates = candidates.filter(c => c.score > 0);

  if (validCandidates.length === 0) {
  return { status: 'NOT_FOUND', topCandidates: [] };
  }

  validCandidates.sort((a, b) => b.score - a.score);

  if (validCandidates.length > 1) {
  const highestScore = validCandidates[0].score;
  const tiedCandidates = validCandidates.filter(c => c.score === highestScore);

  if (tiedCandidates.length > 1) {
    return { status: 'AMBIGUOUS', topCandidates: tiedCandidates };
  }
  }

  return { status: 'MATCHED', topCandidates: [validCandidates[0]] };
}

