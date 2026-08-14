import ts from 'typescript';
import { AstElement, AstAttribute } from './ast-types.js';

function extractAttributes(node: ts.JsxOpeningElement | ts.JsxSelfClosingElement): Record<string, AstAttribute> {
  const attributes: Record<string, AstAttribute> = {};
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
        attributes[name] = { type: 'dynamic', value: prop.initializer.expression ? prop.initializer.expression.getText() : '' };
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

export function parseFileAst(sourceFile: ts.SourceFile, elements: AstElement[], parentChain: ts.Node[] = []) {
  const traverseAST = (node: ts.Node, chain: ts.Node[]) => {
  if (ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)) {
    const tagName = node.tagName.getText();
    const attributes = extractAttributes(node);
    const { line, character } = ts.getLineAndCharacterOfPosition(sourceFile, node.getStart());

    let componentName = "Unknown";
    for (const parent of [...chain].reverse()) {
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
    parentTags: chain.filter(ts.isJsxOpeningElement).map(p => p.tagName.getText().toLowerCase())
    });
  }

  const newChain = [...chain, node];
  ts.forEachChild(node, child => traverseAST(child, newChain));
  };

  traverseAST(sourceFile, parentChain);
}

