"""
Data-access layer. Repositories contain *only* queries; every function that
reads or mutates user-owned data takes `candidate_id` and filters on it so
ownership is enforced in SQL, not after the fact.
"""
