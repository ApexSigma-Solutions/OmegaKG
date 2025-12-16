Project Style Rules

General

Async/Await: Always use async/await instead of raw Promises or callbacks.

Error Handling: All external API calls and database interactions must be wrapped in try/catch blocks.

Logging: Use the project's standardized Logger class. Do not use print() or console.log.

TypeScript / JavaScript

Types: Strict typing is required. The use of any is strictly forbidden unless absolutely necessary (and must be commented).

Immutability: Prefer const over let. Avoid var entirely.

Python

Type Hints: All function signatures must include type hints (PEP 484).

Docstrings: Use Google Style docstrings for all public modules, functions, classes, and methods.