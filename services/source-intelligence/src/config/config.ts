import os from 'os';
import path from 'path';

const defaultRepoRoot = process.env.SOURCE_REPOSITORY_ROOT
  || path.join(os.tmpdir(), 'accessifix_workspaces');

export const config = {
  port: parseInt(process.env.PORT || '8001', 10),
  host: process.env.HOST || '0.0.0.0',
  sourceRepositoryRoot: defaultRepoRoot,
  env: process.env.NODE_ENV || 'development'
};

