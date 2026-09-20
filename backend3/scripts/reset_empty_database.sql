-- Delete all ConceptBridge data while keeping every table and index.
-- Run this against runtime/conceptbridge.db in a SQLite client.
BEGIN TRANSACTION;

DELETE FROM learning_gains;
DELETE FROM evaluations;
DELETE FROM sessions;
DELETE FROM candidate_decisions;
DELETE FROM match_history;
DELETE FROM candidates;
DELETE FROM transitions;
DELETE FROM runs;
DELETE FROM edges;
DELETE FROM answers;
DELETE FROM questions;
DELETE FROM concept_scores;
DELETE FROM concepts;
DELETE FROM students;

COMMIT;
