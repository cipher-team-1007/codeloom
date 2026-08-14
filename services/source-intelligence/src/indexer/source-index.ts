import fs from 'fs';
import path from 'path';
import ts from 'typescript';
import { AstElement } from '../parser/ast-types.js';
import { parseFileAst } from '../parser/tsx-parser.js';

export class SourceIndex {
  private elements: AstElement[] = [];

  public getElements(): AstElement[] {
  return this.elements;
  }

  public buildIndex(dir: string) {
  this.elements = [];
  const files = this.findSourceFiles(dir);

  for (const filePath of files) {
    const code = fs.readFileSync(filePath, 'utf8');
    const sourceFile = ts.createSourceFile(
    filePath,
    code,
    99, 
    true,
    4 
    );
    parseFileAst(sourceFile, this.elements);
  }
  }

  private findSourceFiles(dir: string, fileList: string[] = []): string[] {
  const files = fs.readdirSync(dir);
  for (const file of files) {
    const filePath = path.join(dir, file);

    if (file === 'node_modules' || file === '.git' || file === 'dist' || file === 'build') {
    continue;
    }

    if (fs.statSync(filePath).isDirectory()) {
    this.findSourceFiles(filePath, fileList);
    } else if (filePath.endsWith('.tsx') || filePath.endsWith('.ts') || filePath.endsWith('.jsx')) {
    fileList.push(filePath);
    }
  }
  return fileList;
  }
}

