import { AstElement } from '../parser/ast-types.js';
import { RuntimeEvidence, SourceCandidate } from '../contracts/index.js';

export class CandidateGenerator {

  public generateCandidates(evidence: RuntimeEvidence, sourceElements: AstElement[]): SourceCandidate[] {
  const snippet = evidence.htmlSnippet;

  const matchTag = snippet.match(/^<([a-zA-Z0-9-]+)/);
  const tagName = matchTag ? matchTag[1].toLowerCase() : null;

  const matchClass = snippet.match(/class=["']([^"']+)["']/);
  const classes = matchClass ? matchClass[1].split(' ') : [];

  const matchSrc = snippet.match(/src=["']([^"']+)["']/);
  const src = matchSrc ? matchSrc[1] : null;

  const candidates: SourceCandidate[] = [];

  for (const el of sourceElements) {
    if (tagName && el.tagName !== tagName) continue; 

    let score = 0;
    const signals: string[] = [`+ tag match: ${el.tagName}`];

    if (classes.length > 0 && el.attributes.className) {
     const sourceClass = String(el.attributes.className.value);
     let classMatched = false;
     for (const cls of classes) {
       if (sourceClass.includes(cls)) {
         score += 2;
         signals.push(`+ class match: ${cls}`);
         classMatched = true;
       }
     }
     if (el.attributes.className.type === 'dynamic') {
       signals.push(`+ matched dynamic class structure`);
       if (!classMatched) {
        score += 1;
       }
     }
    }

    if (tagName === 'img' && src) {
      if (el.attributes.src) {
       score += 1;
       signals.push(`+ attribute match: src present`);
      }
    }

    candidates.push({
     file: el.file,
     component: el.component,
     element: el.tagName,
     sourceRange: {
       start: el.location
     },
     score,
     signals
    });
  }

  return candidates;
  }
}

