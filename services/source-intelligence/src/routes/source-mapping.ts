import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { SourceMappingService } from '../services/source-mapping-service.js';
import { SourceMappingRequest } from '../contracts/index.js';

export async function sourceMappingRoutes(fastify: FastifyInstance) {
  const service = new SourceMappingService();

  fastify.post('/v1/source-mappings', async (request: FastifyRequest, reply: FastifyReply) => {
  const payload = request.body as any;

  if (!payload.repositoryPath || !payload.commitSha || !payload.runtimeEvidence) {
    return reply.status(400).send({ error: 'INVALID_REQUEST', message: 'Missing required fields' });
  }

  if (!payload.runtimeEvidence.ruleId || !payload.runtimeEvidence.htmlSnippet) {
     return reply.status(400).send({ error: 'INVALID_REQUEST', message: 'Missing required runtime evidence fields' });
  }

  try {
    const result = await service.mapSource(payload as SourceMappingRequest);
    return reply.send(result);
  } catch (err: any) {
    if (err.message.includes('INVALID_REPOSITORY_PATH')) {
    return reply.status(400).send({ error: 'INVALID_REPOSITORY_PATH', message: err.message });
    }
    if (err.message.includes('SOURCE_ROOT_VIOLATION')) {
    return reply.status(403).send({ error: 'SOURCE_ROOT_VIOLATION', message: err.message });
    }
    fastify.log.error(err);
    return reply.status(500).send({ error: 'INTERNAL_ERROR', message: 'An internal parser error occurred' });
  }
  });

  fastify.get('/health', async (request: FastifyRequest, reply: FastifyReply) => {
  return reply.send({ status: 'ok', service: 'source-intelligence' });
  });
}

