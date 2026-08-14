import Fastify from 'fastify';
import { sourceMappingRoutes } from './routes/source-mapping.js';
import { config } from './config/config.js';

export function buildServer() {
  const fastify = Fastify({
  logger: true
  });

  fastify.register(sourceMappingRoutes);

  return fastify;
}

const start = async () => {
  if (process.argv[1] && process.argv[1].endsWith('server.ts') || process.argv[1] && process.argv[1].endsWith('server.js')) {
  const server = buildServer();
  try {
    await server.listen({ port: config.port, host: config.host });
    console.log(`Source Intelligence service running at http://${config.host}:${config.port}`);
  } catch (err) {
    server.log.error(err);
    process.exit(1);
  }
  }
};

start();

