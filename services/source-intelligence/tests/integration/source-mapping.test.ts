import supertest from 'supertest';
import { buildServer } from '../../src/server.js';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootPath = path.resolve(__dirname, '../../../../');
const fixturePath = path.join(rootPath, 'experiments/source-mapping/fixture/src');

describe('Source Intelligence API', () => {
  let app: any;

  beforeAll(async () => {
  app = buildServer();
  await app.ready();
  });

  afterAll(async () => {
  await app.close();
  });

  it('GET /health returns 200 OK', async () => {
  const response = await supertest(app.server).get('/health');
  expect(response.status).toBe(200);
  expect(response.body).toEqual({ status: 'ok', service: 'source-intelligence' });
  });

  it('POST /v1/source-mappings correctly identifies an EXACT MATCH (Case 1)', async () => {
  const response = await supertest(app.server)
    .post('/v1/source-mappings')
    .send({
    repositoryPath: fixturePath,
    commitSha: 'fake-commit-sha',
    runtimeEvidence: {
      ruleId: 'image-alt',
      targetSelector: 'img.product-image',
      htmlSnippet: '<img class="product-image" src="/placeholder1.jpg">'
    }
    });

  expect(response.status).toBe(200);
  expect(response.body.status).toBe('MATCHED');
  expect(response.body.candidates.length).toBeGreaterThan(0);
  expect(response.body.candidates[0].file.endsWith('ProductCard.tsx')).toBe(true);
  expect(response.body.candidates[0].score).toBe(3);
  });

  it('POST /v1/source-mappings correctly identifies an AMBIGUOUS MATCH (Case 5)', async () => {
  const response = await supertest(app.server)
    .post('/v1/source-mappings')
    .send({
    repositoryPath: fixturePath,
    commitSha: 'fake-commit-sha',
    runtimeEvidence: {
      ruleId: 'image-alt',
      targetSelector: 'img.ambiguous-image',
      htmlSnippet: '<img class="ambiguous-image" src="/profile.jpg">'
    }
    });

  expect(response.status).toBe(200);
  expect(response.body.status).toBe('AMBIGUOUS');
  expect(response.body.candidates.length).toBeGreaterThan(1);
  expect(response.body.candidates[0].score).toBe(response.body.candidates[1].score);
  });

  it('POST /v1/source-mappings correctly identifies NOT_FOUND', async () => {
  const response = await supertest(app.server)
    .post('/v1/source-mappings')
    .send({
    repositoryPath: fixturePath,
    commitSha: 'fake-commit-sha',
    runtimeEvidence: {
      ruleId: 'image-alt',
      targetSelector: 'unknown-tag.does-not-exist',
      htmlSnippet: '<unknown-tag class="does-not-exist"></unknown-tag>'
    }
    });

  expect(response.status).toBe(200);
  expect(response.body.status).toBe('NOT_FOUND');
  expect(response.body.candidates.length).toBe(0);
  });

  it('POST /v1/source-mappings enforces path security (Traversal attempt)', async () => {
  const response = await supertest(app.server)
    .post('/v1/source-mappings')
    .send({
    repositoryPath: '/etc/passwd',
    commitSha: 'fake-commit-sha',
    runtimeEvidence: {
      ruleId: 'image-alt',
      targetSelector: 'img',
      htmlSnippet: '<img>'
    }
    });

  expect(response.status).toBe(403);
  expect(response.body.error).toBe('SOURCE_ROOT_VIOLATION');
  });
});