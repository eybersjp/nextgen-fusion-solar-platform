/**
 * local server entry file, for local development
 */
import dotenv from 'dotenv';
import app from './app.js';

// Load environment variables
dotenv.config();

/**
 * start server with port
 */
const PORT = process.env.PORT || 3002;

const server = app.listen(PORT, () => {
  console.log(`Server ready on port ${PORT}`);
});

/**
 * close server
 */
process.on('SIGTERM', () => {
  console.log('SIGTERM signal received');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('SIGINT signal received');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

export default app;