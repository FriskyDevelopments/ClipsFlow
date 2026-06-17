import { Pool } from 'pg';

let pool: Pool | null = null;

export function getDb() {
  if (!pool) {
    if (!process.env.DATABASE_URL) {
      console.warn('DATABASE_URL is not set. Database operations will fail.');
    }
    pool = new Pool({
      connectionString: process.env.DATABASE_URL,
    });
  }
  return pool;
}
