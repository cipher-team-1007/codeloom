import fs from 'fs';
import path from 'path';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const ts = require('typescript');

function parseSourceFiles(dir, fileList = []) {
  const files = fs.readdirSync(dir);
  for (const file of files) {
  const filePath = path.join(dir, file);
  if (fs.statSync(filePath).isDirectory()) {
    parseSourceFiles(filePath, fileList);
  } else if (filePath.endsWith('.tsx') || filePath.endsWith('.ts')) {
    fileList.push(filePath);
  }
  }
  return fileList;
}

function extractAttributes(node) {
  const attributes = {};
  if (node.attributes && node.attributes.properties) {
  for (const prop of node.attributes.properties) {
    if (ts.isJsxAttribute(prop)) {
    const name = prop.name.getText();
    if (prop.initializer) {
      if (ts.isStringLiteral(prop.initializer)) {
      attributes[name] = { type: 'literal', value: prop.initializer.text };
      } else if (ts.isJsxExpression(prop.initializer)) {
       if (prop.initializer.expression && ts.isTemplateExpression(prop.initializer.expression)) {
        const head = prop.initializer.expression.head.text;
        attributes[name] = { type: 'dynamic', value: head.trim() }; 
       } else if (prop.initializer.expression && ts.isNoSubstitutionTemplateLiteral(prop.initializer.expression)) {
        attributes[name] = { type: 'dynamic', value: prop.initializer.expression.text };
       } else {
        attributes[name] = { type: 'dynamic', value: prop.initializer.expression.getText() };
       }
      }
    } else {
      attributes[name] = { type: 'boolean', value: true };
    }
    }
  }
  }
  return attributes;
}

function traverseAST(node, sourceFile, elements, parentChain = []) {
  if (ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)) {
  const tagName = node.tagName.getText();
  const attributes = extractAttributes(node);
  const { line, character } = ts.getLineAndCharacterOfPosition(sourceFile, node.getStart());

  let componentName = "Unknown";
  for (const parent of parentChain.reverse()) {
     if (ts.isFunctionDeclaration(parent) && parent.name) {
       componentName = parent.name.getText();
       break;
     } else if (ts.isVariableDeclaration(parent) && parent.name) {
       componentName = parent.name.getText();
       break;
     }
  }

  elements.push({
    file: sourceFile.fileName,
    component: componentName,
    tagName: tagName.toLowerCase(),
    attributes,
    location: { line: line + 1, column: character + 1 },
    parentTags: parentChain.filter(p => ts.isJsxOpeningElement(p)).map(p => p.tagName.getText().toLowerCase())
  });
  }

  const newChain = [...parentChain, node];
  ts.forEachChild(node, child => traverseAST(child, sourceFile, elements, newChain));
}

function matchCandidates(finding, sourceElements) {
  const snippet = finding.htmlSnippets[0] || '';
  const matchTag = snippet.match(/^<([a-zA-Z0-9-]+)/);
  const tagName = matchTag ? matchTag[1].toLowerCase() : null;

  const matchClass = snippet.match(/class=["']([^"']+)["']/);
  const classes = matchClass ? matchClass[1].split(' ') : [];

  const matchSrc = snippet.match(/src=["']([^"']+)["']/);
  const src = matchSrc ? matchSrc[1] : null;

  const candidates = [];

  for (const el of sourceElements) {
  if (tagName && el.tagName !== tagName) continue; 

  let score = 0;
  const signals = [`+ tag match: ${el.tagName}`];

  if (classes.length > 0 && el.attributes.className) {
     const sourceClass = el.attributes.className.value;
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
     }
  }

  if (tagName === 'img' && src) {
    if (el.attributes.src) {
       score += 1;
       signals.push(`+ attribute match: src present`);
    }
  }

  candidates.push({
     ...el,
     score,
     signals
  });
  }

  candidates.sort((a, b) => b.score - a.score);

  const validCandidates = candidates.filter(c => c.score > 0);

  let resultType = "NO MATCH";
  if (validCandidates.length > 0) {
    if (validCandidates.length > 1 && validCandidates[0].score === validCandidates[1].score) {
      resultType = "AMBIGUOUS";
    } else {
      resultType = "MATCH FOUND";
    }
  }

  return {
  findingId: finding.ruleId,
  snippet,
  resultType,
  candidates: validCandidates.slice(0, 3) 
  };
}

function run() {
  const sourceFiles = parseSourceFiles(path.resolve('./fixture/src'));
  const elements = [];

  for (const filePath of sourceFiles) {
  const code = fs.readFileSync(filePath, 'utf8');
  const sourceFile = ts.createSourceFile(
    filePath,
    code,
    99, 
    true,
    4 
  );
  traverseAST(sourceFile, sourceFile, elements);
  }

  const findings = JSON.parse(fs.readFileSync('./findings.json', 'utf8'));
  const results = findings.map(f => matchCandidates(f, elements));

  fs.writeFileSync('ast_results.json', JSON.stringify(results, null, 2));
  console.log(`Evaluated ${findings.length} findings.`);
}

run();

