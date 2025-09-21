-- Database initialization script for Scheduler Service
-- This script sets up the initial database schema

-- Create database if it doesn't exist (PostgreSQL syntax)
SELECT 'CREATE DATABASE scheduler_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'scheduler_db')\gexec

-- Connect to the scheduler database
\c scheduler_db;

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- The actual tables will be created by Alembic migrations
-- This file is here for any additional database setup if needed
